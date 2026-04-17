from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearCreateCycleTool(BaseTool):
    name = "linear_create_cycle"
    description = "Create a new cycle (sprint/iteration) in Linear"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LINEAR_ACCESS_TOKEN",
                description="Access token",
                env_var="LINEAR_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "linear",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("LINEAR_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "teamId": {
                    "type": "string",
                    "description": "Team ID to create the cycle in",
                },
                "startsAt": {
                    "type": "string",
                    "description": "Cycle start date (ISO format)",
                },
                "endsAt": {
                    "type": "string",
                    "description": "Cycle end date (ISO format)",
                },
                "name": {
                    "type": "string",
                    "description": "Cycle name (optional, will be auto-generated if not provided)",
                },
            },
            "required": ["teamId", "startsAt", "endsAt"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        input_dict: Dict[str, Any] = {
            "teamId": parameters["teamId"],
            "startsAt": parameters["startsAt"],
            "endsAt": parameters["endsAt"],
        }
        name = parameters.get("name")
        if name is not None and name != "":
            input_dict["name"] = name
        
        body = {
            "query": """
            mutation CreateCycle($input: CycleCreateInput!) {
              cycleCreate(input: $input) {
                success
                cycle {
                  id
                  number
                  name
                  startsAt
                  endsAt
                  completedAt
                  progress
                  createdAt
                  team {
                    id
                    name
                  }
                }
              }
            }
            """,
            "variables": {
                "input": input_dict,
            },
        }
        
        url = "https://api.linear.app/graphql"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to create cycle")
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("cycleCreate", {})
                if not result.get("success", False):
                    return ToolResult(success=False, output="", error="Cycle creation was not successful")
                
                cycle = result.get("cycle")
                if not cycle:
                    return ToolResult(success=False, output="", error="No cycle data returned")
                
                output_data = {"cycle": cycle}
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")