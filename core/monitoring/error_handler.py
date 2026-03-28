"""
Module: core/monitoring/error_handler.py
Responsibility: Centralized error handling with structured logging
Dependencies: structlog, fastapi
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from structlog import get_logger

from core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ExecutionError,
    InsufficientCapitalError,
    KillSwitchActiveError,
    RiskLimitExceededError,
    TraderAIError,
)

logger = get_logger(__name__)


async def trader_ai_exception_handler(
    request: Request, exc: TraderAIError
) -> JSONResponse:
    """Handle all custom TraderAI exceptions with consistent logging."""
    error_id = logger.error(
        "trader_ai_exception",
        error_type=exc.__class__.__name__,
        message=str(exc),
        path=request.url.path,
        method=request.method,
        user_id=getattr(request.state, "user_id", None),
    )

    status_code = 500
    if isinstance(exc, AuthenticationError | AuthorizationError):
        status_code = 401
    elif isinstance(exc, RiskLimitExceededError | KillSwitchActiveError):
        status_code = 422
    elif isinstance(exc, ExecutionError | InsufficientCapitalError):
        status_code = 503

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "error_id": str(error_id),
            "timestamp": logger.bind().info("timestamp"),
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with safe error messages."""
    error_id = logger.error(
        "unexpected_exception",
        error_type=exc.__class__.__name__,
        message=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "error_id": str(error_id),
            "timestamp": logger.bind().info("timestamp"),
        },
    )


class ErrorHandler:
    """Utility class for consistent error handling across the application."""

    @staticmethod
    def log_and_raise(
        error_class: type[TraderAIError],
        message: str,
        context: dict[str, Any] | None = None,
        logger_instance=None,
    ) -> None:
        """Log error context and raise the exception."""
        log_instance = logger_instance or logger
        log_instance.error(
            "raising_exception",
            error_class=error_class.__name__,
            message=message,
            **(context or {}),
        )
        raise error_class(message)

    @staticmethod
    def safe_execute(
        func,
        default_return=None,
        error_message: str = "Operation failed",
        context: dict[str, Any] | None = None,
    ):
        """Execute function safely with error handling."""
        try:
            return func()
        except Exception as exc:
            logger.warning(
                "safe_execute_failed",
                error_message=error_message,
                error_type=exc.__class__.__name__,
                **(context or {}),
            )
            return default_return
