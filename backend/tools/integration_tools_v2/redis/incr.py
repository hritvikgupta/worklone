from typing import Any, Dict
import redis.asyncio as aioredis
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class RedisIncrTool(BaseTool):
    name = "redis_incr"
    description = "Increment the integer value of a key by one in Redis."
    category = "integration"

    @staticmethod
    def _is_placeholder_url(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Redis connection URL (e.g. redis://user:password@host:port)",
                },
                "key": {
                    "type": "string",
                    "description": "The key to increment",
                },
            },
            "required": ["url", "key"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        url = parameters.get("url", "")
        key = parameters.get("key", "")

        if self._is_placeholder_url(url):
            return ToolResult(success=False, output="", error="Redis connection URL not configured.")

        if not url or not key:
            return ToolResult(success=False, output="", error="Missing required parameters: url or key.")

        try:
            client = aioredis.from_url(url)
            value = await client.incr(key)
            await client.aclose()

            return ToolResult(
                success=True,
                output=str(value),
                data={
                    "key": key,
                    "value": int(value),
                },
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Redis error: {str(e)}")