"""
database.py — SQLAlchemy Engine & Session (Supabase PostgreSQL)
=================================================================
Connects to Supabase-hosted PostgreSQL via connection string in .env
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load .env from backend/ directory
load_dotenv(Path(__file__).parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL not set. Create backend/.env with:\n"
        "  DATABASE_URL=postgresql+psycopg2://postgres.<ref>:<password>@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
    )

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,   # reconnect on stale connections
    echo=False,
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
