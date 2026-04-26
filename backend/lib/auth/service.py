"""
Auth Service - Authentication and OAuth integration management
"""

import os
import json
import time
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from backend.core.config import get_settings
from backend.db.stores.auth_store import AuthDB
from backend.db.stores.workflow_store import WorkflowStore
from backend.lib.oauth.providers import OAUTH_PROVIDERS, API_KEY_PROVIDERS

HIDDEN_AVAILABLE_PROVIDERS = {
    "salesforce",
    "docusign",
    "confluence",
    "reddit",
    "x",
    "zoom",
    "pipedrive",
    "webflow",
    "shopify",
    "wordpress",
    "microsoft_dataverse",
    "microsoft_excel",
    "microsoft_planner",
    "microsoft_teams",
    "outlook",
}
_PKCE_TTL_SECONDS = 10 * 60


class AuthService:
    """Service for authentication and OAuth integration management"""

    def __init__(self):
        self.db = AuthDB()
        self.workflow_store = WorkflowStore()
    
    @staticmethod
    def _pkce_key(provider: str, state: str) -> str:
        state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
        return f"oauth_pkce:{provider}:{state_hash}"

    def _store_pkce_verifier(self, user_id: str, provider: str, state: str, code_verifier: str) -> None:
        payload = {
            "code_verifier": code_verifier,
            "expires_at": time.time() + _PKCE_TTL_SECONDS,
        }
        self.workflow_store.set_credential(
            user_id,
            self._pkce_key(provider, state),
            json.dumps(payload),
            f"PKCE verifier for {provider}",
        )

    def _pop_pkce_verifier(self, user_id: str, provider: str, state: str) -> Optional[str]:
        key = self._pkce_key(provider, state)
        raw = self.workflow_store.get_credential(user_id, key)
        self.workflow_store.delete_credential(user_id, key)
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except Exception:  # noqa: BLE001
            return None
        expires_at = float(payload.get("expires_at", 0))
        if expires_at <= time.time():
            return None
        code_verifier = payload.get("code_verifier")
        return code_verifier if isinstance(code_verifier, str) and code_verifier else None

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
    def _get_provider_oauth_url(provider: str, provider_config: Dict[str, Any], key: str) -> str:
        """Allow per-provider OAuth URL overrides via env."""
        suffix = "AUTH_URL" if key == "auth_url" else "TOKEN_URL"
        env_key = f"PROVIDER_{provider.upper()}_{suffix}"
        override = os.getenv(env_key, "").strip()
        return override or provider_config[key]

    @staticmethod
    def _is_google_family_provider(provider: str) -> bool:
        normalized = provider.strip().lower().replace("-", "_")
        return normalized in {"google", "gmail", "google_email"} or normalized.startswith("google_")

    @staticmethod
    def _get_provider_env_value(provider: str, suffix: str) -> tuple[str, str]:
        """
        Resolve provider-specific env vars with compatibility fallbacks.
        Primary: PROVIDER_<NAME>_<SUFFIX>
        Fallback: <NAME>_<SUFFIX>
        Google family integrations share credentials with the base Google provider.
        """
        provider_upper = provider.upper()
        candidates = [
            f"PROVIDER_{provider_upper}_{suffix}",
            f"{provider_upper}_{suffix}",
        ]
        # All Google-family tools use the same OAuth app.
        if AuthService._is_google_family_provider(provider):
            candidates += [f"PROVIDER_GOOGLE_{suffix}", f"GOOGLE_{suffix}"]
        for key in candidates:
            value = os.getenv(key, "").strip()
            if value:
                return value, key
        return "", candidates[0]

    @staticmethod
    def _provider_credential_namespace(provider: str) -> str:
        normalized = provider.strip().lower().replace("-", "_")
        if normalized in {"google", "gmail", "google_email"} or normalized.startswith("google_"):
            return "google"
        return normalized

    @staticmethod
    def _provider_credential_names(provider: str) -> tuple[str, ...]:
        normalized = provider.strip().lower().replace("-", "_")
        namespace = AuthService._provider_credential_namespace(provider)
        if namespace == normalized:
            return (normalized,)
        return (normalized, namespace)

    @classmethod
    def _oauth_cred_key(cls, provider: str, suffix: str) -> str:
        return f"oauth_{suffix.lower()}_{cls._provider_credential_namespace(provider)}"

    def _get_provider_user_value(self, user_id: str, provider: str, suffix: str) -> tuple[str, str]:
        suffix_key = suffix.lower()
        for namespace in self._provider_credential_names(provider):
            cred_key = f"oauth_{suffix_key}_{namespace}"
            value = (self.workflow_store.get_credential(user_id, cred_key) or "").strip()
            if value:
                return value, cred_key
        cred_key = self._oauth_cred_key(provider, suffix)
        return "", cred_key

    def _resolve_provider_client_value(self, user_id: str, provider: str, suffix: str) -> tuple[str, str]:
        mode = get_settings().deployment_mode
        if mode == "self_hosted":
            return self._get_provider_user_value(user_id, provider, suffix)
        return self._get_provider_env_value(provider, suffix)

    def set_oauth_provider_credentials(
        self,
        *,
        user_id: str,
        provider: str,
        client_id: str,
        client_secret: str,
    ) -> Dict[str, Any]:
        if provider not in OAUTH_PROVIDERS:
            return {"success": False, "error": f"Unknown provider: {provider}"}
        if self._is_placeholder_secret(client_id) or self._is_placeholder_secret(client_secret):
            return {"success": False, "error": "Client ID and secret must be real values, not placeholders"}

        client_id_key = self._oauth_cred_key(provider, "client_id")
        client_secret_key = self._oauth_cred_key(provider, "client_secret")
        self.workflow_store.set_credential(user_id, client_id_key, client_id.strip(), f"OAuth client ID for {provider}")
        self.workflow_store.set_credential(
            user_id,
            client_secret_key,
            client_secret.strip(),
            f"OAuth client secret for {provider}",
        )
        return {"success": True}

    def get_oauth_provider_credentials_status(self, user_id: str, provider: str) -> Dict[str, Any]:
        if provider not in OAUTH_PROVIDERS:
            return {"success": False, "error": f"Unknown provider: {provider}"}
        mode = get_settings().deployment_mode
        if mode == "self_hosted":
            client_id, _ = self._get_provider_user_value(user_id, provider, "client_id")
            client_secret, _ = self._get_provider_user_value(user_id, provider, "client_secret")
            return {"success": True, "has_credentials": bool(client_id and client_secret)}
        client_id, _ = self._get_provider_env_value(provider, "CLIENT_ID")
        client_secret, _ = self._get_provider_env_value(provider, "CLIENT_SECRET")
        return {"success": True, "has_credentials": bool(client_id and client_secret)}

    def get_oauth_url(self, provider: str, frontend_url: str, user_id: str) -> Dict[str, Any]:
        """Generate OAuth authorization URL with explicit error context."""
        import base64
        import hashlib
        import urllib.parse
        import secrets

        provider_config = OAUTH_PROVIDERS.get(provider)
        if not provider_config:
            return {"success": False, "error": f"Unknown provider: {provider}"}

        state = secrets.token_urlsafe(16)
        callback_url = f"{self._get_provider_frontend_url(provider, frontend_url)}/integrations/callback"

        # Embed user_id in state so we know who is connecting
        full_state = self._encode_state(state, user_id, provider)

        # Resolve credentials by deployment mode.
        client_id, client_id_key = self._resolve_provider_client_value(user_id, provider, "CLIENT_ID")
        if not client_id:
            mode = get_settings().deployment_mode
            source = "saved key" if mode == "self_hosted" else "env"
            return {
                "success": False,
                "error": f"Missing OAuth client id for {provider} (expected {source}: {client_id_key})",
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

        if self._is_google_family_provider(provider):
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
        elif provider_config.get("scopes"):
            # Most OAuth providers (including Airtable) require scope on authorize.
            params["scope"] = provider_config["scopes"]

        if provider == "airtable":
            # Airtable OAuth expects PKCE in the authorization request.
            code_verifier = secrets.token_urlsafe(64)
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode("utf-8")).digest()
            ).decode("ascii").rstrip("=")
            self._store_pkce_verifier(user_id, provider, full_state, code_verifier)
            params["code_challenge_method"] = "S256"
            params["code_challenge"] = code_challenge

        auth_url = self._get_provider_oauth_url(provider, provider_config, "auth_url")
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

        # Resolve client credentials by deployment mode.
        client_id, client_id_key = self._resolve_provider_client_value(user_id, provider, "CLIENT_ID")
        client_secret, client_secret_key = self._resolve_provider_client_value(user_id, provider, "CLIENT_SECRET")
        mode = get_settings().deployment_mode

        if self._is_placeholder_secret(client_id):
            source = "saved key" if mode == "self_hosted" else "env"
            return {
                "success": False,
                "error": f"OAuth client id not configured for {provider} ({source}: {client_id_key})",
            }
        if self._is_placeholder_secret(client_secret):
            source = "saved key" if mode == "self_hosted" else "env"
            return {
                "success": False,
                "error": f"OAuth client secret not configured for {provider} ({source}: {client_secret_key})",
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
                if provider == "airtable":
                    code_verifier = self._pop_pkce_verifier(user_id, provider, state)
                    if not code_verifier:
                        return {
                            "success": False,
                            "error": "Token exchange failed: missing or expired PKCE verifier; retry Airtable connect.",
                        }
                    token_data["code_verifier"] = code_verifier

                token_headers = {}
                token_request_kwargs: Dict[str, Any] = {}
                if provider == "github":
                    token_headers["Accept"] = "application/json"
                    token_request_kwargs["data"] = token_data
                elif provider == "jira":
                    token_headers["Accept"] = "application/json"
                    token_headers["Content-Type"] = "application/json"
                    token_request_kwargs["json"] = token_data
                elif provider == "airtable":
                    # Airtable token exchange can require client auth via HTTP Basic.
                    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
                    token_headers["Accept"] = "application/json"
                    token_headers["Authorization"] = f"Basic {basic}"
                    token_request_kwargs["data"] = {
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": callback_url,
                        "client_id": client_id,
                        "code_verifier": token_data.get("code_verifier", ""),
                    }
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
                    self._get_provider_oauth_url(provider, provider_config, "token_url"),
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
        deployment_mode = get_settings().deployment_mode
        integrations = self.db.get_user_integrations(user_id)
        provider_list = []

        for key, config in OAUTH_PROVIDERS.items():
            if key in HIDDEN_AVAILABLE_PROVIDERS:
                continue
            integration = next((i for i in integrations if i["provider"] == key), None)
            has_token = bool(
                integration
                and str(integration.get("access_token") or "").strip()
            )
            cred_status = self.get_oauth_provider_credentials_status(user_id, key)
            has_client_credentials = bool(cred_status.get("has_credentials"))
            provider_list.append({
                "id": key,
                "name": config["name"],
                "icon": config.get("icon", ""),
                "connected": has_token,
                "connected_at": integration.get("connected_at") if has_token else None,
                "provider_email": integration.get("provider_email") if has_token else None,
                "client_credentials_required": deployment_mode == "self_hosted",
                "has_client_credentials": has_client_credentials,
                "auth_type": "oauth",
            })

        # Include API key providers
        for key, config in API_KEY_PROVIDERS.items():
            first_field_key = config["fields"][0]["key"] if config["fields"] else ""
            cred_value = self.workflow_store.get_credential(user_id, f"integration_apikey_{key}_{first_field_key}") if first_field_key else None
            connected = bool(cred_value and cred_value.strip())
            provider_list.append({
                "id": key,
                "name": config["name"],
                "icon": config.get("icon", ""),
                "connected": connected,
                "connected_at": None,
                "provider_email": None,
                "client_credentials_required": False,
                "has_client_credentials": False,
                "auth_type": "api_key",
                "fields": config["fields"],
            })

        return {"integrations": provider_list, "deployment_mode": deployment_mode}

    def disconnect_integration(self, user_id: str, provider: str) -> Dict[str, Any]:
        """Disconnect an integration (OAuth or API key)"""
        if provider in API_KEY_PROVIDERS:
            config = API_KEY_PROVIDERS[provider]
            for field in config.get("fields", []):
                try:
                    self.workflow_store.delete_credential(user_id, f"integration_apikey_{provider}_{field['key']}")
                except Exception:
                    pass
            return {"success": True, "message": f"{config['name']} disconnected"}

        provider_config = OAUTH_PROVIDERS.get(provider)
        if not provider_config:
            return {"success": False, "error": "Unknown provider"}

        self.db.disconnect_integration(user_id, provider)
        return {
            "success": True,
            "message": f"{provider_config['name']} disconnected"
        }

    def save_provider_api_keys(self, user_id: str, provider: str, fields: Dict[str, str]) -> Dict[str, Any]:
        """Save API key fields for an API-key-based provider."""
        if provider not in API_KEY_PROVIDERS:
            return {"success": False, "error": "Unknown API key provider"}
        config = API_KEY_PROVIDERS[provider]
        for field in config.get("fields", []):
            value = fields.get(field["key"], "").strip()
            if field.get("required") and not value:
                return {"success": False, "error": f"Field '{field['label']}' is required"}
            if value:
                self.workflow_store.set_credential(user_id, f"integration_apikey_{provider}_{field['key']}", value, field["label"])
        return {"success": True}

    def get_provider_api_keys(self, user_id: str, provider: str) -> Dict[str, str]:
        """Return saved API key fields for a provider (for tool context injection)."""
        if provider not in API_KEY_PROVIDERS:
            return {}
        config = API_KEY_PROVIDERS[provider]
        result = {}
        for field in config.get("fields", []):
            val = self.workflow_store.get_credential(user_id, f"integration_apikey_{provider}_{field['key']}")
            if val:
                result[field["key"]] = val
        return result
