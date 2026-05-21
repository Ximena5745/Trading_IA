"""
Module: core/risk/user_profile_engine.py
Responsibility: Perfiles de riesgo predefinidos para diferentes tipos de trader.
  Perfiles:
    - scalper: alto frequency, bajo riesgo por trade
    - day_trader: trading intraday, riesgo medio
    - swing: posiciones de días/semanas, riesgo mayor
    - position: trading largo plazo, máximo riesgo
    - conservative: mínimo riesgo, máxima calidad
Dependencies: dataclasses
"""
from __future__ import annotations

from dataclasses import dataclass

from core.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TradingProfile:
    """Perfil de trading con parámetros de riesgo."""
    profile_id: str
    risk_per_trade: float
    max_drawdown: float
    min_rr_ratio: float
    min_confidence: float
    max_signals_per_day: int
    max_correlation: float
    description: str


PROFILES = {
    "scalper": TradingProfile(
        profile_id="scalper",
        risk_per_trade=0.005,
        max_drawdown=0.05,
        min_rr_ratio=1.0,
        min_confidence=0.60,
        max_signals_per_day=30,
        max_correlation=0.8,
        description="High frequency, low risk per trade",
    ),
    "day_trader": TradingProfile(
        profile_id="day_trader",
        risk_per_trade=0.010,
        max_drawdown=0.08,
        min_rr_ratio=1.5,
        min_confidence=0.55,
        max_signals_per_day=8,
        max_correlation=0.7,
        description="Intraday trading, medium risk",
    ),
    "swing": TradingProfile(
        profile_id="swing",
        risk_per_trade=0.015,
        max_drawdown=0.12,
        min_rr_ratio=2.0,
        min_confidence=0.60,
        max_signals_per_day=3,
        max_correlation=0.6,
        description="Days/weeks positions, higher risk",
    ),
    "position": TradingProfile(
        profile_id="position",
        risk_per_trade=0.020,
        max_drawdown=0.20,
        min_rr_ratio=2.5,
        min_confidence=0.70,
        max_signals_per_day=1,
        max_correlation=0.5,
        description="Long term positions, maximum risk",
    ),
    "conservative": TradingProfile(
        profile_id="conservative",
        risk_per_trade=0.005,
        max_drawdown=0.05,
        min_rr_ratio=2.5,
        min_confidence=0.75,
        max_signals_per_day=3,
        max_correlation=0.4,
        description="Minimum risk, maximum quality",
    ),
}


class UserProfileEngine:
    """
    Engine de perfiles de riesgo para usuarios.

    M5.6: User Profile Engine con 5 perfiles predefinidos.
    """

    def __init__(self):
        self._profiles = PROFILES.copy()

    def get_profile(self, profile_id: str) -> TradingProfile:
        """Obtener perfil por ID."""
        profile = self._profiles.get(profile_id)
        if not profile:
            logger.warning("profile_not_found", profile_id=profile_id)
            return self._profiles["day_trader"]
        return profile

    def list_profiles(self) -> list[dict]:
        """Listar todos los perfiles disponibles."""
        return [
            {
                "id": p.profile_id,
                "description": p.description,
                "risk_per_trade": p.risk_per_trade,
                "max_drawdown": p.max_drawdown,
                "min_confidence": p.min_confidence,
            }
            for p in self._profiles.values()
        ]

    def create_custom_profile(
        self,
        profile_id: str,
        risk_per_trade: float,
        max_drawdown: float,
        min_rr_ratio: float,
        min_confidence: float,
        max_signals_per_day: int,
        description: str = "Custom profile",
    ) -> TradingProfile:
        """Crear perfil personalizado."""
        profile = TradingProfile(
            profile_id=profile_id,
            risk_per_trade=risk_per_trade,
            max_drawdown=max_drawdown,
            min_rr_ratio=min_rr_ratio,
            min_confidence=min_confidence,
            max_signals_per_day=max_signals_per_day,
            max_correlation=0.6,
            description=description,
        )
        self._profiles[profile_id] = profile
        logger.info("custom_profile_created", profile_id=profile_id)
        return profile