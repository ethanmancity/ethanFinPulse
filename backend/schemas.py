"""
Pydantic v2 response schemas — typed JSON shapes for every endpoint.
Keeps the API contract explicit and auto-generates accurate OpenAPI docs.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


# ── Company ─────────────────────────────────────────────────────────────────

class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    name: str
    sector: Optional[str] = None
    exchange: str = "NSE"
    added_at: Optional[datetime] = None


# ── Stock Price ─────────────────────────────────────────────────────────────

class StockPriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None


# ── Fundamental ─────────────────────────────────────────────────────────────

class FundamentalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_date: date
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    eps: Optional[float] = None
    dividend_yield: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    book_value: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    pct_change: Optional[float] = None
    beta: Optional[float] = None


# ── Composite responses ─────────────────────────────────────────────────────

class StockSummary(BaseModel):
    """Lightweight company + latest fundamentals — used in list endpoints."""
    ticker: str
    name: str
    sector: Optional[str] = None
    exchange: str = "NSE"
    latest_price: Optional[float] = None
    pct_change: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    eps: Optional[float] = None


class StockDetail(BaseModel):
    """Full company detail with latest fundamentals."""
    ticker: str
    name: str
    sector: Optional[str] = None
    exchange: str = "NSE"
    fundamentals: Optional[FundamentalOut] = None


class MarketSummary(BaseModel):
    total_companies: int
    total_market_cap: Optional[float] = None
    avg_pe_ratio: Optional[float] = None
    avg_eps: Optional[float] = None
    top_gainers: list[StockSummary] = []
    top_losers: list[StockSummary] = []
    sector_breakdown: dict[str, dict] = {}


class CompareRequest(BaseModel):
    tickers: list[str]


class CompareResponse(BaseModel):
    companies: list[StockSummary]


class RefreshResponse(BaseModel):
    status: str
    message: str
    summary: Optional[dict] = None


class ErrorResponse(BaseModel):
    detail: str
