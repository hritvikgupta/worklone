import httpx
import os
import json
from urllib.parse import urlencode
from typing import Dict, Any
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelListProjectDomainsTool(BaseTool):
    name = "vercel_list_project_domains"
    description = "List all domains for a Vercel project"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="vercel_access_token",
                description="Vercel Access Token",
                env_var="VERCEL_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        token = None
        if context and "vercel_access_token" in context:
            token = context["vercel_access_token"]
        if not token:
            token = os.getenv("VERCEL_ACCESS_TOKEN")
        if self._is_placeholder_token(token or ""):
            return ""
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "Project ID or name",
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of domains to return",
                },
            },
            "required": ["projectId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        project_id = parameters.get("projectId", "").strip()
        if not project_id:
            return ToolResult(success=False, output="", error="projectId is required.")
        
        query_params = {}
        team_id = parameters.get("teamId")
        if team_id:
            query_params["teamId"] = team_id.strip()
        limit = parameters.get("limit")
        if limit is not None:
            query_params["limit"] = str(limit)
        
        url = f"https://api.vercel.com/v9/projects/{project_id}/domains"
        if query_params:
            url += "?" + urlencode(query_params)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    domains = data.get("domains", [])
                    processed_domains = []
                    for d in domains:
                        processed_domains.append({
                            "name": d.get("name"),
                            "apexName": d.get("apexName"),
                            "redirect": d.get("redirect"),
                            "redirectStatusCode": d.get("redirectStatusCode"),
                            "verified": d.get("verified"),
                            "gitBranch": d.get("gitBranch"),
                            "createdAt": d.get("createdAt"),
                            "updatedAt": d.get("updatedAt"),
                        })
                    output_data = {
                        "domains": processed_domains,
                        "count": len(processed_domains),
                        "hasMore": data.get("pagination", {}).get("next") is not None,
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")