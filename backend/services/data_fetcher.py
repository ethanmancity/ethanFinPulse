"""
Data fetching service — single source of truth for all market data retrieval.

Strategy:
  1. yFinance is the primary and reliable source (uses ".NS" suffix for NSE).
  2. Retries with exponential backoff on transient network errors.
  3. On persistent failure, falls back to the last-known-good value already
     stored in the database (staleness is tracked via snapshot_date).
  4. NSE/BSE direct scraping is intentionally NOT used in production — the
     NSE website actively blocks scrapers (rate limits, CAPTCHAs, ToS risk).
     If enrichment from NSE is ever needed, use the official NSE IT API
     (https://www.nseindia.com/api/) only with explicit permission and a
     realistic request间隔 (≥5 s).  For this assignment yFinance covers
     everything we need.
"""

import time
import logging
from datetime import date, timedelta
from functools import wraps
from typing import Optional

import yfinance as yf
from sqlalchemy.orm import Session

from models import Company, StockPrice, Fundamental

logger = logging.getLogger("finpulse.data_fetcher")

# ── Retry decorator ─────────────────────────────────────────────────────────

def retry(max_attempts: int = 3, base_delay: float = 1.0):
    """
    Retry a function on Exception with exponential backoff.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "  ⚠ %s attempt %d/%d failed: %s — retrying in %.1fs",
                        func.__name__, attempt, max_attempts, exc, delay,
                    )
                    time.sleep(delay)
            logger.error("  ✗ %s: all %d attempts exhausted", func.__name__, max_attempts)
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator


# ── yFinance wrappers ───────────────────────────────────────────────────────

@retry(max_attempts=3, base_delay=1.0)
def _fetch_ticker_info(ticker: str) -> dict:
    """Return yfinance Ticker.info dict for a single ticker."""
    tk = yf.Ticker(ticker)
    return tk.info or {}


@retry(max_attempts=3, base_delay=1.0)
def _fetch_ticker_history(ticker: str, start: str, end: str):
    """Return yfinance history DataFrame for a single ticker."""
    tk = yf.Ticker(ticker)
    return tk.history(start=start, end=end)


# ── Public API ──────────────────────────────────────────────────────────────

def fetch_live_snapshot(session: Session, ticker: str) -> Optional[Fundamental]:
    """
    Fetch the latest quote info for `ticker` and upsert into fundamentals.
    Returns the Fundamental row or None on failure (after fallback attempt).
    """
    today = date.today()

    try:
        info = _fetch_ticker_info(ticker)
    except Exception:
        logger.warning("  ↳ falling back to DB for %s fundamentals", ticker)
        return _fallback_fundamental(session, ticker)

    if not info or info.get("trailingPE") is None and info.get("marketCap") is None:
        logger.warning("  ↳ yfinance returned empty info for %s, falling back", ticker)
        return _fallback_fundamental(session, ticker)

    # Upsert: update today's row or create a new one
    existing = session.query(Fundamental).filter_by(
        ticker=ticker, snapshot_date=today
    ).first()

    if existing:
        row = existing
    else:
        row = Fundamental(ticker=ticker, snapshot_date=today)
        session.add(row)

    row.market_cap = info.get("marketCap") or info.get("market_cap")
    row.pe_ratio = info.get("trailingPE") or info.get("forwardPE")
    row.eps = info.get("trailingEps")
    row.dividend_yield = info.get("dividendYield")
    row.week_52_high = info.get("fiftyTwoWeekHigh")
    row.week_52_low = info.get("fiftyTwoWeekLow")
    row.book_value = info.get("bookValue")
    row.roe = info.get("returnOnEquity")
    row.debt_to_equity = info.get("debtToEquity")
    row.day_high = info.get("dayHigh")
    row.day_low = info.get("dayLow")
    row.pct_change = info.get("regularMarketChangePercent")
    row.beta = info.get("beta")

    try:
        session.commit()
    except Exception:
        session.rollback()
        logger.warning("  ↳ DB commit failed for %s fundamentals", ticker)

    return row


def fetch_historical_prices(
    session: Session,
    ticker: str,
    days: int = 365,
) -> list[StockPrice]:
    """
    Fetch up to `days` calendar days of daily OHLCV for `ticker`.
    Only inserts rows that don't already exist (idempotent).
    Returns list of newly inserted StockPrice rows.
    """
    today = date.today()
    start = today - timedelta(days=days)

    try:
        hist = _fetch_ticker_history(ticker, str(start), str(today))
    except Exception:
        logger.warning("  ↳ falling back to DB for %s history", ticker)
        return _fallback_history(session, ticker)

    if hist is None or hist.empty:
        logger.warning("  ↳ no history returned for %s, falling back", ticker)
        return _fallback_history(session, ticker)

    # Fetch existing dates to avoid duplicates
    existing_dates = {
        row[0]
        for row in session.query(StockPrice.date)
                           .filter(StockPrice.ticker == ticker)
                           .all()
    }

    inserted = []
    for idx, row in hist.iterrows():
        d = idx.date()
        if d in existing_dates:
            continue
        sp = StockPrice(
            ticker=ticker,
            date=d,
            open=round(float(row.get("Open", 0)), 2),
            high=round(float(row.get("High", 0)), 2),
            low=round(float(row.get("Low", 0)), 2),
            close=round(float(row.get("Close", 0)), 2),
            volume=int(row.get("Volume", 0)),
        )
        session.add(sp)
        inserted.append(sp)

    try:
        session.commit()
    except Exception:
        session.rollback()
        logger.warning("  ↳ DB commit failed for %s history", ticker)

    return inserted


def refresh_all(session: Session, days: int = 365) -> dict:
    """
    Full refresh: fetch live fundamentals + recent history for every tracked company.
    Returns a summary dict with counts.
    """
    companies = session.query(Company).all()
    summary = {
        "total_companies": len(companies),
        "fundamentals_ok": 0,
        "fundamentals_failed": 0,
        "history_rows_added": 0,
        "history_failed": 0,
    }

    for company in companies:
        t = company.ticker
        logger.info("Refreshing %s …", t)

        # Fundamentals
        fund = fetch_live_snapshot(session, t)
        if fund:
            summary["fundamentals_ok"] += 1
        else:
            summary["fundamentals_failed"] += 1

        # History (only fetch last 30 days on refresh to be fast)
        try:
            new_rows = fetch_historical_prices(session, t, days=days)
            summary["history_rows_added"] += len(new_rows)
        except Exception:
            summary["history_failed"] += 1

        # Small sleep to avoid hammering yFinance
        time.sleep(0.3)

    logger.info("Refresh complete: %s", summary)
    return summary


# ── Fallback helpers ────────────────────────────────────────────────────────

def _fallback_fundamental(session: Session, ticker: str) -> Optional[Fundamental]:
    """Return the most recent Fundamental row from DB (last-known-good)."""
    row = (
        session.query(Fundamental)
               .filter(Fundamental.ticker == ticker)
               .order_by(Fundamental.snapshot_date.desc())
               .first()
    )
    if row:
        logger.info("  ✓ %s: using fallback fundamentals from %s", ticker, row.snapshot_date)
    return row


def _fallback_history(session: Session, ticker: str) -> list[StockPrice]:
    """Return existing history rows from DB (last-known-good)."""
    rows = (
        session.query(StockPrice)
               .filter(StockPrice.ticker == ticker)
               .order_by(StockPrice.date.desc())
               .limit(365)
               .all()
    )
    if rows:
        logger.info("  ✓ %s: using %d fallback history rows from DB", ticker, len(rows))
    return rows
