from typing import Any, Dict
import httpx
import base64
import re
import urllib.parse
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XUserTool(BaseTool):
    name = "x_user"
    description = "Get user profile information"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="X_ACCESS_TOKEN",
                description="X OAuth access token",
                env_var="X_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "x",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("X_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _transform_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        metrics = user_data.get("public_metrics", {})
        return {
            "id": user_data["id"],
            "username": user_data["username"],
            "name": user_data["name"],
            "description": user_data.get("description"),
            "verified": user_data.get("verified", False),
            "metrics": {
                "followersCount": metrics.get("followers_count", 0),
                "followingCount": metrics.get("following_count", 0),
                "tweetCount": metrics.get("tweet_count", 0),
            },
        }

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Username to look up without @ symbol (e.g., elonmusk, openai)",
                },
            },
            "required": ["username"],
        }

    async def execute(self, parameters: Dict[str, Any], context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        username = parameters["username"]
        username_encoded = urllib.parse.quote(username)
        user_fields = "description,profile_image_url,verified,public_metrics"
        url = f"https://api.twitter.com/2/users/by/username/{username_encoded}?user.fields={user_fields}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, headers=headers)

                if resp.status_code == 429:
                    reset_time = resp.headers.get("x-rate-limit-reset")
                    if reset_time:
                        try:
                            reset_dt = datetime.fromtimestamp(int(reset_time))
                            time_str = reset_dt.strftime("%H:%M:%S")
                            err = f"Rate limit exceeded. Please try again after {time_str}."
                        except ValueError:
                            err = "X API rate limit exceeded. Please try again later."
                    else:
                        err = "X API rate limit exceeded. Please try again later."
                    return ToolResult(success=False, output="", error=err)

                if not 200 <= resp.status_code < 300:
                    return ToolResult(success=False, output="", error=f"HTTP {resp.status_code}: {resp.text}")

                data = resp.json()

                if not isinstance(data, dict) or "data" not in data:
                    return ToolResult(success=False, output="", error="Invalid response format from X API")

                if data.get("errors"):
                    error = data["errors"][0]
                    detail = error.get("detail", "")
                    cleaned_message = re.sub(r"\[(.*?)\]", r"\1", detail)
                    err_msg = f"X API error: {cleaned_message or error.get('message') or str(error)}"
                    return ToolResult(success=False, output="", error=err_msg)

                user_data = data["data"]
                user = self._transform_user(user_data)
                return ToolResult(success=True, output=str({"user": user}), data={"user": user})

        except httpx.RequestError as e:
            return ToolResult(success=False, output="", error=f"Request error: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")