"""
Stock endpoints — /stocks and /stocks/{ticker}.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Company, StockPrice, Fundamental
from schemas import (
    StockSummary, StockDetail, StockPriceOut,
    FundamentalOut, CompareResponse, CompareRequest,
)

router = APIRouter(prefix="/stocks", tags=["stocks"])


def _latest_price(session: Session, ticker: str) -> Optional[StockPrice]:
    """Return the most recent StockPrice row for a ticker."""
    return (
        session.query(StockPrice)
               .filter(StockPrice.ticker == ticker)
               .order_by(StockPrice.date.desc())
               .first()
    )


def _latest_fundamental(session: Session, ticker: str) -> Optional[Fundamental]:
    """Return the most recent Fundamental row for a ticker."""
    return (
        session.query(Fundamental)
               .filter(Fundamental.ticker == ticker)
               .order_by(Fundamental.snapshot_date.desc())
               .first()
    )


def _to_summary(company: Company, session: Session) -> StockSummary:
    """Build a StockSummary from a Company + latest price + fundamentals."""
    price = _latest_price(session, company.ticker)
    fund = _latest_fundamental(session, company.ticker)
    return StockSummary(
        ticker=company.ticker,
        name=company.name,
        sector=company.sector,
        exchange=company.exchange,
        latest_price=price.close if price else None,
        pct_change=fund.pct_change if fund else None,
        market_cap=fund.market_cap if fund else None,
        pe_ratio=fund.pe_ratio if fund else None,
        eps=fund.eps if fund else None,
    )


# ── GET /stocks — list all tracked companies ────────────────────────────────

@router.get("", response_model=list[StockSummary])
def list_stocks(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    db: Session = Depends(get_db),
):
    """Return all tracked companies with their latest snapshot."""
    query = db.query(Company)
    if sector:
        query = query.filter(Company.sector.ilike(f"%{sector}%"))
    companies = query.order_by(Company.ticker).all()
    return [_to_summary(c, db) for c in companies]


# ── GET /stocks/{ticker} — full detail for one company ─────────────────────

@router.get("/{ticker}", response_model=StockDetail)
def get_stock(ticker: str, db: Session = Depends(get_db)):
    """
    Full detail for a single company including latest fundamentals.
    Historical prices are available via /stocks/{ticker}/history.
    """
    ticker = ticker.upper()
    if not ticker.endswith(".NS"):
        ticker += ".NS"

    company = db.query(Company).filter(Company.ticker == ticker).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    fund = _latest_fundamental(db, ticker)
    return StockDetail(
        ticker=company.ticker,
        name=company.name,
        sector=company.sector,
        exchange=company.exchange,
        fundamentals=FundamentalOut.model_validate(fund) if fund else None,
    )


# ── GET /stocks/{ticker}/history — OHLCV time series ───────────────────────

@router.get("/{ticker}/history", response_model=list[StockPriceOut])
def get_history(
    ticker: str,
    range: str = Query("1y", description="Time range: 1mo, 3mo, 6mo, 1y, 2y, 5y"),
    db: Session = Depends(get_db),
):
    """
    Historical daily OHLCV for charting.
    Supported ranges: 1mo, 3mo, 6mo, 1y, 2y, 5y.
    """
    ticker = ticker.upper()
    if not ticker.endswith(".NS"):
        ticker += ".NS"

    if db.query(Company).filter(Company.ticker == ticker).first() is None:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    range_map = {
        "1mo": 30, "3mo": 90, "6mo": 180,
        "1y": 365, "2y": 730, "5y": 1825,
    }
    days = range_map.get(range)
    if days is None:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid range '{range}'. Use: {', '.join(range_map.keys())}",
        )

    from datetime import timedelta
    cutoff = date.today() - timedelta(days=days)

    prices = (
        db.query(StockPrice)
          .filter(StockPrice.ticker == ticker, StockPrice.date >= cutoff)
          .order_by(StockPrice.date.asc())
          .all()
    )
    return [StockPriceOut.model_validate(p) for p in prices]


# ── POST /compare — side-by-side comparison ────────────────────────────────

@router.post("/compare", response_model=CompareResponse)
def compare_stocks(body: CompareRequest, db: Session = Depends(get_db)):
    """
    Compare 2+ tickers side-by-side.
    POST body: {"tickers": ["RELIANCE.NS", "TCS.NS", "INFY.NS"]}
    """
    if len(body.tickers) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 tickers")
    if len(body.tickers) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 tickers per comparison")

    results = []
    for raw in body.tickers:
        t = raw.upper()
        if not t.endswith(".NS"):
            t += ".NS"
        company = db.query(Company).filter(Company.ticker == t).first()
        if not company:
            raise HTTPException(status_code=404, detail=f"Company '{t}' not found")
        results.append(_to_summary(company, db))

    return CompareResponse(companies=results)
