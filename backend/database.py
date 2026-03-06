"""
database.py — SQLAlchemy Engine & Session (Supabase PostgreSQL)
=================================================================
Connects to Supabase-hosted PostgreSQL via connection string in .env.
Falls back to local SQLite for development if DATABASE_URL is not set.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger("petpooja.database")

# Load .env — try backend/ dir first, then project root
_backend_dir = Path(__file__).parent
_project_root = _backend_dir.parent
load_dotenv(_backend_dir / ".env")
load_dotenv(_project_root / ".env")  # fallback to project root .env

from config import DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_RECYCLE, SQLITE_PATH

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=DB_POOL_RECYCLE,
        echo=False,
    )
    logger.info("Connected to PostgreSQL database")
else:
    # Fallback to local SQLite for development / testing
    DATABASE_URL = f"sqlite:///{SQLITE_PATH}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    logger.warning(
        "DATABASE_URL not set — using local SQLite at %s. "
        "Set DATABASE_URL in backend/.env for production.",
        SQLITE_PATH,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and closes it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
