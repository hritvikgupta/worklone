"""Centralized backend logging."""

from __future__ import annotations

import logging
import sys

from backend.core.config.settings import get_settings
from backend.core.logging.request_context import get_request_id


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def configure_logging() -> None:
    settings = get_settings()
    root_logger = logging.getLogger()
    if getattr(root_logger, "_backend_logging_configured", False):
        root_logger.setLevel(getattr(logging, settings.log_level, logging.INFO))
        return

    root_logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(request_id)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestContextFilter())
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.log_level, logging.INFO))
    root_logger._backend_logging_configured = True  # type: ignore[attr-defined]


def get_logger(name: str, level: str | None = None) -> logging.Logger:
    configure_logging()
    logger_name = name if name.startswith("backend.") else f"backend.{name}"
    logger = logging.getLogger(logger_name)
    if level:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger
