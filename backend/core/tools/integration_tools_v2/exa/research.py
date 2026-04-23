from typing import Any, Dict
import httpx
import asyncio
import json
import time
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ExaResearchTool(BaseTool):
    name = "exa_research"
    description = "Perform comprehensive research using AI to generate detailed reports with citations"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="EXA_API_KEY",
                description="Exa AI API Key",
                env_var="EXA_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "exa",
            context=context,
            context_token_keys=("apiKey",},
            env_token_keys=("EXA_API_KEY",},
            placeholder_predicate=self