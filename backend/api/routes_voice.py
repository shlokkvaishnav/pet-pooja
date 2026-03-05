"""
routes_voice.py — Voice Ordering API Endpoints
================================================
All processing runs locally — no external API calls.
"""

import os
import tempfile
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db

router = APIRouter()


def get_pipeline(db: Session = Depends(get_db)):
    """Get pipeline from app state (loaded at startup with DB data)."""
    from main import app
    return app.state.voice_pipeline


class TextInput(BaseModel):
    text: str


@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Audio file -> transcript text only. Uses local Whisper model."""
    suffix = os.path.splitext(audio.filename)[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name
    try:
        from modules.voice.stt import transcribe
        return transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)


@router.post("/process-audio")
async def process_audio(
    audio: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Audio file -> full pipeline result."""
    pipeline = get_pipeline(db)
    suffix = os.path.splitext(audio.filename)[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name
    try:
        return pipeline.process_audio(tmp_path)
    finally:
        os.unlink(tmp_path)


@router.post("/process")
async def process_text(body: TextInput, db: Session = Depends(get_db)):
    """Text -> full pipeline result. For testing without audio."""
    pipeline = get_pipeline(db)
    return pipeline.process_text(body.text)


@router.post("/confirm-order")
async def confirm_order(order: dict, db: Session = Depends(get_db)):
    """Save confirmed order to DB. Returns order_id + KOT."""
    try:
        from modules.voice.order_builder import save_order_to_db
        return save_order_to_db(order, db)
    except ImportError:
        return {"status": "stub", "message": "Order saving not implemented yet"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
async def get_orders(limit: int = 20, db: Session = Depends(get_db)):
    """Recent confirmed voice orders."""
    from models import Order
    orders = db.query(Order).order_by(Order.created_at.desc()).limit(limit).all()
    return [
        {
            "id": o.id,
            "order_id": o.order_id,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "total": o.total,
            "status": o.status,
            "order_type": o.order_type,
        }
        for o in orders
    ]
