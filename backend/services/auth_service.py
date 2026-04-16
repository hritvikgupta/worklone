"""
Auth Service - Authentication and OAuth integration management
"""

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from backend.store.auth_store import AuthDB
from backend.lib.oauth.providers import OAUTH_PROVIDERS


class AuthService:
    """Service for authentication and OAuth integration management"""

    def __init__(self):
        self.db = AuthDB()

    @staticmethod
    def _is_placeholder_secret(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return (
            not normalized
            or normalized.startswith("your-")
            or normalized in {"your-google-client-id", "your-google-client-secret", "changeme", "replace-me"}
        )

    # ─── Authentication ─────────────────────────────────────────────

    def register(self, email: str, password: str, name: str) -> Dict[str, Any]:
        """Register a new user"""
        user = self.db.create_user(email, password, name)
        if not user:
            return {"success": False, "error": "Email already registered"}

        token = self.db.create_session(user["id"])
        return {
            "success": True,
            "token": token,
            "user": user
        }

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login user"""
        user = self.db.authenticate_user(email, password)
        if not user:
            return {"success": False, "error": "Invalid email or password"}

        token = self.db.create_session(user["id"])
        return {
            "success": True,
            "token": token,
            "user": user
        }

    def get_current_user(self, token: str) -> Optional[Dict[str, Any]]:
        """Get current user from session token"""
        return self.db.validate_session(token)

    def logout(self, token: str):
        """Logout user"""
        self.db.delete_session(token)

    # ─── OAuth Integration ──────────────────────────────────────────

    @staticmethod
    def _encode_state(state_nonce: str, user_id: str, provider: str) -> str:
        """Encode OAuth state with provider context."""
        return f"{state_nonce}::{user_id}::{provider}"

    @staticmethod
    def _decode_state(state: str, provider_hint: str = "") -> Dict[str, str]:
        """
        Decode OAuth state.
        Supports:
        - legacy: nonce::user_id
        - current: nonce::user_id::provider
        """
        parts = state.split("::")
        nonce = parts[0] if parts else ""
        user_id = parts[1] if len(parts) >= 2 else ""
        provider = provider_hint
        if len(parts) >= 3 and parts[2]:
            provider = parts[2]
        return {"nonce": nonce, "user_id": user_id, "provider": provider}

    @staticmethod
    def _normalize_token_expiry(raw_expires_in: Any) -> Optional[str]:
        """Convert OAuth expires_in seconds into absolute UTC timestamp."""
        if raw_expires_in is None:
            return None
        try:
            seconds = int(raw_expires_in)
        except (TypeError, ValueError):
            return str(raw_expires_in)
        return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()

    @staticmethod
    def _get_provider_frontend_url(provider: str, frontend_url: Optional[str] = None) -> str:
        env_override = os.getenv(f"PROVIDER_{provider.upper()}_FRONTEND_URL", "").strip()
        if env_override:
            return env_override.rstrip("/")
        if frontend_url:
            return frontend_url.rstrip("/")
        return os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")

    @staticmethod
    def _get_provider_env_value(provider: str, suffix: str) -> tuple[str, str]:
        """
        Resolve provider-specific env vars with compatibility fallbacks.
        Primary: PROVIDER_<NAME>_<SUFFIX>
        Fallback: <NAME>_<SUFFIX>
        Google Drive and Calendar share credentials with the base Google provider.
        """
        provider_upper = provider.upper()
        candidates = [
            f"PROVIDER_{provider_upper}_{suffix}",
            f"{provider_upper}_{suffix}",
        ]
        # Google Drive and Calendar use the same OAuth app as Gmail
        if provider_upper in ("GOOGLE_DRIVE", "GOOGLE_CALENDAR"):
            candidates += [f"PROVIDER_GOOGLE_{suffix}", f"GOOGLE_{suffix}"]
        for key in candidates:
            value = os.getenv(key, "").strip()
            if value:
                return value, key
        return "", candidates[0]

    def get_oauth_url(self, provider: str, frontend_url: str, user_id: str) -> Dict[str, Any]:
        """Generate OAuth authorization URL with explicit error context."""
        import urllib.parse
        import secrets

        provider_config = OAUTH_PROVIDERS.get(provider)
        if not provider_config:
            return {"success": False, "error": f"Unknown provider: {provider}"}

        state = secrets.token_urlsafe(16)
        callback_url = f"{self._get_provider_frontend_url(provider, frontend_url)}/integrations/callback"

        # Embed user_id in state so we know who is connecting
        full_state = self._encode_state(state, user_id, provider)

        # Get credentials from environment
        client_id, client_id_key = self._get_provider_env_value(provider, "CLIENT_ID")
        if not client_id:
            return {
                "success": False,
                "error": f"Missing OAuth client id for {provider} (expected env: {client_id_key})",
            }
        if self._is_placeholder_secret(client_id):
            return {
                "success": False,
                "error": f"OAuth client id for {provider} looks like a placeholder ({client_id_key})",
            }

        # Build authorization URL
        params = {
            "client_id": client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "state": full_state,
        }

        if provider in ("google", "google_drive", "google_calendar"):
            params["scope"] = provider_config["scopes"]
            params["access_type"] = "offline"
            params["prompt"] = "consent"
        elif provider == "slack":
            params["scope"] = provider_config["scopes"]
            params["user_scope"] = ""
        elif provider == "github":
            params["scope"] = provider_config["scopes"]
        elif provider == "jira":
            params["audience"] = "api.atlassian.com"
            params["scope"] = provider_config["scopes"]
            params["prompt"] = "consent"
        elif provider == "notion":
            # Notion requires owner to be explicit in OAuth authorize URL.
            params["owner"] = "user"

        auth_url = provider_config["auth_url"]
        query_string = urllib.parse.urlencode(params)
        return {"success": True, "auth_url": f"{auth_url}?{query_string}"}

    async def handle_oauth_callback(
        self,
        provider: str,
        code: str,
        state: str,
        redirect_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle OAuth callback and store tokens"""
        import base64
        import httpx

        # Extract user_id/provider from state.
        state_data = self._decode_state(state, provider)
        user_id = state_data.get("user_id", "")
        provider = state_data.get("provider", provider)

        if not user_id:
            return {"success": False, "error": "Invalid OAuth state: missing user id"}
        if not self.db.get_user(user_id):
            return {"success": False, "error": "Invalid OAuth state: user not found"}
        
        provider_config = OAUTH_PROVIDERS.get(provider)
        if not provider_config:
            return {"success": False, "error": "Unknown provider"}

        # Get client credentials from environment
        client_id, client_id_key = self._get_provider_env_value(provider, "CLIENT_ID")
        client_secret, client_secret_key = self._get_provider_env_value(provider, "CLIENT_SECRET")

        if self._is_placeholder_secret(client_id):
            return {
                "success": False,
                "error": f"OAuth client id not configured for {provider} (env: {client_id_key})",
            }
        if self._is_placeholder_secret(client_secret):
            return {
                "success": False,
                "error": f"OAuth client secret not configured for {provider} (env: {client_secret_key})",
            }

        callback_url = redirect_uri or f"{self._get_provider_frontend_url(provider)}/integrations/callback"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Exchange code for tokens
                token_data = {
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": callback_url,
                    "client_id": client_id,
                    "client_secret": client_secret,
                }

                token_headers = {}
                token_request_kwargs: Dict[str, Any] = {}
                if provider == "github":
                    token_headers["Accept"] = "application/json"
                    token_request_kwargs["data"] = token_data
                elif provider == "jira":
                    token_headers["Accept"] = "application/json"
                    token_headers["Content-Type"] = "application/json"
                    token_request_kwargs["json"] = token_data
                elif provider == "notion":
                    # Notion OAuth token exchange requires HTTP Basic auth with client_id:client_secret
                    # and a JSON body (not form-encoded client credentials).
                    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
                    token_headers["Accept"] = "application/json"
                    token_headers["Content-Type"] = "application/json"
                    token_headers["Authorization"] = f"Basic {basic}"
                    token_request_kwargs["json"] = {
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": callback_url,
                    }
                else:
                    token_request_kwargs["data"] = token_data

                response = await client.post(
                    provider_config["token_url"],
                    headers=token_headers,
                    **token_request_kwargs,
                )

                if response.status_code != 200:
                    return {"success": False, "error": f"Token exchange failed: {response.text}"}

                tokens = response.json()
                access_token = str(tokens.get("access_token") or "").strip()
                if not access_token:
                    provider_error = (
                        tokens.get("error_description")
                        or tokens.get("error")
                        or tokens.get("message")
                        or "Token exchange did not return access_token"
                    )
                    return {"success": False, "error": f"Token exchange failed: {provider_error}"}

                scopes = tokens.get("scope", "")
                if isinstance(scopes, list):
                    scopes = ",".join(scopes)

                provider_user_id = None
                provider_email = None
                metadata = None

                if provider == "jira":
                    # Jira OAuth (Atlassian 3LO) requires cloud-id routing for API calls.
                    resources_response = await client.get(
                        "https://api.atlassian.com/oauth/token/accessible-resources",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Accept": "application/json",
                        },
                    )
                    if resources_response.status_code != 200:
                        return {
                            "success": False,
                            "error": f"Jira token is valid but failed to list accessible resources: {resources_response.text}",
                        }

                    resources = resources_response.json()
                    if not isinstance(resources, list) or not resources:
                        return {
                            "success": False,
                            "error": "Jira token has no accessible cloud resources. Check site access and app scopes.",
                        }

                    resource = resources[0]
                    metadata = json.dumps(
                        {
                            "cloud_id": resource.get("id"),
                            "site_url": resource.get("url"),
                            "site_name": resource.get("name"),
                            "scopes": resource.get("scopes", []),
                        }
                    )

                    me_response = await client.get(
                        "https://api.atlassian.com/me",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Accept": "application/json",
                        },
                    )
                    if me_response.status_code == 200:
                        me = me_response.json()
                        provider_user_id = me.get("account_id")
                        provider_email = me.get("email")

                # Store integration
                self.db.save_integration(
                    user_id=user_id,
                    provider=provider,
                    access_token=access_token,
                    refresh_token=tokens.get("refresh_token"),
                    token_expires_at=self._normalize_token_expiry(tokens.get("expires_in")),
                    scopes=scopes,
                    provider_user_id=provider_user_id,
                    provider_email=provider_email,
                    metadata=metadata,
                )

                saved_integration = self.db.get_integration(user_id, provider)
                if not saved_integration or str(saved_integration.get("access_token") or "").strip() != access_token:
                    return {
                        "success": False,
                        "error": f"Failed to persist {provider_config['name']} integration for this user",
                    }

                return {
                    "success": True,
                    "provider": provider,
                    "message": f"{provider_config['name']} connected successfully"
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_integration_status(self, user_id: str) -> Dict[str, Any]:
        """Get status of all integrations for a user"""
        integrations = self.db.get_user_integrations(user_id)
        provider_list = []

        for key, config in OAUTH_PROVIDERS.items():
            integration = next((i for i in integrations if i["provider"] == key), None)
            has_token = bool(
                integration
                and str(integration.get("access_token") or "").strip()
            )
            provider_list.append({
                "id": key,
                "name": config["name"],
                "icon": config["icon"],
                "connected": has_token,
                "connected_at": integration.get("connected_at") if has_token else None,
                "provider_email": integration.get("provider_email") if has_token else None,
            })

        return {"integrations": provider_list}

    def disconnect_integration(self, user_id: str, provider: str) -> Dict[str, Any]:
        """Disconnect an integration"""
        provider_config = OAUTH_PROVIDERS.get(provider)
        if not provider_config:
            return {"success": False, "error": "Unknown provider"}

        self.db.disconnect_integration(user_id, provider)
        return {
            "success": True,
            "message": f"{provider_config['name']} disconnected"
        }
