# API endpoints for drawing tools (Phase 1)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from api.dependencies import get_current_user

router = APIRouter(prefix="/drawings", tags=["drawings"])

# --- Models ---
class DrawingBase(BaseModel):
    symbol: str
    timeframe: str
    tool_type: str
    data: dict

class DrawingCreate(DrawingBase):
    pass

class Drawing(DrawingBase):
    id: int
    user_id: Optional[int]
    created_at: datetime
    updated_at: datetime

# --- In-memory store for demo ---
DRAWINGS = []

# --- Endpoints ---
@router.post("/save", response_model=Drawing)
def save_drawing(drawing: DrawingCreate, user=Depends(get_current_user)):
    new_id = len(DRAWINGS) + 1
    now = datetime.utcnow()
    d = Drawing(id=new_id, user_id=user.get("user_id"), created_at=now, updated_at=now, **drawing.dict())
    DRAWINGS.append(d)
    return d

@router.get("/{symbol}", response_model=List[Drawing])
def get_drawings(symbol: str, timeframe: Optional[str] = None, user=Depends(get_current_user)):
    return [d for d in DRAWINGS if d.symbol == symbol and (timeframe is None or d.timeframe == timeframe)]

@router.delete("/{drawing_id}")
def delete_drawing(drawing_id: int, user=Depends(get_current_user)):
    global DRAWINGS
    before = len(DRAWINGS)
    DRAWINGS = [d for d in DRAWINGS if d.id != drawing_id]
    if len(DRAWINGS) == before:
        raise HTTPException(status_code=404, detail="Drawing not found")
    return {"ok": True}

@router.post("/{drawing_id}/undo")
def undo_drawing(drawing_id: int, user=Depends(get_current_user)):
    # For demo: just delete
    return delete_drawing(drawing_id, user)
