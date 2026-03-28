"""
Module: core/agents/microstructure_agent.py
Responsibility: Order book L2 analysis for buy/sell pressure
Dependencies: base_agent, models, logger
"""
from __future__ import annotations


from core.agents.base_agent import AbcAgent
from core.exceptions import AgentPredictionError
from core.models import AgentOutput, FeatureSet
from core.observability.logger import get_logger

logger = get_logger(__name__)

LARGE_ORDER_MULTIPLIER = 10.0


class MicrostructureAgent(AbcAgent):
    """
    Analyzes L2 order book snapshot.
    Only active when order book data is available (optional in MVP).
    """

    agent_id = "microstructure_v1"
    model_version = "v1.0.0"

    def is_ready(self) -> bool:
        return True

    def predict(self, features: FeatureSet) -> AgentOutput:
        try:
            if features.order_book_imbalance is None:
                return self._neutral(features)

            imbalance = features.order_book_imbalance
            spread = features.bid_ask_spread or 0.0

            score = self._compute_score(imbalance, spread)
            direction = "BUY" if score > 0.3 else ("SELL" if score < -0.3 else "NEUTRAL")
            confidence = min(abs(imbalance) * 1.5, 1.0)

            return AgentOutput(
                agent_id=self.agent_id,
                timestamp=features.timestamp,
                symbol=features.symbol,
                direction=direction,
                score=round(score, 4),
                confidence=round(confidence, 4),
                features_used=["order_book_imbalance", "bid_ask_spread"],
                shap_values={
                    "order_book_imbalance": round(imbalance * 0.7, 6),
                    "bid_ask_spread": round(-spread * 0.3, 6),
                },
                model_version=self.model_version,
            )
        except Exception as e:
            raise AgentPredictionError(f"MicrostructureAgent failed: {e}") from e

    def analyze_order_book(self, order_book: dict) -> dict[str, float]:
        """Compute microstructure metrics from raw order book dict."""
        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])
        if not bids or not asks:
            return {"order_book_imbalance": 0.0, "bid_ask_spread": 0.0}

        bid_vol = sum(float(b[1]) for b in bids)
        ask_vol = sum(float(a[1]) for a in asks)
        total_vol = bid_vol + ask_vol
        imbalance = (bid_vol - ask_vol) / total_vol if total_vol > 0 else 0.0

        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        spread = (best_ask - best_bid) / best_bid if best_bid > 0 else 0.0

        return {"order_book_imbalance": round(imbalance, 6), "bid_ask_spread": round(spread, 6)}

    def _compute_score(self, imbalance: float, spread: float) -> float:
        return max(-1.0, min(1.0, imbalance * 0.8 - spread * 0.2))

    def _neutral(self, features: FeatureSet) -> AgentOutput:
        return AgentOutput(
            agent_id=self.agent_id,
            timestamp=features.timestamp,
            symbol=features.symbol,
            direction="NEUTRAL",
            score=0.0,
            confidence=0.0,
            features_used=[],
            shap_values={},
            model_version=self.model_version,
        )
