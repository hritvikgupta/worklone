from typing import Any, Dict, List, Optional
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XReadTool(BaseTool):
    name = "x_read"
    description = "Read tweet details, including replies and conversation context"
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

    def _transform_tweet(self, tweet: Dict[str, Any], users: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        transformed: Dict[str, Any] = {
            "id": tweet["id"],
            "text": tweet["text"],
            "createdAt": tweet["created_at"],
            "authorId": tweet.get("author_id"),
            "conversationId": tweet.get("conversation_id"),
            "inReplyToUserId": tweet.get("in_reply_to_user_id"),
            "publicMetrics": tweet.get("public_metrics", {}),
        }
        if users and transformed["authorId"] in users:
            transformed["author"] = users[transformed["authorId"]]
        return transformed

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "tweetId": {
                    "type": "string",
                    "description": "ID of the tweet to read (e.g., 1234567890123456789)",
                },
                "includeReplies": {
                    "type": "boolean",
                    "description": "Whether to include replies to the tweet",
                },
            },
            "required": ["tweetId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        tweet_id = parameters["tweetId"]
        include_replies = parameters.get("includeReplies", False)

        expansions = (
            "author_id,"
            "in_reply_to_user_id,"
            "referenced_tweets.id,"
            "referenced_tweets.id.author_id,"
            "attachments.media_keys,"
            "attachments.poll_ids"
        )
        tweet_fields = (
            "created_at,"
            "conversation_id,"
            "in_reply_to_user_id,"
            "attachments,"
            "context_annotations,"
            "public_metrics"
        )
        user_fields = (
            "name,"
            "username,"
            "description,"
            "profile_image_url,"
            "verified,"
            "public_metrics"
        )

        url = f"https://api.twitter.com/2/tweets/{tweet_id}"
        params: Dict[str, str] = {
            "expansions": expansions,
            "tweet.fields": tweet_fields,
            "user.fields": user_fields,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)

                if not 200 <= response.status_code < 300:
                    return ToolResult(
                        success=False, output="", error=f"HTTP {response.status_code}: {response.text}"
                    )

                data = response.json()

                if "errors" in data and not data.get("data"):
                    error_msg = (
                        data["errors"][0].get("detail")
                        or data["errors"][0].get("message")
                        or "Failed to fetch tweet"
                    )
                    return ToolResult(success=False, output="", error=error_msg)

                includes = data.get("includes", {})
                users = {user["id"]: user for user in includes.get("users", [])}
                main_tweet_raw = data["data"]
                main_tweet = self._transform_tweet(main_tweet_raw, users)

                context: Dict[str, Dict[str, Any]] = {}
                referenced_tweets = main_tweet_raw.get("referenced_tweets", [])
                parent_ref = next((ref for ref in referenced_tweets if ref.get("type") == "replied_to"), None)
                if parent_ref:
                    parent_tweets = includes.get("tweets", [])
                    parent_raw = next((t for t in parent_tweets if t["id"] == parent_ref["id"]), None)
                    if parent_raw:
                        context["parentTweet"] = self._transform_tweet(parent_raw, users)

                quoted_ref = next((ref for ref in referenced_tweets if ref.get("type") == "quoted"), None)
                if not parent_ref and quoted_ref:
                    parent_tweets = includes.get("tweets", [])
                    quoted_raw = next((t for t in parent_tweets if t["id"] == quoted_ref["id"]), None)
                    if quoted_raw:
                        context["rootTweet"] = self._transform_tweet(quoted_raw, users)

                replies: List[Dict[str, Any]] = []
                if include_replies:
                    conversation_id = main_tweet.get("conversationId") or main_tweet["id"]
                    search_params: Dict[str, str] = {
                        "query": f"conversation_id:{conversation_id}",
                        "expansions": "author_id,referenced_tweets.id",
                        "tweet.fields": "created_at,conversation_id,in_reply_to_user_id,public_metrics",
                        "max_results": "100",
                    }
                    try:
                        replies_response = await client.get(
                            "https://api.twitter.com/2/tweets/search/recent",
                            headers=headers,
                            params=search_params,
                        )
                        if 200 <= replies_response.status_code < 300:
                            replies_data = replies_response.json()
                            if "data" in replies_data:
                                replies_raw = [
                                    tweet for tweet in replies_data["data"] if tweet["id"] != main_tweet["id"]
                                ]
                                replies_includes = replies_data.get("includes", {})
                                replies_users = {
                                    user["id"]: user for user in replies_includes.get("users", [])
                                }
                                replies = [
                                    self._transform_tweet(tweet, replies_users) for tweet in replies_raw
                                ]
                    except Exception:
                        pass  # replies remain empty

                processed: Dict[str, Any] = {"tweet": main_tweet}
                if replies:
                    processed["replies"] = replies
                if context:
                    processed["context"] = context

                output_str = json.dumps(processed, indent=2)
                return ToolResult(success=True, output=output_str, data=processed)

        except httpx.RequestError as e:
            return ToolResult(success=False, output="", error=f"Request error: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")