from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class RedditSubmitPostTool(BaseTool):
    name = "reddit_submit_post"
    description = "Submit a new post to a subreddit (text or link)"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def _normalize_subreddit(self, subreddit: str) -> str:
        subreddit = subreddit.strip()
        if subreddit.startswith("r/"):
            subreddit = subreddit[2:]
        return subreddit.lower()

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
            context_token_keys=("accessToken",),
            env_token_keys=("REDDIT_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "subreddit": {
                    "type": "string",
                    "description": 'The subreddit to post to (e.g., "technology", "programming")',
                },
                "title": {
                    "type": "string",
                    "description": 'Title of the submission (e.g., "Check out this new AI tool"). Max 300 characters',
                },
                "text": {
                    "type": "string",
                    "description": 'Text content for a self post in markdown format (e.g., "This is the **body** of my post")',
                },
                "url": {
                    "type": "string",
                    "description": "URL for a link post (cannot be used with text)",
                },
                "nsfw": {
                    "type": "boolean",
                    "description": "Mark post as NSFW",
                },
                "spoiler": {
                    "type": "boolean",
                    "description": "Mark post as spoiler",
                },
                "send_replies": {
                    "type": "boolean",
                    "description": "Send reply notifications to inbox (default: true)",
                },
                "flair_id": {
                    "type": "string",
                    "description": "Flair template UUID for the post (max 36 characters)",
                },
                "flair_text": {
                    "type": "string",
                    "description": "Flair text to display on the post (max 64 characters)",
                },
                "collection_id": {
                    "type": "string",
                    "description": "Collection UUID to add the post to",
                },
            },
            "required": ["subreddit", "title"],
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

        url = "https://oauth.reddit.com/api/submit"

        form_data: Dict[str, str] = {
            "sr": self._normalize_subreddit(parameters["subreddit"]),
            "title": parameters["title"],
            "api_type": "json",
        }

        text = parameters.get("text")
        url_ = parameters.get("url")
        if text is not None:
            form_data["kind"] = "self"
            form_data["text"] = text
        elif url_ is not None:
            form_data["kind"] = "link"
            form_data["url"] = url_
        else:
            form_data["kind"] = "self"
            form_data["text"] = ""

        if "nsfw" in parameters:
            form_data["nsfw"] = str(parameters["nsfw"]).lower()
        if "spoiler" in parameters:
            form_data["spoiler"] = str(parameters["spoiler"]).lower()
        if "send_replies" in parameters:
            form_data["sendreplies"] = str(parameters["send_replies"]).lower()
        if parameters.get("flair_id"):
            form_data["flair_id"] = parameters["flair_id"]
        if parameters.get("flair_text"):
            form_data["flair_text"] = parameters["flair_text"]
        if parameters.get("collection_id"):
            form_data["collection_id"] = parameters["collection_id"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=form_data)

                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()
                json_data = data.get("json", {})
                errors = json_data.get("errors")
                if errors and len(errors) > 0:
                    error_msg = ", ".join(": ".join(str(e) for e in err) for err in errors)
                    return ToolResult(success=False, output="", error=f"Failed to submit post: {error_msg}")

                post_data = json_data.get("data", {})
                permalink = post_data.get("permalink")
                perm_url = f"https://www.reddit.com{permalink}" if permalink else post_data.get("url", "")
                output_data = {
                    "id": post_data.get("id"),
                    "name": post_data.get("name"),
                    "url": post_data.get("url"),
                    "permalink": perm_url,
                }
                structured_output = {
                    "success": True,
                    "message": "Post submitted successfully",
                    "data": output_data,
                }
                return ToolResult(success=True, output="Post submitted successfully", data=structured_output)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")