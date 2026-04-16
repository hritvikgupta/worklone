from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelGetDeploymentEventsTool(BaseTool):
    name = "vercel_get_deployment_events"
    description = "Get build and runtime events for a Vercel deployment"
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
        if context:
            token = context.get("vercel_access_token")
        if token is None:
            token = os.getenv("VERCEL_ACCESS_TOKEN")
        return token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "deploymentId": {
                    "type": "string",
                    "description": "The unique deployment identifier or hostname",
                },
                "direction": {
                    "type": "string",
                    "description": "Order of events by timestamp: backward or forward (default: forward)",
                },
                "follow": {
                    "type": "number",
                    "description": "When set to 1, returns live events as they happen",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of events to return (-1 for all)",
                },
                "since": {
                    "type": "number",
                    "description": "Timestamp to start pulling build logs from",
                },
                "until": {
                    "type": "number",
                    "description": "Timestamp to stop pulling build logs at",
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": ["deploymentId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Vercel access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        deployment_id_raw = parameters.get("deploymentId")
        if not deployment_id_raw:
            return ToolResult(success=False, output="", error="deploymentId is required.")
        deployment_id = str(deployment_id_raw).strip()

        query_params: Dict[str, str] = {}
        direction = parameters.get("direction")
        if direction:
            query_params["direction"] = str(direction)
        for key in ("follow", "limit", "since", "until"):
            val = parameters.get(key)
            if val is not None:
                query_params[key] = str(val)
        team_id = parameters.get("teamId")
        if team_id:
            query_params["teamId"] = str(team_id).strip()

        url = f"https://api.vercel.com/v3/deployments/{deployment_id}/events"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    events_raw = data if isinstance(data, list) else data.get("events", [])
                    transformed_events = []
                    for e in events_raw:
                        transformed_events.append({
                            "type": e.get("type"),
                            "created": e.get("created"),
                            "date": e.get("date"),
                            "text": e.get("text") or e.get("payload", {}).get("text"),
                            "serial": e.get("serial"),
                            "deploymentId": e.get("deploymentId") or e.get("payload", {}).get("deploymentId"),
                            "id": e.get("id"),
                            "level": e.get("level"),
                        })
                    output_data = {
                        "events": transformed_events,
                        "count": len(transformed_events),
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")