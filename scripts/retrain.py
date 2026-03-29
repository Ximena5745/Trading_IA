"""
Script: scripts/retrain.py
Responsibility: CLI to manually trigger agent retraining from stored features
Usage: python scripts/retrain.py --symbol BTCUSDT [--force]
"""
from __future__ import annotations

import argparse
import asyncio
import sys

sys.path.insert(0, ".")

from core.adaptation.retraining import AdaptationEngine
from core.agents.technical_agent import TechnicalAgent
from core.features.feature_store import FeatureStore
from core.observability.logger import configure_logging, get_logger
from core.config.settings import get_settings

configure_logging()
logger = get_logger("retrain")
settings = get_settings()


async def retrain(symbol: str, force: bool) -> None:
    print("🤖 TRADER AI — Manual Retraining")
    print(f"   Symbol  : {symbol}")
    print(f"   Force   : {force}")
    print()

    feature_store = FeatureStore()
    agent = TechnicalAgent()
    engine = AdaptationEngine(
        technical_agent=agent,
        feature_store=feature_store,
    )

    if force:
        # Bypass cooldown for manual trigger
        engine._last_retrain_at = None

    print("📦 Loading feature history from store...")
    history = feature_store.get_history(symbol, limit=1000)
    print(f"   → {len(history)} feature sets available")

    if not history:
        print("❌ No features found. Run seed_data.py first.")
        return

    print("⚙️  Running retraining...")
    success = await engine.maybe_retrain(symbol=symbol, reason="manual_cli")

    if success:
        status = engine.get_status()
        print("\n✅ Retraining completed!")
        print(f"   Agent version : {status['agent_version']}")
        print(f"   Retrain count : {status['retrain_count']}")
        print(f"   Last retrain  : {status['last_retrain_at']}")
    else:
        status = engine.get_status()
        print("\n⚠️  Retraining skipped. Status:")
        for k, v in status.items():
            print(f"   {k:30s}: {v}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manually trigger agent retraining")
    parser.add_argument("--symbol", default="BTCUSDT", help="Symbol to retrain on")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass cooldown period",
    )
    args = parser.parse_args()

    asyncio.run(retrain(args.symbol, args.force))


if __name__ == "__main__":
    main()
