"""
Background scheduler — refreshes market data on a configurable interval.

Uses APScheduler to run refresh_all() periodically. The scheduler lives
inside the FastAPI process so it starts/stops with the app.

Interval default: 30 minutes (configurable via REFRESH_INTERVAL_MIN env var).
"""

import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("finpulse.scheduler")

# How often to refresh (minutes) — override with env var
REFRESH_INTERVAL_MIN = int(os.getenv("REFRESH_INTERVAL_MIN", "30"))


def _scheduled_refresh():
    """
    Callback invoked by APScheduler.
    Creates its own DB session since it runs outside the request lifecycle.
    """
    from database import SessionLocal
    from services.data_fetcher import refresh_all

    logger.info("[scheduler] Starting scheduled refresh …")
    session = SessionLocal()
    try:
        summary = refresh_all(session, days=30)
        logger.info("[scheduler] Refresh complete: %s", summary)
    except Exception as exc:
        logger.error("[scheduler] Refresh failed: %s", exc)
    finally:
        session.close()


# Module-level scheduler instance (created once, started by main.py)
scheduler = BackgroundScheduler(
    job_defaults={
        "coalesce": True,           # if missed runs pile up, only run once
        "max_instances": 1,         # never run two refreshes concurrently
        "misfire_grace_time": 300,  # allow 5 min grace period
    }
)


def start_scheduler():
    """
    Register the refresh job and start the scheduler.
    Called once from main.py lifespan startup.
    """
    scheduler.add_job(
        _scheduled_refresh,
        trigger=IntervalTrigger(minutes=REFRESH_INTERVAL_MIN),
        id="market_refresh",
        name=f"Market data refresh every {REFRESH_INTERVAL_MIN}m",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "[scheduler] Started — refreshing every %d minutes",
        REFRESH_INTERVAL_MIN,
    )


def stop_scheduler():
    """Gracefully shut down the scheduler. Called on app shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[scheduler] Stopped.")
