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
from api.routes_ops import router as ops_router
from api.routes_voice import router as voice_router
from api.routes_auth import router as auth_router
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
_ALLOWED_ORIGINS = [origin.strip() for origin in _ALLOWED_ORIGINS if origin.strip()]


def _run_auto_migrations(eng):
    """Add any columns defined in ORM models but missing from the live DB.
    Safe to run repeatedly — uses ADD COLUMN IF NOT EXISTS (Postgres)
    or tries/catches for SQLite."""
    from sqlalchemy import inspect as sa_inspect, text
    inspector = sa_inspect(eng)
    is_pg = "postgres" in str(eng.url)
    for table in Base.metadata.tables.values():
        if not inspector.has_table(table.name):
            continue  # create_all will handle new tables
        existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing_cols:
                continue
            col_type = col.type.compile(eng.dialect)
            nullable = "" if col.nullable else " NOT NULL"
            default = ""
            if col.default is not None and col.default.arg is not None and isinstance(col.default.arg, (str, int, float, bool)):
                default = f" DEFAULT {repr(col.default.arg)}"
            if is_pg:
                stmt = f'ALTER TABLE "{table.name}" ADD COLUMN IF NOT EXISTS "{col.name}" {col_type}{nullable}{default}'
            else:
                stmt = f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col_type}{default}'
            try:
                with eng.begin() as conn:
                    conn.execute(text(stmt))
                logger.info("Migration: added column %s.%s", table.name, col.name)
            except Exception as exc:
                # Column may already exist (SQLite has no IF NOT EXISTS for columns)
                logger.debug("Column %s.%s skipped: %s", table.name, col.name, exc)

    # ── Fix column type mismatches ──────────────────────────────────────
    # restaurant_tables.current_order_id should be INTEGER referencing
    # orders.id (integer PK) for better join performance.
    # The seed script already creates it as INTEGER.  If an older DB has
    # it as VARCHAR, convert it back to INTEGER.
    if is_pg:
        try:
            with eng.begin() as conn:
                # Drop any stale FK constraint (either naming convention)
                conn.execute(text(
                    'ALTER TABLE "restaurant_tables" '
                    'DROP CONSTRAINT IF EXISTS "restaurant_tables_current_order_id_fkey"'
                ))
                conn.execute(text(
                    'ALTER TABLE "restaurant_tables" '
                    'DROP CONSTRAINT IF EXISTS "fk_tables_current_order"'
                ))
                conn.execute(text(
                    'ALTER TABLE "restaurant_tables" '
                    'ALTER COLUMN "current_order_id" TYPE INTEGER USING "current_order_id"::INTEGER'
                ))
                conn.execute(text(
                    'ALTER TABLE "restaurant_tables" '
                    'ADD CONSTRAINT "fk_tables_current_order" '
                    'FOREIGN KEY ("current_order_id") REFERENCES orders(id) ON DELETE SET NULL'
                ))
                logger.info("Migration: ensured restaurant_tables.current_order_id → INTEGER FK to orders(id)")
        except Exception as exc:
            logger.debug("current_order_id type migration skipped: %s", exc)


def _background_warmup(app_state):
    """Run heavy ML model warmups in a background thread so the server
    starts accepting requests immediately."""
    # -- Whisper STT --
    try:
        from modules.voice.stt import warmup as stt_warmup
        stt_warmup()
    except Exception as e:
        logger.warning(f"Whisper model warmup failed (will lazy-load on first request): {e}")

    # -- Semantic model --
    try:
        from modules.voice.item_matcher import warmup_semantic_model
        warmup_semantic_model()
    except Exception as e:
        logger.warning(f"Semantic model warmup failed (will lazy-load on first use): {e}")

    # -- TTS engine --
    try:
        from modules.voice.voice_config import cfg as voice_cfg
        if voice_cfg.TTS_ENABLED:
            from modules.voice.tts_engine_indic import indic_engine
            indic_engine.warmup()
        else:
            logger.info("TTS is disabled via config — skipping warmup")
    except Exception as e:
        logger.warning(f"TTS engine warmup failed (TTS will be unavailable): {e}")

    # -- Ollama LLM reachability --
    try:
        from modules.voice.voice_config import cfg as voice_cfg
        if voice_cfg.LLM_ENABLED:
            import httpx
            try:
                resp = httpx.get(f"{voice_cfg.LLM_BASE_URL}/api/tags", timeout=3.0)
                if resp.status_code == 200:
                    models = [m.get("name", "") for m in resp.json().get("models", [])]
                    logger.info(f"Ollama reachable — available models: {models}")
                else:
                    logger.warning(f"Ollama responded with status {resp.status_code}")
            except Exception as e:
                logger.warning(f"Ollama not reachable at {voice_cfg.LLM_BASE_URL}: {e}")
                logger.warning("LLM summarization will use template fallbacks")
        else:
            logger.info("LLM is disabled via config — skipping Ollama check")
    except Exception as e:
        logger.warning(f"Ollama check failed: {e}")

    logger.info("Background warmup complete — all ML models ready")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables and load VoicePipeline with menu data from DB."""
    import threading

    Base.metadata.create_all(bind=engine)
    _run_auto_migrations(engine)

    # -- DYNAMIC: Load menu from DATABASE (fast — just a DB query) --
    db = SessionLocal()
    try:
        from models import MenuItem
        from modules.voice.pipeline import VoicePipeline

        menu_items = db.query(MenuItem).filter(
            MenuItem.is_available == True
        ).all()

        # Build pipeline with DB data -- no hardcoded items
        app.state.voice_pipeline = VoicePipeline(
            menu_items=menu_items,
            combo_rules=[],
            hidden_stars=[],
        )

        logger.info(f"Voice pipeline loaded with {len(menu_items)} menu items from DB")
    except Exception as e:
        logger.warning(f"Voice pipeline failed to load: {e}")
        logger.info("Text-only pipeline will still work")
        app.state.voice_pipeline = None
    finally:
        db.close()

    # -- Combo training is now lazy: runs inline on first GET /combos request --
    # No background scheduler needed — avoids race conditions during hot-reload.
    logger.info("Combo engine: lazy inline training enabled (no startup scheduler)")

    # -- DEFERRED: Heavy ML warmups in a background thread --
    warmup_thread = threading.Thread(
        target=_background_warmup,
        args=(app.state,),
        daemon=True,
        name="ml-warmup",
    )
    warmup_thread.start()

    logger.info("Petpooja AI Copilot — Server ready (ML models warming up in background)")
    logger.info("Revenue engine loaded")

    yield
    # -- Shutdown: stop combo scheduler --
    try:
        from modules.revenue.combo_engine import stop_combo_scheduler
        stop_combo_scheduler()
    except Exception:
        pass
    logger.info("Server shutting down...")


_APP_TITLE = os.getenv("APP_TITLE", "Sizzle AI Copilot")
_APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "Restaurant Revenue Intelligence & Voice Ordering")
_APP_VERSION = os.getenv("APP_VERSION", "0.2.0")

app = FastAPI(
    title=_APP_TITLE,
    description=_APP_DESCRIPTION,
    version=_APP_VERSION,
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
    include_detail = os.getenv("EXPOSE_ERROR_DETAILS", "false").lower() in ("1", "true", "yes")
    content = {"error": "Internal server error"}
    if include_detail:
        content["detail"] = str(exc)
    return JSONResponse(
        status_code=500,
        content=content,
    )


# ── Route registration (auth-gated when AUTH_ENABLED=true) ──
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
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
app.include_router(
    ops_router,
    prefix="/api/ops",
    tags=["Operations"],
    dependencies=[Depends(require_auth)],
)


# ── Auth endpoints (always public) ──

class LoginInput(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6, pattern=r"^\d{4,6}$")


@app.post("/api/auth/staff-login", tags=["Auth"])
def staff_login(body: LoginInput, db=Depends(get_db)):
    """Authenticate staff via PIN → JWT token."""
    return authenticate_staff(body.pin, db)


# ── FAISS index management ──

@app.post("/api/voice/rebuild-index", tags=["Voice"], dependencies=[Depends(require_auth)])
def rebuild_faiss_index(db=Depends(get_db)):
    """
    Force-rebuild the FAISS semantic index from current DB menu items.
    Call this after menu item create/update/delete to keep the index current.
    """
    from models import MenuItem
    from modules.voice.item_matcher import rebuild_index

    corpus = rebuild_index(db)
    menu_items = db.query(MenuItem).filter(MenuItem.is_available == True).all()

    # Also update the pipeline's menu + corpus reference
    pipeline = getattr(app.state, "voice_pipeline", None)
    if pipeline:
        pipeline.refresh_menu(menu_items, corpus=corpus)

    return {"status": "ok", "corpus_size": len(corpus), "menu_items": len(menu_items)}


@app.post("/api/voice/reload-menu", tags=["Voice"], dependencies=[Depends(require_auth)])
def reload_menu(db=Depends(get_db)):
    """
    Refresh menu items in the voice pipeline without rebuilding the FAISS index.
    This updates the fuzzy corpus and in-memory menu references only.
    """
    from models import MenuItem

    menu_items = db.query(MenuItem).filter(MenuItem.is_available == True).all()
    pipeline = getattr(app.state, "voice_pipeline", None)
    if not pipeline:
        return {"status": "error", "detail": "Voice pipeline not loaded"}

    pipeline.refresh_menu(menu_items)
    return {"status": "ok", "menu_items": len(menu_items), "corpus_size": len(pipeline.corpus)}


@app.get("/api/health")
def health():
    """Health check endpoint with TTS + LLM status."""
    result = {
        "status": "healthy",
        "service": "sizzle-ai-copilot",
        "version": _APP_VERSION,
        "pipeline_loaded": getattr(app.state, "voice_pipeline", None) is not None,
    }

    # TTS status
    try:
        from modules.voice.voice_config import cfg as voice_cfg
        if voice_cfg.TTS_ENABLED:
            from modules.voice.tts_engine_indic import indic_engine
            result["tts"] = indic_engine.get_status()
        else:
            result["tts"] = {"status": "disabled"}
    except Exception:
        result["tts"] = {"status": "error"}

    # LLM status
    try:
        from modules.voice.voice_config import cfg as voice_cfg
        if voice_cfg.LLM_ENABLED:
            result["llm"] = {
                "status": "configured",
                "model": voice_cfg.LLM_MODEL,
                "backend": "ollama",
                "base_url": voice_cfg.LLM_BASE_URL,
                "used_for": ["complex_order_summary", "upsell", "query", "ambiguous_3plus"],
            }
        else:
            result["llm"] = {"status": "disabled"}
    except Exception:
        result["llm"] = {"status": "error"}

    return result


@app.get("/health")
def health_root():
    """Root health check (alias)."""
    return health()


if __name__ == "__main__":
    import uvicorn

    _host = os.getenv("HOST", "0.0.0.0")
    _port = int(os.getenv("PORT", "8000"))
    _reload = os.getenv("RELOAD", "false").lower() in ("1", "true", "yes")
    uvicorn.run("main:app", host=_host, port=_port, reload=_reload)
