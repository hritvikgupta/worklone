from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class LinearListIssueRelationsTool(BaseTool):
    name = "linear_list_issue_relations"
    description = "List all relations (dependencies) for an issue in Linear"
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
                "issueId": {
                    "type": "string",
                    "description": "Issue ID",
                },
                "first": {
                    "type": "number",
                    "description": "Number of relations to return (default: 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Cursor for pagination",
                },
            },
            "required": ["issueId"],
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
        
        variables: Dict[str, Any] = {
            "issueId": parameters["issueId"],
            "first": int(parameters.get("first", 50)),
        }
        after = (parameters.get("after") or "").strip()
        if after:
            variables["after"] = after
        
        query = """\
        query ListIssueRelations($issueId: String!, $first: Int, $after: String) {
          issue(id: $issueId) {
            relations(first: $first, after: $after) {
              nodes {
                id
                type
                issue {
                  id
                  title
                }
                relatedIssue {
                  id
                  title
                }
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
        }
        """
        
        json_body = {
            "query": query,
            "variables": variables,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to list issue relations") if data["errors"] else "Failed to list issue relations"
                    return ToolResult(success=False, output="", error=error_msg)
                
                if not data.get("data", {}).get("issue"):
                    return ToolResult(success=False, output="", error="Issue not found")
                
                relations_data = data["data"]["issue"]["relations"]
                output_data = {
                    "relations": relations_data["nodes"],
                    "pageInfo": {
                        "hasNextPage": relations_data["pageInfo"]["hasNextPage"],
                        "endCursor": relations_data["pageInfo"]["endCursor"],
                    },
                }
                output_str = json.dumps(output_data)
                
                return ToolResult(success=True, output=output_str, data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")