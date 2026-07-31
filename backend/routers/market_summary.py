"""
Market summary endpoint — aggregate stats across all tracked companies.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Company, StockPrice, Fundamental
from schemas import MarketSummary, StockSummary

router = APIRouter(tags=["market"])


@router.get("/market-summary", response_model=MarketSummary)
def market_summary(db: Session = Depends(get_db)):
    """
    Aggregate market stats:
      - total companies tracked
      - total market cap
      - average P/E, EPS
      - top 5 gainers / losers
      - sector breakdown
    """
    companies = db.query(Company).order_by(Company.ticker).all()

    # Collect latest fundamentals per company
    fund_map: dict[str, Fundamental] = {}
    price_map: dict[str, StockPrice] = {}
    for c in companies:
        f = (
            db.query(Fundamental)
              .filter(Fundamental.ticker == c.ticker)
              .order_by(Fundamental.snapshot_date.desc())
              .first()
        )
        if f:
            fund_map[c.ticker] = f
        p = (
            db.query(StockPrice)
              .filter(StockPrice.ticker == c.ticker)
              .order_by(StockPrice.date.desc())
              .first()
        )
        if p:
            price_map[c.ticker] = p

    # Aggregate stats
    total_market_cap = sum((f.market_cap or 0) for f in fund_map.values())
    pe_vals = [f.pe_ratio for f in fund_map.values() if f.pe_ratio is not None]
    eps_vals = [f.eps for f in fund_map.values() if f.eps is not None]
    avg_pe = round(sum(pe_vals) / len(pe_vals), 2) if pe_vals else None
    avg_eps = round(sum(eps_vals) / len(eps_vals), 2) if eps_vals else None

    # Build summaries with pct_change for sorting
    summaries: list[StockSummary] = []
    for c in companies:
        f = fund_map.get(c.ticker)
        p = price_map.get(c.ticker)
        summaries.append(StockSummary(
            ticker=c.ticker,
            name=c.name,
            sector=c.sector,
            exchange=c.exchange,
            latest_price=p.close if p else None,
            pct_change=f.pct_change if f else None,
            market_cap=f.market_cap if f else None,
            pe_ratio=f.pe_ratio if f else None,
            eps=f.eps if f else None,
        ))

    # Top gainers / losers (only those with pct_change)
    with_change = [s for s in summaries if s.pct_change is not None]
    top_gainers = sorted(with_change, key=lambda s: s.pct_change, reverse=True)[:5]
    top_losers = sorted(with_change, key=lambda s: s.pct_change)[:5]

    # Sector breakdown
    sector_data: dict[str, dict] = {}
    for s in summaries:
        sec = s.sector or "Unknown"
        if sec not in sector_data:
            sector_data[sec] = {"count": 0, "total_market_cap": 0, "tickers": []}
        sector_data[sec]["count"] += 1
        sector_data[sec]["total_market_cap"] += s.market_cap or 0
        sector_data[sec]["tickers"].append(s.ticker)

    return MarketSummary(
        total_companies=len(companies),
        total_market_cap=total_market_cap,
        avg_pe_ratio=avg_pe,
        avg_eps=avg_eps,
        top_gainers=top_gainers,
        top_losers=top_losers,
        sector_breakdown=sector_data,
    )
