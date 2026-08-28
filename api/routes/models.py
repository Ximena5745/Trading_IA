"""
Module: api/routes/models.py
Responsibility: Model registry endpoints — catalog + model card for the trading agents
Dependencies: consensus voting weights, agent metadata
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from core.consensus.asset_specific_consensus import ASSET_SPECIFIC_WEIGHTS
from core.consensus.voting_engine import AGENT_WEIGHTS_CRYPTO, AGENT_WEIGHTS_MT5

router = APIRouter(prefix="/models", tags=["models"])

# Static catalog sourced from each agent's class attributes (agent_id, model_version)
# and module docstring. There is currently no persisted registry of trained-model
# metrics (accuracy/F1/precision) in the codebase — see metrics_tracked=False below.
_MODEL_CATALOG: list[dict] = [
    {
        "id": "technical_v1",
        "name": "Technical Agent",
        "model_version": "v1.0.0",
        "model_type": "LightGBM",
        "description": "LightGBM model over technical features with SHAP explanations.",
    },
    {
        "id": "regime_v1",
        "name": "Regime Agent",
        "model_version": "v2.0.0",
        "model_type": "HMM / Random Forest",
        "description": "Market regime classification (5-8 states) using HMM or Random Forest.",
    },
    {
        "id": "microstructure_v1",
        "name": "Microstructure Agent",
        "model_version": "v1.0.0",
        "model_type": "Order book heuristics",
        "description": "Order book L2 analysis for buy/sell pressure.",
    },
    {
        "id": "fundamental",
        "name": "Fundamental Agent",
        "model_version": "v2_multi_asset",
        "model_type": "Sentiment scoring",
        "description": "Fundamental signals based on macro sentiment, per asset class.",
    },
    {
        "id": "asset_specific_v1",
        "name": "Asset-Specific Agent",
        "model_version": "v1.0.0",
        "model_type": "Multi-model ensemble",
        "description": "Asset-specific multi-model agent with ensemble architecture.",
    },
]

_WEIGHT_SCHEMES = {
    "crypto": AGENT_WEIGHTS_CRYPTO,
    "mt5": AGENT_WEIGHTS_MT5,
    "asset_specific": ASSET_SPECIFIC_WEIGHTS,
}


def _build_model_entry(model: dict) -> dict:
    weights = {
        scheme: weights_dict.get(model["id"])
        for scheme, weights_dict in _WEIGHT_SCHEMES.items()
    }
    is_active = any(w for w in weights.values() if w)
    return {
        **model,
        "consensus_weights": weights,
        "status": "active" if is_active else "supplementary",
        "metrics_tracked": False,
        "accuracy": None,
        "f1_score": None,
        "precision": None,
    }


@router.get("")
async def list_models():
    """Public endpoint for dashboard without auth requirement."""
    entries = [_build_model_entry(m) for m in _MODEL_CATALOG]
    return {"count": len(entries), "models": entries}


@router.get("/{model_id}")
async def get_model(model_id: str):
    """Public endpoint for dashboard without auth requirement."""
    model = next((m for m in _MODEL_CATALOG if m["id"] == model_id), None)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Model not found"
        )
    return _build_model_entry(model)
