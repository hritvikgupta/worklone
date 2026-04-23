import httpx
import base64
import os
import json
from datetime import datetime
from typing import Any, Dict
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyListApplicationsTool(BaseTool):
    name = "ashby_list_applications"
    description = "Lists all applications in an Ashby organization with pagination and optional filters for status, job, candidate, and creation date."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ASHBY_API_KEY",
                description="Ashby API Key",
                env_var="ASHBY_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _resolve_api_key(self, context: dict | None) -> str | None:
        api_key = context.get("ASHBY_API_KEY") if context else None
        if api_key is None:
            api_key = os.getenv("ASHBY_API_KEY")
        if self._is_placeholder_token(api_key or ""):
            return None
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "cursor": {
                    "type": "string",
                    "description": "Opaque pagination cursor from a previous response nextCursor value",
                },
                "perPage": {
                    "type": "number",
                    "description": "Number of results per page (default 100)",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by application status: Active, Hired, Archived, or Lead",
                },
                "jobId": {
                    "type": "string",
                    "description": "Filter applications by a specific job UUID",
                },
                "candidateId": {
                    "type": "string",
                    "description": "Filter applications by a specific candidate UUID",
                },
                "createdAfter": {
                    "type": "string",
                    "description": "Filter to applications created after this ISO 8601 timestamp (e.g. 2024-01-01T00:00:00Z)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)

        if api_key is None:
            return ToolResult(success=False, output="", error="Ashby API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
        }

        body: Dict[str, Any] = {}
        if cursor := parameters.get("cursor"):
            body["cursor"] = cursor
        if per_page := parameters.get("perPage"):
            body["limit"] = per_page
        if status := parameters.get("status"):
            body["status"] = [status]
        if job_id := parameters.get("jobId"):
            body["jobId"] = job_id
        if candidate_id := parameters.get("candidateId"):
            body["candidateId"] = candidate_id
        if created_after := parameters.get("createdAfter"):
            try:
                created_after_str = str(created_after)
                if created_after_str.endswith("Z"):
                    dt_str = created_after_str[:-1] + "+00:00"
                else:
                    dt_str = created_after_str
                dt = datetime.fromisoformat(dt_str)
                body["createdAfter"] = int(dt.timestamp() * 1000)
            except ValueError:
                return ToolResult(
                    success=False,
                    output="",
                    error="Invalid createdAfter format. Must be ISO 8601 timestamp.",
                )

        url = "https://api.ashbyhq.com/application.list"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if not data.get("success", False):
                    error_msg = data.get("errorInfo", {}).get("message", "Failed to list applications")
                    return ToolResult(success=False, output="", error=error_msg)

                applications = []
                for a in data.get("results", []):
                    app: Dict[str, Any] = {
                        "id": a.get("id"),
                        "status": a.get("status"),
                        "candidate": {
                            "id": a.get("candidate", {}).get("id"),
                            "name": a.get("candidate", {}).get("name"),
                        },
                        "job": {
                            "id": a.get("job", {}).get("id"),
                            "title": a.get("job", {}).get("title"),
                        },
                        "createdAt": a.get("createdAt"),
                        "updatedAt": a.get("updatedAt"),
                    }
                    current_stage = a.get("currentInterviewStage")
                    if current_stage:
                        app["currentInterviewStage"] = {
                            "id": current_stage.get("id"),
                            "title": current_stage.get("title"),
                            "type": current_stage.get("type"),
                        }
                    source = a.get("source")
                    if source:
                        app["source"] = {
                            "id": source.get("id"),
                            "title": source.get("title"),
                        }
                    applications.append(app)

                transformed = {
                    "applications": applications,
                    "moreDataAvailable": data.get("moreDataAvailable", False),
                    "nextCursor": data.get("nextCursor"),
                }

                output_str = json.dumps(transformed, default=str)

                return ToolResult(success=True, output=output_str, data=transformed)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")