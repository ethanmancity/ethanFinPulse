# FinPulse — Indian Stock Market Monitoring Platform

> Track 24 NSE-listed Indian companies — live prices, historical data, fundamentals, and comparisons.

---

## Quick Start

### Prerequisites
- Python 3.11+
- pip

### 1. Clone & setup

```bash
git clone https://github.com/yourusername/finpulse.git
cd finpulse

# Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # macOS/Linux
pip install -r requirements.txt

# Dashboard (separate terminal)
cd ../dashboard
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env if needed (defaults work for local dev)
```

### 3. Seed the database

```bash
cd backend
python seed.py              # Companies only (fast)
python seed.py --with-data  # + 1yr history + fundamentals (takes ~5 min)
```

### 4. Run

**Backend** (Terminal 1):
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Dashboard** (Terminal 2):
```bash
cd dashboard
streamlit run app.py
```

Open:
- Dashboard: http://localhost:8501
- API docs:  http://localhost:8000/docs

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Dashboard                       │
│         (app.py → pages/ → utils/api_client.py)             │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (REST API)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│   main.py → routers/ → services/data_fetcher.py             │
│   (schemas.py)         (services/scheduler.py)              │
└──────────────────────────┬──────────────────────────────────┘
                           │ SQLAlchemy ORM
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Database                                  │
│   SQLite (local)  │  Supabase Postgres (production)        │
│   companies, stock_prices, fundamentals                     │
└──────────────────────────┬──────────────────────────────────┘
                           │ yFinance API
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Sources                              │
│   yFinance (.NS tickers) — NSE market data                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| ORM | SQLAlchemy 2.0 |
| Schemas | Pydantic v2 |
| Database | SQLite (local) / Supabase Postgres (prod) |
| Data Source | yFinance (NSE via .NS suffix) |
| Scheduler | APScheduler (background, in-process) |
| Dashboard | Streamlit |
| Charts | Plotly (candlestick, bar, line, treemap, pie) |
| HTTP Client | httpx |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API root — lists all endpoints |
| GET | `/stocks` | All 24 companies + latest snapshot |
| GET | `/stocks/{ticker}` | Full detail for one company |
| GET | `/stocks/{ticker}/history?range=1y` | Historical OHLCV for charting |
| POST | `/stocks/compare` | Side-by-side comparison (2-10 tickers) |
| GET | `/market-summary` | Aggregate stats, gainers, losers, sectors |
| POST | `/admin/refresh?days=30` | Trigger manual data refresh |
| GET | `/admin/health` | DB health check |

Interactive docs at http://localhost:8000/docs

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./finpulse.db` | DB connection string |
| `REFRESH_INTERVAL_MIN` | `30` | Scheduler refresh interval (minutes) |
| `BACKEND_URL` | `http://localhost:8000` | Backend URL for dashboard |
| `GEMINI_API_KEY` | (empty) | Google Gemini API key for AI insights |

---

## Tracked Companies (24 NSE stocks)

| Ticker | Company | Sector |
|--------|---------|--------|
| RELIANCE.NS | Reliance Industries | Energy |
| TCS.NS | Tata Consultancy Services | IT |
| HDFCBANK.NS | HDFC Bank | Banking |
| INFY.NS | Infosys | IT |
| ICICIBANK.NS | ICICI Bank | Banking |
| HINDUNILVR.NS | Hindustan Unilever | FMCG |
| SBIN.NS | State Bank of India | Banking |
| BHARTIARTL.NS | Bharti Airtel | Telecom |
| ITC.NS | ITC | FMCG |
| KOTAKBANK.NS | Kotak Mahindra Bank | Banking |
| LT.NS | Larsen & Toubro | Infrastructure |
| AXISBANK.NS | Axis Bank | Banking |
| BAJFINANCE.NS | Bajaj Finance | NBFC |
| ASIANPAINT.NS | Asian Paints | Consumer |
| MARUTI.NS | Maruti Suzuki | Auto |
| SUNPHARMA.NS | Sun Pharmaceutical | Pharma |
| TITAN.NS | Titan Company | Consumer |
| TATAMOTORS.NS | Tata Motors | Auto |
| WIPRO.NS | Wipro | IT |
| ULTRACEMCO.NS | UltraTech Cement | Materials |
| ONGC.NS | ONGC | Energy |
| NTPC.NS | NTPC | Power |
| TATASTEEL.NS | Tata Steel | Metals |
| HCLTECH.NS | HCL Technologies | IT |

---

## Project Structure

```
finpulse/
├── backend/
│   ├── main.py              # FastAPI app, lifespan, CORS
│   ├── database.py          # DB engine, sessions, init_db
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic response models
│   ├── seed.py              # Seed 24 companies + optional data
│   ├── routers/
│   │   ├── stocks.py        # /stocks, /stocks/{ticker}, /history, /compare
│   │   ├── market_summary.py # /market-summary
│   │   └── admin.py         # /admin/refresh, /admin/health
│   ├── services/
│   │   ├── data_fetcher.py  # yFinance integration, retry, fallback
│   │   └── scheduler.py     # APScheduler background refresh
│   └── requirements.txt
├── dashboard/
│   ├── app.py               # Streamlit entrypoint
│   ├── pages/
│   │   ├── 1_Overview.py    # All stocks table + pie chart
│   │   ├── 2_Company_Detail.py # Candlestick, fundamentals cards
│   │   ├── 3_Compare.py     # Multi-company comparison
│   │   └── 4_Screener.py    # Filter by P/E, cap, sector
│   ├── utils/
│   │   └── api_client.py    # HTTP wrapper for backend calls
│   └── requirements.txt
├── README.md
├── PROJECT_REPORT.md
├── .env.example
└── .gitignore
```

---

## Deployment

### Backend → Render

1. Push repo to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect GitHub repo
4. Settings:
   - **Root Directory:** `finpulse/backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add env vars:
   - `DATABASE_URL` = your Supabase Postgres URL
   - `REFRESH_INTERVAL_MIN` = `30`

### Database → Supabase

1. Go to [supabase.com](https://supabase.com) → New Project
2. Copy the Postgres connection string
3. Set `DATABASE_URL` in Render env vars
4. Tables are auto-created by SQLAlchemy on first startup

### Dashboard → Streamlit Community Cloud

1. Push repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Deploy from GitHub — select `finpulse/dashboard/app.py`
4. Add env var: `BACKEND_URL` = your Render backend URL

---

## External APIs & Tools Used

- **yFinance** — Primary data source for NSE market data (via `.NS` tickers)
- **Google Gemini API** — Used for AI-powered stock insights (bonus feature)
- **FastAPI** — REST API framework with auto-generated OpenAPI docs
- **SQLAlchemy** — ORM for database abstraction
- **Plotly** — Interactive charts (candlestick, bar, line, treemap, pie)
- **Streamlit** — Dashboard framework
- **APScheduler** — Background task scheduling for periodic data refresh
- **Pydantic** — Request/response validation and serialization

> **Note:** This project was developed with assistance from Google Gemini / Google AI Studio for code generation and architecture decisions.

---

## License

For educational purposes — SoFI AlgoLabs Assignment 1.
