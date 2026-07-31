"""
FinPulse Dashboard — Streamlit entrypoint.

Run:
    cd dashboard
    streamlit run app.py

Expects the FastAPI backend to be running at BACKEND_URL (default http://localhost:8000).
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from utils.api_client import health_check, get_market_summary, get_all_stocks

st.set_page_config(
    page_title="FinPulse",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📈 FinPulse — Indian Stock Market Dashboard")

st.markdown(
    "Track **24 NSE-listed companies** across sectors — live prices, historical data, "
    "fundamentals, and comparisons.  \n"
    "Use the **sidebar** to navigate between pages."
)

# ── Health check ────────────────────────────────────────────────────────────

health = health_check()
if health is None:
    st.error(
        "⚠️ Cannot reach the FinPulse API backend.  \n"
        "Make sure the backend is running:  \n"
        "```bash\ncd backend && uvicorn main:app --reload --port 8000\n```"
    )
    st.stop()
else:
    st.success(f"API connected — {health.get('companies_tracked', '?')} companies tracked")

# ── Quick market snapshot ───────────────────────────────────────────────────

st.header("Market Snapshot")

summary = get_market_summary()
if summary:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Companies Tracked", summary.get("total_companies", 0))
    with col2:
        mcap = summary.get("total_market_cap")
        if mcap:
            if mcap >= 1e12:
                st.metric("Total Market Cap", f"₹{mcap/1e12:.1f}T")
            elif mcap >= 1e9:
                st.metric("Total Market Cap", f"₹{mcap/1e9:.1f}B")
            else:
                st.metric("Total Market Cap", f"₹{mcap:,.0f}")
        else:
            st.metric("Total Market Cap", "N/A")
    with col3:
        pe = summary.get("avg_pe_ratio")
        st.metric("Avg P/E", f"{pe:.1f}" if pe else "N/A")
    with col4:
        eps = summary.get("avg_eps")
        st.metric("Avg EPS", f"₹{eps:.2f}" if eps else "N/A")

    # Top gainers / losers side by side
    st.subheader("Top Movers Today")
    g_col, l_col = st.columns(2)

    with g_col:
        st.markdown("**🟢 Top Gainers**")
        for s in summary.get("top_gainers", []):
            pct = s.get("pct_change", 0) or 0
            price = s.get("latest_price")
            price_str = f"₹{price:.2f}" if price else "—"
            st.markdown(f"- **{s['ticker'].replace('.NS','')}** — {price_str} (+{pct:.2f}%)")

    with l_col:
        st.markdown("**🔴 Top Losers**")
        for s in summary.get("top_losers", []):
            pct = s.get("pct_change", 0) or 0
            price = s.get("latest_price")
            price_str = f"₹{price:.2f}" if price else "—"
            st.markdown(f"- **{s['ticker'].replace('.NS','')}** — {price_str} ({pct:.2f}%)")

    # Sector breakdown
    st.subheader("Sector Breakdown")
    sectors = summary.get("sector_breakdown", {})
    if sectors:
        import pandas as pd
        sec_df = pd.DataFrame([
            {"Sector": k, "Companies": v["count"], "Total MCap (₹)": v["total_market_cap"]}
            for k, v in sectors.items()
        ]).sort_values("Total MCap (₹)", ascending=False)
        st.dataframe(sec_df, use_container_width=True, hide_index=True)
else:
    st.info("Market summary not available yet — run a refresh first.")

# ── Sidebar navigation hint ─────────────────────────────────────────────────

st.sidebar.markdown("---")
st.sidebar.markdown("### Pages")
st.sidebar.markdown(
    "- **Overview** — all stocks table  \n"
    "- **Company Detail** — deep dive + chart  \n"
    "- **Compare** — side-by-side  \n"
    "- **Screener** — filter by P/E, sector, market cap"
)
