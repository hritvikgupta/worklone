from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearReadIssuesTool(BaseTool):
    name = "linear_read_issues"
    description = "Fetch and filter issues from Linear"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LINEAR_ACCESS_TOKEN",
                description="Access token for Linear",
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
                    "description": "Linear team ID (UUID format) to filter issues by team",
                },
                "projectId": {
                    "type": "string",
                    "description": "Linear project ID (UUID format) to filter issues by project",
                },
                "assigneeId": {
                    "type": "string",
                    "description": "User ID to filter by assignee",
                },
                "stateId": {
                    "type": "string",
                    "description": "Workflow state ID to filter by status",
                },
                "priority": {
                    "type": "number",
                    "description": "Priority to filter by (0=No priority, 1=Urgent, 2=High, 3=Normal, 4=Low)",
                },
                "labelIds": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of label IDs to filter by",
                },
                "createdAfter": {
                    "type": "string",
                    "description": "Filter issues created after this date (ISO 8601 format)",
                },
                "updatedAfter": {
                    "type": "string",
                    "description": "Filter issues updated after this date (ISO 8601 format)",
                },
                "includeArchived": {
                    "type": "boolean",
                    "description": "Include archived issues (default: false)",
                },
                "first": {
                    "type": "number",
                    "description": "Number of issues to return (default: 50, max: 250)",
                },
                "after": {
                    "type": "string",
                    "description": "Pagination cursor for next page",
                },
                "orderBy": {
                    "type": "string",
                    "description": 'Sort order: "createdAt" or "updatedAt" (default: "updatedAt")',
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
        
        filter_ = {}
        team_id = parameters.get("teamId")
        if team_id is not None and str(team_id) != "":
            filter_["team"] = {"id": {"eq": str(team_id)}}
        project_id = parameters.get("projectId")
        if project_id is not None and str(project_id) != "":
            filter_["project"] = {"id": {"eq": str(project_id)}}
        assignee_id = parameters.get("assigneeId")
        if assignee_id is not None and str(assignee_id) != "":
            filter_["assignee"] = {"id": {"eq": str(assignee_id)}}
        state_id = parameters.get("stateId")
        if state_id is not None and str(state_id) != "":
            filter_["state"] = {"id": {"eq": str(state_id)}}
        priority = parameters.get("priority")
        if priority is not None:
            filter_["priority"] = {"eq": int(float(priority))}
        label_ids = parameters.get("labelIds")
        if label_ids is not None and isinstance(label_ids, list) and len(label_ids) > 0:
            filter_["labels"] = {"some": {"id": {"in": label_ids}}}
        created_after = parameters.get("createdAfter")
        if created_after is not None and str(created_after) != "":
            filter_["createdAt"] = {"gte": str(created_after)}
        updated_after = parameters.get("updatedAfter")
        if updated_after is not None and str(updated_after) != "":
            filter_["updatedAt"] = {"gte": str(updated_after)}

        variables: Dict[str, Any] = {}
        if filter_:
            variables["filter"] = filter_
        first = parameters.get("first")
        if first is not None:
            variables["first"] = min(int(float(first)), 250)
        after = parameters.get("after")
        if after is not None:
            after_trim = str(after).strip()
            if after_trim:
                variables["after"] = after_trim
        include_archived = parameters.get("includeArchived")
        if include_archived is not None:
            variables["includeArchived"] = bool(include_archived)
        order_by = parameters.get("orderBy")
        if order_by is not None:
            variables["orderBy"] = str(order_by)

        query = """
        query Issues(
          $filter: IssueFilter
          $first: Int
          $after: String
          $includeArchived: Boolean
          $orderBy: PaginationOrderBy
        ) {
          issues(
            filter: $filter
            first: $first
            after: $after
            includeArchived: $includeArchived
            orderBy: $orderBy
          ) {
            nodes {
              id
              title
              description
              priority
              estimate
              url
              dueDate
              createdAt
              updatedAt
              state {
                id
                name
                type
              }
              assignee {
                id
                name
                email
              }
              team {
                id
                name
              }
              project {
                id
                name
              }
              cycle {
                id
                number
                name
              }
              labels {
                nodes {
                  id
                  name
                  color
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """
        body = {
            "query": query.strip(),
            "variables": variables,
        }
        url = "https://api.linear.app/graphql"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output=response.text, error="Invalid JSON response")
                
                if data.get("errors"):
                    error_msg = (
                        data["errors"][0].get("message", "GraphQL error")
                        if isinstance(data["errors"], list) and len(data["errors"]) > 0
                        else "GraphQL errors"
                    )
                    return ToolResult(success=False, output=response.text, error=error_msg)
                
                if not data.get("data", {}).get("issues"):
                    return ToolResult(success=False, output=response.text, error="No issues data returned")
                
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")