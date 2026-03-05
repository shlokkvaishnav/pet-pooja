"""
Petpooja AI Copilot -- FastAPI Application Entry Point
======================================================
No external APIs -- everything runs locally.
SQLite database, faster-whisper STT, rule-based NLP.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base, SessionLocal
from api.routes_revenue import router as revenue_router
from api.routes_voice import router as voice_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables and load VoicePipeline with menu data from DB."""
    Base.metadata.create_all(bind=engine)

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
            combo_rules=[],       # D fills this from combo_engine
            hidden_stars=[],      # A fills this from hidden_stars
        )

        print(f"Petpooja AI Copilot -- Server ready")
        print(f"Revenue engine loaded")
        print(f"Voice pipeline loaded with {len(menu_items)} menu items from DB")
    except Exception as e:
        print(f"Warning: Voice pipeline failed to load: {e}")
        print("Text-only pipeline will still work")

    yield

    db.close()
    print("Server shutting down...")


app = FastAPI(
    title="Petpooja AI Copilot",
    description="Restaurant Revenue Intelligence & Voice Ordering -- fully offline, no external APIs",
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

# -- Route registration --
app.include_router(revenue_router, prefix="/api/revenue", tags=["Revenue"])
app.include_router(voice_router, prefix="/api/voice", tags=["Voice"])


@app.get("/api/health")
def health():
    return {"status": "healthy", "service": "petpooja-ai-copilot", "mode": "offline"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
