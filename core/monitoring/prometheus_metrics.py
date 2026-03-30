"""
Module: core/monitoring/prometheus_metrics.py
Responsibility: Prometheus counters, histograms and gauges
Dependencies: prometheus-client
"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Signal metrics
signals_generated = Counter(
    "trader_ai_signals_generated_total",
    "Total signals generated",
    ["symbol", "direction"],
)
signals_blocked = Counter(
    "trader_ai_signals_blocked_total",
    "Total signals blocked",
    ["reason"],
)

# Execution metrics
execution_latency = Histogram(
    "trader_ai_execution_latency_ms",
    "Time from signal to order sent (ms)",
    buckets=[10, 50, 100, 250, 500, 1000, 2000],
)
orders_submitted = Counter(
    "trader_ai_orders_submitted_total",
    "Total orders submitted",
    ["symbol", "side", "mode"],
)

# WebSocket
ws_reconnections = Counter(
    "trader_ai_websocket_reconnections_total",
    "WebSocket reconnection attempts",
    ["symbol"],
)

# Kill switch
kill_switch_activations = Counter(
    "trader_ai_kill_switch_activations_total",
    "Number of kill switch activations",
    ["reason"],
)

# Model inference
model_latency = Histogram(
    "trader_ai_model_prediction_latency_ms",
    "Agent inference latency (ms)",
    ["agent_id"],
    buckets=[1, 5, 10, 25, 50, 100, 250],
)

# Portfolio gauges
portfolio_pnl = Gauge("trader_ai_portfolio_pnl", "Current portfolio P&L in USD")
portfolio_drawdown = Gauge(
    "trader_ai_portfolio_drawdown", "Current drawdown percentage"
)
portfolio_capital = Gauge("trader_ai_portfolio_capital", "Total portfolio capital")


def start_metrics_server(port: int = 8001) -> None:
    start_http_server(port)
