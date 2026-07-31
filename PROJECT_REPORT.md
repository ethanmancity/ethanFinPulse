# FinPulse — Project Report

**AlgoLabs Assignment 1 — Society of Finance and Investing (SoFI)**

---

## 1. Architecture Overview

FinPulse follows a three-tier architecture with clear separation of concerns:

```
Presentation (Streamlit) → API Layer (FastAPI) → Data Layer (SQLAlchemy + DB)
```

**Key architectural decisions:**

- **Dashboard never touches the database directly.** All data flows through the REST API, ensuring proper layering and making it trivial to swap the dashboard for any other client (mobile app, React frontend, etc.).
- **SQLite for local development, Supabase Postgres for production.** SQLAlchemy's engine abstraction means swapping requires only a `DATABASE_URL` env var change — zero code modifications.
- **APScheduler runs inside the FastAPI process** rather than as a separate service. This keeps deployment simple (single process) while still providing background refresh. For production scale, this could be extracted to a separate worker.
- **Retry + fallback pattern for all external calls.** yFinance is called with exponential backoff (3 attempts), and on persistent failure the system falls back to last-known-good values from the database rather than crashing.

---

## 2. APIs Used

### Primary Data Source
- **yFinance** (`yfinance` Python library) — fetches live quotes, historical OHLCV, and fundamental metrics for NSE-listed stocks using the `.NS` suffix (e.g., `RELIANCE.NS`). This is the sole data source; NSE/BSE direct scraping was intentionally avoided due to ToS and rate-limiting concerns.

### AI Integration
- **Google Gemini API** — available for generating plain-English summaries of stock performance (configured via `GEMINI_API_KEY` env var).

### Internal APIs (FastAPI)
The application exposes its own REST API with 7 endpoints covering stock listing, detail, history, comparison, market summary, refresh, and health check. Interactive documentation is auto-generated at `/docs`.

---

## 3. Database Design

### Tables

**companies** — static metadata for each tracked stock
| Column | Type | Notes |
|--------|------|-------|
| ticker | VARCHAR(20) PK | e.g., "RELIANCE.NS" |
| name | VARCHAR(200) | Company name |
| sector | VARCHAR(100) | e.g., "Banking", "IT" |
| exchange | VARCHAR(10) | Default "NSE" |
| added_at | DATETIME | Auto-set on insert |

**stock_prices** — daily OHLCV time series
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| ticker | VARCHAR(20) FK | References companies.ticker |
| date | DATE | Trading date |
| open, high, low, close | FLOAT | Price data |
| volume | INTEGER | Trading volume |

Unique constraint on `(ticker, date)` prevents duplicate rows. Indexed for fast range queries.

**fundamentals** — periodic valuation snapshots
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| ticker | VARCHAR(20) FK | References companies.ticker |
| snapshot_date | DATE | When the data was fetched |
| market_cap, pe_ratio, eps | FLOAT | Core metrics |
| dividend_yield, week_52_high/low | FLOAT | Extended metrics |
| book_value, roe, debt_to_equity | FLOAT | Financial ratios |
| day_high, day_low, pct_change, beta | FLOAT | Trading data |

Unique constraint on `(ticker, snapshot_date)`.

### Design Decisions
- **Unique constraints** enable safe upsert logic — running `refresh_all()` multiple times never creates duplicates.
- **`pool_pre_ping=True`** on the engine ensures stale connections (common with Supabase's idle timeout) are automatically recycled.
- **Separate fundamentals table** rather than adding columns to companies, because fundamentals change daily while company metadata is static. This avoids updating the same row constantly.

---

## 4. Features Implemented

### Required Features
1. **24 NSE-listed companies** across 10+ sectors (Banking, IT, FMCG, Auto, Pharma, Energy, Telecom, NBFC, Consumer, Infrastructure, Materials, Metals, Power)
2. **Live + historical OHLCV data** via yFinance with up to 5 years of history
3. **Fundamental metrics** — Market Cap, P/E, EPS, Dividend Yield, 52W High/Low, Book Value, ROE, Debt/Equity, Beta
4. **SQLite database** with proper schema, unique constraints, and indexes
5. **REST API** with 7 endpoints, Pydantic schemas, proper HTTP status codes, CORS, OpenAPI docs
6. **Interactive Streamlit dashboard** with 4 pages, calling the REST API (not the DB)
7. **Scheduled refresh** via APScheduler (every 30 minutes) + manual POST /admin/refresh

### Bonus Features (5 implemented)
1. **Interactive candlestick charts with volume overlay** — Plotly dark theme, colored volume bars (green/red by direction)
2. **Sector-wise comparison** — breakdown in market summary + sector filter on overview page
3. **Custom stock screener** — filter by P/E range, market cap range, sector, minimum EPS, minimum dividend yield
4. **Financial ratio visualization** — P/E bar chart + market cap treemap colored by daily % change
5. **Normalized price overlay** — compare stocks by % change from a common starting point, regardless of absolute price

---

## 5. Challenges & Solutions

### Challenge 1: yFinance Rate Limiting
**Problem:** yFinance throttles requests when fetching data for 24 stocks sequentially.
**Solution:** Added 0.3s sleep between tickers in `refresh_all()`, plus exponential backoff retry (3 attempts with 1s/2s/4s delays). On persistent failure, falls back to DB values.

### Challenge 2: Duplicate Data on Re-seed
**Problem:** Running the seed script or refresh multiple times could create duplicate rows.
**Solution:** Unique constraints on `(ticker, date)` for stock_prices and `(ticker, snapshot_date)` for fundamentals. All insert logic checks for existing rows before inserting.

### Challenge 3: SQLite Thread Safety
**Problem:** FastAPI uses async handlers but SQLite doesn't allow cross-thread access by default.
**Solution:** Set `check_same_thread=False` in the engine connection args, which is the standard approach for SQLite with FastAPI.

### Challenge 4: Background Refresh Without Blocking
**Problem:** Data refresh takes several minutes but the API should respond immediately.
**Solution:** Used FastAPI's `BackgroundTasks` for the manual refresh endpoint, and APScheduler's `BackgroundScheduler` (not `BlockingScheduler`) for the periodic job.

### Challenge 5: Dashboard-Backend Decoupling
**Problem:** The spec requires the dashboard to call the REST API, not the database directly.
**Solution:** Created `utils/api_client.py` as a clean abstraction layer. All HTTP calls go through this module, making it trivial to change the backend URL for deployment.

---

## 6. Future Improvements

1. **AI-Powered Insights** — Integrate Gemini API to generate natural-language summaries of each stock's performance and fundamentals
2. **Email/Telegram Alerts** — Price threshold notifications using a message queue
3. **User Authentication** — Add user accounts with personal watchlists
4. **WebSocket Live Prices** — Real-time price updates instead of polling
5. **Postgres Migration** — Move to Supabase for production with connection pooling
6. **Docker Deployment** — Containerize backend + dashboard for one-command deployment
7. **Data Export** — PDF reports per company or market summary
8. **Backtesting Engine** — Let users test simple trading strategies against historical data
9. **More Data Sources** — BSE data, mutual funds, indices (Nifty 50, Sensex)
10. **Performance Optimization** — Redis caching for frequently accessed endpoints

---

## 7. Running Locally

```bash
# Backend
cd backend
pip install -r requirements.txt
python seed.py --with-data
uvicorn main:app --reload --port 8000

# Dashboard (separate terminal)
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501 for the dashboard and http://localhost:8000/docs for API documentation.

---

## 8. Submission Checklist

| Requirement | Status |
|-------------|--------|
| 20+ NSE companies tracked | ✅ 24 companies across 10+ sectors |
| Live + historical OHLCV | ✅ yFinance with up to 5yr history |
| Market Cap, P/E, EPS | ✅ Plus 10+ additional metrics |
| SQLite database | ✅ With Postgres-ready architecture |
| REST API endpoints | ✅ 7 endpoints (stocks, history, compare, summary, refresh, health) |
| Pydantic schemas | ✅ Typed response models for all endpoints |
| OpenAPI docs | ✅ Auto-generated at /docs |
| CORS enabled | ✅ Configured for all origins |
| Error handling | ✅ 404/400/500 with clear messages |
| Scheduled refresh | ✅ APScheduler every 30min |
| Manual refresh | ✅ POST /admin/refresh |
| Historical price charts | ✅ Plotly candlestick + volume |
| Fundamental metrics display | ✅ 12-metric cards |
| Company comparison | ✅ Multi-select, table + charts |
| 3+ bonus features | ✅ 5 implemented (candlestick, screener, sector, treemap, overlay) |
| Dashboard calls REST API | ✅ api_client.py layer |
| README.md | ✅ Setup, architecture, env vars, tech stack |
| PROJECT_REPORT.md | ✅ This document |
| requirements.txt | ✅ Both backend and dashboard |
| .gitignore | ✅ Excludes .env, __pycache__, .db, venv |
| .env.example | ✅ Template with all variables |
| External APIs documented | ✅ yFinance, Gemini, all libraries listed |

---

*Generated with assistance from Google Gemini / Google AI Studio.*
