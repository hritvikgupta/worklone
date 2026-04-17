"""
Shared OAuth resolution helpers for integration tools.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

import httpx

from backend.db.stores.auth_store import AuthDB


def _get_provider_env_value(provider: str, suffix: str) -> str:
    provider_upper = provider.upper().replace("-", "_")
    candidates = [
        f"PROVIDER_{provider_upper}_{suffix}",
        f"{provider_upper}_{suffix}",
    ]
    # Google Drive and Calendar share the same OAuth app credentials as Gmail
    if provider_upper in ("GOOGLE_DRIVE", "GOOGLE_CALENDAR"):
        candidates += [f"PROVIDER_GOOGLE_{suffix}", f"GOOGLE_{suffix}"]
    for key in candidates:
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def _normalize_expiry(raw_expires_in: Any) -> Optional[str]:
    if raw_expires_in is None:
        return None
    try:
        seconds = int(raw_expires_in)
    except (TypeError, ValueError):
        return str(raw_expires_in)
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _is_expired(timestamp: str) -> bool:
    value = str(timestamp or "").strip()
    if not value:
        return False
    try:
        expires_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return expires_at <= datetime.now(timezone.utc)


@dataclass
class OAuthConnection:
    provider: str
    user_id: str
    db: AuthDB
    row: dict[str, Any] | None
    access_token: str = ""
    refresh_token: str = ""
    token_expires_at: str = ""
    provider_email: str = ""
    provider_user_id: str = ""
    scopes: str = ""
    metadata_raw: str = ""
    metadata: dict[str, Any] | None = None

    def save(
        self,
        *,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[str] = None,
        provider_email: Optional[str] = None,
        provider_user_id: Optional[str] = None,
        scopes: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        if not self.user_id:
            return

        next_access_token = access_token if access_token is not None else self.access_token
        next_refresh_token = refresh_token if refresh_token is not None else self.refresh_token
        next_expires_at = token_expires_at if token_expires_at is not None else self.token_expires_at
        next_provider_email = provider_email if provider_email is not None else self.provider_email
        next_provider_user_id = provider_user_id if provider_user_id is not None else self.provider_user_id
        next_scopes = scopes if scopes is not None else self.scopes
        next_metadata = metadata if metadata is not None else (self.metadata or {})

        self.db.save_integration(
            user_id=self.user_id,
            provider=self.provider,
            access_token=next_access_token,
            refresh_token=next_refresh_token,
            token_expires_at=next_expires_at,
            scopes=next_scopes,
            provider_user_id=next_provider_user_id,
            provider_email=next_provider_email,
            metadata=json.dumps(next_metadata) if next_metadata else self.metadata_raw,
        )

        self.access_token = next_access_token or ""
        self.refresh_token = next_refresh_token or ""
        self.token_expires_at = next_expires_at or ""
        self.provider_email = next_provider_email or ""
        self.provider_user_id = next_provider_user_id or ""
        self.scopes = next_scopes or ""
        self.metadata = next_metadata
        self.metadata_raw = json.dumps(next_metadata) if next_metadata else self.metadata_raw
        self.row = self.db.get_integration(self.user_id, self.provider)

    def merged_metadata(self, updates: dict[str, Any]) -> dict[str, Any]:
        current = dict(self.metadata or {})
        current.update(updates)
        return current


async def refresh_oauth_access_token(connection: OAuthConnection) -> str:
    provider = connection.provider
    refresh_token = connection.refresh_token.strip()
    client_id = _get_provider_env_value(provider, "CLIENT_ID")
    client_secret = _get_provider_env_value(provider, "CLIENT_SECRET")
    if not refresh_token or not client_id or not client_secret:
        return ""

    if provider in ("google", "google-drive", "google_drive", "google-calendar", "google_calendar"):
        url = "https://oauth2.googleapis.com/token"
        request_kwargs: dict[str, Any] = {
            "data": {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        }
    elif provider == "jira":
        url = "https://auth.atlassian.com/oauth/token"
        request_kwargs = {
            "json": {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        }
    else:
        return ""

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, **request_kwargs)

    if response.status_code != 200:
        return ""

    payload = response.json()
    access_token = str(payload.get("access_token") or "").strip()
    if not access_token:
        return ""

    next_refresh_token = str(payload.get("refresh_token") or refresh_token).strip()
    connection.save(
        access_token=access_token,
        refresh_token=next_refresh_token,
        token_expires_at=_normalize_expiry(payload.get("expires_in")) or connection.token_expires_at,
    )
    return access_token


async def resolve_oauth_connection(
    provider: str,
    *,
    context: dict | None = None,
    context_token_keys: tuple[str, ...] = (),
    env_token_keys: tuple[str, ...] = (),
    placeholder_predicate: Optional[Callable[[str], bool]] = None,
    allow_refresh: bool = True,
) -> OAuthConnection:
    # Normalize hyphens to underscores so "google-calendar" matches "google_calendar" in DB
    provider = provider.replace("-", "_")
    db = AuthDB()
    user_id = str((context or {}).get("user_id") or "").strip()
    row = db.get_integration(user_id, provider) if user_id else None

    metadata_raw = str((row or {}).get("metadata") or "")
    metadata: dict[str, Any] | None = None
    if metadata_raw:
        try:
            parsed = json.loads(metadata_raw)
            metadata = parsed if isinstance(parsed, dict) else {}
        except (TypeError, json.JSONDecodeError):
            metadata = {}

    connection = OAuthConnection(
        provider=provider,
        user_id=user_id,
        db=db,
        row=row,
        access_token=str((row or {}).get("access_token") or "").strip(),
        refresh_token=str((row or {}).get("refresh_token") or "").strip(),
        token_expires_at=str((row or {}).get("token_expires_at") or "").strip(),
        provider_email=str((row or {}).get("provider_email") or "").strip(),
        provider_user_id=str((row or {}).get("provider_user_id") or "").strip(),
        scopes=str((row or {}).get("scopes") or "").strip(),
        metadata_raw=metadata_raw,
        metadata=metadata or {},
    )

    def is_invalid(value: str) -> bool:
        normalized = str(value or "").strip()
        if not normalized:
            return True
        if placeholder_predicate:
            return placeholder_predicate(normalized)
        return False

    if (
        allow_refresh
        and connection.access_token
        and connection.refresh_token
        and connection.token_expires_at
        and _is_expired(connection.token_expires_at)
    ):
        refreshed = await refresh_oauth_access_token(connection)
        if refreshed:
            connection.access_token = refreshed

    if is_invalid(connection.access_token):
        for key in context_token_keys:
            value = str((context or {}).get(key) or "").strip()
            if not is_invalid(value):
                connection.access_token = value
                break

    if is_invalid(connection.access_token):
        for key in env_token_keys:
            value = os.getenv(key, "").strip()
            if not is_invalid(value):
                connection.access_token = value
                break

    return connection
