from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SlackPublishViewTool(BaseTool):
    name = "slack_publish_view"
    description = "Publish a static view to a user's Home tab in Slack. Used to create or update the app's Home tab experience."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SLACK_ACCESS_TOKEN",
                description="Access token or bot token for Slack API",
                env_var="SLACK_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "slack",
            context=context,
            context_token_keys=("accessToken", "botToken"),
            env_token_keys=("SLACK_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "authMethod": {
                    "type": "string",
                    "description": "Authentication method: oauth or bot_token",
                },
                "botToken": {
                    "type": "string",
                    "description": "Bot token for Custom Bot",
                },
                "accessToken": {
                    "type": "string",
                    "description": "OAuth access token or bot token for Slack API",
                },
                "userId": {
                    "type": "string",
                    "description": "The user ID to publish the Home tab view to (e.g., U0BPQUNTA)",
                },
                "hash": {
                    "type": "string",
                    "description": "View state hash to protect against race conditions. Obtained from a previous views response",
                },
                "view": {
                    "type": "object",
                    "description": "A view payload object defining the Home tab. Must include type (\"home\") and blocks array",
                },
            },
            "required": ["userId", "view"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = "https://slack.com/api/views.publish"

        try:
            user_id = parameters["userId"].strip()
            view_input = parameters["view"]
            if isinstance(view_input, str):
                view = json.loads(view_input)
            elif isinstance(view_input, dict):
                view = view_input
            else:
                return ToolResult(success=False, output="", error="view must be a valid JSON object or string")

            body: Dict[str, Any] = {
                "user_id": user_id,
                "view": view,
            }
            hash_val = (parameters.get("hash") or "").strip()
            if hash_val:
                body["hash"] = hash_val

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                try:
                    data = response.json()
                except json.JSONDecodeError:
                    return ToolResult(success=False, output=response.text, error="Invalid JSON response from Slack API")

                if data.get("ok"):
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    error = data.get("error", "Unknown error")
                    if error == "invalid_arguments":
                        messages = data.get("response_metadata", {}).get("messages", [])
                        err_msg = f"Invalid view arguments: {', '.join(messages) if messages else error}"
                    elif error in ["invalid_auth", "not_authed", "token_expired"]:
                        err_msg = "Invalid authentication. Please check your Slack credentials."
                    else:
                        error_map = {
                            "not_found": "User not found. Please check the user ID and try again.",
                            "not_enabled": "The Home tab is not enabled for this app. Enable it in your app configuration.",
                            "hash_conflict": "The view has been modified since the hash was generated. Retrieve the latest view and try again.",
                            "view_too_large": "The view payload is too large (max 250kb). Reduce the number of blocks or content.",
                            "duplicate_external_id": "A view with this external_id already exists. Use a unique external_id per workspace.",
                            "missing_scope": "Missing required permissions. Please reconnect your Slack account with the necessary scopes.",
                        }
                        err_msg = error_map.get(error, error or "Failed to publish view in Slack")
                    return ToolResult(success=False, output="", error=err_msg)

        except json.JSONDecodeError as e:
            return ToolResult(success=False, output="", error=f"Invalid view JSON: {str(e)}")
        except KeyError as e:
            return ToolResult(success=False, output="", error=f"Missing required parameter: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")