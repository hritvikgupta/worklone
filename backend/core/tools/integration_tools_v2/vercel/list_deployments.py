from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class VercelListDeploymentsTool(BaseTool):
    name = "vercel_list_deployments"
    description = "List deployments for a Vercel project or team"
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
        connection = await resolve_oauth_connection(
            "vercel",
            context=context,
            context_token_keys=("apiKey",),
            env_token_keys=("VERCEL_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "Filter deployments by project ID or name",
                },
                "target": {
                    "type": "string",
                    "description": "Filter by environment: production or staging",
                },
                "state": {
                    "type": "string",
                    "description": "Filter by state: BUILDING, ERROR, INITIALIZING, QUEUED, READY, CANCELED",
                },
                "app": {
                    "type": "string",
                    "description": "Filter by deployment name",
                },
                "since": {
                    "type": "number",
                    "description": "Get deployments created after this JavaScript timestamp",
                },
                "until": {
                    "type": "number",
                    "description": "Get deployments created before this JavaScript timestamp",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of deployments to return per request",
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        query_params: Dict[str, str] = {}
        project_id = parameters.get("projectId")
        if project_id:
            query_params["projectId"] = str(project_id).strip()
        target = parameters.get("target")
        if target:
            query_params["target"] = str(target)
        state = parameters.get("state")
        if state:
            query_params["state"] = str(state)
        app = parameters.get("app")
        if app:
            query_params["app"] = str(app).strip()
        since = parameters.get("since")
        if since is not None:
            query_params["since"] = str(since)
        until = parameters.get("until")
        if until is not None:
            query_params["until"] = str(until)
        limit = parameters.get("limit")
        if limit is not None:
            query_params["limit"] = str(limit)
        team_id = parameters.get("teamId")
        if team_id:
            query_params["teamId"] = str(team_id).strip()
        
        url = "https://api.vercel.com/v6/deployments"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    deployments = []
                    for d in data.get("deployments", []):
                        creator = d.get("creator", {})
                        dep = {
                            "uid": d.get("uid"),
                            "name": d.get("name"),
                            "url": d.get("url"),
                            "state": d.get("state") or d.get("readyState") or "UNKNOWN",
                            "target": d.get("target"),
                            "created": d.get("created") or d.get("createdAt"),
                            "projectId": d.get("projectId", ""),
                            "source": d.get("source", ""),
                            "inspectorUrl": d.get("inspectorUrl", ""),
                            "creator": {
                                "uid": creator.get("uid", ""),
                                "email": creator.get("email", ""),
                                "username": creator.get("username", ""),
                            },
                            "meta": d.get("meta", {}),
                        }
                        deployments.append(dep)
                    transformed = {
                        "deployments": deployments,
                        "count": len(deployments),
                        "hasMore": data.get("pagination", {}).get("next") is not None,
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(transformed, indent=2),
                        data=transformed,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")