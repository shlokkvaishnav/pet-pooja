"""
database.py — SQLAlchemy Engine & Session
==========================================
Connects to Supabase (PostgreSQL) via DATABASE_URL env var.
Set DATABASE_URL in a .env file or environment variable.
Format: postgresql://user:password@host:port/dbname
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL not set. Add it to .env file.\n"
        "Format: postgresql://postgres.<ref>:<password>@<host>:5432/postgres"
    )

engine = create_engine(
    DATABASE_URL,
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
