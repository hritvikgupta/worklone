from typing import Any, Dict
import httpx
from datetime import datetime, timezone
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearUpdateNotificationTool(BaseTool):
    name = "linear_update_notification"
    description = "Mark a notification as read or unread in Linear"
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
                "notificationId": {
                    "type": "string",
                    "description": "Notification ID to update",
                },
                "readAt": {
                    "type": "string",
                    "description": "Timestamp to mark as read (ISO format). Pass null or omit to mark as unread",
                },
            },
            "required": ["notificationId"],
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

        input_ = {}
        if "readAt" in parameters:
            input_["readAt"] = parameters["readAt"]
        else:
            input_["readAt"] = datetime.now(timezone.utc).isoformat()

        body = {
            "query": """
                mutation UpdateNotification($id: String!, $input: NotificationUpdateInput!) {
                  notificationUpdate(id: $id, input: $input) {
                    success
                    notification {
                      id
                      type
                      createdAt
                      readAt
                      issue {
                        id
                        title
                      }
                    }
                  }
                }
            """,
            "variables": {
                "id": parameters["notificationId"],
                "input": input_,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if data.get("errors"):
                    errors = data["errors"]
                    error_msg = errors[0].get("message") if errors else "Failed to update notification"
                    return ToolResult(success=False, output="", error=error_msg)

                result = data.get("data", {}).get("notificationUpdate", {})
                if not result.get("success", False):
                    return ToolResult(success=False, output="", error="Notification update was not successful")

                return ToolResult(success=True, output=response.text, data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")