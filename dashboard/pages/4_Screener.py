"""
Screener page — filter stocks by P/E, market cap, sector, EPS, etc.
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from utils.api_client import get_all_stocks

st.set_page_config(page_title="FinPulse — Screener", page_icon="🔎", layout="wide")
st.title("🔎 Stock Screener")

# ── Fetch all data ──────────────────────────────────────────────────────────

stocks = get_all_stocks()
if not stocks:
    st.warning("No stock data available.")
    st.stop()

df = pd.DataFrame(stocks)
df["ticker_clean"] = df["ticker"].str.replace(".NS", "", regex=False)

# ── Filter controls ─────────────────────────────────────────────────────────

st.subheader("Filters")

col1, col2, col3 = st.columns(3)

with col1:
    sectors = sorted(df["sector"].dropna().unique())
    selected_sectors = st.multiselect("Sector", sectors, default=sectors)

with col2:
    pe_min, pe_max = st.slider(
        "P/E Ratio Range",
        min_value=0.0,
        max_value=200.0,
        value=(0.0, 100.0),
        step=5.0,
    )

with col3:
    mcap_min, mcap_max = st.slider(
        "Market Cap Range (₹ Bn)",
        min_value=0.0,
        max_value=5000.0,
        value=(0.0, 5000.0),
        step=100.0,
    )

col4, col5 = st.columns(2)

with col4:
    eps_min = st.number_input("Min EPS (₹)", value=-100.0, step=10.0)

with col5:
    div_min = st.number_input("Min Dividend Yield (%)", value=0.0, step=0.5)

# ── Apply filters ──────────────────────────────────────────────────────────

filtered = df.copy()

# Sector filter
if selected_sectors:
    filtered = filtered[filtered["sector"].isin(selected_sectors)]

# P/E filter (use latest fundamental data from API — stored in df)
# We need to fetch detailed data; for now filter on what's available in list
if "pe_ratio" in filtered.columns:
    filtered = filtered[
        (filtered["pe_ratio"].isna()) |
        ((filtered["pe_ratio"] >= pe_min) & (filtered["pe_ratio"] <= pe_max))
    ]

# Market cap filter (convert Bn to actual value)
if "market_cap" in filtered.columns:
    mcap_min_actual = mcap_min * 1e9
    mcap_max_actual = mcap_max * 1e9
    filtered = filtered[
        (filtered["market_cap"].isna()) |
        ((filtered["market_cap"] >= mcap_min_actual) & (filtered["market_cap"] <= mcap_max_actual))
    ]

# EPS filter
if "eps" in filtered.columns:
    filtered = filtered[
        (filtered["eps"].isna()) |
        (filtered["eps"] >= eps_min)
    ]

# ── Results ─────────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader(f"Results: {len(filtered)} companies")

if filtered.empty:
    st.info("No companies match your filters. Try adjusting the criteria.")
else:

    def fmt(val, prefix="", suffix="", decimals=2):
        if pd.isna(val):
            return "—"
        return f"{prefix}{val:,.{decimals}f}{suffix}"

    def fmt_mcap(val):
        if pd.isna(val) or val == 0:
            return "—"
        if val >= 1e12:
            return f"₹{val/1e12:.2f}T"
        if val >= 1e9:
            return f"₹{val/1e9:.1f}B"
        return f"₹{val/1e6:.0f}M"

    result_df = filtered[["ticker_clean", "name", "sector", "latest_price", "pct_change", "market_cap", "pe_ratio", "eps"]].copy()
    result_df.columns = ["Ticker", "Company", "Sector", "Price (₹)", "Change %", "Market Cap", "P/E", "EPS (₹)"]

    result_df["Price (₹)"] = result_df["Price (₹)"].apply(lambda x: fmt(x, prefix="₹"))
    result_df["Change %"] = result_df["Change %"].apply(lambda x: fmt(x, suffix="%"))
    result_df["Market Cap"] = result_df["Market Cap"].apply(fmt_mcap)
    result_df["P/E"] = result_df["P/E"].apply(lambda x: fmt(x, decimals=1))
    result_df["EPS (₹)"] = result_df["EPS (₹)"].apply(lambda x: fmt(x, prefix="₹"))

    st.dataframe(result_df, use_container_width=True, hide_index=True)

    # ── P/E distribution chart ─────────────────────────────────────────────

    chart_data = filtered[filtered["pe_ratio"].notna() & (filtered["pe_ratio"] > 0)].copy()

    if not chart_data.empty:
        st.subheader("P/E Ratio Distribution")

        fig_pe = px.bar(
            chart_data.sort_values("pe_ratio", ascending=True),
            x="ticker_clean",
            y="pe_ratio",
            color="sector",
            title="P/E Ratio by Company",
            labels={"ticker_clean": "Ticker", "pe_ratio": "P/E Ratio"},
        )
        fig_pe.update_layout(
            template="plotly_dark",
            height=400,
            margin=dict(l=0, r=0, t=40, b=0),
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig_pe, use_container_width=True)

    # ── Market cap treemap ────────────────────────────────────────────────

    mcap_data = filtered[filtered["market_cap"].notna() & (filtered["market_cap"] > 0)].copy()

    if not mcap_data.empty:
        st.subheader("Market Cap Treemap")

        fig_tree = px.treemap(
            mcap_data,
            path=["sector", "ticker_clean"],
            values="market_cap",
            color="pct_change",
            color_continuous_scale=["#ef5350", "#26a69a"],
            color_continuous_midpoint=0,
            title="Market Cap Treemap (colored by daily change %)",
        )
        fig_tree.update_layout(
            height=500,
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig_tree, use_container_width=True)
