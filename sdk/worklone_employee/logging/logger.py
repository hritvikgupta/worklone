"""Logging for the worklone_employee SDK."""

from __future__ import annotations

import logging
import sys


def get_logger(name: str, level: str | None = None) -> logging.Logger:
    logger_name = name if name.startswith("worklone_employee.") else f"worklone_employee.{name}"
    logger = logging.getLogger(logger_name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"))
        logger.addHandler(handler)
        logger.propagate = False
    if level:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    elif not logger.level:
        logger.setLevel(logging.INFO)
    return logger
