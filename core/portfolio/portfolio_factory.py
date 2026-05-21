"""
Module: core/portfolio/portfolio_factory.py
Responsibility: Factory para elegir implementación Redis o in-memory
"""
from core.config.settings import Settings, get_settings
from core.portfolio.portfolio_manager import PortfolioManager
from core.portfolio.portfolio_manager_redis import PortfolioManagerRedis


def get_portfolio_manager(
    use_redis: bool = True,
    settings: Settings | None = None,
    initial_capital: float = 10_000.0,
):
    """
    Factory para obtener PortfolioManager.
    Args:
        use_redis: Si True, usa la versión con persistencia Redis.
                   Si False, usa la versión in-memory.
    """
    settings = settings or get_settings()
    if use_redis:
        try:
            return PortfolioManagerRedis()
        except Exception:
            return PortfolioManager(settings=settings, initial_capital=initial_capital)
    return PortfolioManager(settings=settings, initial_capital=initial_capital)