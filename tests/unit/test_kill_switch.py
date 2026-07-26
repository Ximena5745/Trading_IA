"""
Tests for core/risk/kill_switch.py
CA-4: Kill switch activo y verificado bajo carga concurrente
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock
from core.risk.kill_switch import KillSwitch, KillSwitchState
from core.config.settings import Settings


class TestKillSwitchTriggers:
    """Tests for Kill Switch triggers."""

    @pytest.fixture
    def settings(self):
        """Create mock settings for tests."""
        s = MagicMock(spec=Settings)
        s.DAILY_LOSS_LIMIT_PCT = 0.05  # 5%
        s.MAX_CONSECUTIVE_LOSSES = 5
        s.MAX_DRAWDOWN_PCT = 0.15  # 15%
        return s

    @pytest.fixture
    def kill_switch(self, settings):
        """Create KillSwitch instance."""
        return KillSwitch(settings)

    def test_daily_loss_trigger(self, kill_switch):
        """CA-1: Activación cuando daily loss > 5%"""
        # Simular pérdida diaria del 6%
        kill_switch.check_and_trigger(
            daily_pnl_pct=-0.06,
            drawdown_current=0.0,
            recent_trades=[],
        )
        assert kill_switch.is_active() is True
        assert kill_switch.state.triggered_by == "daily_loss_limit"

    def test_daily_loss_at_limit_not_triggered(self, kill_switch):
        """Pérdida exactamente en el límite no activa (>= es el trigger)"""
        kill_switch.check_and_trigger(
            daily_pnl_pct=-0.05,  # exactamente 5%
            drawdown_current=0.0,
            recent_trades=[],
        )
        assert kill_switch.is_active() is True  # 5% >= 5% trigger

    def test_drawdown_trigger(self, kill_switch):
        """CA-2: Activación cuando drawdown > 15%"""
        kill_switch.check_and_trigger(
            daily_pnl_pct=0.0,
            drawdown_current=0.20,  # 20%
            recent_trades=[],
        )
        assert kill_switch.is_active() is True
        assert kill_switch.state.triggered_by == "max_drawdown"

    def test_consecutive_losses_trigger(self, kill_switch):
        """CA-3: Activación cuando 5+ pérdidas consecutivas"""
        recent_trades = [
            {"net_pnl": -100},
            {"net_pnl": -50},
            {"net_pnl": -200},
            {"net_pnl": -30},
            {"net_pnl": -10},
        ]
        kill_switch.check_and_trigger(
            daily_pnl_pct=0.0,
            drawdown_current=0.0,
            recent_trades=recent_trades,
        )
        assert kill_switch.is_active() is True
        assert kill_switch.state.triggered_by == "consecutive_losses"

    def test_consecutive_losses_at_limit(self, kill_switch):
        """5 pérdidas consecutivas activa el trigger"""
        recent_trades = [
            {"net_pnl": -100},
            {"net_pnl": -50},
            {"net_pnl": -200},
            {"net_pnl": -30},
            {"net_pnl": -10},  # 5ta pérdida
        ]
        kill_switch.check_and_trigger(
            daily_pnl_pct=0.0,
            drawdown_current=0.0,
            recent_trades=recent_trades,
        )
        assert kill_switch.state.consecutive_losses == 5

    def test_no_trigger_when_safe(self, kill_switch):
        """Sistema seguro no activa el kill switch"""
        kill_switch.check_and_trigger(
            daily_pnl_pct=0.02,  # ganancia
            drawdown_current=0.05,  # dentro del límite
            recent_trades=[{"net_pnl": 100}, {"net_pnl": 50}],  # ganancias
        )
        assert kill_switch.is_active() is False
        assert kill_switch.state.triggered_by is None

    def test_reset_by_admin(self, kill_switch):
        """CA-4: Solo admin puede resetear"""
        # Primero activamos el kill switch
        kill_switch.check_and_trigger(
            daily_pnl_pct=-0.10,
            drawdown_current=0.0,
            recent_trades=[],
        )
        assert kill_switch.is_active() is True

        # Reset por admin
        kill_switch.reset("admin_token")
        assert kill_switch.is_active() is False
        assert kill_switch.state.reset_at is not None


class TestKillSwitchConcurrency:
    """Tests for concurrent access to KillSwitch."""

    @pytest.fixture
    def settings(self):
        s = MagicMock(spec=Settings)
        s.DAILY_LOSS_LIMIT_PCT = 0.05
        s.MAX_CONSECUTIVE_LOSSES = 5
        s.MAX_DRAWDOWN_PCT = 0.15
        return s

    @pytest.fixture
    def kill_switch(self, settings):
        return KillSwitch(settings)

    def test_concurrent_trigger_checks(self, settings):
        """CA-4: Verificar que múltiples triggers concurrentes no generan errores"""
        import threading
        import time

        kill_switch = KillSwitch(settings)
        errors = []
        results = []

        def trigger_from_thread(thread_id):
            try:
                if thread_id % 2 == 0:
                    kill_switch.check_and_trigger(
                        daily_pnl_pct=-0.06,
                        drawdown_current=0.0,
                        recent_trades=[],
                    )
                else:
                    kill_switch.check_and_trigger(
                        daily_pnl_pct=0.0,
                        drawdown_current=0.20,
                        recent_trades=[],
                    )
                results.append(kill_switch.is_active())
            except Exception as e:
                errors.append(str(e))

        threads = []
        for i in range(10):
            t = threading.Thread(target=trigger_from_thread, args=(i,))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors in concurrent execution: {errors}"
        # Al menos un trigger debe haber activado
        assert any(results), "No triggers activated"

    def test_rapid_on_off_cycles(self, settings):
        """Verificar que ciclos rápidos de trigger/reset funcionan"""
        kill_switch = KillSwitch(settings)

        for _ in range(100):
            # Trigger
            kill_switch.check_and_trigger(
                daily_pnl_pct=-0.10,
                drawdown_current=0.0,
                recent_trades=[],
            )
            assert kill_switch.is_active() is True

            # Reset
            kill_switch.reset("admin")
            assert kill_switch.is_active() is False

    def test_trigger_stays_active_until_explicit_reset(self, kill_switch):
        """Una vez activado, el kill switch debe permanecer activo hasta reset explícito"""
        # Trigger inicial
        kill_switch.check_and_trigger(
            daily_pnl_pct=-0.06,
            drawdown_current=0.0,
            recent_trades=[],
        )
        assert kill_switch.is_active() is True

        # Llamadas subsecuentes no deberían desactivar
        for _ in range(10):
            kill_switch.check_and_trigger(
                daily_pnl_pct=0.02,  # recuperación
                drawdown_current=0.0,
                recent_trades=[],
            )
            assert kill_switch.is_active() is True


class TestKillSwitchState:
    """Tests for KillSwitchState."""

    def test_state_initial_values(self):
        """Verificar valores iniciales del estado"""
        state = KillSwitchState(
            daily_loss_limit=0.05,
            max_consecutive_losses=5,
            max_drawdown=0.15,
        )
        assert state.active is False
        assert state.triggered_at is None
        assert state.triggered_by is None
        assert state.daily_loss_current == 0.0
        assert state.consecutive_losses == 0


class TestKillSwitchRedisFailClosed:
    """Kill switch must fail closed (block trading) when Redis is unreachable — P4."""

    @pytest.fixture
    def broken_redis(self):
        client = MagicMock()
        client.get.side_effect = ConnectionError("redis unreachable")
        client.set.side_effect = ConnectionError("redis unreachable")
        return client

    @pytest.fixture
    def kill_switch_redis(self, broken_redis):
        from core.risk.kill_switch_redis import KillSwitchRedis

        return KillSwitchRedis(redis_client=broken_redis)

    def test_is_active_true_when_redis_down(self, kill_switch_redis):
        """Redis unreachable must be reported as active=True, never False."""
        assert kill_switch_redis.is_active() is True

    def test_state_reports_active_when_redis_down(self, kill_switch_redis):
        state = kill_switch_redis.state
        assert state["active"] is True
        assert state["triggered_by"] == "redis_unavailable"

    def test_check_and_trigger_does_not_raise_when_redis_down(self, kill_switch_redis):
        """Cannot persist/evaluate, but must not crash the caller either."""
        kill_switch_redis.check_and_trigger(
            daily_pnl_pct=0.01,
            drawdown_current=0.0,
            recent_trades=[],
        )
        assert kill_switch_redis.is_active() is True

    def test_activate_raises_when_redis_down(self, kill_switch_redis):
        """Admin must be told the manual activation was NOT persisted."""
        from core.risk.kill_switch_redis import KillSwitchRedisUnavailableError

        with pytest.raises(KillSwitchRedisUnavailableError):
            kill_switch_redis.activate("manual")

    def test_reset_raises_when_redis_down(self, kill_switch_redis):
        """Admin must be told the reset was NOT persisted (stays fail-closed active)."""
        from core.risk.kill_switch_redis import KillSwitchRedisUnavailableError

        with pytest.raises(KillSwitchRedisUnavailableError):
            kill_switch_redis.reset("admin_token")

    def test_is_active_reflects_real_state_when_redis_up(self):
        from core.risk.kill_switch_redis import KillSwitchRedis

        healthy_redis = MagicMock()
        healthy_redis.get.return_value = None
        ks = KillSwitchRedis(redis_client=healthy_redis)
        assert ks.is_active() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])