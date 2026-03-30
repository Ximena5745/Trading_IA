"""
Module: core/signals/xai_module.py
Responsibility: Convert SHAP values into human-readable explanations
Dependencies: models, logger
"""
from __future__ import annotations

from core.models import AgentOutput, ConsensusOutput, SignalExplanationFactor
from core.observability.logger import get_logger

logger = get_logger(__name__)

TOP_N_FACTORS = 5

FEATURE_DESCRIPTIONS = {
    "rsi_14": lambda v,
    s: f"RSI(14) en zona de {'sobreventa' if s > 0 else 'sobrecompra'} ({v:.1f})",
    "rsi_7": lambda v, s: f"RSI(7) en {v:.1f}",
    "macd_histogram": lambda v,
    s: f"MACD histograma {'positivo' if v > 0 else 'negativo'} ({v:+.4f})",
    "macd_line": lambda v, s: f"MACD línea en {v:.4f}",
    "ema_50": lambda v, s: f"EMA50 {'por encima' if s > 0 else 'por debajo'} de precio",
    "ema_200": lambda v,
    s: f"EMA200 señal de {'tendencia alcista' if s > 0 else 'tendencia bajista'}",
    "atr_14": lambda v,
    s: f"ATR(14) en {v:.2f} (volatilidad {'alta' if v > 0 else 'baja'})",
    "bb_width": lambda v,
    s: f"Bandas Bollinger {'expandidas' if v > 0.05 else 'comprimidas'} ({v:.4f})",
    "volume_ratio": lambda v,
    s: f"Volumen {v:.1f}× por {'encima' if v > 1 else 'debajo'} de la media",
    "obv": lambda v, s: f"OBV {'creciente' if s > 0 else 'decreciente'} ({v:+.0f})",
    "order_book_imbalance": lambda v,
    s: f"Presión {'compradora' if v > 0 else 'vendedora'} ({v:+.2f})",
}


class XAIModule:
    def build_explanation(
        self,
        consensus: ConsensusOutput,
        top_n: int = TOP_N_FACTORS,
    ) -> list[SignalExplanationFactor]:
        """Extract top SHAP contributors from the highest-weight agent."""
        lead_agent = self._get_lead_agent(consensus)
        if not lead_agent or not lead_agent.shap_values:
            return []

        sorted_shap = sorted(
            lead_agent.shap_values.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:top_n]

        factors = []
        for feature, shap_val in sorted_shap:
            direction = "bullish" if shap_val > 0 else "bearish"
            feature_val = shap_val  # use shap as proxy when raw value unavailable
            desc_fn = FEATURE_DESCRIPTIONS.get(feature)
            description = (
                desc_fn(feature_val, shap_val)
                if desc_fn
                else f"{feature}: {shap_val:+.4f}"
            )
            factors.append(
                SignalExplanationFactor(
                    factor=feature,
                    weight=round(abs(shap_val), 6),
                    direction=direction,
                    description=description,
                )
            )
        return factors

    def generate_summary(
        self,
        factors: list[SignalExplanationFactor],
        direction: str,
        confidence: float,
        symbol: str,
    ) -> str:
        action = "COMPRA" if direction == "BUY" else "VENTA"
        conf_pct = int(confidence * 100)
        top = factors[:3]
        reasons = "; ".join(f.description for f in top)
        return f"Señal de {action} en {symbol} con confianza {conf_pct}%: {reasons}."

    @staticmethod
    def _get_lead_agent(consensus: ConsensusOutput) -> AgentOutput | None:
        from core.consensus.voting_engine import AGENT_WEIGHTS

        best = None
        best_weight = -1.0
        for output in consensus.agent_outputs:
            w = AGENT_WEIGHTS.get(output.agent_id, 0.0)
            if w > best_weight:
                best_weight = w
                best = output
        return best
