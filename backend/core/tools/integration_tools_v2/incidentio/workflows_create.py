from typing import Any, Optional
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class IncidentioWorkflowsCreateTool(BaseTool):
    name = "incidentio_workflows_create"
    description = "Create a new workflow in incident.io."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="incidentio_api_key",
                description="incident.io API Key",
                env_var="INCIDENTIO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "incidentio",
            context=context,
            context_token_keys=("incidentio_api_key",),
            env_token_keys=("INCIDENTIO_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def _parse_json_param(self, json_string: Optional[str], default: Any) -> Any:
        if not json_string:
            return default
        try:
            return json.loads(json_string)
        except json.JSONDecodeError:
            return default

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": 'Name of the workflow (e.g., "Notify on Critical Incidents")',
                },
                "folder": {
                    "type": "string",
                    "description": "Folder to organize the workflow in",
                },
                "state": {
                    "type": "string",
                    "description": "State of the workflow (active, draft, or disabled)",
                },
                "trigger": {
                    "type": "string",
                    "description": 'Trigger type for the workflow (e.g., "incident.updated", "incident.created")',
                },
                "steps": {
                    "type": "string",
                    "description": 'Array of workflow steps as JSON string. Example: "[{\\"label\\": \\"Notify team\\", \\"name\\": \\"slack.post_message\\"}]"',
                },
                "condition_groups": {
                    "type": "string",
                    "description": 'Array of condition groups as JSON string to control when the workflow runs. Example: "[{\\"conditions\\": [{\\"operation\\": \\"one_of\\", \\"param_bindings\\": [], \\"subject\\": \\"incident.severity\\"}]}]"',
                },
                "runs_on_incidents": {
                    "type": "string",
                    "description": 'When to run the workflow: "newly_created" (only new incidents), "newly_created_and_active" (new and active incidents), "active" (only active incidents), or "all" (all incidents)',
                },
                "runs_on_incident_modes": {
                    "type": "string",
                    "description": 'Array of incident modes to run on as JSON string. Example: "[\\"standard\\", \\"retrospective\\"]"',
                },
                "include_private_incidents": {
                    "type": "boolean",
                    "description": "Whether to include private incidents",
                },
                "continue_on_step_error": {
                    "type": "boolean",
                    "description": "Whether to continue executing subsequent steps if a step fails",
                },
                "once_for": {
                    "type": "string",
                    "description": 'Array of fields to ensure the workflow runs only once per unique combination of these fields, as JSON string. Example: "[\\"incident.id\\"]"',
                },
                "expressions": {
                    "type": "string",
                    "description": 'Array of workflow expressions as JSON string for advanced workflow logic. Example: "[{\\"label\\": \\"My expression\\", \\"operations\\": []}]"',
                },
                "delay": {
                    "type": "string",
                    "description": 'Delay configuration as JSON string. Example: "{\\"for_seconds\\": 60, \\"conditions_apply_over_delay\\": false}"',
                },
            },
            "required": ["name"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = "https://api.incident.io/v2/workflows"

        body: dict[str, Any] = {
            "name": parameters["name"],
            "trigger": parameters.get("trigger", "incident.updated"),
            "once_for": self._parse_json_param(parameters.get("once_for"), []),
            "condition_groups": self._parse_json_param(parameters.get("condition_groups"), []),
            "steps": self._parse_json_param(parameters.get("steps"), []),
            "expressions": self._parse_json_param(parameters.get("expressions"), []),
            "include_private_incidents": parameters.get("include_private_incidents", True),
            "runs_on_incident_modes": self._parse_json_param(parameters.get("runs_on_incident_modes"), ["standard"]),
            "continue_on_step_error": parameters.get("continue_on_step_error", False),
            "runs_on_incidents": parameters.get("runs_on_incidents", "newly_created"),
            "state": parameters.get("state", "draft"),
        }

        folder = parameters.get("folder")
        if folder:
            body["folder"] = folder

        delay_str = parameters.get("delay")
        if delay_str:
            delay_parsed = self._parse_json_param(delay_str, None)
            if delay_parsed is not None:
                body["delay"] = delay_parsed

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")