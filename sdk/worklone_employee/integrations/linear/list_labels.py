from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class LinearListLabelsTool(BaseTool):
    name = "linear_list_labels"
    description = "List all labels in Linear workspace or team"
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
            context_token_keys=("linear_token",),
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
                    "description": "Filter by team ID",
                },
                "first": {
                    "type": "number",
                    "description": "Number of labels to return (default: 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Cursor for pagination",
                },
            },
            "required": [],
        }

    def _build_graphql_body(self, parameters: dict) -> dict[str, Any]:
        filter_dict: dict[str, Any] = {}
        team_id = parameters.get("teamId")
        if team_id:
            filter_dict["team"] = {"id": {"eq": team_id}}

        variables: dict[str, Any] = {
            "first": int(parameters.get("first", 50)),
        }

        after_val = parameters.get("after")
        if after_val:
            after_str = str(after_val).strip()
            if after_str:
                variables["after"] = after_str

        if filter_dict:
            variables["filter"] = filter_dict

        query = """
query ListLabels($filter: IssueLabelFilter, $first: Int, $after: String) {
  issueLabels(filter: $filter, first: $first, after: $after) {
    nodes {
      id
      name
      color
      description
      isGroup
      createdAt
      updatedAt
      archivedAt
      team {
        id
        name
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
        """.strip()

        return {
            "query": query,
            "variables": variables,
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.linear.app/graphql"
        json_body = self._build_graphql_body(parameters)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code >= 400:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to list labels") if data["errors"] else "GraphQL error"
                    return ToolResult(success=False, output="", error=error_msg)
                
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")