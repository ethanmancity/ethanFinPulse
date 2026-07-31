"""
Seed script — populates the companies table with 24 tracked NSE stocks
and optionally back-fills 1 year of historical OHLCV + current fundamentals.

Usage:
    python seed.py              # seed companies only (fast, no API calls)
    python seed.py --with-data  # also fetch 1yr history + fundamentals (slow, needs network)

Run from the backend/ directory so relative imports work, or use:
    cd backend && python seed.py
"""

import sys
import os
import argparse
from datetime import date, timedelta

# Ensure backend/ is on the path so imports resolve
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, init_db
from models import Company, StockPrice, Fundamental

# ── The 24 companies we track ──────────────────────────────────────────────
TRACKED_COMPANIES = [
    # ticker,              name,                          sector
    ("RELIANCE.NS",        "Reliance Industries Ltd",     "Energy / Conglomerate"),
    ("TCS.NS",             "Tata Consultancy Services",   "IT"),
    ("HDFCBANK.NS",        "HDFC Bank Ltd",               "Banking"),
    ("INFY.NS",            "Infosys Ltd",                  "IT"),
    ("ICICIBANK.NS",       "ICICI Bank Ltd",               "Banking"),
    ("HINDUNILVR.NS",      "Hindustan Unilever Ltd",      "FMCG"),
    ("SBIN.NS",            "State Bank of India",          "Banking"),
    ("BHARTIARTL.NS",      "Bharti Airtel Ltd",            "Telecom"),
    ("ITC.NS",             "ITC Ltd",                      "FMCG"),
    ("KOTAKBANK.NS",       "Kotak Mahindra Bank Ltd",     "Banking"),
    ("LT.NS",              "Larsen & Toubro Ltd",          "Infrastructure"),
    ("AXISBANK.NS",        "Axis Bank Ltd",                "Banking"),
    ("BAJFINANCE.NS",      "Bajaj Finance Ltd",            "NBFC"),
    ("ASIANPAINT.NS",      "Asian Paints Ltd",             "Consumer"),
    ("MARUTI.NS",          "Maruti Suzuki India Ltd",      "Auto"),
    ("SUNPHARMA.NS",       "Sun Pharmaceutical Industries","Pharma"),
    ("TITAN.NS",           "Titan Company Ltd",            "Consumer"),
    ("TATAMOTORS.NS",      "Tata Motors Ltd",              "Auto"),
    ("WIPRO.NS",           "Wipro Ltd",                    "IT"),
    ("ULTRACEMCO.NS",      "UltraTech Cement Ltd",         "Materials"),
    ("ONGC.NS",            "Oil & Natural Gas Corp",       "Energy"),
    ("NTPC.NS",            "NTPC Ltd",                     "Power"),
    ("TATASTEEL.NS",       "Tata Steel Ltd",               "Metals"),
    ("HCLTECH.NS",         "HCL Technologies Ltd",         "IT"),
]


def seed_companies(session):
    """Insert companies that don't already exist (idempotent)."""
    existing = {c.ticker for c in session.query(Company.ticker).all()}
    added = 0
    for ticker, name, sector in TRACKED_COMPANIES:
        if ticker not in existing:
            session.add(Company(ticker=ticker, name=name, sector=sector, exchange="NSE"))
            added += 1
    session.commit()
    print(f"[seed] Companies: {added} added, {len(TRACKED_COMPANIES) - added} already present "
          f"({len(TRACKED_COMPANIES)} total tracked)")
    return added


def seed_historical_data(session, days=365):
    """
    Fetch ~1 year of daily OHLCV for every tracked company via yFinance.
    Uses bulk insert with upsert logic (skip if date already exists).
    """
    try:
        import yfinance as yf
    except ImportError:
        print("[seed] yfinance not installed — run: pip install yfinance")
        return

    tickers = [t[0] for t in TRACKED_COMPANIES]
    end = date.today()
    start = end - timedelta(days=days)

    print(f"[seed] Fetching {days} days of history for {len(tickers)} tickers …")

    for ticker in tickers:
        try:
            tk = yf.Ticker(ticker)
            hist = tk.history(start=str(start), end=str(end))
            if hist.empty:
                print(f"  ⚠ {ticker}: no data returned, skipping")
                continue

            existing_dates = {
                row[0] for row in
                session.query(StockPrice.date)
                       .filter(StockPrice.ticker == ticker)
                       .all()
            }

            rows_added = 0
            for idx, row in hist.iterrows():
                d = idx.date()
                if d in existing_dates:
                    continue
                session.add(StockPrice(
                    ticker=ticker,
                    date=d,
                    open=round(row.get("Open", 0), 2),
                    high=round(row.get("High", 0), 2),
                    low=round(row.get("Low", 0), 2),
                    close=round(row.get("Close", 0), 2),
                    volume=int(row.get("Volume", 0)),
                ))
                rows_added += 1

            session.commit()
            print(f"  ✓ {ticker}: {rows_added} new rows")
        except Exception as e:
            session.rollback()
            print(f"  ✗ {ticker}: {e}")

    print("[seed] Historical data seeding complete.")


def seed_fundamentals(session):
    """Fetch current fundamentals for every tracked company via yFinance."""
    try:
        import yfinance as yf
    except ImportError:
        print("[seed] yfinance not installed — run: pip install yfinance")
        return

    today = date.today()
    tickers = [t[0] for t in TRACKED_COMPANIES]

    print(f"[seed] Fetching fundamentals for {len(tickers)} tickers …")

    for ticker in tickers:
        try:
            tk = yf.Ticker(ticker)
            info = tk.info or {}

            # Avoid duplicate snapshot for same day
            existing = session.query(Fundamental).filter_by(
                ticker=ticker, snapshot_date=today
            ).first()
            if existing:
                print(f"  ⏭ {ticker}: snapshot already exists for today")
                continue

            session.add(Fundamental(
                ticker=ticker,
                snapshot_date=today,
                market_cap=info.get("marketCap"),
                pe_ratio=info.get("trailingPE") or info.get("forwardPE"),
                eps=info.get("trailingEps"),
                dividend_yield=info.get("dividendYield"),
                week_52_high=info.get("fiftyTwoWeekHigh"),
                week_52_low=info.get("fiftyTwoWeekLow"),
                book_value=info.get("bookValue"),
                roe=info.get("returnOnEquity"),
                debt_to_equity=info.get("debtToEquity"),
                day_high=info.get("dayHigh"),
                day_low=info.get("dayLow"),
                pct_change=info.get("regularMarketChangePercent"),
                beta=info.get("beta"),
            ))
            session.commit()
            print(f"  ✓ {ticker}")
        except Exception as e:
            session.rollback()
            print(f"  ✗ {ticker}: {e}")

    print("[seed] Fundamentals seeding complete.")


def main():
    parser = argparse.ArgumentParser(description="Seed the FinPulse database")
    parser.add_argument(
        "--with-data", action="store_true",
        help="Also fetch 1yr history + fundamentals (requires network, takes a few minutes)",
    )
    args = parser.parse_args()

    # Create tables
    init_db()
    print("[seed] Tables created / verified.")

    session = SessionLocal()
    try:
        seed_companies(session)

        if args.with_data:
            seed_historical_data(session, days=365)
            seed_fundamentals(session)
        else:
            print("[seed] Skipping data fetch. Run with --with-data to populate history + fundamentals.")
    finally:
        session.close()

    print("[seed] Done.")


if __name__ == "__main__":
    main()
