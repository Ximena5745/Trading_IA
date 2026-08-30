"""
Tests for SPEC-B04 / F-06 — decision trace producer + retrieval.

  * TraceStore round-trips ordered steps.
  * _pipeline_cycle emits a full trace and stamps correlation_id on the models.
  * GET /trace/{correlation_id} reconstructs the chain (404 when unknown).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from core.models import AgentOutput, ConsensusOutput, FeatureSet, MarketData, Signal
from core.observability.decision_tracer import TRACE_STEPS, TraceStore, set_trace_store
import scripts.run_pipeline as rp


# ── helpers ──────────────────────────────────────────────────────────────
def _candles(n=60, start=100.0):
    ts0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    out = []
    for i in range(n):
        px = Decimal(str(start + i))  # steadily rising ⇒ momentum = +1 (confirms BUY)
        out.append(
            MarketData(
                timestamp=ts0.replace(hour=0) + pd.Timedelta(hours=i),
                symbol="BTCUSDT", open=px, high=px + 1, low=px - 1, close=px,
                volume=Decimal("10"), source="test",
            )
        )
    return out


def _feature_set():
    return FeatureSet(
        timestamp=datetime(2024, 1, 3, tzinfo=timezone.utc), symbol="BTCUSDT",
        rsi_14=55.0, rsi_7=57.0, macd_line=1.0, macd_signal=0.5, macd_histogram=0.5,
        ema_9=110.0, ema_21=108.0, ema_50=105.0, ema_200=100.0, trend_direction="bullish",
        atr_14=2.0, bb_upper=120.0, bb_lower=100.0, bb_width=20.0, volatility_regime="medium",
        vwap=110.0, volume_sma_20=10.0, volume_ratio=1.1, obv=1000.0, close=159.0,
    )


def _agent(agent_id, score):
    return AgentOutput(
        agent_id=agent_id, timestamp=datetime(2024, 1, 3, tzinfo=timezone.utc),
        symbol="BTCUSDT", direction="BUY", score=score, confidence=0.7,
        features_used=["rsi_14"], shap_values={"rsi_14": 0.1}, model_version="v1",
    )


def _signal():
    return Signal(
        id="sig-1", idempotency_key="k1", timestamp=datetime(2024, 1, 3, tzinfo=timezone.utc),
        symbol="BTCUSDT", action="BUY", entry_price=159.0, stop_loss=150.0,
        take_profit=180.0, risk_reward_ratio=2.3, confidence=0.7, strategy_id="Momentum",
    )


class _Spec:
    defaults = {}

    def signal_fn(self, df, params):
        return pd.Series([1] * len(df))  # confirms a BUY


class _Approved:
    strategy_id = "Momentum"
    params = {"lookback": 12}
    sharpe_net_holdout = 1.3
    approved_at = "2026-07-26T00:00:00+00:00"


def _components(portfolio):
    consensus_out = ConsensusOutput(
        timestamp=datetime(2024, 1, 3, tzinfo=timezone.utc), symbol="BTCUSDT",
        final_direction="BUY", weighted_score=0.6, agents_agreement=0.8,
        blocked_by_regime=False, agent_outputs=[_agent("technical_v1", 0.6)], conflicts=[],
    )
    binance = MagicMock()
    binance.get_klines = AsyncMock(return_value=_candles())
    binance.get_order_book = AsyncMock(return_value={})

    feature_engine = MagicMock()
    feature_engine.calculate = MagicMock(return_value=_feature_set())

    tech = MagicMock(); tech.predict = MagicMock(return_value=_agent("technical_v1", 0.6))
    regime = MagicMock(); regime.predict = MagicMock(return_value=_agent("regime_v1", 0.6))
    micro = MagicMock()
    micro.predict = MagicMock(return_value=_agent("micro_v1", 0.1))
    micro.analyze_order_book = MagicMock(return_value={})

    consensus = MagicMock(); consensus.aggregate = MagicMock(return_value=consensus_out)
    signal_engine = MagicMock(); signal_engine.generate = MagicMock(return_value=_signal())

    registry = MagicMock(); registry.get_i1_spec = MagicMock(return_value=_Spec())

    risk = MagicMock()
    risk.validate_signal = MagicMock(return_value=(True, ""))
    risk.calculate_position_size = MagicMock(return_value=1.0)
    risk.update_kill_switch = MagicMock()

    executor = MagicMock()
    executor.execute = AsyncMock(
        return_value={"fill_price": 159.0, "execution_mode": "paper", "id": "o1"}
    )

    fund = MagicMock(); fund.is_blocked_by_event = MagicMock(return_value=False)
    calendar = MagicMock(); calendar.is_market_open = MagicMock(return_value=True)

    repo = MagicMock()
    repo.save_signal = AsyncMock(); repo.save_order = AsyncMock()
    repo.save_portfolio_snapshot = AsyncMock()
    fs = MagicMock(); fs.save = AsyncMock()
    alert = MagicMock(); alert.on_signal = AsyncMock(); alert.on_critical_error = AsyncMock()

    return {
        "settings": MagicMock(EXECUTION_MODE="paper", TRADING_ENABLED=False),
        "binance": binance, "mt5_client": None, "mt5_executor": None,
        "feature_engine": feature_engine, "tech_agent_crypto": tech, "tech_agent_mt5": tech,
        "regime_agent": regime, "micro_agent": micro, "fund_agent": fund,
        "consensus": consensus, "signal_engine": signal_engine, "strategy_registry": registry,
        "risk": risk, "executor_paper": executor, "portfolio": portfolio,
        "feature_store": fs, "repo": repo, "alert": alert, "calendar": calendar,
        "tracer": None,  # falls back to the module store
        "audit": None,
    }


# ── tests ────────────────────────────────────────────────────────────────
def test_trace_store_roundtrip():
    s = TraceStore()
    for step in TRACE_STEPS:
        s.record("c1", step, {"n": 1})
    assert [e["step"] for e in s.get("c1")] == list(TRACE_STEPS)
    assert s.get("unknown") == []


def test_pipeline_cycle_produces_full_trace(monkeypatch):
    from core.config.settings import Settings
    from core.portfolio.portfolio_manager import PortfolioManager

    store = TraceStore()
    set_trace_store(store)
    monkeypatch.setattr(rp, "load_approved_strategy", lambda symbol: _Approved())

    pm = PortfolioManager(settings=Settings(), initial_capital=10_000.0)
    comps = _components(pm)

    asyncio.run(rp._pipeline_cycle("BTCUSDT", comps))

    # exactly one correlation_id was produced
    cids = list(store._mem.keys())
    assert len(cids) == 1
    steps = [e["step"] for e in store.get(cids[0])]
    for stage in ("market_data", "features", "agent_output", "consensus",
                  "signal", "risk_check", "execution", "portfolio"):
        assert stage in steps, f"missing trace stage: {stage} (got {steps})"

    # the signal persisted carries the correlation_id
    saved = comps["repo"].save_signal.call_args[0][0]
    assert saved.correlation_id == cids[0]


def test_trace_endpoint(monkeypatch):
    from starlette.testclient import TestClient
    import api.main as main

    store = TraceStore()
    store.record("cid-abc", "market_data", {"symbol": "BTCUSDT"})
    store.record("cid-abc", "signal", {"action": "BUY"})
    set_trace_store(store)

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(main, "init_pool", _noop)
    monkeypatch.setattr(main, "run_migrations", lambda: None)
    monkeypatch.setattr(main, "_load_parquet_data", lambda: None)
    monkeypatch.setattr(main, "start_metrics_server", lambda *a, **k: None)

    from api.dependencies import require_trader

    main.app.dependency_overrides[require_trader] = lambda: {"sub": "t", "role": "trader"}
    try:
        with TestClient(main.app) as client:
            ok = client.get("/trace/cid-abc")
            missing = client.get("/trace/nope")
    finally:
        main.app.dependency_overrides.clear()

    assert ok.status_code == 200
    body = ok.json()
    assert body["correlation_id"] == "cid-abc"
    assert body["step_count"] == 2
    assert "market_data" in body["stages_present"]
    assert missing.status_code == 404


@pytest.fixture(autouse=True)
def _reset_store():
    yield
    set_trace_store(None)
