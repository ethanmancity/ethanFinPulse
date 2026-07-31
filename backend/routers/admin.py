"""
Admin endpoints — manual refresh, DB health, etc.
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from schemas import RefreshResponse
from services.data_fetcher import refresh_all

router = APIRouter(prefix="/admin", tags=["admin"])


def _run_refresh(days: int = 365):
    """
    Background task — creates its own DB session so it doesn't
    tie up the request lifecycle.
    """
    from database import SessionLocal
    session = SessionLocal()
    try:
        refresh_all(session, days=days)
    finally:
        session.close()


@router.post("/refresh", response_model=RefreshResponse)
def trigger_refresh(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    days: int = 30,
):
    """
    Trigger a manual data refresh.
    Runs in the background so the endpoint returns immediately.
    Optionally pass ?days=N to control how many days of history to fetch (default 30).
    """
    from models import Company
    count = db.query(Company).count()
    if count == 0:
        return RefreshResponse(
            status="skipped",
            message="No companies in DB. Run seed.py first.",
        )

    background_tasks.add_task(_run_refresh, days=days)
    return RefreshResponse(
        status="started",
        message=f"Refresh started in background for {count} companies (last {days} days). "
                "Check server logs for progress.",
        summary={"companies_queued": count},
    )


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Simple DB health check."""
    from models import Company
    count = db.query(Company).count()
    return {"status": "ok", "companies_tracked": count}
