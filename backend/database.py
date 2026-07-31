"""
Database connection and session management.

Supports SQLite for local dev and Postgres (Supabase) for production.
Swap the DATABASE_URL env var to switch — SQLAlchemy handles the rest.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load .env if present (local dev); env vars set on the host always win
load_dotenv()

# Read DATABASE_URL from environment, default to local SQLite
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./finpulse.db",
)

# SQLite-specific: allow same connection across threads (needed for FastAPI)
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,       # verify connections before using them
    echo=False,                # set True for SQL debug logging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency that yields a DB session and ensures cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Create all tables defined by ORM models that inherit from Base.
    Called once at startup.
    """
    from models import Company, StockPrice, Fundamental  # noqa: F401 — triggers registration
    Base.metadata.create_all(bind=engine)
