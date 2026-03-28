"""
Module: app/pages/simulator.py
Responsibility: Streamlit "what if" historical simulator — interactive scenario analysis
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

API_BASE = "http://localhost:8000"


def _get_headers() -> dict:
    token = st.session_state.get("access_token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _fetch_strategies() -> list[dict]:
    try:
        r = requests.get(f"{API_BASE}/strategies", headers=_get_headers(), timeout=5)
        if r.status_code == 200:
            return r.json().get("strategies", [])
    except Exception:
        pass
    return []


def _submit_simulation(payload: dict) -> dict | None:
    try:
        r = requests.post(
            f"{API_BASE}/simulation",
            json=payload,
            headers=_get_headers(),
            timeout=10,
        )
        if r.status_code in (200, 202):
            return r.json()
        st.error(f"Submit error {r.status_code}: {r.text}")
    except Exception as exc:
        st.error(str(exc))
    return None


def _poll_results(job_id: str, max_attempts: int = 20) -> dict | None:
    import time

    for _ in range(max_attempts):
        try:
            r = requests.get(
                f"{API_BASE}/simulation/{job_id}",
                headers=_get_headers(),
                timeout=5,
            )
            if r.status_code == 200:
                job = r.json()
                if job.get("status") == "completed":
                    results_r = requests.get(
                        f"{API_BASE}/simulation/{job_id}/results",
                        headers=_get_headers(),
                        timeout=5,
                    )
                    if results_r.status_code == 200:
                        return results_r.json()
                elif job.get("status") == "failed":
                    st.error(f"Simulation failed: {job.get('error')}")
                    return None
        except Exception:
            pass
        time.sleep(1)
    st.warning("Simulation taking too long. Refresh the page to check status.")
    return None


def render_equity_curve(equity_curve: list[dict]) -> None:
    if not equity_curve:
        return
    df = pd.DataFrame(equity_curve)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["capital"],
            mode="lines",
            name="Capital (USD)",
            line=dict(color="#00C4FF", width=2),
            fill="tozeroy",
            fillcolor="rgba(0,196,255,0.06)",
        )
    )
    if "in_position" in df.columns and df["in_position"].any():
        pos_df = df[df["in_position"]]
        fig.add_trace(
            go.Scatter(
                x=pos_df["timestamp"],
                y=pos_df["capital"],
                mode="markers",
                name="In Position",
                marker=dict(color="#FFD700", size=4, symbol="circle"),
            )
        )
    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Date",
        yaxis_title="Capital (USD)",
        template="plotly_dark",
        height=350,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_trade_analysis(trades: list[dict]) -> None:
    if not trades:
        st.info("No trades generated in this simulation.")
        return

    df = pd.DataFrame(trades)
    pnl_col = "net_pnl"

    # P&L distribution
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=list(range(len(df))),
            y=df[pnl_col],
            marker_color=["#00E096" if v >= 0 else "#FF4B4B" for v in df[pnl_col]],
            name="Trade P&L",
        )
    )
    fig.update_layout(
        title="Trade P&L Distribution",
        xaxis_title="Trade #",
        yaxis_title="Net P&L (USD)",
        template="plotly_dark",
        height=280,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        df[
            (
                [
                    "entry_ts",
                    "exit_ts",
                    "side",
                    "entry_price",
                    "exit_price",
                    "net_pnl",
                    "bars_held",
                ]
                if all(c in df.columns for c in ["entry_ts", "bars_held"])
                else df.columns.tolist()
            )
        ],
        use_container_width=True,
    )


def render():
    st.title("🔬 Historical Simulator")
    st.markdown(
        "Run any strategy on any historical date range and see what would have happened."
    )

    # ── Configuration form ─────────────────────────────────────────────────
    strategies = _fetch_strategies()
    strategy_options = {
        s.get("name", s.get("strategy_id")): s.get("strategy_id") for s in strategies
    }

    with st.form("sim_form"):
        col1, col2 = st.columns(2)
        with col1:
            symbol = st.text_input("Symbol", value="BTCUSDT")
            strategy_name = st.selectbox(
                "Strategy",
                options=list(strategy_options.keys()) or ["ema_rsi", "mean_reversion"],
            )
            initial_capital = st.number_input(
                "Initial Capital (USD)", value=10_000.0, step=1000.0
            )

        with col2:
            start_date = st.date_input(
                "Start Date", value=datetime.now() - timedelta(days=180)
            )
            end_date = st.date_input(
                "End Date", value=datetime.now() - timedelta(days=1)
            )
            risk_pct = st.slider(
                "Risk per Trade (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.5
            )

        col3, col4 = st.columns(2)
        with col3:
            commission = st.number_input(
                "Commission (%)", value=0.10, step=0.01, format="%.2f"
            )
        with col4:
            slippage = st.number_input(
                "Slippage (%)", value=0.05, step=0.01, format="%.2f"
            )

        run_btn = st.form_submit_button("▶️ Run Simulation", use_container_width=True)

    if run_btn:
        strategy_id = strategy_options.get(strategy_name, strategy_name)
        payload = {
            "symbol": symbol.upper(),
            "strategy_id": strategy_id,
            "start": datetime.combine(start_date, datetime.min.time()).isoformat(),
            "end": datetime.combine(end_date, datetime.max.time()).isoformat(),
            "initial_capital": initial_capital,
            "risk_per_trade_pct": risk_pct / 100,
            "commission_pct": commission / 100,
            "slippage_pct": slippage / 100,
        }

        with st.spinner("Running simulation..."):
            job = _submit_simulation(payload)
            if job:
                results = _poll_results(job["job_id"])
                if results:
                    st.session_state["sim_results"] = results

    # ── Display results ────────────────────────────────────────────────────
    results = st.session_state.get("sim_results")
    if not results:
        st.info("Configure the parameters above and click **Run Simulation** to start.")
        return

    st.divider()
    st.subheader("📊 Simulation Results")

    metrics = results.get("metrics", {})
    config = results.get("config", {})

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("💰 Final Capital", f"${metrics.get('final_capital', 0):,.2f}")
    col2.metric(
        "📈 Total Return",
        f"{metrics.get('total_return_pct', 0):.2f}%",
        delta=f"{metrics.get('total_return_pct', 0):.2f}%",
    )
    col3.metric("📐 Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.3f}")
    col4.metric("📉 Max Drawdown", f"{metrics.get('max_drawdown', 0)*100:.1f}%")
    col5.metric("🎯 Win Rate", f"{metrics.get('win_rate', 0)*100:.1f}%")

    col6, col7, col8 = st.columns(3)
    col6.metric("🔄 Total Trades", metrics.get("total_trades", 0))
    col7.metric("⚡ Profit Factor", f"{metrics.get('profit_factor', 0):.2f}")
    col8.metric("📊 Expectancy", f"${metrics.get('expectancy', 0):.2f}")

    st.divider()
    render_equity_curve(results.get("equity_curve", []))

    st.divider()
    st.subheader("📋 Trade Log")
    render_trade_analysis(results.get("trades", []))

    # ── Export ─────────────────────────────────────────────────────────────
    import json

    st.download_button(
        "⬇️ Export Results (JSON)",
        data=json.dumps(results, indent=2),
        file_name=f"simulation_{config.get('symbol', 'BTCUSDT')}_{results.get('simulation_id', 'result')}.json",
        mime="application/json",
    )


render()
