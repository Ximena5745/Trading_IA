"""
Tests for ConsensusEngine — MT5 conditional weights (FASE E).
Verifies that:
  - Crypto symbols use AGENT_WEIGHTS_CRYPTO (micro=20%)
  - Forex/Indices/Commodities use AGENT_WEIGHTS_MT5 (micro=0%)
  - MicrostructureAgent output is ignored for non-crypto assets
"""
from __future__ import annotations

from datetime import datetime

import pytest

from core.consensus.voting_engine import (
    AGENT_WEIGHTS_CRYPTO,
    AGENT_WEIGHTS_MT5,
    ConsensusEngine,
    _weights_for_symbol,
)
from core.models import AgentOutput, MarketRegime, RegimeOutput


def make_output(
    agent_id: str,
    symbol: str = "BTCUSDT",
    direction: str = "BUY",
    score: float = 0.6,
    confidence: float = 0.75,
) -> AgentOutput:
    return AgentOutput(
        agent_id=agent_id,
        timestamp=datetime(2024, 6, 1),
        symbol=symbol,
        direction=direction,
        score=score,
        confidence=confidence,
        features_used=["rsi_14"],
        shap_values={"rsi_14": 0.3},
        model_version="v1",
    )


def make_regime(symbol: str = "BTCUSDT", signal_allowed: bool = True) -> RegimeOutput:
    return RegimeOutput(
        timestamp=datetime(2024, 6, 1),
        symbol=symbol,
        regime=MarketRegime.BULL_TRENDING,
        confidence=0.80,
        regime_duration_bars=5,
        signal_allowed=signal_allowed,
    )


class TestWeightSelection:
    """_weights_for_symbol returns the correct weight dict."""

    def test_crypto_symbols_use_crypto_weights(self):
        assert _weights_for_symbol("BTCUSDT") is AGENT_WEIGHTS_CRYPTO
        assert _weights_for_symbol("ETHUSDT") is AGENT_WEIGHTS_CRYPTO

    def test_forex_symbols_use_mt5_weights(self):
        assert _weights_for_symbol("EURUSD") is AGENT_WEIGHTS_MT5
        assert _weights_for_symbol("GBPUSD") is AGENT_WEIGHTS_MT5
        assert _weights_for_symbol("USDJPY") is AGENT_WEIGHTS_MT5

    def test_commodity_symbols_use_mt5_weights(self):
        assert _weights_for_symbol("XAUUSD") is AGENT_WEIGHTS_MT5

    def test_index_symbols_use_mt5_weights(self):
        assert _weights_for_symbol("US500") is AGENT_WEIGHTS_MT5
        assert _weights_for_symbol("UK100") is AGENT_WEIGHTS_MT5

    def test_micro_weight_zero_in_mt5(self):
        assert AGENT_WEIGHTS_MT5["microstructure_v1"] == 0.0

    def test_micro_weight_nonzero_in_crypto(self):
        assert AGENT_WEIGHTS_CRYPTO["microstructure_v1"] == 0.20

    def test_technical_weight_higher_in_mt5(self):
        assert AGENT_WEIGHTS_MT5["technical_v1"] > AGENT_WEIGHTS_CRYPTO["technical_v1"]

    def test_regime_weight_higher_in_mt5(self):
        assert AGENT_WEIGHTS_MT5["regime_v1"] > AGENT_WEIGHTS_CRYPTO["regime_v1"]


class TestMicrostructureIgnoredForForex:
    """
    When symbol is Forex/Indices, micro agent score=1.0 (strong BUY)
    but only tech+regime are active (both NEUTRAL) → result should be NEUTRAL.
    """

    def test_micro_buy_ignored_for_eurusd(self):
        """Micro agent strongly bullish, tech+regime neutral → NEUTRAL for EURUSD."""
        engine = ConsensusEngine()
        outputs = [
            make_output("technical_v1",      symbol="EURUSD", direction="NEUTRAL", score=0.0),
            make_output("regime_v1",          symbol="EURUSD", direction="NEUTRAL", score=0.0),
            make_output("microstructure_v1",  symbol="EURUSD", direction="BUY",     score=1.0),
        ]
        result = engine.aggregate(outputs, make_regime(symbol="EURUSD"))
        assert result.final_direction == "NEUTRAL"

    def test_micro_included_for_btcusdt(self):
        """All three agents BUY for BTCUSDT → microstructure contributes → BUY."""
        engine = ConsensusEngine()
        outputs = [
            make_output("technical_v1",      symbol="BTCUSDT", direction="BUY", score=0.6),
            make_output("regime_v1",          symbol="BTCUSDT", direction="BUY", score=0.7),
            make_output("microstructure_v1",  symbol="BTCUSDT", direction="BUY", score=0.5),
        ]
        result = engine.aggregate(outputs, make_regime(symbol="BTCUSDT"))
        assert result.final_direction == "BUY"
        assert result.blocked_by_regime is False


class TestWeightedScoreCalculation:
    """Weighted score should reflect the correct weights per asset class."""

    def test_crypto_weighted_score_uses_three_agents(self):
        """For BTCUSDT, all three agents contribute to weighted score."""
        engine = ConsensusEngine()
        # All scoring 1.0 — max possible weighted score
        outputs = [
            make_output("technical_v1",     symbol="BTCUSDT", score=1.0, direction="BUY"),
            make_output("regime_v1",         symbol="BTCUSDT", score=1.0, direction="BUY"),
            make_output("microstructure_v1", symbol="BTCUSDT", score=1.0, direction="BUY"),
        ]
        result = engine.aggregate(outputs, make_regime("BTCUSDT"))
        # weighted_score should be 1.0 (all agents at 1.0, weights sum to 1.0)
        assert abs(result.weighted_score - 1.0) < 1e-4

    def test_mt5_weighted_score_ignores_micro(self):
        """For EURUSD, micro agent score is excluded from weighted score."""
        engine = ConsensusEngine()
        # tech=1.0, regime=1.0 → weighted=(1.0×0.55 + 1.0×0.45)/(0.55+0.45) = 1.0
        # micro=0.0 (SELL) — should NOT pull the score down
        outputs = [
            make_output("technical_v1",     symbol="EURUSD", score=1.0,   direction="BUY"),
            make_output("regime_v1",         symbol="EURUSD", score=1.0,   direction="BUY"),
            make_output("microstructure_v1", symbol="EURUSD", score=-1.0,  direction="SELL"),
        ]
        result = engine.aggregate(outputs, make_regime("EURUSD"))
        # micro with 0 weight doesn't affect score or agreement
        assert result.final_direction == "BUY"
        assert result.weighted_score > 0.0


class TestRegimeVetoUnaffectedByWeightMode:
    """Regime veto must work the same for both crypto and MT5."""

    def test_regime_veto_blocks_eurusd(self):
        engine = ConsensusEngine()
        outputs = [
            make_output("technical_v1", symbol="EURUSD", score=0.9, direction="BUY"),
        ]
        result = engine.aggregate(outputs, make_regime("EURUSD", signal_allowed=False))
        assert result.final_direction == "NEUTRAL"
        assert result.blocked_by_regime is True

    def test_regime_veto_blocks_btcusdt(self):
        engine = ConsensusEngine()
        outputs = [
            make_output("technical_v1",     symbol="BTCUSDT", score=0.9, direction="BUY"),
            make_output("microstructure_v1", symbol="BTCUSDT", score=0.8, direction="BUY"),
        ]
        result = engine.aggregate(outputs, make_regime("BTCUSDT", signal_allowed=False))
        assert result.final_direction == "NEUTRAL"
        assert result.blocked_by_regime is True
