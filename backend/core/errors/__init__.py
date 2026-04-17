"""Shared application error primitives."""

from backend.core.errors.exceptions import (
    AppError,
    InvalidProviderResponseError,
    ProviderRequestError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from backend.core.errors.handlers import register_exception_handlers

__all__ = [
    "AppError",
    "InvalidProviderResponseError",
    "ProviderRequestError",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "register_exception_handlers",
]
