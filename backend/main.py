"""
Petpooja AI Copilot -- FastAPI Application Entry Point
======================================================
Supabase PostgreSQL database, faster-whisper STT, rule-based NLP.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import engine, Base, SessionLocal
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
    """Create DB tables and load VoicePipeline with menu data from DB."""
    Base.metadata.create_all(bind=engine)
    logger.info("Petpooja AI Copilot — Server ready")
    logger.info("Revenue engine loaded")

    # -- PRE-LOAD: Warm up ML models before the first request arrives --
    try:
        from modules.voice.stt import warmup as stt_warmup
        stt_warmup()
    except Exception as e:
        logger.warning(f"Whisper model warmup failed (will lazy-load on first request): {e}")

    try:
        from modules.voice.item_matcher import warmup_semantic_model
        warmup_semantic_model()
    except Exception as e:
        logger.warning(f"Semantic model warmup failed (will lazy-load on first use): {e}")

    # -- DYNAMIC: Load menu from DATABASE --
    db = SessionLocal()
    try:
        from models import MenuItem
        from modules.voice.pipeline import VoicePipeline

        menu_items = db.query(MenuItem).filter(
            MenuItem.is_available == True
        ).all()

        # Build pipeline with DB data -- no hardcoded items
        app.state.voice_pipeline = VoicePipeline(
            db_session=db,
            menu_items=menu_items,
            combo_rules=[],
            hidden_stars=[],
        )

        logger.info(f"Voice pipeline loaded with {len(menu_items)} menu items from DB")
    except Exception as e:
        logger.warning(f"Voice pipeline failed to load: {e}")
        logger.info("Text-only pipeline will still work")
        app.state.voice_pipeline = None

    # -- Start background combo training scheduler --
    try:
        from modules.revenue.combo_engine import start_combo_scheduler
        start_combo_scheduler(SessionLocal)
    except Exception as e:
        logger.warning(f"Combo scheduler failed to start: {e}")

    yield
    # -- Shutdown: stop combo scheduler --
    try:
        from modules.revenue.combo_engine import stop_combo_scheduler
        stop_combo_scheduler()
    except Exception:
        pass
    db.close()
    logger.info("Server shutting down...")


app = FastAPI(
    title="Petpooja AI Copilot",
    description="Restaurant Revenue Intelligence & Voice Ordering — Supabase PostgreSQL backend",
    version="0.2.0",
    lifespan=lifespan,
)

# ── Rate limiter (per-IP) ──
_RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
limiter = Limiter(key_func=get_remote_address, default_limits=[_RATE_LIMIT_DEFAULT])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
