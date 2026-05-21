"""
Tests for UserProfileEngine (M5.6).
"""
from __future__ import annotations

import pytest

from core.risk.user_profile_engine import (
    PROFILES,
    TradingProfile,
    UserProfileEngine,
)


class TestUserProfileEngine:
    """Tests para UserProfileEngine."""

    def test_get_scalper_profile(self):
        """Verificar valores de perfil scalper."""
        engine = UserProfileEngine()
        profile = engine.get_profile("scalper")

        assert profile.profile_id == "scalper"
        assert profile.risk_per_trade == 0.005
        assert profile.max_drawdown == 0.05
        assert profile.min_rr_ratio == 1.0
        assert profile.min_confidence == 0.60
        assert profile.max_signals_per_day == 30
        assert profile.max_correlation == 0.8

    def test_get_day_trader_profile(self):
        """Verificar valores de perfil day_trader."""
        engine = UserProfileEngine()
        profile = engine.get_profile("day_trader")

        assert profile.profile_id == "day_trader"
        assert profile.risk_per_trade == 0.010
        assert profile.max_drawdown == 0.08
        assert profile.min_rr_ratio == 1.5
        assert profile.min_confidence == 0.55
        assert profile.max_signals_per_day == 8

    def test_get_swing_profile(self):
        """Verificar valores de perfil swing."""
        engine = UserProfileEngine()
        profile = engine.get_profile("swing")

        assert profile.profile_id == "swing"
        assert profile.risk_per_trade == 0.015
        assert profile.max_drawdown == 0.12
        assert profile.min_rr_ratio == 2.0
        assert profile.min_confidence == 0.60
        assert profile.max_signals_per_day == 3

    def test_get_position_profile(self):
        """Verificar valores de perfil position."""
        engine = UserProfileEngine()
        profile = engine.get_profile("position")

        assert profile.profile_id == "position"
        assert profile.risk_per_trade == 0.020
        assert profile.max_drawdown == 0.20
        assert profile.min_rr_ratio == 2.5
        assert profile.min_confidence == 0.70
        assert profile.max_signals_per_day == 1

    def test_get_conservative_profile(self):
        """Verificar valores de perfil conservative."""
        engine = UserProfileEngine()
        profile = engine.get_profile("conservative")

        assert profile.profile_id == "conservative"
        assert profile.risk_per_trade == 0.005
        assert profile.max_drawdown == 0.05
        assert profile.min_rr_ratio == 2.5
        assert profile.min_confidence == 0.75
        assert profile.max_signals_per_day == 3

    def test_profile_not_found_fallback(self):
        """Fallback a day_trader si perfil no existe."""
        engine = UserProfileEngine()
        profile = engine.get_profile("nonexistent")

        assert profile.profile_id == "day_trader"

    def test_list_profiles(self):
        """Verificar que devuelve los 5 perfiles."""
        engine = UserProfileEngine()
        profiles = engine.list_profiles()

        assert len(profiles) == 5

        profile_ids = [p["id"] for p in profiles]
        assert "scalper" in profile_ids
        assert "day_trader" in profile_ids
        assert "swing" in profile_ids
        assert "position" in profile_ids
        assert "conservative" in profile_ids

    def test_list_profiles_format(self):
        """Verificar formato de lista de perfiles."""
        engine = UserProfileEngine()
        profiles = engine.list_profiles()

        for profile in profiles:
            assert "id" in profile
            assert "description" in profile
            assert "risk_per_trade" in profile
            assert "max_drawdown" in profile
            assert "min_confidence" in profile

    def test_create_custom_profile(self):
        """Crear perfil personalizado y verificar."""
        engine = UserProfileEngine()
        profile = engine.create_custom_profile(
            profile_id="aggressive",
            risk_per_trade=0.03,
            max_drawdown=0.25,
            min_rr_ratio=3.0,
            min_confidence=0.80,
            max_signals_per_day=2,
            description="Custom aggressive profile",
        )

        assert profile.profile_id == "aggressive"
        assert profile.risk_per_trade == 0.03
        assert profile.max_drawdown == 0.25
        assert profile.min_rr_ratio == 3.0
        assert profile.min_confidence == 0.80
        assert profile.max_signals_per_day == 2

    def test_get_custom_profile(self):
        """Recuperar perfil personalizado creado."""
        engine = UserProfileEngine()
        engine.create_custom_profile(
            profile_id="test_profile",
            risk_per_trade=0.025,
            max_drawdown=0.15,
            min_rr_ratio=2.0,
            min_confidence=0.65,
            max_signals_per_day=5,
        )

        profile = engine.get_profile("test_profile")
        assert profile.profile_id == "test_profile"
        assert profile.risk_per_trade == 0.025


class TestTradingProfile:
    """Tests para la clase TradingProfile."""

    def test_profile_attributes_complete(self):
        """Verificar que todos los perfiles tienen atributos completos."""
        for profile in PROFILES.values():
            assert profile.profile_id is not None
            assert profile.risk_per_trade > 0
            assert profile.max_drawdown > 0
            assert profile.min_rr_ratio > 0
            assert profile.min_confidence > 0
            assert profile.max_signals_per_day > 0
            assert 0 <= profile.max_correlation <= 1
            assert profile.description is not None


class TestProfileComparison:
    """Tests comparativos entre perfiles."""

    def test_scalper_vs_conservative(self):
        """Scalper debe ser más agresivo que conservative en señales, menos en confianza."""
        engine = UserProfileEngine()
        scalper = engine.get_profile("scalper")
        conservative = engine.get_profile("conservative")

        assert scalper.max_signals_per_day > conservative.max_signals_per_day
        assert scalper.min_confidence < conservative.min_confidence

    def test_swing_vs_position(self):
        """Swing debe ser menos agresivo que position."""
        engine = UserProfileEngine()
        swing = engine.get_profile("swing")
        position = engine.get_profile("position")

        assert swing.risk_per_trade < position.risk_per_trade
        assert swing.max_drawdown < position.max_drawdown
        assert swing.min_confidence < position.min_confidence


if __name__ == "__main__":
    pytest.main([__file__, "-v"])