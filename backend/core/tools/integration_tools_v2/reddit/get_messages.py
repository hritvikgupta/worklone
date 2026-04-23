from typing import Any, Dict
import httpx
import json
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class RedditGetMessagesTool(BaseTool):
    name = "reddit_get_messages"
    description = "Retrieve private messages from your Reddit inbox"
    category = "integration"

    ALLOWED_MESSAGE_FOLDERS = [
        "inbox",
        "unread",
        "sent",
        "messages",
        "comments",
        "selfreply",
        "mentions",
    ]

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="REDDIT_ACCESS_TOKEN",
                description="Access token for Reddit API",
                env_var="REDDIT_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "reddit",
            context=context,
            context_token_keys=("access_token",),
            env_token_keys=("REDDIT_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        children = data.get("data", {}).get("children", [])
        messages = []
        for child in children:
            msg = child.get("data", {}) if isinstance(child, dict) else {}
            messages.append({
                "id": msg.get("id", ""),
                "name": msg.get("name", ""),
                "author": msg.get("author", ""),
                "dest": msg.get("dest", ""),
                "subject": msg.get("subject", ""),
                "body": msg.get("body", ""),
                "created_utc": msg.get("created_utc", 0),
                "new": msg.get("new", False),
                "was_comment": msg.get("was_comment", False),
                "context": msg.get("context", ""),
                "distinguished": msg.get("distinguished"),
            })
        return {
            "messages": messages,
            "after": data.get("data", {}).get("after"),
            "before": data.get("data", {}).get("before"),
        }

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "where": {
                    "type": "string",
                    "description": 'Message folder to retrieve: "inbox" (all), "unread", "sent", "messages" (direct messages only), "comments" (comment replies), "selfreply" (self-post replies), or "mentions" (username mentions). Default: "inbox"',
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of messages to return (e.g., 25). Default: 25, max: 100",
                },
                "after": {
                    "type": "string",
                    "description": "Fullname of a thing to fetch items after (for pagination)",
                },
                "before": {
                    "type": "string",
                    "description": "Fullname of a thing to fetch items before (for pagination)",
                },
                "mark": {
                    "type": "boolean",
                    "description": "Whether to mark fetched messages as read",
                },
                "count": {
                    "type": "number",
                    "description": "A count of items already seen in the listing (used for numbering)",
                },
                "show": {
                    "type": "string",
                    "description": 'Show items that would normally be filtered (e.g., "all")',
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        where = parameters.get("where", "inbox")
        if where not in self.ALLOWED_MESSAGE_FOLDERS:
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid 'where' value: {where}. Must be one of {self.ALLOWED_MESSAGE_FOLDERS}",
            )
        
        limit_raw = parameters.get("limit", 25)
        limit = min(max(1, int(limit_raw)), 100)
        
        params_dict: Dict[str, str] = {
            "limit": str(limit),
            "raw_json": "1",
        }
        
        for key in ("after", "before", "show"):
            value = parameters.get(key)
            if value is not None:
                params_dict[key] = str(value)
        
        mark = parameters.get("mark")
        if mark is not None:
            params_dict["mark"] = "true" if bool(mark) else "false"
        
        count = parameters.get("count")
        if count is not None:
            params_dict["count"] = str(int(count))
        
        query_string = urllib.parse.urlencode(params_dict)
        url = f"https://oauth.reddit.com/message/{where}?{query_string}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "sim-studio/1.0 (https://github.com/simstudioai/sim)",
            "Accept": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    raw_data = response.json()
                    output_data = self._transform(raw_data)
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_data),
                        data=output_data,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")