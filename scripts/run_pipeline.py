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
from uuid import uuid4

import pandas as pd

try:
    import structlog

    _bind_ctx = structlog.contextvars.bind_contextvars
    _clear_ctx = structlog.contextvars.clear_contextvars
except Exception:  # noqa: BLE001 — structlog optional
    def _bind_ctx(**_kw):  # type: ignore
        return None

    def _clear_ctx(*_a, **_kw):  # type: ignore
        return None

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agents.fundamental_agent import FundamentalAgent
from core.agents.microstructure_agent import MicrostructureAgent
from core.agents.regime_agent import RegimeAgent
from core.agents.technical_agent import TechnicalAgent
from core.config.constants import TRADED_UNIVERSE, has_market_data
from core.config.settings import get_settings
from core.consensus.voting_engine import ConsensusEngine
from core.db.repository import TradingRepository
from core.db.session import close_pool, init_pool
from core.execution.paper_executor import PaperExecutor
from core.features.feature_engineering import FeatureEngine
from core.features.feature_store import FeatureStore
from core.ingestion.binance_client import BinanceClient
from core.ingestion.market_calendar import MarketCalendar
from core.models import (
    AssetClass,
    AgentOutput,
    MarketData,
    MarketRegime,
    RegimeOutput,
    detect_asset_class,
    get_instrument,
)
from core.compliance.audit_system import AuditEntry, AuditLog
from core.infrastructure.scheduler_lock import SchedulerLock
from core.monitoring.alert_engine import AlertEngine
from core.monitoring.prometheus_metrics import pipeline_cycles_total
from core.observability.decision_tracer import get_trace_store
from core.notifications.telegram_bot import TelegramBot
from core.observability.logger import configure_logging, get_logger
from core.bootstrap import create_kill_switch, create_order_tracker, create_portfolio_manager
from core.risk.risk_manager import RiskManager
from core.signals.signal_engine import SignalEngine
from core.strategies.approved_params import load_approved_strategy
from core.strategies.strategy_registry import StrategyRegistry

configure_logging()
logger = get_logger("pipeline")

# ── Schedule — DERIVED from core.config.constants.TRADED_UNIVERSE (SPEC-B03) ──
# One cycle per symbol per hour, staggered evenly across the hour. Adding or
# removing a symbol is done in constants.TRADED_UNIVERSE, never here.
_STAGGER_MIN = max(1, 60 // len(TRADED_UNIVERSE))
SCHEDULE: list[tuple[str, int]] = [
    (symbol, (idx * _STAGGER_MIN) % 60)
    for idx, symbol in enumerate(TRADED_UNIVERSE)
]

# Model paths — TechnicalAgent falls back to rule-based if file does not exist
MODEL_CRYPTO = "data/models/technical_crypto_v1.pkl"
MODEL_FOREX = "data/models/technical_forex_v1.pkl"

HISTORY_CANDLES = 250


# ── Helpers ───────────────────────────────────────────────────────────────────


def _market_data_to_df(candles: list[MarketData], symbol: str) -> pd.DataFrame:
    rows = [
        {
            "timestamp": c.timestamp,
            "symbol": c.symbol,
            "open": float(c.open),
            "high": float(c.high),
            "low": float(c.low),
            "close": float(c.close),
            "volume": float(c.volume),
        }
        for c in candles
    ]
    return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)


def _strategy_confirms(spec, df: pd.DataFrame, params: dict, action: str) -> tuple[bool, float]:
    """The I1-approved strategy must not contradict the consensus direction.

    Returns (confirmed, last_signal_value). Fail-closed: any error computing the
    validated signal ⇒ not confirmed (ADR-005 — anything driving execution is
    fail-safe). A flat (0) strategy signal does NOT veto.
    """
    try:
        merged = {**getattr(spec, "defaults", {}), **(params or {})}
        series = spec.signal_fn(df, merged)
        last = float(series.iloc[-1]) if len(series) else 0.0
    except Exception as exc:  # noqa: BLE001
        logger.warning("strategy_confirm_error", error=str(exc))
        return False, 0.0
    want_long = action == "BUY"
    if last != 0.0 and (last > 0) != want_long:
        return False, last
    return True, last


def _make_regime_gate(agent_output: AgentOutput, features) -> RegimeOutput:
    signal_allowed = agent_output.score > -0.9 and agent_output.confidence >= 0.50
    regime = (
        MarketRegime.VOLATILE_CRASH
        if not signal_allowed
        else (
            MarketRegime.BULL_TRENDING
            if agent_output.score >= 0.5
            else MarketRegime.BEAR_TRENDING
            if agent_output.score <= -0.5
            else MarketRegime.SIDEWAYS_LOW_VOL
        )
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
    is_crypto = asset_class == AssetClass.CRYPTO

    logger.info("cycle_start", symbol=symbol, asset_class=asset_class.value)
    try:
        pipeline_cycles_total.labels(symbol=symbol).inc()
    except Exception:  # noqa: BLE001 — metrics must never break a cycle
        pass

    # ── Gate 0: data availability (SPEC-B03) ──────────────────────────────────
    if not has_market_data(symbol):
        logger.warning(
            "cycle_skipped_no_data",
            symbol=symbol,
            data_available=False,
            hint="no 1h parquet in data/raw/ and not a live-crypto symbol",
        )
        return

    # ── Gate 0b: approved strategy (SPEC-B06 / ADR-003 — fail-safe quant) ─────
    # No data/models/i1_params/<symbol>.json ⇒ the I1 gate has NOT approved an
    # edge for this symbol ⇒ it does not emit signals.
    approved = load_approved_strategy(symbol)
    if approved is None:
        logger.info(
            "no_approved_strategy",
            symbol=symbol,
            hint="run the I1 gate; needs data/models/i1_params/%s.json" % symbol.upper(),
        )
        return

    # ── Decision trace (SPEC-B04 / F-06) ────────────────────────────────────
    correlation_id = str(uuid4())
    _bind_ctx(correlation_id=correlation_id, symbol=symbol)
    tracer = components.get("tracer") or get_trace_store()
    audit: AuditLog | None = components.get("audit")

    def _decide(entity_id: str, result: str, **details) -> None:
        tracer.record(correlation_id, "risk_check", {"result": result, **details})
        if audit is not None:
            try:
                audit.append(
                    AuditEntry(
                        timestamp=datetime.now(timezone.utc),
                        user_id="pipeline",
                        action_type="signal_decision",
                        details={"symbol": symbol, **details},
                        entity_type="signal",
                        entity_id=entity_id,
                        result=result,
                        metadata={"correlation_id": correlation_id},
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("audit_append_failed", error=str(exc))

    try:
        binance: BinanceClient = components["binance"]
        mt5_client = components.get("mt5_client")  # may be None
        feature_engine: FeatureEngine = components["feature_engine"]
        tech_agent_crypto: TechnicalAgent = components["tech_agent_crypto"]
        tech_agent_mt5: TechnicalAgent = components["tech_agent_mt5"]
        regime_agent: RegimeAgent = components["regime_agent"]
        micro_agent: MicrostructureAgent = components["micro_agent"]
        fund_agent: FundamentalAgent = components["fund_agent"]
        consensus: ConsensusEngine = components["consensus"]
        signal_engine: SignalEngine = components["signal_engine"]
        risk: RiskManager = components["risk"]
        executor_paper: PaperExecutor = components["executor_paper"]
        mt5_executor = components.get("mt5_executor")
        portfolio: PortfolioManager = components["portfolio"]
        strategy_registry: StrategyRegistry = components["strategy_registry"]
        feature_store: FeatureStore = components["feature_store"]
        repo: TradingRepository = components["repo"]
        alert: AlertEngine = components["alert"]
        calendar: MarketCalendar = components["calendar"]

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
            candles = await binance.get_klines(symbol, "1h", HISTORY_CANDLES)
        else:
            candles = await mt5_client.get_klines(symbol, "1h", HISTORY_CANDLES)

        if not candles:
            logger.warning("no_candles_returned", symbol=symbol)
            return

        df = _market_data_to_df(candles, symbol)
        tracer.record(
            correlation_id,
            "market_data",
            {"symbol": symbol, "candles": len(df),
             "last_close": float(df["close"].iloc[-1]) if len(df) else None},
        )

        # ── 2. Features ───────────────────────────────────────────────────────
        features = feature_engine.calculate(df)
        features = features.model_copy(update={"correlation_id": correlation_id})

        # ── 3. Order book enrichment (Binance crypto only — MT5 has no L2) ───
        if is_crypto:
            try:
                order_book = await binance.get_order_book(symbol, depth=20)
                micro_data = micro_agent.analyze_order_book(order_book)
                features = features.model_copy(update=micro_data)
            except Exception:
                pass  # microstructure optional
        tracer.record(
            correlation_id,
            "features",
            {"version": features.version, "rsi_14": features.rsi_14,
             "atr_14": features.atr_14, "trend": features.trend_direction},
        )

        # ── 4. Agents ─────────────────────────────────────────────────────────
        tech_agent = tech_agent_crypto if is_crypto else tech_agent_mt5
        tech_output = tech_agent.predict(features)
        regime_output = regime_agent.predict(features)
        micro_output = micro_agent.predict(features)
        for out in (tech_output, regime_output, micro_output):
            try:
                tracer.record(
                    correlation_id,
                    "agent_output",
                    {"agent_id": getattr(out, "agent_id", "?"),
                     "score": getattr(out, "score", None),
                     "confidence": getattr(out, "confidence", None)},
                )
            except Exception:  # noqa: BLE001
                pass

        # ── 5. Consensus (weights conditional on asset_class) ─────────────────
        regime_gate = _make_regime_gate(regime_output, features)
        consensus_out = consensus.aggregate(
            [tech_output, regime_output, micro_output], regime_gate
        )
        consensus_out = consensus_out.model_copy(
            update={"correlation_id": correlation_id}
        )
        tracer.record(
            correlation_id,
            "consensus",
            {"final_direction": consensus_out.final_direction,
             "weighted_score": consensus_out.weighted_score,
             "blocked_by_regime": consensus_out.blocked_by_regime},
        )

        # ── 6. Signal (stamped with the I1-approved strategy_id) ──────────────
        signal = signal_engine.generate(
            consensus_out, features, strategy_id=approved.strategy_id
        )
        if signal is None:
            logger.info("no_signal", symbol=symbol, reason="neutral_or_filtered")
            tracer.record(correlation_id, "signal", {"generated": False,
                          "reason": "neutral_or_filtered"})
            return
        signal = signal.model_copy(update={"correlation_id": correlation_id})
        tracer.record(
            correlation_id,
            "signal",
            {"generated": True, "id": signal.id, "action": signal.action,
             "entry": signal.entry_price, "sl": signal.stop_loss,
             "tp": signal.take_profit, "rr": signal.risk_reward_ratio,
             "strategy_id": signal.strategy_id},
        )

        # ── 6b. Confirmation: the validated strategy must agree with consensus ─
        try:
            spec = strategy_registry.get_i1_spec(approved.strategy_id)
        except Exception:  # noqa: BLE001 — id not in the catalogue
            logger.error(
                "approved_strategy_id_unknown",
                symbol=symbol,
                strategy_id=approved.strategy_id,
            )
            return
        confirmed, strat_sig = _strategy_confirms(spec, df, approved.params, signal.action)
        if not confirmed:
            logger.info(
                "signal_vetoed_by_strategy",
                symbol=symbol,
                strategy_id=approved.strategy_id,
                consensus_action=signal.action,
                strategy_signal=strat_sig,
            )
            _decide(signal.id, "vetoed_by_strategy", strategy_signal=strat_sig,
                    action=signal.action)
            return

        # ── 7. Risk validation ────────────────────────────────────────────────
        portfolio_state = portfolio.get_portfolio()
        risk_ok, reason = risk.validate_signal(
            signal.model_dump(), portfolio_state.model_dump()
        )
        if not risk_ok:
            logger.info("signal_rejected_by_risk", symbol=symbol, reason=reason)
            _decide(signal.id, "rejected_by_risk", reason=reason)
            return
        _decide(signal.id, "approved", action=signal.action,
                strategy_id=signal.strategy_id, confidence=signal.confidence)

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
        if isinstance(order, dict):
            order["correlation_id"] = correlation_id
        tracer.record(
            correlation_id,
            "execution",
            {"fill_price": order.get("fill_price") if isinstance(order, dict) else None,
             "quantity": quantity,
             "mode": order.get("execution_mode") if isinstance(order, dict) else None},
        )

        # ── 10. Portfolio update ──────────────────────────────────────────────
        portfolio.open_position(signal, quantity, order["fill_price"])
        new_state = portfolio.get_portfolio()
        recent_trades = getattr(portfolio, "get_recent_trades", lambda: [])()
        risk.update_kill_switch(new_state.model_dump(), recent_trades)
        tracer.record(
            correlation_id,
            "portfolio",
            {"open_positions": len(new_state.positions),
             "available_capital": new_state.available_capital,
             "daily_pnl_pct": new_state.daily_pnl_pct},
        )

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
        try:
            tracer.record(correlation_id, "error", {"error": str(exc)})
        except Exception:  # noqa: BLE001
            pass
        await components["alert"].on_critical_error(
            "pipeline_cycle", f"{symbol}: {exc}"
        )
    finally:
        _clear_ctx()


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
    mt5_client = None
    mt5_executor = None

    if settings.MT5_LOGIN != 0 and settings.MT5_PASSWORD:
        try:
            from core.ingestion.providers.mt5_client import MT5Client
            from core.execution.mt5_executor import MT5Executor

            mt5_client = MT5Client(
                server=settings.MT5_SERVER,
                account_number=settings.MT5_LOGIN,
                password=settings.MT5_PASSWORD,
            )
            await mt5_client.connect()
            logger.info(
                "mt5_connected", server=settings.MT5_SERVER, login=settings.MT5_LOGIN
            )

            kill_switch_temp = create_kill_switch(settings)
            mt5_executor = MT5Executor(settings, kill_switch_temp, mt5_client)

        except Exception as exc:
            logger.warning(
                "mt5_connection_failed",
                error=str(exc),
                hint="MT5 symbols will be skipped this session",
            )
            mt5_client = None
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

    kill_switch = create_kill_switch(settings)
    portfolio = create_portfolio_manager(settings, use_redis=True)
    order_tracker = create_order_tracker(use_redis=True)
    risk = RiskManager(settings=settings, kill_switch=kill_switch)

    telegram = TelegramBot(
        token=settings.TELEGRAM_BOT_TOKEN, chat_id=settings.TELEGRAM_CHAT_ID
    )
    alert = AlertEngine(telegram_bot=telegram)

    fund_agent = FundamentalAgent()
    await fund_agent.refresh()

    components = {
        "settings": settings,
        "binance": binance,
        "mt5_client": mt5_client,
        "mt5_executor": mt5_executor,
        "calendar": calendar,
        "feature_engine": FeatureEngine(feature_version=settings.FEATURE_VERSION),
        # Two TechnicalAgent instances — each with its own model path
        # Both fall back to rule-based scoring if the .pkl does not exist yet
        "tech_agent_crypto": TechnicalAgent(model_path=MODEL_CRYPTO),
        "tech_agent_mt5": TechnicalAgent(model_path=MODEL_FOREX),
        "regime_agent": RegimeAgent(),
        "micro_agent": MicrostructureAgent(),
        "fund_agent": fund_agent,
        "consensus": ConsensusEngine(),
        "signal_engine": SignalEngine(),
        "strategy_registry": StrategyRegistry(),
        "tracer": get_trace_store(),
        "audit": AuditLog(),
        "risk": risk,
        "executor_paper": PaperExecutor(),
        "portfolio": portfolio,
        "order_tracker": order_tracker,
        "feature_store": feature_store,
        "repo": TradingRepository(),
        "alert": alert,
    }

    mt5_symbols = [s for s, _ in SCHEDULE if detect_asset_class(s) != AssetClass.CRYPTO]
    crypto_symbols = [
        s for s, _ in SCHEDULE if detect_asset_class(s) == AssetClass.CRYPTO
    ]
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
    """Single-owner pipeline scheduler.

    This process is the ONLY owner of the APScheduler. Before starting any job it
    must win the Redis lock ``trader:scheduler:owner`` (SET NX EX); if another
    process holds it, this one waits in passive mode and retries. The API never
    schedules jobs (see api/main.py) — so even with ``uvicorn --workers 4`` the
    pipeline runs exactly once per symbol per window.
    """
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        print("❌ APScheduler not installed. Run: pip install apscheduler")
        sys.exit(1)

    # ── Become the single scheduler owner (blocks in passive mode) ──────────
    lock = SchedulerLock(settings.REDIS_URL)
    print(f"▶ Scheduler owner id={lock.owner_id}; acquiring lock '{lock.key}'...")
    await lock.wait_until_owner()

    await init_pool(settings.DATABASE_URL)
    components = await _build_components(settings)

    # Refresh ForexFactory events every 4 hours
    async def _refresh_calendar():
        await components["calendar"].refresh_events()

    # Refresh macro-event calendar for the FundamentalAgent every 30 min
    # (moved here from api/main.py — the API no longer runs background jobs)
    async def _refresh_fundamental():
        try:
            await components["fund_agent"].refresh()
        except Exception as exc:  # noqa: BLE001
            logger.warning("fundamental_refresh_failed", error=str(exc))

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
    scheduler.add_job(
        _refresh_fundamental,
        trigger=CronTrigger(minute="*/30", timezone="UTC"),
        id="fundamental_refresh",
        name="FundamentalAgent macro-event refresh",
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    total = len(SCHEDULE)
    print(
        f"✅ Scheduler activo. {total} símbolos programados (2 crypto + 10 MT5). Ctrl+C para detener."
    )
    logger.info("scheduler_started", total_symbols=total, schedule=SCHEDULE)

    # ── Keep renewing the ownership lock; exit non-zero if we ever lose it ──
    async def _on_lock_lost() -> None:
        scheduler.shutdown(wait=False)
        await _teardown(components)

    renew_task = asyncio.create_task(lock.keep_renewed(on_lost=_on_lock_lost))

    try:
        while True:
            await asyncio.sleep(60)
            if renew_task.done():
                logger.critical("scheduler_stopping_lock_lost", owner_id=lock.owner_id)
                sys.exit(1)
    except (KeyboardInterrupt, SystemExit):
        renew_task.cancel()
        scheduler.shutdown()
        lock.release()
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
    parser = argparse.ArgumentParser(
        description="TRADER AI — Multi-Asset Signal Pipeline"
    )
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
