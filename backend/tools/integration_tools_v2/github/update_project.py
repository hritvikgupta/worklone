from typing import Any, Dict, List
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubUpdateProjectTool(BaseTool):
    name = "github_update_project"
    description = "Update an existing GitHub Project V2. Can update title, description, visibility (public), or status (closed). Requires the project Node ID."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> List[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GITHUB_ACCESS_TOKEN",
                description="GitHub Personal Access Token with project write permissions",
                env_var="GITHUB_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "github",
            context=context,
            context_token_keys=("github_token",),
            env_token_keys=("GITHUB_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def _build_graphql_query(self, parameters: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        input_fields: List[str] = ["projectId: $projectId"]
        variables: Dict[str, Any] = {"projectId": parameters["project_id"]}
        var_defs: List[str] = ["$projectId: ID!"]

        field_mappings = [
            ("title", "title: $title", "$title: String"),
            ("shortDescription", "shortDescription: $shortDescription", "$shortDescription: String"),
            ("project_public", "public: $project_public", "$project_public: Boolean"),
            ("closed", "closed: $closed", "$closed: Boolean"),
        ]

        for key, input_field, var_def in field_mappings:
            if key in parameters:
                input_fields.append(input_field)
                variables[key] = parameters[key]
                var_defs.append(var_def)

        query = f"""mutation({', '.join(var_defs)}) {{
          updateProjectV2(input: {{
            {chr(10).join('            ' + field for field in input_fields)}
          }}) {{
            projectV2 {{
              id
              title
              number
              url
              closed
              public
              shortDescription
            }}
          }}
        }}"""
        return query, variables

    def get_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project Node ID (format: PVT_...)",
                },
                "title": {
                    "type": "string",
                    "description": "New project title",
                },
                "shortDescription": {
                    "type": "string",
                    "description": "New project short description",
                },
                "project_public": {
                    "type": "boolean",
                    "description": "Set project visibility (true = public, false = private)",
                },
                "closed": {
                    "type": "boolean",
                    "description": "Set project status (true = closed, false = open)",
                },
            },
            "required": ["project_id"],
        }

    async def execute(self, parameters: Dict[str, Any], context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        query, variables = self._build_graphql_query(parameters)
        json_body = {
            "query": query,
            "variables": variables,
        }
        url = "https://api.github.com/graphql"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)

                if response.status_code not in [200]:
                    return ToolResult(success=False, output="", error=response.text)

                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output=response.text, error="Invalid JSON response")

                if data.get("errors"):
                    errors = data["errors"]
                    error_msg = errors[0].get("message", "GraphQL error") if isinstance(errors, list) and errors else "GraphQL errors"
                    return ToolResult(success=False, output="", error=error_msg)

                project = data.get("data", {}).get("updateProjectV2", {}).get("projectV2", {})
                if not project.get("id"):
                    return ToolResult(success=False, output="", error="Failed to update project")

                return ToolResult(success=True, output=response.text, data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")