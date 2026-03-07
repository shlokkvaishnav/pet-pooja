"""
database.py - SQLAlchemy Engine & Session
=========================================
Local-first database setup for reliable development:
- Uses SQLite by default.
- Uses DATABASE_URL only when USE_REMOTE_DATABASE=true.
- Falls back to SQLite automatically if remote DB is unreachable.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger("petpooja.database")

# Load .env - try backend dir first, then project root.
_backend_dir = Path(__file__).parent
_project_root = _backend_dir.parent
load_dotenv(_backend_dir / ".env")
load_dotenv(_project_root / ".env")

_sqlite_path = Path(os.getenv("SQLITE_DB_PATH", _backend_dir / "petpooja.db"))
_sqlite_url = f"sqlite:///{_sqlite_path}"
_remote_database_url = os.getenv("DATABASE_URL", "").strip()
_use_remote_database = os.getenv("USE_REMOTE_DATABASE", "false").lower() in ("1", "true", "yes")


def _build_sqlite_engine():
    logger.info("Using local SQLite database at %s", _sqlite_path)
    return create_engine(
        _sqlite_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )


DATABASE_URL = _sqlite_url
engine = _build_sqlite_engine()

if _use_remote_database and _remote_database_url:
    try:
        remote_engine = create_engine(
            _remote_database_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False,
        )
        with remote_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine = remote_engine
        DATABASE_URL = _remote_database_url
        logger.info("Connected to remote PostgreSQL database")
    except Exception as exc:
        logger.warning("Remote database unavailable; falling back to SQLite: %s", exc)
elif _use_remote_database and not _remote_database_url:
    logger.warning("USE_REMOTE_DATABASE=true but DATABASE_URL is empty; using SQLite")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency - yields a DB session and closes it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
