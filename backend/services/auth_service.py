"""
Auth Service - Authentication and OAuth integration management
"""

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from backend.models.auth_db import AuthDB

# OAuth provider configurations
OAUTH_PROVIDERS = {
    "google": {
        "name": "Gmail",
        "icon": "mail",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": "https://www.googleapis.com/auth/gmail.modify",
    },
    "slack": {
        "name": "Slack",
        "icon": "message-circle",
        "auth_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "scopes": "chat:write,channels:read,groups:read,im:read,mpim:read",
    },
    "notion": {
        "name": "Notion",
        "icon": "file-text",
        "auth_url": "https://api.notion.com/v1/oauth/authorize",
        "token_url": "https://api.notion.com/v1/oauth/token",
        "scopes": "",
    },
    "github": {
        "name": "GitHub",
        "icon": "github",
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "scopes": "repo,user,read:org",
    },
    "jira": {
        "name": "Jira",
        "icon": "briefcase",
        "auth_url": "https://auth.atlassian.com/authorize",
        "token_url": "https://auth.atlassian.com/oauth/token",
        "scopes": "read:jira-work write:jira-work offline_access",
    },
}


class AuthService:
    """Service for authentication and OAuth integration management"""

    def __init__(self):
        self.db = AuthDB()

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

    def get_oauth_url(self, provider: str, frontend_url: str, user_id: str) -> Optional[str]:
        """Generate OAuth authorization URL"""
        import urllib.parse
        import secrets

        provider_config = OAUTH_PROVIDERS.get(provider)
        if not provider_config:
            return None

        state = secrets.token_urlsafe(16)
        callback_url = f"{frontend_url}/integrations/callback"

        # Embed user_id in state so we know who is connecting
        full_state = self._encode_state(state, user_id, provider)

        # Get credentials from environment
        client_id = os.getenv(f"PROVIDER_{provider.upper()}_CLIENT_ID", "")
        if not client_id:
            return None

        # Build authorization URL
        params = {
            "client_id": client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "state": full_state,
        }

        if provider == "google":
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

        auth_url = provider_config["auth_url"]
        query_string = urllib.parse.urlencode(params)
        return f"{auth_url}?{query_string}"

    async def handle_oauth_callback(
        self,
        provider: str,
        code: str,
        state: str,
        redirect_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle OAuth callback and store tokens"""
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
        client_id = os.getenv(f"PROVIDER_{provider.upper()}_CLIENT_ID", "")
        client_secret = os.getenv(f"PROVIDER_{provider.upper()}_CLIENT_SECRET", "")

        if not client_id or not client_secret:
            return {"success": False, "error": f"OAuth credentials not configured for {provider}"}

        callback_url = (
            redirect_uri
            or (os.getenv("FRONTEND_URL", "http://localhost:3000") + "/integrations/callback")
        )

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
