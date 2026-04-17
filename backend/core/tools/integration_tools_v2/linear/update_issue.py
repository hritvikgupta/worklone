from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearUpdateIssueTool(BaseTool):
    name = "linear_update_issue"
    description = "Update an existing issue in Linear"
    category = "integration"

    QUERY = """
mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    success
    issue {
      id
      title
      description
      priority
      estimate
      url
      updatedAt
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
      team {
        id
      }
      project {
        id
      }
      cycle {
        id
        number
        name
      }
      parent {
        id
        title
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
    """

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

    def _build_input(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        input_: Dict[str, Any] = {}
        string_fields = [
            "title",
            "description",
            "stateId",
            "assigneeId",
            "projectId",
            "cycleId",
            "parentId",
            "dueDate",
        ]
        for field in string_fields:
            value = parameters.get(field)
            if value is not None and str(value) != "":
                input_[field] = str(value)
        number_fields = [("priority", int), ("estimate", int)]
        for field, converter in number_fields:
            value = parameters.get(field)
            if value is not None:
                input_[field] = converter(value)
        array_fields = ["labelIds", "addedLabelIds", "removedLabelIds"]
        for field in array_fields:
            value = parameters.get(field)
            if value is not None and isinstance(value, list):
                input_[field] = [str(item) for item in value]
        return input_

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "issueId": {
                    "type": "string",
                    "description": "Linear issue ID to update",
                },
                "title": {
                    "type": "string",
                    "description": "New issue title",
                },
                "description": {
                    "type": "string",
                    "description": "New issue description",
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
                    "items": {"type": "string"},
                    "description": "Array of label IDs to set on the issue (replaces all existing labels)",
                },
                "projectId": {
                    "type": "string",
                    "description": "Project ID to move the issue to",
                },
                "cycleId": {
                    "type": "string",
                    "description": "Cycle ID to assign the issue to",
                },
                "parentId": {
                    "type": "string",
                    "description": "Parent issue ID (for making this a sub-issue)",
                },
                "dueDate": {
                    "type": "string",
                    "description": "Due date in ISO 8601 format (date only: YYYY-MM-DD)",
                },
                "addedLabelIds": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of label IDs to add to the issue (without replacing existing labels)",
                },
                "removedLabelIds": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of label IDs to remove from the issue",
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
        input_ = self._build_input(parameters)
        variables = {
            "id": parameters["issueId"],
            "input": input_,
        }
        body = {
            "query": self.QUERY,
            "variables": variables,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

            if response.status_code not in [200, 201, 204]:
                return ToolResult(success=False, output="", error=response.text)

            data = response.json()

        except json.JSONDecodeError:
            return ToolResult(success=False, output=response.text, error="Invalid JSON response")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")

        errors = data.get("errors")
        if errors:
            error_msg = errors[0].get("message", "Failed to update issue") if isinstance(errors, list) else "GraphQL errors"
            return ToolResult(success=False, output=response.text, error=error_msg)

        issue_update = data.get("data", {}).get("issueUpdate")
        if not issue_update or not issue_update.get("success"):
            return ToolResult(success=False, output=response.text, error="Issue update was not successful")

        issue = issue_update.get("issue")
        if not issue:
            return ToolResult(success=False, output=response.text, error="No issue data returned")

        output_issue: Dict[str, Any] = {
            "id": issue["id"],
            "title": issue["title"],
            "description": issue["description"],
            "priority": issue["priority"],
            "estimate": issue["estimate"],
            "url": issue["url"],
            "updatedAt": issue["updatedAt"],
            "dueDate": issue["dueDate"],
            "state": issue["state"],
            "assignee": issue["assignee"],
            "teamId": issue.get("team", {}).get("id"),
            "projectId": issue.get("project", {}).get("id"),
            "cycleId": issue.get("cycle", {}).get("id"),
            "cycleNumber": issue.get("cycle", {}).get("number"),
            "cycleName": issue.get("cycle", {}).get("name"),
            "parentId": issue.get("parent", {}).get("id"),
            "parentTitle": issue.get("parent", {}).get("title"),
            "labels": issue.get("labels", {}).get("nodes", []),
        }

        result_data = {"issue": output_issue}
        return ToolResult(
            success=True,
            output=json.dumps(result_data),
            data=result_data,
        )