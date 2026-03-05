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

# Load .env from backend/ directory
load_dotenv(Path(__file__).parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300,  # recycle connections every 5 min
        echo=False,
    )
    logger.info("Connected to PostgreSQL database")
else:
    # Fallback to local SQLite for development / testing
    _sqlite_path = Path(__file__).parent / "petpooja.db"
    DATABASE_URL = f"sqlite:///{_sqlite_path}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    logger.warning(
        "DATABASE_URL not set — using local SQLite at %s. "
        "Set DATABASE_URL in backend/.env for production.",
        _sqlite_path,
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
