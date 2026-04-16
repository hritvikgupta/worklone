from typing import Any, Dict
import httpx
import json
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ParallelDeepResearchTool(BaseTool):
    name = "parallel_deep_research"
    description = "Conduct comprehensive deep research across the web using Parallel AI. Synthesizes information from multiple sources with citations. Can take up to 45 minutes to complete."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PARALLEL_API_KEY",
                description="Parallel AI API Key",
                env_var="PARALLEL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Research query or question (up to 15,000 characters)",
                },
                "processor": {
                    "type": "string",
                    "description": "Processing tier: pro, ultra, pro-fast, ultra-fast (default: pro)",
                },
                "include_domains": {
                    "type": "string",
                    "description": "Comma-separated list of domains to restrict research to (source policy)",
                },
                "exclude_domains": {
                    "type": "string",
                    "description": "Comma-separated list of domains to exclude from research (source policy)",
                },
            },
            "required": ["input"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("PARALLEL_API_KEY") if context else None
        api_key = api_key or os.environ.get("PARALLEL_API_KEY")
        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Parallel AI API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }

        body: dict = {
            "input": parameters["input"],
            "processor": parameters.get("processor", "pro"),
            "task_spec": {
                "output_schema": "auto",
            },
        }

        source_policy: dict[str, list[str]] = {}
        include_domains = parameters.get("include_domains")
        if include_domains:
            source_policy["include_domains"] = [d.strip() for d in include_domains.split(",") if d.strip()]
        exclude_domains = parameters.get("exclude_domains")
        if exclude_domains:
            source_policy["exclude_domains"] = [d.strip() for d in exclude_domains.split(",") if d.strip()]
        if source_policy:
            body["source_policy"] = source_policy

        url = "https://api.parallel.ai/v1/tasks/runs"

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30.0, read=3600.0)) as client:
                resp = await client.post(url, headers=headers, json=body)

                if resp.status_code not in [200, 201]:
                    return ToolResult(success=False, output="", error=resp.text)

                data = resp.json()
                run_id = data.get("run_id")
                if not run_id:
                    return ToolResult(success=False, output="", error="No run_id returned from task creation")

                result_url = f"https://api.parallel.ai/v1/tasks/runs/{str(run_id).strip()}/result"

                resp2 = await client.get(result_url, headers=headers)

                if resp2.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=f"Failed to get task result: {resp2.status_code} - {resp2.text}")

                task_result = resp2.json()

                output = task_result.get("output", {})
                status = task_result.get("status", "completed")
                output_dict = {
                    "status": status,
                    "run_id": run_id,
                    "message": "Research completed successfully",
                    "content": output.get("content", {}),
                    "basis": output.get("basis", []),
                }

                return ToolResult(
                    success=True,
                    output=json.dumps(output_dict),
                    data=output_dict,
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")