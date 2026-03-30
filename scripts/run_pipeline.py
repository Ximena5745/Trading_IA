"""
Script: scripts/run_pipeline.py
Responsibility: Full multi-asset trading pipeline with APScheduler.
  Data sources:
    - Crypto  (BTCUSDT, ETHUSDT)      → BinanceClient
    - Forex   (EURUSD … USDCAD)       → MT5Client (IC Markets)
    - Indices (US500, US30, UK100)    → MT5Client (IC Markets)
    - Commodity (XAUUSD)              → MT5Client (IC Markets)

  Decision routing per cycle:
    1. MarketCalendar.is_market_open()       → skip if market closed
    2. FundamentalAgent.is_blocked_by_event()→ skip if macro event window ±30 min
    3. Fetch OHLCV (Binance or MT5)
    4. Features → Agents → Consensus (weights conditional on asset_class)
    5. Risk validation + position sizing (InstrumentConfig-aware)
    6. Execute (PaperExecutor paper mode / MT5Executor live mode)
    7. Persist + Alert

Usage:
  python scripts/run_pipeline.py                  # starts scheduler (runs forever)
  python scripts/run_pipeline.py --once EURUSD    # one cycle and exit (testing)
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
from core.ingestion.market_calendar import MarketCalendar
from core.models import AssetClass, AgentOutput, MarketData, MarketRegime, RegimeOutput, detect_asset_class, get_instrument
from core.monitoring.alert_engine import AlertEngine
from core.notifications.telegram_bot import TelegramBot
from core.observability.logger import configure_logging, get_logger
from core.portfolio.portfolio_manager import PortfolioManager
from core.risk.kill_switch import KillSwitch
from core.risk.risk_manager import RiskManager
from core.signals.signal_engine import SignalEngine

configure_logging()
logger = get_logger("pipeline")

# ── Schedule: all 12 symbols, staggered every 5 min throughout the hour ──────
SCHEDULE: list[tuple[str, int]] = [
    # Crypto — Binance
    ("BTCUSDT", 0),
    ("ETHUSDT", 5),
    # Forex majors — MT5 / IC Markets
    ("EURUSD",  10),
    ("GBPUSD",  15),
    ("USDJPY",  20),
    ("AUDUSD",  25),
    ("USDCHF",  30),
    ("USDCAD",  35),
    # Commodity — MT5
    ("XAUUSD",  40),
    # Indices — MT5
    ("US500",   45),
    ("US30",    50),
    ("UK100",   55),
]

# Model paths — TechnicalAgent falls back to rule-based if file does not exist
MODEL_CRYPTO = "data/models/technical_crypto_v1.pkl"
MODEL_FOREX  = "data/models/technical_forex_v1.pkl"

HISTORY_CANDLES = 250


# ── Helpers ───────────────────────────────────────────────────────────────────

def _market_data_to_df(candles: list[MarketData], symbol: str) -> pd.DataFrame:
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
    signal_allowed = (
        agent_output.score > -0.9
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
    start = datetime.now(timezone.utc)
    asset_class = detect_asset_class(symbol)
    is_crypto   = asset_class == AssetClass.CRYPTO

    logger.info("cycle_start", symbol=symbol, asset_class=asset_class.value)

    try:
        binance: BinanceClient           = components["binance"]
        mt5_client                       = components.get("mt5_client")   # may be None
        feature_engine: FeatureEngine    = components["feature_engine"]
        tech_agent_crypto: TechnicalAgent = components["tech_agent_crypto"]
        tech_agent_mt5: TechnicalAgent    = components["tech_agent_mt5"]
        regime_agent: RegimeAgent         = components["regime_agent"]
        micro_agent: MicrostructureAgent  = components["micro_agent"]
        fund_agent: FundamentalAgent      = components["fund_agent"]
        consensus: ConsensusEngine        = components["consensus"]
        signal_engine: SignalEngine       = components["signal_engine"]
        risk: RiskManager                 = components["risk"]
        executor_paper: PaperExecutor     = components["executor_paper"]
        mt5_executor                      = components.get("mt5_executor")
        portfolio: PortfolioManager       = components["portfolio"]
        feature_store: FeatureStore       = components["feature_store"]
        repo: TradingRepository           = components["repo"]
        alert: AlertEngine                = components["alert"]
        calendar: MarketCalendar          = components["calendar"]

        # ── Gate 1: Market open check ─────────────────────────────────────────
        if not calendar.is_market_open(symbol):
            logger.info("cycle_skipped_market_closed", symbol=symbol)
            return

        # ── Gate 2: Macro event window check (non-crypto only) ────────────────
        if not is_crypto and fund_agent.is_blocked_by_event(symbol):
            logger.info("cycle_skipped_macro_event", symbol=symbol)
            return

        # ── Gate 3: MT5 client availability for non-crypto ───────────────────
        if not is_crypto and mt5_client is None:
            logger.warning(
                "cycle_skipped_mt5_not_configured",
                symbol=symbol,
                hint="Set MT5_LOGIN, MT5_PASSWORD, MT5_SERVER in .env",
            )
            return

        # ── 1. Fetch OHLCV ────────────────────────────────────────────────────
        if is_crypto:
            candles = await binance.get_historical_klines(symbol, "1h", HISTORY_CANDLES)
        else:
            candles = await mt5_client.get_historical_klines(symbol, "1h", HISTORY_CANDLES)

        if not candles:
            logger.warning("no_candles_returned", symbol=symbol)
            return

        df = _market_data_to_df(candles, symbol)

        # ── 2. Features ───────────────────────────────────────────────────────
        features = feature_engine.calculate(df)

        # ── 3. Order book enrichment (Binance crypto only — MT5 has no L2) ───
        if is_crypto:
            try:
                order_book = await binance.get_order_book(symbol, depth=20)
                micro_data = micro_agent.analyze_order_book(order_book)
                features = features.model_copy(update=micro_data)
            except Exception:
                pass  # microstructure optional

        # ── 4. Agents ─────────────────────────────────────────────────────────
        tech_agent   = tech_agent_crypto if is_crypto else tech_agent_mt5
        tech_output  = tech_agent.predict(features)
        regime_output = regime_agent.predict(features)
        micro_output  = micro_agent.predict(features)

        # ── 5. Consensus (weights conditional on asset_class) ─────────────────
        regime_gate   = _make_regime_gate(regime_output, features)
        consensus_out = consensus.aggregate(
            [tech_output, regime_output, micro_output], regime_gate
        )

        # ── 6. Signal ─────────────────────────────────────────────────────────
        signal = signal_engine.generate(consensus_out, features, strategy_id="default_v1")
        if signal is None:
            logger.info("no_signal", symbol=symbol, reason="neutral_or_filtered")
            return

        # ── 7. Risk validation ────────────────────────────────────────────────
        portfolio_state = portfolio.get_portfolio()
        approved, reason = risk.validate_signal(
            signal.model_dump(), portfolio_state.model_dump()
        )
        if not approved:
            logger.info("signal_rejected_by_risk", symbol=symbol, reason=reason)
            return

        # ── 8. Position sizing (InstrumentConfig-aware for MT5) ───────────────
        instrument = get_instrument(symbol) if not is_crypto else None
        quantity = risk.calculate_position_size(
            signal.model_dump(),
            portfolio_state.model_dump(),
            instrument=instrument,
        )
        if quantity <= 0:
            logger.warning("zero_quantity", symbol=symbol)
            return

        # ── 9. Execution ──────────────────────────────────────────────────────
        settings = components["settings"]
        if (
            not is_crypto
            and mt5_executor is not None
            and settings.EXECUTION_MODE == "live"
            and settings.TRADING_ENABLED
        ):
            order = await mt5_executor.execute(signal.model_dump(), quantity)
        else:
            order = await executor_paper.execute(signal.model_dump(), quantity)

        # ── 10. Portfolio update ──────────────────────────────────────────────
        portfolio.open_position(signal, quantity, order["fill_price"])
        new_state = portfolio.get_portfolio()
        risk.update_kill_switch(new_state.model_dump(), [])

        # ── 11. Persist ───────────────────────────────────────────────────────
        await feature_store.save(features)
        await repo.save_signal(signal)
        await repo.save_order(order)
        await repo.save_portfolio_snapshot(new_state)

        # ── 12. Alert ─────────────────────────────────────────────────────────
        await alert.on_signal(signal)

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        logger.info(
            "cycle_complete",
            symbol=symbol,
            asset_class=asset_class.value,
            signal=signal.action,
            confidence=signal.confidence,
            quantity=quantity,
            elapsed_s=round(elapsed, 2),
        )

    except Exception as exc:
        logger.error("cycle_error", symbol=symbol, error=str(exc), exc_info=True)
        await components["alert"].on_critical_error("pipeline_cycle", f"{symbol}: {exc}")


# ── Bootstrap ─────────────────────────────────────────────────────────────────

async def _build_components(settings) -> dict:
    # ── Binance ───────────────────────────────────────────────────────────────
    binance = BinanceClient(
        api_key=settings.BINANCE_API_KEY,
        secret_key=settings.BINANCE_SECRET_KEY,
        testnet=settings.BINANCE_TESTNET,
    )
    await binance.connect()

    # ── MT5 (optional — skip if not configured) ───────────────────────────────
    mt5_client   = None
    mt5_executor = None

    if settings.MT5_LOGIN != 0 and settings.MT5_PASSWORD:
        try:
            from core.ingestion.providers.mt5_client import MT5Client
            from core.execution.mt5_executor import MT5Executor

            mt5_client = MT5Client(
                server=settings.MT5_SERVER,
                login=settings.MT5_LOGIN,
                password=settings.MT5_PASSWORD,
            )
            await mt5_client.connect()
            logger.info("mt5_connected", server=settings.MT5_SERVER, login=settings.MT5_LOGIN)

            kill_switch_temp = KillSwitch(settings)
            mt5_executor = MT5Executor(settings, kill_switch_temp, mt5_client)

        except Exception as exc:
            logger.warning(
                "mt5_connection_failed",
                error=str(exc),
                hint="MT5 symbols will be skipped this session",
            )
            mt5_client   = None
            mt5_executor = None
    else:
        logger.warning(
            "mt5_not_configured",
            hint="Set MT5_LOGIN, MT5_PASSWORD, MT5_SERVER in .env to enable forex/indices",
        )

    # ── MarketCalendar ────────────────────────────────────────────────────────
    calendar = MarketCalendar()
    await calendar.refresh_events()

    # ── Shared components ─────────────────────────────────────────────────────
    feature_store = FeatureStore(redis_url=settings.REDIS_URL)
    await feature_store.connect()

    kill_switch = KillSwitch(settings)
    portfolio   = PortfolioManager(settings=settings, initial_capital=10_000.0)
    risk        = RiskManager(settings=settings, kill_switch=kill_switch)

    telegram = TelegramBot(token=settings.TELEGRAM_BOT_TOKEN, chat_id=settings.TELEGRAM_CHAT_ID)
    alert    = AlertEngine(telegram_bot=telegram)

    fund_agent = FundamentalAgent()
    await fund_agent.refresh()

    components = {
        "settings":          settings,
        "binance":           binance,
        "mt5_client":        mt5_client,
        "mt5_executor":      mt5_executor,
        "calendar":          calendar,
        "feature_engine":    FeatureEngine(feature_version=settings.FEATURE_VERSION),
        # Two TechnicalAgent instances — each with its own model path
        # Both fall back to rule-based scoring if the .pkl does not exist yet
        "tech_agent_crypto": TechnicalAgent(model_path=MODEL_CRYPTO),
        "tech_agent_mt5":    TechnicalAgent(model_path=MODEL_FOREX),
        "regime_agent":      RegimeAgent(),
        "micro_agent":       MicrostructureAgent(),
        "fund_agent":        fund_agent,
        "consensus":         ConsensusEngine(),
        "signal_engine":     SignalEngine(),
        "risk":              risk,
        "executor_paper":    PaperExecutor(),
        "portfolio":         portfolio,
        "feature_store":     feature_store,
        "repo":              TradingRepository(),
        "alert":             alert,
    }

    mt5_symbols = [s for s, _ in SCHEDULE if detect_asset_class(s) != AssetClass.CRYPTO]
    crypto_symbols = [s for s, _ in SCHEDULE if detect_asset_class(s) == AssetClass.CRYPTO]
    logger.info(
        "components_initialized",
        crypto_symbols=crypto_symbols,
        mt5_symbols=mt5_symbols if mt5_client else [],
        mt5_available=mt5_client is not None,
    )
    return components


async def _teardown(components: dict) -> None:
    try:
        await components["binance"].disconnect()
    except Exception:
        pass
    if components.get("mt5_client"):
        try:
            components["mt5_client"].disconnect()
        except Exception:
            pass
    await close_pool()


# ── Scheduler ─────────────────────────────────────────────────────────────────

async def run_scheduler(settings) -> None:
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        print("❌ APScheduler not installed. Run: pip install apscheduler")
        sys.exit(1)

    await init_pool(settings.DATABASE_URL)
    components = await _build_components(settings)

    # Refresh ForexFactory events every 4 hours
    async def _refresh_calendar():
        await components["calendar"].refresh_events()

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

    # Calendar refresh at :02 every 4 hours
    scheduler.add_job(
        _refresh_calendar,
        trigger=CronTrigger(hour="0,4,8,12,16,20", minute=2, timezone="UTC"),
        id="calendar_refresh",
        name="ForexFactory calendar refresh",
    )

    scheduler.start()
    total = len(SCHEDULE)
    print(f"✅ Scheduler activo. {total} símbolos programados (2 crypto + 10 MT5). Ctrl+C para detener.")
    logger.info("scheduler_started", total_symbols=total, schedule=SCHEDULE)

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        await _teardown(components)
        logger.info("scheduler_stopped")


# ── CLI ───────────────────────────────────────────────────────────────────────

async def run_once(symbol: str, settings) -> None:
    await init_pool(settings.DATABASE_URL)
    components = await _build_components(settings)
    try:
        await _pipeline_cycle(symbol, components)
    finally:
        await _teardown(components)


def main() -> None:
    parser = argparse.ArgumentParser(description="TRADER AI — Multi-Asset Signal Pipeline")
    parser.add_argument(
        "--once",
        metavar="SYMBOL",
        help="Run one cycle for SYMBOL and exit. E.g.: --once EURUSD",
    )
    args = parser.parse_args()
    settings = get_settings()

    if args.once:
        print(f"▶ Running single cycle for {args.once}...")
        asyncio.run(run_once(args.once, settings))
    else:
        print("▶ Starting multi-asset pipeline scheduler...")
        asyncio.run(run_scheduler(settings))


if __name__ == "__main__":
    main()
