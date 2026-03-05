"""
routes_voice.py — Voice Ordering API Endpoints
================================================
/api/voice/* — Transcription, full pipeline processing,
order confirmation, and order history.
"""

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from database import get_db
from models import Order
from modules.voice.pipeline import process_voice_order
from modules.voice.order_builder import build_order, generate_kot, save_order_to_db

router = APIRouter()
logger = logging.getLogger("petpooja.api.voice")

# Max audio file size: 10 MB
_MAX_AUDIO_SIZE = 10 * 1024 * 1024
_ALLOWED_EXTENSIONS = {".wav", ".mp3", ".ogg", ".webm", ".m4a", ".flac"}


class TextInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None


class ConfirmOrderInput(BaseModel):
    order: dict
    kot: dict | None = None


async def _save_audio_temp(audio: UploadFile) -> str:
    """Validate and save uploaded audio to a temp file. Returns path."""
    suffix = Path(audio.filename or "audio.wav").suffix.lower() or ".wav"
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format '{suffix}'. Allowed: {', '.join(_ALLOWED_EXTENSIONS)}",
        )

    content = await audio.read()
    if len(content) > _MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Audio file too large ({len(content)} bytes). Max: {_MAX_AUDIO_SIZE} bytes.",
        )
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(content)
        tmp.flush()
        return tmp.name
    finally:
        tmp.close()


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
    audio_path = await _save_audio_temp(audio)
    try:
        from modules.voice.stt import transcribe_audio as stt_transcribe
        result = stt_transcribe(audio_path)

        return {
            "transcript": result if isinstance(result, str) else result.get("transcript", ""),
            "detected_language": result.get("detected_language", "en") if isinstance(result, dict) else "en",
            "confidence": result.get("confidence", 0.0) if isinstance(result, dict) else 0.0,
        }
    except Exception as e:
        logger.exception("Transcription failed")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    finally:
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
    audio_path = await _save_audio_temp(audio)
    try:
        result = process_voice_order(
            db=db,
            audio_path=audio_path,
            session_id=session_id,
        )
        return result
    except Exception as e:
        logger.exception("Voice pipeline failed")
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {e}")
    finally:
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
    try:
        result = process_voice_order(
            db=db,
            text_input=body.text,
            session_id=body.session_id,
        )
        return result
    except Exception as e:
        logger.exception("Text processing failed")
        raise HTTPException(status_code=500, detail=f"Text processing failed: {e}")


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
    if not order or not order.get("items"):
        raise HTTPException(status_code=400, detail="Order must contain items.")

    kot = body.kot
    if not kot:
        kot = generate_kot(order)

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
        logger.exception("Order confirmation failed")
        raise HTTPException(status_code=500, detail=f"Order save failed: {e}")


# ── 5. GET /api/voice/orders ──

@router.get("/orders")
def get_recent_orders(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Recent orders with pagination, sorted by created_at desc.
    """
    total = db.query(func.count(Order.id)).scalar() or 0

    orders = (
        db.query(Order)
        .order_by(desc(Order.created_at))
        .offset(offset)
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
        "total": total,
        "offset": offset,
        "limit": limit,
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

    try:
        if audio and audio.filename:
            audio_path = await _save_audio_temp(audio)

        result = process_voice_order(
            db=db,
            audio_path=audio_path,
            text_input=text,
            session_id=session_id,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Legacy voice order failed")
        raise HTTPException(status_code=500, detail=f"Voice order failed: {e}")
    finally:
        if audio_path:
            Path(audio_path).unlink(missing_ok=True)
