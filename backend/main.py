"""
FinPulse — FastAPI application entrypoint.

Run locally:
    cd backend
    uvicorn main:app --reload --port 8000

Docs available at:
    http://localhost:8000/docs      (Swagger UI)
    http://localhost:8000/redoc     (ReDoc)
"""

import os
import sys
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend/ is on sys.path for relative imports
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db
from routers import stocks, market_summary, admin

# ── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-24s  %(levelname)-5s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("finpulse")

# ── Lifespan (startup / shutdown) ──────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup, optionally seed data."""
    logger.info("Initializing database …")
    init_db()
    logger.info("Database ready.")

    # Auto-seed companies if the table is empty
    from database import SessionLocal
    from models import Company
    from seed import TRACKED_COMPANIES
    session = SessionLocal()
    try:
        existing = session.query(Company).count()
        if existing == 0:
            logger.info("Companies table empty — auto-seeding %d companies …", len(TRACKED_COMPANIES))
            from seed import seed_companies
            seed_companies(session)
            logger.info("Auto-seed complete.")
        else:
            logger.info("Companies table has %d entries — skipping auto-seed.", existing)
    finally:
        session.close()

    # Start background scheduler
    from services.scheduler import start_scheduler, stop_scheduler
    start_scheduler()

    yield

    stop_scheduler()
    logger.info("Shutting down FinPulse.")


# ── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="FinPulse API",
    description=(
        "Stock market monitoring platform — tracks 24 NSE-listed Indian companies, "
        "serves live + historical market data, fundamentals, and comparison endpoints."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Streamlit (localhost:8501) and any deployed frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ───────────────────────────────────────────────────────

app.include_router(stocks.router)
app.include_router(market_summary.router)
app.include_router(admin.router)


# ── Root endpoint ───────────────────────────────────────────────────────────

@app.get("/", tags=["root"])
def root():
    return {
        "app": "FinPulse",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "stocks": "/stocks",
            "stock_detail": "/stocks/{ticker}",
            "history": "/stocks/{ticker}/history?range=1mo",
            "compare": "POST /stocks/compare",
            "market_summary": "/market-summary",
            "refresh": "POST /admin/refresh",
            "health": "/admin/health",
        },
    }
