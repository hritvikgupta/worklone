"""Compatibility shim for legacy workflow logger imports."""

from backend.core.logging.logger import get_logger

logger = get_logger("workflows.engine")
