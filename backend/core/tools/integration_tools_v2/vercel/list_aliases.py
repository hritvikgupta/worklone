from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelListAliasesTool(BaseTool):
    name = "vercel_list_aliases"
    description = "List aliases for a Vercel project or team"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="VERCEL_ACCESS_TOKEN",
                description="Vercel Access Token",
                env_var="VERCEL_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "Filter aliases by project ID",
                },
                "domain": {
                    "type": "string",
                    "description": "Filter aliases by domain",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of aliases to return",
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("VERCEL_ACCESS_TOKEN") if context else None

        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        query_params = {}
        for field in ["projectId", "domain", "teamId"]:
            val = parameters.get(field)
            if val:
                query_params[field] = str(val).strip()
        lim = parameters.get("limit")
        if lim:
            query_params["limit"] = str(lim)

        url = "https://api.vercel.com/v4/aliases"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200, 201, 204]:
                    raw_data = response.json()
                    aliases_raw = raw_data.get("aliases", [])
                    transformed_aliases = []
                    for a in aliases_raw:
                        transformed_aliases.append({
                            "uid": a.get("uid"),
                            "alias": a.get("alias"),
                            "deploymentId": a.get("deploymentId"),
                            "projectId": a.get("projectId"),
                            "createdAt": a.get("createdAt"),
                            "updatedAt": a.get("updatedAt"),
                        })
                    transformed = {
                        "aliases": transformed_aliases,
                        "count": len(transformed_aliases),
                        "hasMore": raw_data.get("pagination", {}).get("next") is not None,
                    }
                    return ToolResult(success=True, output=response.text, data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")