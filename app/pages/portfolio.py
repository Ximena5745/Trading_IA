"""
Module: app/pages/portfolio.py
Responsibility: Streamlit P&L dashboard with positions, performance and equity curve
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

API_BASE = "http://localhost:8000"


def _get_headers() -> dict:
    token = st.session_state.get("access_token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _fetch(path: str) -> dict | list | None:
    try:
        r = requests.get(f"{API_BASE}{path}", headers=_get_headers(), timeout=5)
        if r.status_code == 200:
            return r.json()
        st.warning(f"API error {r.status_code}: {r.text[:120]}")
    except Exception as exc:
        st.error(f"Connection error: {exc}")
    return None


def render_equity_curve(snapshots: list[dict]) -> None:
    if not snapshots:
        st.info("No portfolio history yet.")
        return

    df = pd.DataFrame(snapshots)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["total_capital"],
            mode="lines",
            name="Capital (USD)",
            line=dict(color="#00C4FF", width=2),
            fill="tozeroy",
            fillcolor="rgba(0,196,255,0.08)",
        )
    )
    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Time",
        yaxis_title="Capital (USD)",
        template="plotly_dark",
        height=320,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_drawdown_chart(snapshots: list[dict]) -> None:
    if not snapshots:
        return

    df = pd.DataFrame(snapshots)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if "drawdown_current" not in df.columns:
        return

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["timestamp"],
            y=df["drawdown_current"] * -100,
            name="Drawdown %",
            marker_color="#FF4B4B",
        )
    )
    fig.update_layout(
        title="Drawdown (%)",
        xaxis_title="Time",
        yaxis_title="Drawdown %",
        template="plotly_dark",
        height=240,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)


def render():
    st.title("📊 Portfolio Dashboard")

    # ── Portfolio summary ──────────────────────────────────────────────────
    portfolio = _fetch("/portfolio")
    if portfolio:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 Total Capital", f"${portfolio.get('total_capital', 0):,.2f}")
        col2.metric(
            "📈 Daily P&L",
            f"{portfolio.get('daily_pnl_pct', 0) * 100:.2f}%",
            delta=f"{portfolio.get('daily_pnl_pct', 0) * 100:.2f}%",
        )
        col3.metric("📉 Drawdown", f"{portfolio.get('drawdown_current', 0) * 100:.2f}%")
        col4.metric("🔢 Open Positions", len(portfolio.get("positions", {})))

    st.divider()

    # ── Equity curve + drawdown ────────────────────────────────────────────
    history = _fetch("/portfolio/history?limit=500")
    if history:
        snapshots = history.get("snapshots", [])
        render_equity_curve(snapshots)
        render_drawdown_chart(snapshots)

    st.divider()

    # ── Open positions ─────────────────────────────────────────────────────
    st.subheader("📋 Open Positions")
    positions_data = _fetch("/portfolio/positions")
    if positions_data and positions_data.get("positions"):
        df_pos = pd.DataFrame(positions_data["positions"])
        display_cols = [
            c
            for c in [
                "symbol",
                "side",
                "size",
                "entry_price",
                "current_price",
                "unrealized_pnl",
            ]
            if c in df_pos.columns
        ]
        st.dataframe(
            df_pos[display_cols] if display_cols else df_pos, use_container_width=True
        )
    else:
        st.info("No open positions.")

    st.divider()

    # ── Strategy performance ───────────────────────────────────────────────
    st.subheader("🏆 Strategy Performance")
    perf = _fetch("/portfolio/performance")
    if perf and perf.get("strategies"):
        strategies = [s for s in perf["strategies"] if s.get("total_trades", 0) > 0]
        if strategies:
            df_perf = pd.DataFrame(strategies)
            st.dataframe(df_perf, use_container_width=True)

            # Win rate bar chart
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=df_perf["strategy_id"],
                    y=(
                        df_perf.get("win_rate", []) * 100
                        if "win_rate" in df_perf
                        else []
                    ),
                    name="Win Rate %",
                    marker_color="#00E096",
                )
            )
            fig.update_layout(
                title="Win Rate by Strategy (%)",
                template="plotly_dark",
                height=260,
                margin=dict(l=0, r=0, t=40, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No completed trades yet.")
    else:
        st.info("No strategy data available.")

    # ── Reset daily (admin action) ─────────────────────────────────────────
    with st.expander("⚙️ Admin Actions"):
        if st.button("🔄 Reset Daily Counters"):
            try:
                r = requests.post(
                    f"{API_BASE}/portfolio/reset-daily",
                    headers=_get_headers(),
                    timeout=5,
                )
                if r.status_code == 200:
                    st.success("Daily counters reset successfully.")
                else:
                    st.error(f"Reset failed: {r.text}")
            except Exception as exc:
                st.error(str(exc))


render()
