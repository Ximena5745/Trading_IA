"""
Script: scripts/run_pipeline_mock.py
Responsibility: Run full pipeline with synthetic/mock data - no external APIs needed
Usage: python scripts/run_pipeline_mock.py
"""
from __future__ import annotations

import asyncio
import io
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agents.regime_agent import RegimeAgent
from core.agents.technical_agent import TechnicalAgent
from core.consensus.voting_engine import ConsensusEngine
from core.config.settings import get_settings
from core.db.repository import TradingRepository
from core.db.session import close_pool, init_pool
from core.execution.paper_executor import PaperExecutor
from core.features.feature_engineering import FeatureEngine
from core.features.feature_store import FeatureStore
from core.models import (
    FeatureSet,
    MarketData,
    Signal,
)
from core.observability.logger import configure_logging, get_logger
from core.portfolio.portfolio_manager import PortfolioManager
from core.risk.kill_switch import KillSwitch
from core.risk.risk_manager import RiskManager
from core.signals.signal_engine import SignalEngine

configure_logging()
logger = get_logger("pipeline_mock")

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
INITIAL_CAPITAL = 10_000.0
HISTORY_CANDLES = 250


def generate_mock_candles(symbol: str, n: int = HISTORY_CANDLES) -> list[MarketData]:
    """Generate realistic synthetic OHLCV candles."""
    random.seed(hash(symbol) % (2**32))
    base_price = {"BTCUSDT": 65_000, "ETHUSDT": 3_500}.get(symbol, 100)
    candles = []
    price = base_price
    now = datetime.now(timezone.utc)

    for i in range(n):
        ts = now - timedelta(hours=n - i)
        volatility = random.uniform(0.001, 0.02)
        change = random.gauss(0, volatility)
        o = price
        c = price * (1 + change)
        h = max(o, c) * (1 + abs(random.gauss(0, volatility * 0.5)))
        l = min(o, c) * (1 - abs(random.gauss(0, volatility * 0.5)))
        v = random.uniform(100, 10_000)

        candles.append(
            MarketData(
                timestamp=ts,
                symbol=symbol,
                open=round(o, 2),
                high=round(h, 2),
                low=round(l, 2),
                close=round(c, 2),
                volume=round(v, 2),
            )
        )
        price = c
    return candles


def candles_to_df(candles: list[MarketData]):
    """Convert MarketData list to DataFrame."""
    import pandas as pd

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


async def run_mock_pipeline():
    """Run end-to-end pipeline with mock data."""
    settings = get_settings()
    print("=" * 60)
    print("  TRADER AI — Pipeline Mock Test")
    print("=" * 60)

    # 1. Init DB pool
    await init_pool(settings.DATABASE_URL)
    print("✅ DB pool initialized")

    # 2. Init components
    feature_engine = FeatureEngine(feature_version="v1")
    tech_agent = TechnicalAgent()
    regime_agent = RegimeAgent()
    consensus = ConsensusEngine()
    signal_engine = SignalEngine()
    kill_switch = KillSwitch(settings)
    portfolio = PortfolioManager(settings=settings, initial_capital=INITIAL_CAPITAL)
    risk = RiskManager(settings=settings, kill_switch=kill_switch)
    executor = PaperExecutor()
    feature_store = FeatureStore(redis_url=settings.REDIS_URL)
    await feature_store.connect()
    repo = TradingRepository()

    print("✅ Components initialized")
    print(f"   Mode: {settings.EXECUTION_MODE}")
    print(f"   Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    print()

    total_signals = 0
    total_orders = 0

    for symbol in SYMBOLS:
        print(f"{'─' * 60}")
        print(f"  📊 Processing: {symbol}")
        print(f"{'─' * 60}")

        # Generate mock data
        candles = generate_mock_candles(symbol)
        df = candles_to_df(candles)
        print(f"   Generated {len(candles)} candles")
        print(f"   Price range: ${df['close'].min():,.2f} - ${df['close'].max():,.2f}")

        # Calculate features
        features = feature_engine.calculate(df)
        print(f"   Features calculated: {len(features.model_dump())} fields")

        # Technical agent
        tech_output = tech_agent.predict(features)
        print(f"   Technical: score={tech_output.score:.3f}, conf={tech_output.confidence:.3f}")

        # Regime agent
        regime_classified = regime_agent.classify_regime(features)
        regime_output = regime_agent.predict(features)
        print(f"   Regime: {regime_classified.regime.value}, signal_allowed={regime_classified.signal_allowed}")

        # Consensus
        consensus_out = consensus.aggregate(
            [tech_output, regime_output], regime_classified
        )
        # ConsensusOutput fields: final_direction, weighted_score, agents_agreement
        print(
            f"   Consensus: {consensus_out.final_direction}, weighted_score={consensus_out.weighted_score:.3f}, "
            f"agreements={consensus_out.agents_agreement:.2f}"
        )

        # Signal generation
        signal = signal_engine.generate(consensus_out, features, strategy_id="mock_v1")
        if signal is None:
            print("   ⏭️  No signal generated (neutral/filtered)")
            print()
            continue

        total_signals += 1
        print(f"   ⚡ Signal: {signal.action} @ ${signal.entry_price:,.2f}")
        print(f"      SL: ${signal.stop_loss:,.2f} | TP: ${signal.take_profit:,.2f}")

        # Risk validation
        portfolio_state = portfolio.get_portfolio()
        approved, reason = risk.validate_signal(
            signal.model_dump(), portfolio_state.model_dump()
        )
        if not approved:
            print(f"   ❌ Rejected by risk: {reason}")
            print()
            continue

        # Position sizing
        quantity = risk.calculate_position_size(
            signal.model_dump(), portfolio_state.model_dump()
        )
        if quantity <= 0:
            print("   ❌ Zero quantity")
            print()
            continue

        print(f"   ✅ Approved | Qty: {quantity:.6f}")

        # Execute (paper)
        order = await executor.execute(signal.model_dump(), quantity)
        total_orders += 1
        print(f"   📝 Order filled @ ${order['fill_price']:,.2f}")

        # Portfolio update
        portfolio.open_position(signal, quantity, order["fill_price"])
        new_state = portfolio.get_portfolio()
        risk.update_kill_switch(new_state.model_dump(), [])

        # Persist to DB
        await feature_store.save(features)
        await repo.save_signal(signal)
        await repo.save_order(order)
        await repo.save_portfolio_snapshot(new_state)

        print(f"   💾 Saved to DB")
        print()

    # Summary
    print("=" * 60)
    print("  📋 Pipeline Summary")
    print("=" * 60)
    print(f"   Symbols processed: {len(SYMBOLS)}")
    print(f"   Signals generated: {total_signals}")
    print(f"   Orders executed:   {total_orders}")
    print(f"   Portfolio state:")
    final = portfolio.get_portfolio()
    print(f"     Total Capital:   ${final.total_capital:,.2f}")
    print(f"     Available:       ${final.available_capital:,.2f}")
    print(f"     Open Positions:  {len(final.positions)}")
    print(f"     Daily P&L:       {final.daily_pnl_pct:.2%}")
    print()

    # Cleanup
    # feature_store has connect/save; no explicit disconnect() method
    # Ensure a clean exit by closing the DB pool if applicable
    try:
        await close_pool()
    except Exception:
        pass
    print("✅ Cleanup complete")
    print()
    print("🎉 Pipeline mock test PASSED — all components working!")


if __name__ == "__main__":
    asyncio.run(run_mock_pipeline())
