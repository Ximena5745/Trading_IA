"""
Tests for backtesting components.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta
import numpy as np

from core.backtesting.metrics import compute_all
from core.backtesting.costs import CostModel


class TestBacktestMetrics:
    def test_sharpe_positive_returns(self):
        """Sharpe ratio should be positive for consistent gains."""
        pnls = [10.0, 15.0, 8.0, 12.0, 9.0, 11.0, 14.0, 10.0]
        metrics = compute_all(pnls)
        assert metrics["sharpe_ratio"] > 0
        assert metrics["win_rate"] == 1.0

    def test_max_drawdown_all_positive(self):
        """Max drawdown is 0 when all trades are profitable."""
        pnls = [5.0, 10.0, 8.0, 12.0]
        metrics = compute_all(pnls)
        assert metrics["max_drawdown"] == 0.0

    def test_empty_pnl_returns_zeros(self):
        """compute_all handles empty list without error."""
        metrics = compute_all([])
        assert metrics["sharpe_ratio"] == 0.0
        assert metrics["win_rate"] == 0.0

    def test_negative_returns_sharpe(self):
        """Sharpe ratio should be negative for consistent losses."""
        pnls = [-5.0, -10.0, -8.0, -12.0]
        metrics = compute_all(pnls)
        assert metrics["sharpe_ratio"] < 0
        assert metrics["win_rate"] == 0.0

    def test_mixed_returns_metrics(self):
        """Test metrics with mixed winning and losing trades."""
        pnls = [10.0, -5.0, 15.0, -3.0, 8.0, -2.0, 12.0]
        metrics = compute_all(pnls)
        
        assert 0 < metrics["win_rate"] < 1
        assert metrics["total_trades"] == len(pnls)
        assert metrics["total_pnl"] == sum(pnls)
        assert metrics["avg_win"] > 0
        assert metrics["avg_loss"] < 0

    def test_consecutive_losses_tracking(self):
        """Test tracking of consecutive losses."""
        pnls = [5.0, -3.0, -2.0, -4.0, 8.0, -1.0, -2.0, -3.0]
        metrics = compute_all(pnls)
        
        assert metrics["max_consecutive_losses"] == 3
        assert metrics["max_consecutive_wins"] == 1

    def test_profit_factor_calculation(self):
        """Test profit factor calculation."""
        pnls = [20.0, 15.0, -5.0, -8.0, 25.0, -3.0]
        metrics = compute_all(pnls)
        
        total_wins = sum(p for p in pnls if p > 0)
        total_losses = abs(sum(p for p in pnls if p < 0))
        expected_profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        assert abs(metrics["profit_factor"] - expected_profit_factor) < 0.01

    def test_volatility_calculation(self):
        """Test volatility (standard deviation) calculation."""
        pnls = [10.0, 15.0, 8.0, 12.0, 9.0]
        metrics = compute_all(pnls)
        
        expected_vol = np.std(pnls)
        assert abs(metrics["volatility"] - expected_vol) < 0.01

    def test_calmar_ratio(self):
        """Test Calmar ratio calculation."""
        pnls = [10.0, 15.0, 8.0, -5.0, 12.0, 20.0, 18.0]
        metrics = compute_all(pnls)
        
        # Calmar ratio = total_return / max_drawdown
        if metrics["max_drawdown"] > 0:
            expected_calmar = metrics["total_pnl"] / metrics["max_drawdown"]
            assert abs(metrics["calmar_ratio"] - expected_calmar) < 0.01
        else:
            # When no drawdown, Calmar should be very high or inf
            assert metrics["calmar_ratio"] >= 0


class TestCostModel:
    def test_costs_reduce_pnl(self):
        """Cost model must reduce gross P&L."""
        model = CostModel()
        gross_pnl = 100.0
        entry_price = 50000.0
        size = 0.01
        net = model.apply(gross_pnl, entry_price, size)
        assert net < gross_pnl

    def test_zero_pnl_still_has_costs(self):
        """Break-even trade is actually a loss after costs."""
        model = CostModel()
        net = model.apply(0.0, 50000.0, 0.01)
        assert net < 0.0

    def test_cost_calculation_accuracy(self):
        """Test cost calculation with known values."""
        model = CostModel()
        
        # For a $50,000 trade with 0.01 size = $500 notional
        # Commission: 0.1% of $500 = $0.5
        # Slippage: 0.05% of $500 = $0.25
        # Total cost: $0.75
        gross_pnl = 10.0
        entry_price = 50000.0
        size = 0.01
        
        net = model.apply(gross_pnl, entry_price, size)
        expected_net = gross_pnl - (50000.0 * 0.01 * 0.0015)  # 0.15% total costs
        
        assert abs(net - expected_net) < 0.01

    def test_negative_pnl_with_costs(self):
        """Test that costs make negative P&L worse."""
        model = CostModel()
        gross_pnl = -10.0
        entry_price = 50000.0
        size = 0.01
        
        net = model.apply(gross_pnl, entry_price, size)
        assert net < gross_pnl  # More negative after costs

    def test_large_trade_costs(self):
        """Test cost scaling with trade size."""
        model = CostModel()
        gross_pnl = 100.0
        entry_price = 50000.0
        
        # Small trade
        net_small = model.apply(gross_pnl, entry_price, 0.01)
        
        # Large trade (10x size)
        net_large = model.apply(gross_pnl, entry_price, 0.1)
        
        # Large trade should have proportionally more costs
        assert net_large < net_small

    def test_zero_size_trade(self):
        """Test edge case with zero position size."""
        model = CostModel()
        gross_pnl = 100.0
        entry_price = 50000.0
        size = 0.0
        
        net = model.apply(gross_pnl, entry_price, size)
        # Zero size should result in zero costs
        assert net == gross_pnl
