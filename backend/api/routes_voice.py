"""
routes_voice.py — Voice Ordering API Endpoints
================================================
/api/voice/* — Transcription, full pipeline processing,
order confirmation, and order history.
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import Order
from modules.voice.pipeline import process_voice_order
from modules.voice.order_builder import build_order, generate_kot, save_order_to_db

router = APIRouter()


class TextInput(BaseModel):
    text: str
    session_id: str | None = None


class ConfirmOrderInput(BaseModel):
    order: dict
    kot: dict | None = None


# ── 1. POST /api/voice/transcribe ──

@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Audio → transcript only (no order processing).
    Returns: {transcript, detected_language, confidence}
    """
    audio_path = None
    try:
        suffix = Path(audio.filename).suffix or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            content = await audio.read()
            tmp.write(content)
            audio_path = tmp.name

        # Use only STT
        from modules.voice.stt import transcribe_audio as stt_transcribe
        result = stt_transcribe(audio_path)

        return {
            "transcript": result if isinstance(result, str) else result.get("transcript", ""),
            "detected_language": result.get("detected_language", "en") if isinstance(result, dict) else "en",
            "confidence": result.get("confidence", 0.0) if isinstance(result, dict) else 0.0,
        }
    except Exception as e:
        return {"transcript": "", "error": str(e)}
    finally:
        if audio_path:
            Path(audio_path).unlink(missing_ok=True)


# ── 2. POST /api/voice/process-audio ──

@router.post("/process-audio")
async def process_audio(
    audio: UploadFile = File(...),
    session_id: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Full pipeline: audio → transcript → parsed order → upsell suggestions.
    Returns: {transcript, intent, order, upsell_suggestions}
    """
    audio_path = None
    try:
        suffix = Path(audio.filename).suffix or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            content = await audio.read()
            tmp.write(content)
            audio_path = tmp.name

        result = process_voice_order(
            db=db,
            audio_path=audio_path,
            session_id=session_id,
        )
        return result
    except Exception as e:
        return {"error": str(e), "order": None, "upsells": []}
    finally:
        if audio_path:
            Path(audio_path).unlink(missing_ok=True)


# ── 3. POST /api/voice/process ──

@router.post("/process")
def process_text(
    body: TextInput,
    db: Session = Depends(get_db),
):
    """
    Text → full pipeline result (for testing without microphone).
    Accepts: {text: string}
    Returns: same as /process-audio but from text input
    """
    result = process_voice_order(
        db=db,
        text_input=body.text,
        session_id=body.session_id,
    )
    return result


# ── 4. POST /api/voice/confirm-order ──

@router.post("/confirm-order")
def confirm_order(
    body: ConfirmOrderInput,
    db: Session = Depends(get_db),
):
    """
    Save confirmed order to DB.
    Accepts: {order: {...}}
    Returns: {order_id, kot}
    """
    order = body.order
    kot = body.kot

    # Generate KOT if not provided
    if not kot:
        kot = generate_kot(order)

    # Save to database
    try:
        result = save_order_to_db(order, kot, db)
        return {
            "success": True,
            "order_id": result["order_id"],
            "kot_id": result["kot_id"],
            "kot": kot,
            "status": "confirmed",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── 5. GET /api/voice/orders ──

@router.get("/orders")
def get_recent_orders(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Recent orders list (last 50), sorted by created_at desc.
    """
    orders = (
        db.query(Order)
        .order_by(desc(Order.created_at))
        .limit(limit)
        .all()
    )

    return {
        "orders": [
            {
                "order_id": o.order_id,
                "order_number": o.order_number,
                "total_amount": o.total_amount,
                "status": o.status,
                "order_type": o.order_type,
                "table_number": o.table_number,
                "source": o.source,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ],
        "count": len(orders),
    }


# ── Legacy endpoints for backward compatibility ──

@router.post("/order")
async def voice_order_legacy(
    audio: UploadFile = File(None),
    text: str = None,
    session_id: str = None,
    db: Session = Depends(get_db),
):
    """Legacy endpoint — process voice or text order."""
    audio_path = None

    if audio and audio.filename:
        suffix = Path(audio.filename).suffix or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            content = await audio.read()
            tmp.write(content)
            audio_path = tmp.name

    result = process_voice_order(
        db=db,
        audio_path=audio_path,
        text_input=text,
        session_id=session_id,
    )

    if audio_path:
        Path(audio_path).unlink(missing_ok=True)

    return result
