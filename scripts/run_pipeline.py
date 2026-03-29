"""
Script: scripts/run_pipeline.py
Responsibility: Full trading pipeline with APScheduler.
  Chains all modules: ingest → features → agents → consensus → risk → execute → persist → alert.

Usage:
  python scripts/run_pipeline.py                # starts scheduler (runs forever)
  python scripts/run_pipeline.py --once BTCUSDT # runs one cycle and exits (for testing)

Scheduler config (EXECUTION_OFFSETS):
  BTCUSDT → every 60 min at :00
  ETHUSDT → every 60 min at :05 (offset avoids simultaneous load)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agents.fundamental_agent import FundamentalAgent
from core.agents.microstructure_agent import MicrostructureAgent
from core.agents.regime_agent import RegimeAgent
from core.agents.technical_agent import TechnicalAgent
from core.config.settings import get_settings
from core.consensus.voting_engine import ConsensusEngine
from core.db.repository import TradingRepository
from core.db.session import close_pool, init_pool
from core.execution.paper_executor import PaperExecutor
from core.features.feature_engineering import FeatureEngine
from core.features.feature_store import FeatureStore
from core.ingestion.binance_client import BinanceClient
from core.models import AgentOutput, MarketData, MarketRegime, RegimeOutput
from core.monitoring.alert_engine import AlertEngine
from core.notifications.telegram_bot import TelegramBot
from core.observability.logger import configure_logging, get_logger
from core.portfolio.portfolio_manager import PortfolioManager
from core.risk.kill_switch import KillSwitch
from core.risk.risk_manager import RiskManager
from core.signals.signal_engine import SignalEngine

configure_logging()
logger = get_logger("pipeline")

# ── Symbols and schedule offsets (minutes past the hour) ──────────────────────
SCHEDULE: list[tuple[str, int]] = [
    ("BTCUSDT", 0),   # :00 of each hour
    ("ETHUSDT", 5),   # :05 of each hour
]

HISTORY_CANDLES = 250   # candles fetched per cycle (enough for all indicators)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _market_data_to_df(candles: list[MarketData], symbol: str) -> pd.DataFrame:
    """Convert list[MarketData] to the DataFrame format FeatureEngine expects."""
    rows = [
        {
            "timestamp": c.timestamp,
            "symbol":    c.symbol,
            "open":      float(c.open),
            "high":      float(c.high),
            "low":       float(c.low),
            "close":     float(c.close),
            "volume":    float(c.volume),
        }
        for c in candles
    ]
    return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)


def _make_regime_gate(agent_output: AgentOutput, features) -> RegimeOutput:
    """Build a minimal RegimeOutput for the ConsensusEngine gate."""
    signal_allowed = (
        agent_output.score > -0.9          # not VOLATILE_CRASH
        and agent_output.confidence >= 0.50
    )
    regime = MarketRegime.VOLATILE_CRASH if not signal_allowed else (
        MarketRegime.BULL_TRENDING  if agent_output.score >= 0.5  else
        MarketRegime.BEAR_TRENDING  if agent_output.score <= -0.5 else
        MarketRegime.SIDEWAYS_LOW_VOL
    )
    return RegimeOutput(
        timestamp=features.timestamp,
        symbol=features.symbol,
        regime=regime,
        confidence=agent_output.confidence,
        regime_duration_bars=1,
        signal_allowed=signal_allowed,
    )


# ── Core pipeline cycle ───────────────────────────────────────────────────────

async def _pipeline_cycle(symbol: str, components: dict) -> None:
    """Execute one full pipeline cycle for a symbol. Errors are caught and logged."""
    start = datetime.now(timezone.utc)
    logger.info("cycle_start", symbol=symbol)

    try:
        binance: BinanceClient     = components["binance"]
        feature_engine: FeatureEngine     = components["feature_engine"]
        tech_agent: TechnicalAgent        = components["tech_agent"]
        regime_agent: RegimeAgent         = components["regime_agent"]
        micro_agent: MicrostructureAgent  = components["micro_agent"]
        fund_agent: FundamentalAgent      = components["fund_agent"]
        consensus: ConsensusEngine        = components["consensus"]
        signal_engine: SignalEngine       = components["signal_engine"]
        risk: RiskManager                 = components["risk"]
        executor: PaperExecutor           = components["executor"]
        portfolio: PortfolioManager       = components["portfolio"]
        feature_store: FeatureStore       = components["feature_store"]
        repo: TradingRepository           = components["repo"]
        alert: AlertEngine                = components["alert"]

        # 1. Fetch market data
        candles = await binance.get_historical_klines(symbol, "1h", HISTORY_CANDLES)
        if not candles:
            logger.warning("no_candles_returned", symbol=symbol)
            return
        df = _market_data_to_df(candles, symbol)

        # 2. Calculate features
        features = feature_engine.calculate(df)

        # 3. Enrich features with order book (microstructure)
        try:
            order_book = await binance.get_order_book(symbol, depth=20)
            micro_data = micro_agent.analyze_order_book(order_book)
            features = features.model_copy(update=micro_data)
        except Exception:
            pass  # microstructure is optional; continues without it

        # 4. Run agents
        tech_output    = tech_agent.predict(features)
        regime_output  = regime_agent.predict(features)
        micro_output   = micro_agent.predict(features)

        # 5. Consensus (regime gate derived from regime agent output)
        regime_gate = _make_regime_gate(regime_output, features)
        consensus_out = consensus.aggregate(
            [tech_output, regime_output, micro_output], regime_gate
        )

        # 6. Generate signal
        signal = signal_engine.generate(consensus_out, features, strategy_id="default_v1")
        if signal is None:
            logger.info("no_signal", symbol=symbol, reason="neutral_or_filtered")
            return

        # 7. Risk validation
        portfolio_state = portfolio.get_portfolio()
        approved, reason = risk.validate_signal(signal.model_dump(), portfolio_state.model_dump())
        if not approved:
            logger.info("signal_rejected_by_risk", symbol=symbol, reason=reason)
            return

        # 8. Position sizing + execution
        quantity = risk.calculate_position_size(signal.model_dump(), portfolio_state.model_dump())
        if quantity <= 0:
            logger.warning("zero_quantity", symbol=symbol)
            return

        order = await executor.execute(signal.model_dump(), quantity)

        # 9. Update portfolio state
        portfolio.open_position(signal, quantity, order["fill_price"])

        # 10. Update kill switch checks
        new_state = portfolio.get_portfolio()
        risk.update_kill_switch(new_state.model_dump(), [])

        # 11. Persist to Redis + PostgreSQL
        await feature_store.save(features)
        await repo.save_signal(signal)
        await repo.save_order(order)
        await repo.save_portfolio_snapshot(new_state)

        # 12. Alert
        await alert.on_signal(signal)

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        logger.info("cycle_complete", symbol=symbol, signal=signal.action,
                    confidence=signal.confidence, elapsed_s=round(elapsed, 2))

    except Exception as exc:
        logger.error("cycle_error", symbol=symbol, error=str(exc), exc_info=True)
        await components["alert"].on_critical_error("pipeline_cycle", f"{symbol}: {exc}")


# ── Bootstrap (initialize all components once) ────────────────────────────────

async def _build_components(settings) -> dict:
    binance = BinanceClient(
        api_key=settings.BINANCE_API_KEY,
        secret_key=settings.BINANCE_SECRET_KEY,
        testnet=settings.BINANCE_TESTNET,
    )
    await binance.connect()

    feature_store = FeatureStore(redis_url=settings.REDIS_URL)
    await feature_store.connect()

    kill_switch = KillSwitch(settings)
    portfolio   = PortfolioManager(settings=settings, initial_capital=10_000.0)
    risk        = RiskManager(settings=settings, kill_switch=kill_switch)

    telegram = TelegramBot(token=settings.TELEGRAM_BOT_TOKEN, chat_id=settings.TELEGRAM_CHAT_ID)
    alert    = AlertEngine(telegram_bot=telegram)

    fund_agent = FundamentalAgent()
    await fund_agent.refresh()   # prime the cache before first cycle

    components = {
        "binance":        binance,
        "feature_engine": FeatureEngine(feature_version=settings.FEATURE_VERSION),
        "tech_agent":     TechnicalAgent(),
        "regime_agent":   RegimeAgent(),
        "micro_agent":    MicrostructureAgent(),
        "fund_agent":     fund_agent,
        "consensus":      ConsensusEngine(),
        "signal_engine":  SignalEngine(),
        "risk":           risk,
        "executor":       PaperExecutor(),
        "portfolio":      portfolio,
        "feature_store":  feature_store,
        "repo":           TradingRepository(),
        "alert":          alert,
    }
    logger.info("components_initialized")
    return components


async def _teardown(components: dict) -> None:
    try:
        await components["binance"].disconnect()
    except Exception:
        pass
    await close_pool()


# ── Scheduler (APScheduler) ───────────────────────────────────────────────────

async def run_scheduler(settings) -> None:
    """Start APScheduler and run the pipeline for each symbol on schedule."""
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        print("❌ APScheduler not installed. Run: pip install apscheduler")
        sys.exit(1)

    await init_pool(settings.DATABASE_URL)
    components = await _build_components(settings)

    scheduler = AsyncIOScheduler(timezone="UTC")
    for symbol, minute_offset in SCHEDULE:
        scheduler.add_job(
            _pipeline_cycle,
            trigger=CronTrigger(minute=minute_offset, timezone="UTC"),
            args=[symbol, components],
            id=f"pipeline_{symbol}",
            name=f"Pipeline {symbol}",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=120,
        )
        logger.info("job_scheduled", symbol=symbol, minute_offset=minute_offset)

    scheduler.start()
    logger.info("scheduler_started", jobs=len(SCHEDULE))
    print(f"✅ Scheduler activo. {len(SCHEDULE)} símbolos programados. Ctrl+C para detener.")

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        await _teardown(components)
        logger.info("scheduler_stopped")


# ── CLI ───────────────────────────────────────────────────────────────────────

async def run_once(symbol: str, settings) -> None:
    """Run a single pipeline cycle (for testing/debugging)."""
    await init_pool(settings.DATABASE_URL)
    components = await _build_components(settings)
    try:
        await _pipeline_cycle(symbol, components)
    finally:
        await _teardown(components)


def main() -> None:
    parser = argparse.ArgumentParser(description="TRADER AI — Signal Pipeline")
    parser.add_argument("--once", metavar="SYMBOL",
                        help="Run one cycle for SYMBOL and exit (e.g. --once BTCUSDT)")
    args = parser.parse_args()

    settings = get_settings()

    if args.once:
        print(f"▶ Running single cycle for {args.once}...")
        asyncio.run(run_once(args.once, settings))
    else:
        print("▶ Starting pipeline scheduler...")
        asyncio.run(run_scheduler(settings))


if __name__ == "__main__":
    main()
