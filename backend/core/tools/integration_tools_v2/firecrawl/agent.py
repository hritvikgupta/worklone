from typing import Any, Dict
import httpx
import asyncio
import time
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class FirecrawlAgentTool(BaseTool):
    name = "firecrawl_agent"
    description = "Autonomous web data extraction agent. Searches and gathers information based on natural language prompts without requiring specific URLs."
    category = "integration"
    POLL_INTERVAL = 5.0
    MAX_POLL_TIME = 300.0

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="firecrawl_api_key",
                description="Firecrawl API key",
                env_var="FIRECRAWL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _get_api_key(self, context: dict | None) -> str:
        if context and "firecrawl_api_key" in context:
            api_key = context["firecrawl_api_key"]
            if not self._is_placeholder_token(api_key):
                return api_key
        return ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Natural language description of the data to extract (max 10,000 characters)",
                },
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional array of URLs to focus the agent on (e.g., [\"https://example.com\", \"https://docs.example.com\"])",
                },
                "schema": {
                    "type": "object",
                    "description": "JSON Schema defining the structure of data to extract",
                },
                "maxCredits": {
                    "type": "number",
                    "description": "Maximum credits to spend on this agent task",
                },
                "strictConstrainToURLs": {
                    "type": "boolean",
                    "description": "If true, agent will only visit URLs provided in the urls array",
                },
            },
            "required": ["prompt"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._get_api_key(context)
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Firecrawl API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        body: Dict[str, Any] = {
            "prompt": parameters["prompt"],
        }
        if "urls" in parameters:
            body["urls"] = parameters["urls"]
        if "schema" in parameters:
            body["schema"] = parameters["schema"]
        if "maxCredits" in parameters:
            body["maxCredits"] = parameters["maxCredits"]
        if "strictConstrainToURLs" in parameters:
            body["strictConstrainToURLs"] = parameters["strictConstrainToURLs"]

        url = "https://api.firecrawl.dev/v2/agent"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201]:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()
                job_id = data.get("id")
                if not job_id:
                    return ToolResult(success=False, output="", error="No job ID returned from API.")

                start_time = time.monotonic()
                while True:
                    status_url = f"https://api.firecrawl.dev/v2/agent/{job_id}"
                    status_response = await client.get(status_url, headers=headers)

                    if status_response.status_code not in [200, 201]:
                        return ToolResult(
                            success=False, output="", error=f"Failed to get agent status: {status_response.text}"
                        )

                    agent_data = status_response.json()
                    status = agent_data.get("status")

                    if status == "completed":
                        result_output = {
                            "jobId": job_id,
                            "success": True,
                            "status": "completed",
                            "data": agent_data.get("data", {}),
                            "creditsUsed": agent_data.get("creditsUsed"),
                            "expiresAt": agent_data.get("expiresAt"),
                            "sources": agent_data.get("sources"),
                        }
                        return ToolResult(
                            success=True, output=json.dumps(result_output), data=result_output
                        )

                    if status == "failed":
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Agent job failed: {agent_data.get('error', 'Unknown error')}",
                        )

                    if time.monotonic() - start_time > self.MAX_POLL_TIME:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Agent job did not complete within the maximum polling time ({self.MAX_POLL_TIME / 60:.1f} minutes)",
                        )

                    await asyncio.sleep(self.POLL_INTERVAL)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")