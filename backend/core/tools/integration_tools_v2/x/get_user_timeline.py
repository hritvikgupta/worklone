from typing import Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XGetUserTimelineTool(BaseTool):
    name = "x_get_user_timeline"
    description = "Get the reverse chronological home timeline for the authenticated user"
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
            context_token_keys=("access_token",),
            env_token_keys=("X_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "userId": {
                    "type": "string",
                    "description": "The authenticated user ID",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of results (1-100, default 10)",
                },
                "paginationToken": {
                    "type": "string",
                    "description": "Pagination token for next page of results",
                },
                "startTime": {
                    "type": "string",
                    "description": "Oldest UTC timestamp in ISO 8601 format",
                },
                "endTime": {
                    "type": "string",
                    "description": "Newest UTC timestamp in ISO 8601 format",
                },
                "sinceId": {
                    "type": "string",
                    "description": "Returns tweets with ID greater than this",
                },
                "untilId": {
                    "type": "string",
                    "description": "Returns tweets with ID less than this",
                },
                "exclude": {
                    "type": "string",
                    "description": "Comma-separated types to exclude: \"retweets\", \"replies\"",
                },
            },
            "required": ["userId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        user_id = parameters["userId"].strip()
        url = f"https://api.x.com/2/users/{user_id}/timelines/reverse_chronological"
        
        query_params: dict[str, str] = {
            "expansions": "author_id,referenced_tweets.id,attachments.media_keys,attachments.poll_ids",
            "tweet.fields": "created_at,conversation_id,in_reply_to_user_id,attachments,context_annotations,public_metrics",
            "user.fields": "name,username,description,profile_image_url,verified,public_metrics",
        }
        
        max_results = parameters.get("maxResults")
        if max_results is not None:
            try:
                mr = int(max_results)
                mr = max(1, min(100, mr))
                query_params["max_results"] = str(mr)
            except (ValueError, TypeError):
                pass
        
        pagination_token = parameters.get("paginationToken")
        if pagination_token:
            query_params["pagination_token"] = pagination_token
        
        start_time = parameters.get("startTime")
        if start_time:
            query_params["start_time"] = start_time
        
        end_time = parameters.get("endTime")
        if end_time:
            query_params["end_time"] = end_time
        
        since_id = parameters.get("sinceId")
        if since_id:
            query_params["since_id"] = since_id
        
        until_id = parameters.get("untilId")
        if until_id:
            query_params["until_id"] = until_id
        
        exclude = parameters.get("exclude")
        if exclude:
            query_params["exclude"] = exclude
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code >= 400:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if "data" not in data or not isinstance(data["data"], list):
                    error_detail = "No timeline data found or invalid response"
                    if "errors" in data and data["errors"]:
                        error_detail = data["errors"][0].get("detail", error_detail)
                    elif "title" in data:
                        error_detail = data["title"]
                    return ToolResult(success=False, output="", error=error_detail)
                
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")