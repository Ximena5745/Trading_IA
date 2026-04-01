"""
Module: core/observability/logger.py
Responsibility: Structured JSON logging with structlog
Dependencies: structlog
"""
from __future__ import annotations

import logging

try:
    import structlog
except ImportError:
    structlog = None  # type: ignore


def configure_logging(log_level: str = "INFO") -> None:
    if structlog is None:
        # Fallback to estándar cuando structlog no está instalado
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        return

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    if structlog is None:
        return logging.getLogger(name)
    return structlog.get_logger(name)
