from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearCreateIssueTool(BaseTool):
    name = "linear_issue_writer"
    description = "Create a new issue in Linear"
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
            context_token_keys=("linear_token",),
            env_token_keys=("LINEAR_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _build_input(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        input_data: Dict[str, Any] = {
            "teamId": parameters["teamId"],
            "title": parameters["title"],
        }
        string_keys = [
            "projectId",
            "description",
            "stateId",
            "assigneeId",
            "cycleId",
            "parentId",
            "dueDate",
            "projectMilestoneId",
        ]
        for key in string_keys:
            val = parameters.get(key)
            if val is not None and str(val).strip() != "":
                input_data[key] = val
        pri = parameters.get("priority")
        if pri is not None:
            input_data["priority"] = float(pri)
        est = parameters.get("estimate")
        if est is not None:
            input_data["estimate"] = float(est)
        labs = parameters.get("labelIds")
        if labs is not None and isinstance(labs, list):
            input_data["labelIds"] = labs
        subs = parameters.get("subscriberIds")
        if subs is not None and isinstance(subs, list):
            input_data["subscriberIds"] = subs
        return input_data

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "teamId": {
                    "type": "string",
                    "description": "Linear team ID (UUID format) where the issue will be created",
                },
                "projectId": {
                    "type": "string",
                    "description": "Linear project ID (UUID format) to associate with the issue",
                },
                "title": {
                    "type": "string",
                    "description": "Issue title",
                },
                "description": {
                    "type": "string",
                    "description": "Issue description",
                },
                "stateId": {
                    "type": "string",
                    "description": "Workflow state ID (status)",
                },
                "assigneeId": {
                    "type": "string",
                    "description": "User ID to assign the issue to",
                },
                "priority": {
                    "type": "number",
                    "description": "Priority (0=No priority, 1=Urgent, 2=High, 3=Normal, 4=Low)",
                },
                "estimate": {
                    "type": "number",
                    "description": "Estimate in points",
                },
                "labelIds": {
                    "type": "array",
                    "description": "Array of label IDs to set on the issue",
                },
                "cycleId": {
                    "type": "string",
                    "description": "Cycle ID to assign the issue to",
                },
                "parentId": {
                    "type": "string",
                    "description": "Parent issue ID (for creating sub-issues)",
                },
                "dueDate": {
                    "type": "string",
                    "description": "Due date in ISO 8601 format (date only: YYYY-MM-DD)",
                },
                "subscriberIds": {
                    "type": "array",
                    "description": "Array of user IDs to subscribe to the issue",
                },
                "projectMilestoneId": {
                    "type": "string",
                    "description": "Project milestone ID to associate with the issue",
                },
            },
            "required": ["teamId", "title"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        title = (parameters.get("title") or "").strip()
        if not title:
            return ToolResult(success=False, output="", error="Title is required to create a Linear issue")

        team_id = parameters.get("teamId")
        if not team_id:
            return ToolResult(success=False, output="", error="Team ID is required to create a Linear issue")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        input_data = self._build_input(parameters)
        body = {
            "query": """
            mutation CreateIssue($input: IssueCreateInput!) {
              issueCreate(input: $input) {
                issue {
                  id
                  title
                  description
                  priority
                  estimate
                  url
                  dueDate
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
                  team { id }
                  project { id }
                  cycle {
                    id
                    number
                    name
                  }
                  parent {
                    id
                    title
                  }
                  projectMilestone {
                    id
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
              }
            }
            """,
            "variables": {"input": input_data},
        }

        url = "https://api.linear.app/graphql"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200]:
                    return ToolResult(
                        success=False, output="", error=f"HTTP {response.status_code}: {response.text}"
                    )

                try:
                    data = response.json()
                except json.JSONDecodeError:
                    return ToolResult(
                        success=False, output=response.text, error="Invalid JSON response from Linear API"
                    )

                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to create issue")
                    return ToolResult(success=False, output="", error=error_msg)

                result = data.get("data", {}).get("issueCreate")
                if not result or not result.get("issue"):
                    return ToolResult(
                        success=False, output="", error="Issue creation was not successful"
                    )

                issue = result["issue"]
                transformed_issue = {
                    "id": issue.get("id"),
                    "title": issue.get("title"),
                    "description": issue.get("description"),
                    "priority": issue.get("priority"),
                    "estimate": issue.get("estimate"),
                    "url": issue.get("url"),
                    "dueDate": issue.get("dueDate"),
                    "state": issue.get("state"),
                    "assignee": issue.get("assignee"),
                    "teamId": issue.get("team", {}).get("id"),
                    "projectId": issue.get("project", {}).get("id"),
                    "cycleId": issue.get("cycle", {}).get("id"),
                    "cycleNumber": issue.get("cycle", {}).get("number"),
                    "cycleName": issue.get("cycle", {}).get("name"),
                    "parentId": issue.get("parent", {}).get("id"),
                    "parentTitle": issue.get("parent", {}).get("title"),
                    "projectMilestoneId": issue.get("projectMilestone", {}).get("id"),
                    "projectMilestoneName": issue.get("projectMilestone", {}).get("name"),
                    "labels": issue.get("labels", {}).get("nodes", []),
                }
                transformed = {"issue": transformed_issue}
                return ToolResult(
                    success=True, output=json.dumps(transformed), data=transformed
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")