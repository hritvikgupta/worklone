"""Environment-backed application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class AppSettings:
    environment: str
    log_level: str
    log_include_request_id: bool
    provider_error_body_limit: int
    deployment_mode: str


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    environment = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).strip() or "development"
    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"
    include_request_id = os.getenv("LOG_INCLUDE_REQUEST_ID", "true").strip().lower() != "false"
    provider_error_body_limit = int(os.getenv("PROVIDER_ERROR_BODY_LIMIT", "600"))
    # AUTH_MODE takes priority, falls back to DEPLOYMENT_MODE
    deployment_mode = (
        os.getenv("AUTH_MODE") or os.getenv("DEPLOYMENT_MODE") or "self_hosted"
    ).strip().lower()
    if deployment_mode not in {"cloud", "self_hosted"}:
        deployment_mode = "self_hosted"
    return AppSettings(
        environment=environment,
        log_level=log_level,
        log_include_request_id=include_request_id,
        provider_error_body_limit=provider_error_body_limit,
        deployment_mode=deployment_mode,
    )
