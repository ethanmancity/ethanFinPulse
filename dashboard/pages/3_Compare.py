"""
Compare page — side-by-side comparison of 2+ companies.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from utils.api_client import get_all_stocks, compare_stocks, get_history

st.set_page_config(page_title="FinPulse — Compare", page_icon="⚖️", layout="wide")
st.title("⚖️ Company Comparison")

# ── Ticker multi-select ─────────────────────────────────────────────────────

stocks = get_all_stocks()
if not stocks:
    st.warning("No stock data available.")
    st.stop()

options = {f"{s['name']} ({s['ticker'].replace('.NS','')})": s["ticker"] for s in stocks}
selected_labels = st.multiselect(
    "Select 2–10 companies to compare",
    list(options.keys()),
    default=list(options.keys())[:3],
)

if len(selected_labels) < 2:
    st.info("Select at least 2 companies to compare.")
    st.stop()

if len(selected_labels) > 10:
    st.warning("Maximum 10 companies. Showing first 10.")
    selected_labels = selected_labels[:10]

selected_tickers = [options[label] for label in selected_labels]

# ── Fetch comparison data ──────────────────────────────────────────────────

companies = compare_stocks(selected_tickers)

if not companies:
    st.error("Comparison data not available.")
    st.stop()

# ── Metrics comparison table ────────────────────────────────────────────────

st.subheader("Metrics Comparison")

def fmt(val, prefix="", suffix="", decimals=2):
    if val is None:
        return "—"
    return f"{prefix}{val:,.{decimals}f}{suffix}"

def fmt_mcap(val):
    if val is None:
        return "—"
    if val >= 1e12:
        return f"₹{val/1e12:.2f}T"
    if val >= 1e9:
        return f"₹{val/1e9:.1f}B"
    return f"₹{val/1e6:.0f}M"

comp_df = pd.DataFrame([
    {
        "Company": c["name"],
        "Ticker": c["ticker"].replace(".NS", ""),
        "Price (₹)": fmt(c.get("latest_price"), prefix="₹"),
        "Change %": fmt(c.get("pct_change"), suffix="%"),
        "Market Cap": fmt_mcap(c.get("market_cap")),
        "P/E": fmt(c.get("pe_ratio"), decimals=1),
        "EPS": fmt(c.get("eps"), prefix="₹"),
        "Sector": c.get("sector", "—"),
    }
    for c in companies
])

st.dataframe(comp_df, use_container_width=True, hide_index=True)

# ── Bar chart comparisons ──────────────────────────────────────────────────

st.subheader("Visual Comparison")

metric_choice = st.selectbox(
    "Compare by metric",
    ["market_cap", "pe_ratio", "eps", "pct_change"],
    format_func=lambda x: {
        "market_cap": "Market Cap",
        "pe_ratio": "P/E Ratio",
        "eps": "EPS",
        "pct_change": "Change %",
    }[x],
)

bar_data = pd.DataFrame([
    {
        "Company": c["name"].split(" ")[0] if len(c["name"]) > 15 else c["name"],
        metric_choice: c.get(metric_choice),
    }
    for c in companies
    if c.get(metric_choice) is not None
])

if not bar_data.empty:
    color_map = px.colors.qualitative.Set2
    fig_bar = px.bar(
        bar_data,
        x="Company",
        y=metric_choice,
        color="Company",
        color_discrete_sequence=color_map,
        title=f"{metric_choice.replace('_', ' ').title()} Comparison",
    )
    fig_bar.update_layout(
        template="plotly_dark",
        showlegend=False,
        height=400,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info(f"No data available for {metric_choice}.")

# ── Historical price overlay ────────────────────────────────────────────────

st.subheader("Historical Price Overlay")

overlay_range = st.selectbox(
    "Time range for overlay",
    ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
    index=3,
)

fig_overlay = go.Figure()
colors = px.colors.qualitative.Plotly

for i, ticker in enumerate(selected_tickers):
    hist = get_history(ticker, range=overlay_range)
    if hist:
        df_hist = pd.DataFrame(hist)
        df_hist["date"] = pd.to_datetime(df_hist["date"])
        df_hist = df_hist.sort_values("date")
        label = ticker.replace(".NS", "")

        # Normalize to percentage change from first close for fair comparison
        first_close = df_hist["close"].iloc[0]
        if first_close and first_close > 0:
            df_hist["norm"] = ((df_hist["close"] / first_close) - 1) * 100

        fig_overlay.add_trace(go.Scatter(
            x=df_hist["date"],
            y=df_hist["norm"],
            mode="lines",
            name=label,
            line=dict(color=colors[i % len(colors)], width=2),
        ))

fig_overlay.update_layout(
    template="plotly_dark",
    height=450,
    xaxis_title="Date",
    yaxis_title="Change from Start (%)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=0, r=0, t=20, b=0),
)
fig_overlay.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

st.plotly_chart(fig_overlay, use_container_width=True)
