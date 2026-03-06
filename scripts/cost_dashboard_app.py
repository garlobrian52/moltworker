"""
cost_dashboard_app.py — Streamlit UI for the billing cost dashboard.

Run with:
    streamlit run scripts/cost_dashboard_app.py

Requirements:
    pip install streamlit pandas

Or with the optional extras:
    pip install -r scripts/requirements.txt
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

# Streamlit import with a friendly error if not installed
try:
    import streamlit as st
except ImportError:
    print(
        "Streamlit is not installed. Install it with:\n"
        "    pip install streamlit\n"
        "Then run:\n"
        "    streamlit run scripts/cost_dashboard_app.py",
        file=sys.stderr,
    )
    sys.exit(1)

import pandas as pd

# Add the scripts directory to the path so we can import cost_dashboard
sys.path.insert(0, str(Path(__file__).parent))
from cost_dashboard import (  # noqa: E402
    daily_totals,
    spend_by_dimensions,
    cost_component_breakdown,
    load_csv,
    TOTAL_COL,
    DATE_COL,
)

st.set_page_config(page_title="Cost Dashboard", layout="wide")
st.title("☁️ Cloudflare Billing Cost Dashboard")

# ---------------------------------------------------------------------------
# File selection
# ---------------------------------------------------------------------------
st.sidebar.header("Data Source")
upload = st.sidebar.file_uploader("Upload a billing CSV", type=["csv"])

default_path = Path(__file__).parent.parent / "data" / "sample_billing.csv"
use_sample = st.sidebar.checkbox(
    "Use sample CSV",
    value=(not upload and default_path.exists()),
)

df: pd.DataFrame | None = None

if upload:
    try:
        df = load_csv(io.StringIO(upload.getvalue().decode("utf-8")))
        st.sidebar.success(f"Loaded {len(df)} rows from uploaded file.")
    except (FileNotFoundError, ValueError, UnicodeDecodeError) as exc:
        st.sidebar.error(f"Error loading file: {exc}")
elif use_sample and default_path.exists():
    try:
        df = load_csv(default_path)
        st.sidebar.info(f"Using sample CSV ({len(df)} rows).")
    except (FileNotFoundError, ValueError) as exc:
        st.sidebar.error(f"Error loading sample: {exc}")
else:
    st.info("Upload a CSV using the sidebar, or enable 'Use sample CSV'.")

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
if df is not None:
    t1 = daily_totals(df)
    t2 = spend_by_dimensions(df)
    t3 = cost_component_breakdown(df)

    # --- Daily totals line chart ---
    st.subheader("Daily Total Spend")
    chart_data = t1.set_index(DATE_COL)["total_usd"]
    st.line_chart(chart_data)

    st.subheader("Table 1 — Daily Totals")
    st.dataframe(t1, use_container_width=True)

    st.subheader("Table 2 — Spend by Dimensions")
    st.dataframe(t2, use_container_width=True)

    st.subheader("Table 3 — Cost-Component Breakdown")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(t3, use_container_width=True)
    with col2:
        st.bar_chart(t3.set_index("cost_component")["total_usd"])

    # --- CSV downloads ---
    st.subheader("Download Tables")
    dl1, dl2, dl3 = st.columns(3)
    with dl1:
        st.download_button(
            "⬇ Daily Totals CSV",
            t1.to_csv(index=False).encode(),
            "daily_totals.csv",
            "text/csv",
        )
    with dl2:
        st.download_button(
            "⬇ Spend by Dimensions CSV",
            t2.to_csv(index=False).encode(),
            "spend_by_dimensions.csv",
            "text/csv",
        )
    with dl3:
        st.download_button(
            "⬇ Cost Components CSV",
            t3.to_csv(index=False).encode(),
            "cost_component_breakdown.csv",
            "text/csv",
        )
