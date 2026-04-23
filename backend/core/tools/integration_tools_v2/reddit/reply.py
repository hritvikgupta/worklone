from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class RedditReplyTool(BaseTool):
    name = "reddit_reply"
    description = "Add a comment reply to a Reddit post or comment"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="REDDIT_ACCESS_TOKEN",
                description="Access token",
                env_var="REDDIT_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "reddit",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("REDDIT_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "parent_id": {
                    "type": "string",
                    "description": 'Thing fullname to reply to (e.g., "t3_abc123" for post, "t1_def456" for comment)',
                },
                "text": {
                    "type": "string",
                    "description": 'Comment text in markdown format (e.g., "Great post! Here is my **reply**")',
                },
                "return_rtjson": {
                    "type": "boolean",
                    "description": "Return response in Rich Text JSON format",
                },
            },
            "required": ["parent_id", "text"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "sim-studio/1.0 (https://github.com/simstudioai/sim)",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        url = "https://oauth.reddit.com/api/comment"
        
        body = {
            "thing_id": parameters["parent_id"],
            "text": parameters["text"],
            "api_type": "json",
        }
        return_rtjson = parameters.get("return_rtjson")
        if return_rtjson is not None:
            body["return_rtjson"] = str(return_rtjson).lower()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=body)
                
                data = response.json() if response.content else {}
                
                if response.status_code not in [200, 201, 204]:
                    error_msg = data.get("message", f"HTTP error {response.status_code}")
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to post reply: {error_msg}",
                    )
                
                json_data = data.get("json", {})
                if json_data.get("errors") and len(json_data["errors"]) > 0:
                    errors = ", ".join(": ".join(str(e) for e in err) for err in json_data["errors"])
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to post reply: {errors}",
                    )
                
                comment_data = (
                    json_data.get("data", {})
                    .get("things", [{}])[0]
                    .get("data", {})
                )
                id_ = comment_data.get("id")
                name = comment_data.get("name")
                permalink = (
                    f"https://www.reddit.com{comment_data.get('permalink')}"
                    if comment_data.get("permalink")
                    else None
                )
                body_text = comment_data.get("body")
                
                output_data = {
                    "success": True,
                    "message": "Reply posted successfully",
                    "data": {
                        "id": id_,
                        "name": name,
                        "permalink": permalink,
                        "body": body_text,
                    },
                }
                return ToolResult(
                    success=True,
                    output="Reply posted successfully",
                    data=output_data,
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")