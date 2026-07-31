"""
SQLAlchemy ORM models for FinPulse.

Tables:
  - companies     : static info about each tracked stock
  - stock_prices  : daily OHLCV time series
  - fundamentals  : periodic snapshots of valuation ratios & metrics
"""

from datetime import datetime, date
from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Date, Text,
    ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from database import Base


class Company(Base):
    __tablename__ = "companies"

    ticker = Column(String(20), primary_key=True)       # e.g. "RELIANCE.NS"
    name = Column(String(200), nullable=False)
    sector = Column(String(100), nullable=True)
    exchange = Column(String(10), default="NSE")
    added_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    prices = relationship("StockPrice", back_populates="company", cascade="all, delete-orphan")
    fundamentals = relationship("Fundamental", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Company {self.ticker} — {self.name}>"


class StockPrice(Base):
    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), ForeignKey("companies.ticker"), nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)

    company = relationship("Company", back_populates="prices")

    # One row per ticker per date
    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_ticker_date"),
        Index("ix_stock_prices_ticker_date", "ticker", "date"),
    )

    def __repr__(self):
        return f"<StockPrice {self.ticker} {self.date} C={self.close}>"


class Fundamental(Base):
    __tablename__ = "fundamentals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), ForeignKey("companies.ticker"), nullable=False)
    snapshot_date = Column(Date, default=date.today)

    market_cap = Column(Float, nullable=True)
    pe_ratio = Column(Float, nullable=True)
    eps = Column(Float, nullable=True)
    dividend_yield = Column(Float, nullable=True)
    week_52_high = Column(Float, nullable=True)
    week_52_low = Column(Float, nullable=True)
    book_value = Column(Float, nullable=True)
    roe = Column(Float, nullable=True)
    debt_to_equity = Column(Float, nullable=True)
    day_high = Column(Float, nullable=True)
    day_low = Column(Float, nullable=True)
    pct_change = Column(Float, nullable=True)
    beta = Column(Float, nullable=True)

    company = relationship("Company", back_populates="fundamentals")

    __table_args__ = (
        UniqueConstraint("ticker", "snapshot_date", name="uq_ticker_snapshot"),
        Index("ix_fundamentals_ticker_date", "ticker", "snapshot_date"),
    )

    def __repr__(self):
        return f"<Fundamental {self.ticker} {self.snapshot_date} MCap={self.market_cap}>"
