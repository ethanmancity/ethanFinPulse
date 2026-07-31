"""
Company Detail page — deep dive into a single stock with charts and fundamentals.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.api_client import get_all_stocks, get_stock, get_history

st.set_page_config(page_title="FinPulse — Company Detail", page_icon="🔍", layout="wide")
st.title("🔍 Company Detail")

# ── Ticker selector ─────────────────────────────────────────────────────────

stocks = get_all_stocks()
if not stocks:
    st.warning("No stock data available.")
    st.stop()

ticker_options = {f"{s['name']} ({s['ticker'].replace('.NS','')})": s["ticker"] for s in stocks}
selected_label = st.selectbox("Select a company", list(ticker_options.keys()))
ticker = ticker_options[selected_label]

# ── Time range selector ─────────────────────────────────────────────────────

range_options = {"1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo", "1 Year": "1y", "2 Years": "2y", "5 Years": "5y"}
selected_range_label = st.selectbox("Time range", list(range_options.keys()), index=3)
time_range = range_options[selected_range_label]

# ── Fetch data ──────────────────────────────────────────────────────────────

detail = get_stock(ticker)
history = get_history(ticker, range=time_range)

if not detail:
    st.error(f"No data found for {ticker}")
    st.stop()

# ── Company header ──────────────────────────────────────────────────────────

st.subheader(f"{detail['name']} ({ticker.replace('.NS', '')})")
st.caption(f"Sector: {detail.get('sector', 'N/A')} | Exchange: {detail.get('exchange', 'NSE')}")

# ── Fundamentals cards ──────────────────────────────────────────────────────

fund = detail.get("fundamentals")
if fund:
    st.markdown("---")
    st.subheader("Key Metrics")

    def fmt(val, prefix="", suffix="", decimals=2):
        if val is None:
            return "N/A"
        if isinstance(val, float):
            return f"{prefix}{val:,.{decimals}f}{suffix}"
        return f"{prefix}{val}{suffix}"

    def fmt_mcap(val):
        if val is None:
            return "N/A"
        if val >= 1e12:
            return f"₹{val/1e12:.2f}T"
        if val >= 1e9:
            return f"₹{val/1e9:.1f}B"
        return f"₹{val/1e6:.0f}M"

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Market Cap", fmt_mcap(fund.get("market_cap")))
    c2.metric("P/E Ratio", fmt(fund.get("pe_ratio"), decimals=1))
    c3.metric("EPS", fmt(fund.get("eps"), prefix="₹"))
    c4.metric("52W High", fmt(fund.get("week_52_high"), prefix="₹"))
    c5.metric("52W Low", fmt(fund.get("week_52_low"), prefix="₹"))
    c6.metric("Change", fmt(fund.get("pct_change"), suffix="%", decimals=2))

    c7, c8, c9, c10, c11, c12 = st.columns(6)
    c7.metric("Dividend Yield", fmt(fund.get("dividend_yield"), suffix="%", decimals=2))
    c8.metric("Book Value", fmt(fund.get("book_value"), prefix="₹"))
    c9.metric("ROE", fmt(fund.get("roe"), suffix="%", decimals=2))
    c10.metric("Debt/Equity", fmt(fund.get("debt_to_equity"), decimals=2))
    c11.metric("Beta", fmt(fund.get("beta"), decimals=2))
    c12.metric("Snapshot", str(fund.get("snapshot_date", "N/A")))

# ── Price chart (candlestick + volume) ─────────────────────────────────────

if history:
    st.markdown("---")
    st.subheader(f"Price Chart — {selected_range_label}")

    hist_df = pd.DataFrame(history)
    hist_df["date"] = pd.to_datetime(hist_df["date"])
    hist_df = hist_df.sort_values("date")

    # Candlestick + volume overlay
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
        subplot_titles=("Candlestick", "Volume"),
    )

    fig.add_trace(
        go.Candlestick(
            x=hist_df["date"],
            open=hist_df["open"],
            high=hist_df["high"],
            low=hist_df["low"],
            close=hist_df["close"],
            name="OHLC",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1, col=1,
    )

    # Color volume bars: green if close >= open, red otherwise
    colors = [
        "#26a69a" if c >= o else "#ef5350"
        for c, o in zip(hist_df["close"], hist_df["open"])
    ]

    fig.add_trace(
        go.Bar(
            x=hist_df["date"],
            y=hist_df["volume"],
            marker_color=colors,
            name="Volume",
            showlegend=False,
        ),
        row=2, col=1,
    )

    fig.update_layout(
        height=600,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        showlegend=True,
        margin=dict(l=0, r=0, t=30, b=0),
    )
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Price (₹)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # Simple line chart toggle
    if st.checkbox("Show simple line chart instead"):
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=hist_df["date"], y=hist_df["close"],
            mode="lines", name="Close",
            line=dict(color="#42a5f5", width=2),
        ))
        fig_line.update_layout(
            height=400,
            template="plotly_dark",
            xaxis_title="Date",
            yaxis_title="Close Price (₹)",
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig_line, use_container_width=True)

else:
    st.info("No historical price data available for this ticker and range.")
