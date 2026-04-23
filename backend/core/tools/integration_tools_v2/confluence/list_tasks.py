from typing import Any, Dict
import httpx
import json
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceListTasksTool(BaseTool):
    name = "confluence_list_tasks"
    description = "List inline tasks from Confluence. Optionally filter by page, space, assignee, or status."
    category = "integration"

    QUERY = """
query ListTasks($first: Int!, $after: String, $filter: TasksFilterInput) {
  tasks(first: $first, after: $after, filter: $filter) {
    pageInfo {
      endCursor
      hasNextPage
    }
    nodes {
      id
      localId
      status
      body(format: STORAGE)
      createdAt
      updatedAt
      dueAt
      completedAt
      creator {
        accountId
      }
      assignee {
        accountId
      }
      completer {
        accountId
      }
      content {
        id
        type
      }
      space {
        key
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
                key="CONFLUENCE_ACCESS_TOKEN",
                description="OAuth access token for Confluence",
                env_var="CONFLUENCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            ),
            CredentialRequirement(
                key="CONFLUENCE_DOMAIN",
                description="Your Confluence domain (e.g., yourcompany.atlassian.net)",
                env_var="CONFLUENCE_DOMAIN",
                required=True,
                auth_type="text",
            ),
            CredentialRequirement(
                key="CONFLUENCE_CLOUD_ID",
                description="Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                env_var="CONFLUENCE_CLOUD_ID",
                required=False,
                auth_type="text",
            ),
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "confluence",
            context=context,
            context_token_keys=("confluence_token",),
            env_token_keys=("CONFLUENCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    async def _get_cloud_id(self, access_token: str, domain: str) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            resources: list[dict[str, Any]] = response.json()
            norm_domain = domain.strip().lower().rstrip("/")
            for resource in resources:
                res_url = resource.get("url", "").strip().lower().rstrip("/")
                scopes = resource.get("scopes", [])
                if res_url.endswith(norm_domain) and any("confluence" in scope.lower() for scope in scopes):
                    return resource["id"]
            raise ValueError(f"No matching Confluence site found for domain '{domain}'")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pageId": {
                    "type": "string",
                    "description": "Filter tasks by page ID",
                },
                "spaceId": {
                    "type": "string",
                    "description": "Filter tasks by space ID",
                },
                "assignedTo": {
                    "type": "string",
                    "description": "Filter tasks by assignee account ID",
                },
                "status": {
                    "type": "string",
                    "description": "Filter tasks by status (complete or incomplete)",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of tasks to return (default: 50, max: 250)",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        domain = context.get("CONFLUENCE_DOMAIN") if context else None
        cloud_id = context.get("CONFLUENCE_CLOUD_ID") if context else None

        if not domain:
            return ToolResult(success=False, output="", error="Confluence domain not configured.")

        if not cloud_id:
            try:
                cloud_id = await self._get_cloud_id(access_token, domain)
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Failed to resolve cloud ID: {str(e)}")

        filters: dict[str, Any] = {}
        content_filter: dict[str, Any] = {}
        page_id = parameters.get("pageId")
        if page_id:
            content_filter["ids"] = [page_id]
        space_id = parameters.get("spaceId")
        if space_id:
            content_filter["spaceKeys"] = [space_id]
        if content_filter:
            filters["content"] = content_filter
        assignee = parameters.get("assignedTo")
        if assignee:
            filters["assigneeAccountId"] = assignee
        status_param = parameters.get("status")
        if status_param:
            status_lower = status_param.strip().lower()
            if status_lower == "complete":
                filters["status"] = "COMPLETE"
            elif status_lower == "incomplete":
                filters["status"] = "INCOMPLETE"

        limit_param = parameters.get("limit")
        limit = 50
        if limit_param is not None:
            try:
                limit = max(1, min(int(limit_param), 250))
            except ValueError:
                limit = 50
        cursor = parameters.get("cursor")

        variables: dict[str, Any] = {"first": limit}
        if cursor:
            variables["after"] = cursor
        if filters:
            variables["filter"] = filters

        url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/graphql"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        json_body = {
            "query": self.QUERY,
            "variables": variables,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)

                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if "errors" in data:
                    return ToolResult(
                        success=False,
                        output="",
                        error=json.dumps(data["errors"]) if isinstance(data["errors"], list) else str(data["errors"]),
                    )

                tasks_conn = data.get("data", {}).get("tasks", {})
                nodes = tasks_conn.get("nodes", [])
                tasks: list[dict[str, Any]] = []
                for node in nodes:
                    content = node.get("content", {})
                    content_type = content.get("type")
                    page_id_val = content.get("id") if content_type == "page" else None
                    blog_post_id_val = content.get("id") if content_type == "blogpost" else None
                    space_val = node.get("space", {})
                    space_id_val = space_val.get("key") if space_val else None
                    status_val = node.get("status", "").lower()
                    tasks.append({
                        "id": node.get("id"),
                        "localId": node.get("localId"),
                        "spaceId": space_id_val,
                        "pageId": page_id_val,
                        "blogPostId": blog_post_id_val,
                        "status": status_val,
                        "body": node.get("body"),
                        "createdBy": node.get("creator", {}).get("accountId"),
                        "assignedTo": node.get("assignee", {}).get("accountId"),
                        "completedBy": node.get("completer", {}).get("accountId"),
                        "createdAt": node.get("createdAt"),
                        "updatedAt": node.get("updatedAt"),
                        "dueAt": node.get("dueAt"),
                        "completedAt": node.get("completedAt"),
                    })

                page_info = tasks_conn.get("pageInfo", {})
                has_next = page_info.get("hasNextPage", False)
                end_cursor = page_info.get("endCursor")
                next_cursor = end_cursor if has_next else None

                output_data = {
                    "ts": datetime.utcnow().isoformat(),
                    "tasks": tasks,
                    "nextCursor": next_cursor,
                }
                output_str = json.dumps(output_data)

                return ToolResult(success=True, output=output_str, data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")