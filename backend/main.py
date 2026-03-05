"""
Petpooja AI Copilot — FastAPI Application Entry Point
======================================================
Supabase PostgreSQL database, faster-whisper STT, rule-based NLP.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from api.routes_revenue import router as revenue_router
from api.routes_voice import router as voice_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables and load pipeline on startup."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("🚀 Petpooja AI Copilot — Server ready")
    print("📊 Revenue engine loaded")

    # Load voice pipeline into app.state for shared access
    try:
        from modules.voice.pipeline import process_voice_order
        app.state.pipeline = process_voice_order
        print("🎙️ Voice pipeline ready (faster-whisper)")
    except Exception as e:
        print(f"⚠️ Voice pipeline load warning: {e}")
        print("   Voice endpoints will still work but may be slower on first call")
        app.state.pipeline = None

    yield
    print("Server shutting down...")


app = FastAPI(
    title="Petpooja AI Copilot",
    description="Restaurant Revenue Intelligence & Voice Ordering — Supabase PostgreSQL backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        "mode": "offline",
        "pipeline_loaded": hasattr(app.state, "pipeline") and app.state.pipeline is not None,
    }


@app.get("/health")
def health_root():
    """Root health check (alias)."""
    return health()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
