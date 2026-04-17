"""Typed application errors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppError(Exception):
    code: str
    message: str
    status_code: int = 500
    retryable: bool = False
    details: dict[str, Any] = field(default_factory=dict)
    log_message: str | None = None

    def __str__(self) -> str:
        return self.message

    def to_payload(self) -> dict[str, Any]:
        return {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "retryable": self.retryable,
                "details": self.details,
            },
        }


class ProviderUnavailableError(AppError):
    def __init__(self, service: str, provider: str, *, details: dict[str, Any] | None = None):
        super().__init__(
            code="PROVIDER_UNAVAILABLE",
            message=f"{service} is not configured right now.",
            status_code=503,
            retryable=False,
            details={"service": service, "provider": provider, **(details or {})},
            log_message=f"Provider unavailable for service={service} provider={provider}",
        )


class ProviderTimeoutError(AppError):
    def __init__(self, service: str, provider: str, model: str):
        super().__init__(
            code="PROVIDER_TIMEOUT",
            message=f"{service} is taking too long to respond. Try again in a moment.",
            status_code=504,
            retryable=True,
            details={"service": service, "provider": provider, "model": model},
            log_message=f"Provider timeout for service={service} provider={provider} model={model}",
        )


class ProviderRequestError(AppError):
    def __init__(
        self,
        service: str,
        provider: str,
        *,
        model: str,
        upstream_status: int,
        retryable: bool | None = None,
        details: dict[str, Any] | None = None,
    ):
        if retryable is None:
            retryable = upstream_status == 429 or upstream_status >= 500
        message = (
            f"{service} is busy right now. Try again in a moment."
            if retryable
            else f"{service} could not complete the request."
        )
        super().__init__(
            code="PROVIDER_REQUEST_FAILED",
            message=message,
            status_code=503 if retryable else 502,
            retryable=retryable,
            details={
                "service": service,
                "provider": provider,
                "model": model,
                "upstream_status": upstream_status,
                **(details or {}),
            },
            log_message=(
                f"Provider request failed for service={service} provider={provider} "
                f"model={model} upstream_status={upstream_status}"
            ),
        )


class InvalidProviderResponseError(AppError):
    def __init__(self, service: str, provider: str, *, model: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="INVALID_PROVIDER_RESPONSE",
            message=f"{service} returned an invalid response. Try again in a moment.",
            status_code=502,
            retryable=True,
            details={"service": service, "provider": provider, "model": model, **(details or {})},
            log_message=f"Invalid provider response for service={service} provider={provider} model={model}",
        )
