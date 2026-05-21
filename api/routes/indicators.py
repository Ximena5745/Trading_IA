# API endpoints for indicators manager (Phase 3)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from api.dependencies import get_current_user

router = APIRouter(prefix="/indicators", tags=["indicators"])

# --- Models ---
class IndicatorMeta(BaseModel):
    key: str
    name: str
    params: list
    yAxis: str
    min: Optional[float] = None
    max: Optional[float] = None

class IndicatorPreset(BaseModel):
    id: int
    symbol: str
    preset_name: str
    indicators_json: str
    created_at: datetime

class IndicatorPresetCreate(BaseModel):
    symbol: str
    preset_name: str
    indicators_json: str

# --- In-memory store for demo ---
INDICATORS_META = [
    IndicatorMeta(key='RSI', name='RSI', params=[{'period': 14}], yAxis='secondary', min=0, max=100),
    IndicatorMeta(key='MACD', name='MACD', params=[{'fast': 12, 'slow': 26, 'signal': 9}], yAxis='secondary'),
    # ... add all 15
]
PRESETS = []

# --- Endpoints ---
@router.get("/", response_model=List[IndicatorMeta])
def list_indicators(user=Depends(get_current_user)):
    return INDICATORS_META

@router.post("/presets", response_model=IndicatorPreset)
def save_preset(preset: IndicatorPresetCreate, user=Depends(get_current_user)):
    new_id = len(PRESETS) + 1
    now = datetime.utcnow()
    p = IndicatorPreset(id=new_id, created_at=now, **preset.dict())
    PRESETS.append(p)
    return p

@router.get("/presets/{symbol}", response_model=List[IndicatorPreset])
def get_presets(symbol: str, user=Depends(get_current_user)):
    return [p for p in PRESETS if p.symbol == symbol]

@router.delete("/presets/{preset_id}")
def delete_preset(preset_id: int, user=Depends(get_current_user)):
    global PRESETS
    before = len(PRESETS)
    PRESETS = [p for p in PRESETS if p.id != preset_id]
    if len(PRESETS) == before:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"ok": True}
