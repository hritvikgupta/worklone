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
            context_token_keys=("apiKey",),
            env_token_keys=("EXA_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Research query or topic",
                },
                "model": {
                    "type": "string",
                    "description": "Research model: exa-research-fast, exa-research (default), or exa-research-pro",
                },
            },
            "required": ["query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_access_token(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }

        body: Dict[str, Any] = {
            "instructions": parameters["query"],
        }

        model = parameters.get("model")
        if model:
            body["model"] = model

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.exa.ai/research/v1",
                    headers=headers,
                    json=body,
                )

                if response.status_code not in [200, 201, 202]:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()
                task_id = data.get("researchId")

                if not task_id:
                    return ToolResult(success=True, output=response.text, data=data)

                # Poll for completion
                max_wait = 300
                elapsed = 0
                poll_interval = 5

                while elapsed < max_wait:
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval

                    status_resp = await client.get(
                        f"https://api.exa.ai/research/v1/{task_id}",
                        headers=headers,
                    )

                    if not status_resp.is_success:
                        return ToolResult(success=False, output="", error=status_resp.text)

                    task_data = status_resp.json()
                    status = task_data.get("status")

                    if status == "completed":
                        content = (
                            task_data.get("output", {}).get("content")
                            or task_data.get("output", {}).get("parsed")
                            or "Research completed successfully"
                        )
                        if not isinstance(content, str):
                            content = json.dumps(content, indent=2)

                        result = {
                            "research": [
                                {
                                    "title": "Research Complete",
                                    "url": "",
                                    "summary": content,
                                    "text": content,
                                    "score": 1.0,
                                }
                            ]
                        }
                        return ToolResult(success=True, output=json.dumps(result), data=result)

                    if status in ("failed", "canceled"):
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Research task {status}: {task_data.get('error', 'Unknown error')}",
                        )

                return ToolResult(
                    success=False,
                    output="",
                    error=f"Research task did not complete within {max_wait}s",
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
