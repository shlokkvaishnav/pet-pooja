"""
deps.py — Shared API dependencies
=================================
Centralizes common FastAPI dependencies to avoid circular imports.
"""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db


def get_voice_pipeline(
    request: Request,
    db: Session = Depends(get_db),  # keeps DB available if needed later
):
    """Resolve the VoicePipeline from app state."""
    pipeline = getattr(request.app.state, "voice_pipeline", None)
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Voice pipeline not loaded")
    return pipeline

