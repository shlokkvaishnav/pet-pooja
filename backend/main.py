"""
Petpooja AI Copilot -- FastAPI Application Entry Point
======================================================
Supabase PostgreSQL database, faster-whisper STT, rule-based NLP.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from database import engine, Base, SessionLocal, get_db
from api.routes_revenue import router as revenue_router
from api.routes_voice import router as voice_router
from api.auth import require_auth, authenticate_staff
from api.rate_limit import rate_limit_middleware

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

    yield
    db.close()
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

# ── Rate limiting middleware ──
app.middleware("http")(rate_limit_middleware)


# ── Global exception handler ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# ── Route registration (auth-gated when AUTH_ENABLED=true) ──
app.include_router(
    revenue_router,
    prefix="/api/revenue",
    tags=["Revenue"],
    dependencies=[Depends(require_auth)],
)
app.include_router(
    voice_router,
    prefix="/api/voice",
    tags=["Voice"],
    dependencies=[Depends(require_auth)],
)


# ── Auth endpoints (always public) ──

class LoginInput(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6, pattern=r"^\d{4,6}$")


@app.post("/api/auth/login", tags=["Auth"])
def login(body: LoginInput, db=Depends(get_db)):
    """Authenticate staff via PIN → JWT token."""
    return authenticate_staff(body.pin, db)


# ── FAISS index management ──

@app.post("/api/voice/rebuild-index", tags=["Voice"], dependencies=[Depends(require_auth)])
def rebuild_faiss_index(db=Depends(get_db)):
    """
    Force-rebuild the FAISS semantic index from current DB menu items.
    Call this after menu item create/update/delete to keep the index current.
    """
    from modules.voice.item_matcher import rebuild_index
    corpus = rebuild_index(db)
    # Also update the pipeline's corpus reference
    pipeline = getattr(app.state, "voice_pipeline", None)
    if pipeline:
        pipeline.corpus = corpus
    return {"status": "ok", "corpus_size": len(corpus)}


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
