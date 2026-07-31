"""
Overview page — table of all tracked companies with key metrics.
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from utils.api_client import get_all_stocks, get_market_summary

st.set_page_config(page_title="FinPulse — Overview", page_icon="📊", layout="wide")
st.title("📊 Company Overview")

# ── Fetch data ──────────────────────────────────────────────────────────────

stocks = get_all_stocks()

if not stocks:
    st.warning("No stock data available. Make sure the backend is running and data has been seeded.")
    st.stop()

# ── Sector filter ───────────────────────────────────────────────────────────

sectors = sorted(set(s.get("sector", "Unknown") for s in stocks if s.get("sector")))
selected_sector = st.selectbox("Filter by sector", ["All"] + sectors)

if selected_sector != "All":
    stocks = [s for s in stocks if s.get("sector") == selected_sector]

# ── Build DataFrame ─────────────────────────────────────────────────────────

df = pd.DataFrame(stocks)
df["ticker_clean"] = df["ticker"].str.replace(".NS", "", regex=False)

# Format columns for display
display_cols = ["ticker_clean", "name", "sector", "latest_price", "pct_change", "market_cap", "pe_ratio", "eps"]
col_rename = {
    "ticker_clean": "Ticker",
    "name": "Company",
    "sector": "Sector",
    "latest_price": "Price (₹)",
    "pct_change": "Change %",
    "market_cap": "Market Cap (₹)",
    "pe_ratio": "P/E",
    "eps": "EPS (₹)",
}

# ── Summary metrics ─────────────────────────────────────────────────────────

summary = get_market_summary()
if summary:
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Companies", len(stocks))
    with m2:
        avg_pe = df["pe_ratio"].dropna().mean() if "pe_ratio" in df else None
        st.metric("Avg P/E", f"{avg_pe:.1f}" if pd.notna(avg_pe) else "N/A")
    with m3:
        avg_eps = df["eps"].dropna().mean() if "eps" in df else None
        st.metric("Avg EPS", f"₹{avg_eps:.2f}" if pd.notna(avg_eps) else "N/A")
    with m4:
        total_mcap = df["market_cap"].dropna().sum() if "market_cap" in df else 0
        if total_mcap >= 1e12:
            st.metric("Total MCap", f"₹{total_mcap/1e12:.1f}T")
        elif total_mcap > 0:
            st.metric("Total MCap", f"₹{total_mcap/1e9:.1f}B")
        else:
            st.metric("Total MCap", "N/A")

st.markdown("---")

# ── Data table ──────────────────────────────────────────────────────────────

st.subheader(f"All Companies ({len(stocks)})")

df_display = df[display_cols].copy()
df_display.columns = [col_rename.get(c, c) for c in display_cols]

# Format large numbers
if "Market Cap (₹)" in df_display.columns:
    df_display["Market Cap (₹)"] = df_display["Market Cap (₹)"].apply(
        lambda x: f"₹{x/1e9:.1f}B" if pd.notna(x) and x >= 1e9 else
                  (f"₹{x/1e6:.0f}M" if pd.notna(x) and x >= 1e6 else
                   (f"₹{x:,.0f}" if pd.notna(x) else "—"))
    )

if "Price (₹)" in df_display.columns:
    df_display["Price (₹)"] = df_display["Price (₹)"].apply(
        lambda x: f"₹{x:.2f}" if pd.notna(x) else "—"
    )

if "Change %" in df_display.columns:
    df_display["Change %"] = df_display["Change %"].apply(
        lambda x: f"{x:+.2f}%" if pd.notna(x) else "—"
    )

if "P/E" in df_display.columns:
    df_display["P/E"] = df_display["P/E"].apply(
        lambda x: f"{x:.1f}" if pd.notna(x) else "—"
    )

if "EPS (₹)" in df_display.columns:
    df_display["EPS (₹)"] = df_display["EPS (₹)"].apply(
        lambda x: f"₹{x:.2f}" if pd.notna(x) else "—"
    )

st.dataframe(df_display, use_container_width=True, hide_index=True)

# ── Market cap pie chart ────────────────────────────────────────────────────

st.subheader("Market Cap Distribution")
chart_df = df[df["market_cap"].notna() & (df["market_cap"] > 0)][["ticker_clean", "market_cap", "sector"]].copy()
chart_df.columns = ["Ticker", "Market Cap", "Sector"]

if not chart_df.empty:
    fig = px.pie(
        chart_df,
        values="Market Cap",
        names="Ticker",
        color="Sector",
        title="Market Cap Share",
        hole=0.3,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Market cap data not available for charting.")
