from typing import Any, Dict
import httpx
import json
import os
from urllib.parse import urlencode
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelListProjectsTool(BaseTool):
    name = "vercel_list_projects"
    description = "List all projects in a Vercel team or account"
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        token = context.get("VERCEL_ACCESS_TOKEN") if context else None
        if token is None:
            token = os.getenv("VERCEL_ACCESS_TOKEN")
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "search": {
                    "type": "string",
                    "description": "Search projects by name"
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of projects to return"
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request"
                }
            },
            "required": []
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        query_params = {}
        search = parameters.get("search")
        if search:
            query_params["search"] = str(search)
        limit = parameters.get("limit")
        if limit is not None:
            query_params["limit"] = str(limit)
        team_id = parameters.get("teamId")
        if team_id:
            trimmed_team_id = str(team_id).strip()
            if trimmed_team_id:
                query_params["teamId"] = trimmed_team_id
        
        qs = urlencode(query_params)
        url = f"https://api.vercel.com/v10/projects{'?' + qs if qs else ''}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    projects = []
                    for p in data.get("projects", []):
                        projects.append({
                            "id": p["id"],
                            "name": p["name"],
                            "framework": p.get("framework"),
                            "createdAt": p["createdAt"],
                            "updatedAt": p["updatedAt"],
                            "domains": p.get("domains", []),
                        })
                    result = {
                        "projects": projects,
                        "count": len(projects),
                        "hasMore": data.get("pagination", {}).get("next") is not None,
                    }
                    output_str = json.dumps(result)
                    return ToolResult(success=True, output=output_str, data=result)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")