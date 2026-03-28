"""
Module: core/exceptions.py
Responsibility: Project-wide exception hierarchy
Dependencies: none
"""


class TraderAIError(Exception):
    """Base exception for all TraderAI errors."""


class ConfigurationError(TraderAIError):
    """Invalid settings at startup."""


class DataValidationError(TraderAIError):
    """Malformed data from exchange."""


class FeatureCalculationError(TraderAIError):
    """Excessive NaN or invalid values in features."""


class AgentPredictionError(TraderAIError):
    """Model inference failure."""


class ExecutionError(TraderAIError):
    """Failed to submit order."""


class KillSwitchActiveError(ExecutionError):
    """Trade attempted while kill switch is active."""


class InsufficientCapitalError(ExecutionError):
    """Not enough available capital for the position."""


class RiskLimitExceededError(ExecutionError):
    """Signal rejected because a risk limit would be breached."""


class AuthenticationError(TraderAIError):
    """Invalid or expired JWT token."""


class AuthorizationError(TraderAIError):
    """Insufficient role for the requested action."""


class StrategyNotFoundError(TraderAIError):
    """Strategy ID not found in registry."""


class BacktestError(TraderAIError):
    """Backtesting engine failure."""
