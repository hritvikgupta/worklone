from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioGetThreadTool(BaseTool):
    name = "attio_get_thread"
    description = "Get a single comment thread by ID from Attio"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ATTIO_ACCESS_TOKEN",
                description="The OAuth access token for the Attio API",
                env_var="ATTIO_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "attio",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("ATTIO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "threadId": {
                    "type": "string",
                    "description": "The thread ID",
                },
            },
            "required": ["threadId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        thread_id = parameters["threadId"].strip()
        url = f"https://api.attio.com/v2/threads/{thread_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                try:
                    resp_data = response.json()
                except:
                    resp_data = {}

                if response.status_code != 200:
                    error_msg = resp_data.get("message", "Failed to get thread")
                    return ToolResult(success=False, output="", error=error_msg)

                t = resp_data.get("data", {})
                comments_raw = t.get("comments", [])
                comments = []
                for c in comments_raw:
                    comment_id = c.get("id", {}).get("comment_id")
                    content_plaintext = c.get("content_plaintext")
                    author_raw = c.get("author")
                    author = None
                    if author_raw:
                        author = {
                            "type": author_raw.get("type"),
                            "id": author_raw.get("id"),
                        }
                    created_at = c.get("created_at")
                    comments.append({
                        "commentId": comment_id,
                        "contentPlaintext": content_plaintext,
                        "author": author,
                        "createdAt": created_at,
                    })

                output_data = {
                    "threadId": t.get("id", {}).get("thread_id"),
                    "comments": comments,
                    "createdAt": t.get("created_at"),
                }

                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")