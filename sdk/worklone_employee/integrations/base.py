"""
Base classes for SDK integrations.

TokenStore pattern:
  - Developer implements TokenStore (or uses InMemoryTokenStore for dev/testing)
  - One integration instance serves ALL end-users
  - SDK reads/writes tokens through the store keyed by user_id
  - SDK never holds tokens in memory between calls

Two auth patterns:
  OAuthIntegration  — token_store + client_id + client_secret, user_id comes from context
  ApiKeyIntegration — single api_key (no per-user tokens, no store needed)
"""

import inspect
from abc import ABC
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


# ─── TokenStore Protocol ───────────────────────────────────────────────────────

class TokenStore:
    """
    Interface developers implement to plug in their own token storage.

    Example with a dict DB:
        class MyStore(TokenStore):
            async def get(self, user_id, provider):
                return db[user_id][provider]   # {"access_token": ..., "refresh_token": ...}
            async def set(self, user_id, provider, tokens):
                db[user_id][provider] = tokens
            async def delete(self, user_id, provider):
                del db[user_id][provider]
    """

    async def get(self, user_id: str, provider: str) -> Optional[Dict[str, str]]:
        raise NotImplementedError

    async def set(self, user_id: str, provider: str, tokens: Dict[str, str]) -> None:
        raise NotImplementedError

    async def delete(self, user_id: str, provider: str) -> None:
        raise NotImplementedError


class InMemoryTokenStore(TokenStore):
    """
    In-memory store for local dev and testing. Not for production.

    Usage:
        store = InMemoryTokenStore()
        store.seed("user_123", "gmail", {"access_token": "...", "refresh_token": "..."})
        gmail = Gmail(client_id=..., client_secret=..., token_store=store)
    """

    def __init__(self):
        self._data: Dict[str, Dict[str, Dict]] = {}

    def seed(self, user_id: str, provider: str, tokens: Dict[str, str]) -> None:
        self._data.setdefault(user_id, {})[provider] = tokens

    async def get(self, user_id: str, provider: str) -> Optional[Dict[str, str]]:
        return self._data.get(user_id, {}).get(provider)

    async def set(self, user_id: str, provider: str, tokens: Dict[str, str]) -> None:
        self._data.setdefault(user_id, {})[provider] = tokens

    async def delete(self, user_id: str, provider: str) -> None:
        self._data.get(user_id, {}).pop(provider, None)


# ─── Base ──────────────────────────────────────────────────────────────────────

class BaseIntegration(ABC):
    def all(self) -> List[BaseTool]:
        raise NotImplementedError


# ─── OAuth Integration ─────────────────────────────────────────────────────────

class OAuthIntegration(BaseIntegration, ABC):
    """
    Base for OAuth integrations. One instance serves all end-users.

    Usage:
        store = MyPostgresStore()   # your implementation of TokenStore
        gmail = Gmail(client_id=..., client_secret=..., token_store=store)
        emp.add_tools(gmail.all())

        # Tokens are fetched from store using user_id from the agent context
        await emp.run("check inbox", user_id="alice")

    First-time OAuth (one-time per user):
        url = Gmail.get_auth_url(client_id, client_secret, redirect_uri)
        tokens = await Gmail.exchange_code(code, client_id, client_secret, redirect_uri)
        await store.set("alice", "gmail", tokens)
    """

    PROVIDER: str = ""  # e.g. "gmail", "slack" — set in each subclass

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_store: TokenStore,
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self._store = token_store

    async def _get_token(self, user_id: str) -> str:
        tokens = await self._store.get(user_id, self.PROVIDER)
        if not tokens:
            raise ValueError(f"No tokens found for user '{user_id}' provider '{self.PROVIDER}'. Run OAuth flow first.")
        return tokens["access_token"]

    async def _refresh(self, user_id: str) -> str:
        tokens = await self._store.get(user_id, self.PROVIDER)
        if not tokens or not tokens.get("refresh_token"):
            raise ValueError(f"No refresh token for user '{user_id}' provider '{self.PROVIDER}'.")
        new_tokens = await self._do_refresh(tokens["refresh_token"])
        merged = {**tokens, **new_tokens}
        await self._store.set(user_id, self.PROVIDER, merged)
        return merged["access_token"]

    async def _do_refresh(self, refresh_token: str) -> Dict[str, str]:
        """Override in subclasses to call the provider's token endpoint."""
        raise NotImplementedError


# ─── Google OAuth base ─────────────────────────────────────────────────────────

class GoogleOAuthIntegration(OAuthIntegration, ABC):
    _TOKEN_URL = "https://oauth2.googleapis.com/token"
    _AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
    SCOPES: List[str] = []

    @classmethod
    def get_auth_url(cls, client_id: str, client_secret: str, redirect_uri: str, scopes: Optional[List[str]] = None) -> str:
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes or cls.SCOPES),
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{cls._AUTH_BASE}?{urlencode(params)}"

    @classmethod
    async def exchange_code(cls, code: str, client_id: str, client_secret: str, redirect_uri: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(cls._TOKEN_URL, data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
            })
            resp.raise_for_status()
            return resp.json()

    async def _do_refresh(self, refresh_token: str) -> Dict[str, str]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self._TOKEN_URL, data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            })
            resp.raise_for_status()
            data = resp.json()
            result = {"access_token": data["access_token"]}
            if "refresh_token" in data:
                result["refresh_token"] = data["refresh_token"]
            return result


# ─── API Key Integration ────────────────────────────────────────────────────────

class ApiKeyIntegration(BaseIntegration, ABC):
    """
    For API-key integrations (GitHub PAT, Stripe, Notion, etc.).
    No per-user tokens — one key for the whole integration.

    Usage:
        github = Github(api_key="ghp_xxx")
        emp.add_tools(github.all())
    """

    def __init__(self, api_key: str):
        self._api_key = api_key

    def _get_token(self) -> str:
        return self._api_key
