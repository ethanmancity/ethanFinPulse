"""
API client — wraps all calls to the FastAPI backend.
Keeps the dashboard decoupled from HTTP details.
"""

import os
import time
import httpx
import streamlit as st

# Backend URL — Streamlit Cloud secrets take priority, then env var, then local default
BACKEND_URL = (
    st.secrets.get("BACKEND_URL")
    or os.getenv("BACKEND_URL")
    or "http://localhost:8000"
)


def _get(path: str, params: dict | None = None) -> dict | list | None:
    """GET request to backend. Returns parsed JSON or None on error."""
    for attempt in range(3):
        try:
            with httpx.Client(timeout=120) as client:
                resp = client.get(f"{BACKEND_URL}{path}", params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except httpx.TransportError:
            # Free-tier hosts sleep on idle and take ~1 min to wake up
            time.sleep(15)
    return None


def _post(path: str, json: dict | None = None) -> dict | None:
    """POST request to backend. Returns parsed JSON or None on error."""
    for attempt in range(3):
        try:
            with httpx.Client(timeout=120) as client:
                resp = client.post(f"{BACKEND_URL}{path}", json=json)
                resp.raise_for_status()
                return resp.json()
        except Exception:
            time.sleep(15)
    return None


# ── Public helpers ──────────────────────────────────────────────────────────

def get_all_stocks(sector: str | None = None) -> list[dict]:
    params = {}
    if sector:
        params["sector"] = sector
    result = _get("/stocks", params=params)
    return result if isinstance(result, list) else []


def get_stock(ticker: str) -> dict | None:
    return _get(f"/stocks/{ticker}")


def get_history(ticker: str, range: str = "1y") -> list[dict]:
    result = _get(f"/stocks/{ticker}/history", params={"range": range})
    return result if isinstance(result, list) else []


def compare_stocks(tickers: list[str]) -> list[dict]:
    result = _post("/stocks/compare", json={"tickers": tickers})
    if result and "companies" in result:
        return result["companies"]
    return []


def get_market_summary() -> dict | None:
    return _get("/market-summary")


def trigger_refresh(days: int = 30) -> dict | None:
    return _post(f"/admin/refresh?days={days}")


def health_check() -> dict | None:
    return _get("/admin/health")
