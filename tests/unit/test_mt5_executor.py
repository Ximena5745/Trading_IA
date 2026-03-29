"""
Tests for MT5Executor — safety checks and order routing (FASE E).
All tests use mocked MT5Client to avoid requiring a live MT5 terminal.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.config.settings import Settings
from core.exceptions import ExecutionError, KillSwitchActiveError
from core.execution.mt5_executor import MT5Executor


def make_settings(
    execution_mode: str = "live",
    trading_enabled: bool = True,
) -> Settings:
    s = MagicMock(spec=Settings)
    s.EXECUTION_MODE = execution_mode
    s.TRADING_ENABLED = trading_enabled
    return s


def make_kill_switch(active: bool = False) -> MagicMock:
    ks = MagicMock()
    ks.is_active.return_value = active
    ks.state.triggered_by = "manual" if active else None
    return ks


def make_mt5_client(fill_price: float = 1.1015) -> MagicMock:
    client = MagicMock()
    client.place_order = AsyncMock(return_value={
        "exchange_order_id": "MT5_ORDER_123",
        "fill_price": fill_price,
        "status": "filled",
    })
    return client


def make_signal(
    symbol: str = "EURUSD",
    action: str = "BUY",
    entry_price: float = 1.1000,
    stop_loss: float = 1.0950,
    take_profit: float = 1.1100,
    idempotency_key: str = "test-key-001",
) -> dict:
    return {
        "id": "signal-001",
        "symbol": symbol,
        "action": action,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "idempotency_key": idempotency_key,
    }


class TestSafetyChecks:
    """MT5Executor must block all orders when safety conditions not met."""

    @pytest.mark.asyncio
    async def test_rejects_paper_mode(self):
        executor = MT5Executor(
            settings=make_settings(execution_mode="paper"),
            kill_switch=make_kill_switch(),
            mt5_client=make_mt5_client(),
        )
        with pytest.raises(ExecutionError, match="EXECUTION_MODE"):
            await executor.execute(make_signal(), quantity=0.01)

    @pytest.mark.asyncio
    async def test_rejects_when_trading_disabled(self):
        executor = MT5Executor(
            settings=make_settings(trading_enabled=False),
            kill_switch=make_kill_switch(),
            mt5_client=make_mt5_client(),
        )
        with pytest.raises(ExecutionError, match="TRADING_ENABLED"):
            await executor.execute(make_signal(), quantity=0.01)

    @pytest.mark.asyncio
    async def test_rejects_when_kill_switch_active(self):
        executor = MT5Executor(
            settings=make_settings(),
            kill_switch=make_kill_switch(active=True),
            mt5_client=make_mt5_client(),
        )
        with pytest.raises(KillSwitchActiveError):
            await executor.execute(make_signal(), quantity=0.01)

    @pytest.mark.asyncio
    async def test_all_three_checks_independent(self):
        """Each check independently blocks — test paper mode + disabled + kill switch."""
        # paper mode alone
        for mode, enabled, ks_active in [
            ("paper", True,  False),
            ("live",  False, False),
            ("live",  True,  True),
        ]:
            executor = MT5Executor(
                settings=make_settings(execution_mode=mode, trading_enabled=enabled),
                kill_switch=make_kill_switch(active=ks_active),
                mt5_client=make_mt5_client(),
            )
            with pytest.raises((ExecutionError, KillSwitchActiveError)):
                await executor.execute(make_signal(), quantity=0.01)


class TestSuccessfulExecution:
    """Happy path — all checks pass, order placed."""

    @pytest.mark.asyncio
    async def test_returns_order_dict(self):
        executor = MT5Executor(
            settings=make_settings(),
            kill_switch=make_kill_switch(),
            mt5_client=make_mt5_client(fill_price=1.1015),
        )
        order = await executor.execute(make_signal(), quantity=0.01)
        assert order is not None
        assert order["symbol"] == "EURUSD"
        assert order["side"] == "BUY"
        assert order["quantity"] == 0.01
        assert order["status"] == "filled"
        assert order["provider"] == "mt5"

    @pytest.mark.asyncio
    async def test_order_has_execution_mode_live(self):
        executor = MT5Executor(
            settings=make_settings(),
            kill_switch=make_kill_switch(),
            mt5_client=make_mt5_client(),
        )
        order = await executor.execute(make_signal(), quantity=0.05)
        assert order["execution_mode"] == "live"

    @pytest.mark.asyncio
    async def test_commission_is_zero_for_mt5(self):
        """IC Markets Raw account: spread-only, no separate commission."""
        executor = MT5Executor(
            settings=make_settings(),
            kill_switch=make_kill_switch(),
            mt5_client=make_mt5_client(),
        )
        order = await executor.execute(make_signal(), quantity=0.01)
        assert order["commission"] == 0.0

    @pytest.mark.asyncio
    async def test_fill_price_comes_from_client(self):
        fill = 1.1022
        executor = MT5Executor(
            settings=make_settings(),
            kill_switch=make_kill_switch(),
            mt5_client=make_mt5_client(fill_price=fill),
        )
        order = await executor.execute(make_signal(entry_price=1.1000), quantity=0.01)
        assert order["fill_price"] == fill

    @pytest.mark.asyncio
    async def test_order_has_unique_uuid(self):
        executor = MT5Executor(
            settings=make_settings(),
            kill_switch=make_kill_switch(),
            mt5_client=make_mt5_client(),
        )
        order1 = await executor.execute(make_signal(idempotency_key="key-1"), quantity=0.01)
        order2 = await executor.execute(make_signal(idempotency_key="key-2"), quantity=0.01)
        assert order1["id"] != order2["id"]


class TestIdempotency:
    """Duplicate idempotency keys must be rejected."""

    @pytest.mark.asyncio
    async def test_duplicate_key_raises_execution_error(self):
        executor = MT5Executor(
            settings=make_settings(),
            kill_switch=make_kill_switch(),
            mt5_client=make_mt5_client(),
        )
        signal = make_signal(idempotency_key="unique-key-xyz")
        await executor.execute(signal, quantity=0.01)

        with pytest.raises(ExecutionError, match="Duplicate"):
            await executor.execute(signal, quantity=0.01)

    @pytest.mark.asyncio
    async def test_different_keys_both_execute(self):
        executor = MT5Executor(
            settings=make_settings(),
            kill_switch=make_kill_switch(),
            mt5_client=make_mt5_client(),
        )
        order1 = await executor.execute(make_signal(idempotency_key="key-A"), quantity=0.01)
        order2 = await executor.execute(make_signal(idempotency_key="key-B"), quantity=0.01)
        assert order1 is not None
        assert order2 is not None


class TestCancelAndStatus:
    """Unimplemented methods must raise NotImplementedError."""

    @pytest.mark.asyncio
    async def test_cancel_order_not_implemented(self):
        executor = MT5Executor(
            settings=make_settings(),
            kill_switch=make_kill_switch(),
            mt5_client=make_mt5_client(),
        )
        with pytest.raises(NotImplementedError):
            await executor.cancel_order("order-001")

    @pytest.mark.asyncio
    async def test_get_order_status_not_implemented(self):
        executor = MT5Executor(
            settings=make_settings(),
            kill_switch=make_kill_switch(),
            mt5_client=make_mt5_client(),
        )
        with pytest.raises(NotImplementedError):
            await executor.get_order_status("order-001")
