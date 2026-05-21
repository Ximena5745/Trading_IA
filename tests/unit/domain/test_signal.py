"""
Tests for domain/entities/signal.py
CA-1: Signal con action=BUY tiene stop_loss < entry_price < take_profit
CA-2: Signal confidence está en rango [0, 1]
"""
import pytest
from datetime import datetime
from domain.entities.signal import Signal, SignalExplanationFactor


class TestSignalInvariants:
    """Tests for Signal entity invariants."""

    def test_buy_signal_valid_invariant(self):
        """CA-1: BUY signal must have stop_loss < entry_price < take_profit."""
        signal = Signal(
            id="test-1",
            idempotency_key="key-1",
            symbol="BTCUSDT",
            action="BUY",
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            risk_reward_ratio=2.0,
            confidence=0.8,
        )
        assert signal.is_valid_for_buy() is True

    def test_buy_signal_invalid_invariant(self):
        """CA-1: BUY signal with invalid SL/TP should fail invariant."""
        signal = Signal(
            id="test-2",
            idempotency_key="key-2",
            symbol="BTCUSDT",
            action="BUY",
            entry_price=50000.0,
            stop_loss=51000.0,  # SL > entry (invalid)
            take_profit=52000.0,
            risk_reward_ratio=0.5,
            confidence=0.8,
        )
        assert signal.is_valid_for_buy() is False

    def test_sell_signal_valid_invariant(self):
        """CA-1: SELL signal must have take_profit < entry_price < stop_loss."""
        signal = Signal(
            id="test-3",
            idempotency_key="key-3",
            symbol="BTCUSDT",
            action="SELL",
            entry_price=50000.0,
            stop_loss=51000.0,
            take_profit=49000.0,
            risk_reward_ratio=2.0,
            confidence=0.7,
        )
        assert signal.is_valid_for_sell() is True

    def test_sell_signal_invalid_invariant(self):
        """CA-1: SELL signal with invalid SL/TP should fail invariant."""
        signal = Signal(
            id="test-4",
            idempotency_key="key-4",
            symbol="BTCUSDT",
            action="SELL",
            entry_price=50000.0,
            stop_loss=49000.0,  # SL < entry (invalid)
            take_profit=48000.0,
            risk_reward_ratio=0.5,
            confidence=0.7,
        )
        assert signal.is_valid_for_sell() is False

    def test_confidence_range_lower_bound(self):
        """CA-2: Confidence 0.0 should be valid."""
        signal = Signal(
            id="test-5",
            idempotency_key="key-5",
            symbol="BTCUSDT",
            action="BUY",
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            risk_reward_ratio=2.0,
            confidence=0.0,
        )
        assert signal.confidence == 0.0

    def test_confidence_range_upper_bound(self):
        """CA-2: Confidence 1.0 should be valid."""
        signal = Signal(
            id="test-6",
            idempotency_key="key-6",
            symbol="BTCUSDT",
            action="BUY",
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            risk_reward_ratio=2.0,
            confidence=1.0,
        )
        assert signal.confidence == 1.0

    def test_confidence_below_zero_invalid(self):
        """CA-2: Confidence < 0 should raise ValidationError."""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            Signal(
                id="test-7",
                idempotency_key="key-7",
                symbol="BTCUSDT",
                action="BUY",
                entry_price=50000.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                risk_reward_ratio=2.0,
                confidence=-0.1,
            )

    def test_confidence_above_one_invalid(self):
        """CA-2: Confidence > 1 should raise ValidationError."""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            Signal(
                id="test-8",
                idempotency_key="key-8",
                symbol="BTCUSDT",
                action="BUY",
                entry_price=50000.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                risk_reward_ratio=2.0,
                confidence=1.5,
            )

    def test_entry_price_must_be_positive(self):
        """Entry price must be positive."""
        with pytest.raises(ValueError, match="Entry price must be positive"):
            Signal(
                id="test-9",
                idempotency_key="key-9",
                symbol="BTCUSDT",
                action="BUY",
                entry_price=0.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                risk_reward_ratio=2.0,
                confidence=0.8,
            )

    def test_hold_signal_always_valid(self):
        """HOLD signals should not have SL/TP invariants."""
        signal = Signal(
            id="test-10",
            idempotency_key="key-10",
            symbol="BTCUSDT",
            action="HOLD",
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            risk_reward_ratio=0.0,
            confidence=0.5,
        )
        assert signal.is_valid_for_buy() is True
        assert signal.is_valid_for_sell() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])