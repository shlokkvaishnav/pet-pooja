"""
Petpooja AI Copilot — FastAPI Application Entry Point
======================================================
Supabase PostgreSQL database, faster-whisper STT, rule-based NLP.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import engine, Base
from api.routes_revenue import router as revenue_router
from api.routes_voice import router as voice_router

# ── Structured logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("petpooja")

# ── Allowed origins (configurable via env, defaults to localhost for safety) ──
_ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
).split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables and load pipeline on startup."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Petpooja AI Copilot — Server ready")
    logger.info("Revenue engine loaded")

    # Load voice pipeline into app.state for shared access
    try:
        from modules.voice.pipeline import process_voice_order
        app.state.pipeline = process_voice_order
        logger.info("Voice pipeline ready (faster-whisper)")
    except Exception as e:
        logger.warning("Voice pipeline load warning: %s", e)
        logger.info("Voice endpoints will still work but may be slower on first call")
        app.state.pipeline = None

    yield
    logger.info("Server shutting down...")


app = FastAPI(
    title="Petpooja AI Copilot",
    description="Restaurant Revenue Intelligence & Voice Ordering — Supabase PostgreSQL backend",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# ── Global exception handler ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# ── Route registration ──
app.include_router(revenue_router, prefix="/api/revenue", tags=["Revenue"])
app.include_router(voice_router, prefix="/api/voice", tags=["Voice"])


@app.get("/api/health")
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "petpooja-ai-copilot",
        "version": "0.2.0",
        "pipeline_loaded": hasattr(app.state, "pipeline") and app.state.pipeline is not None,
    }


@app.get("/health")
def health_root():
    """Root health check (alias)."""
    return health()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
