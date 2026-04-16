from typing import Any, Dict
import redis.asyncio as aioredis
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class RedisLPushTool(BaseTool):
    name = "redis_lpush"
    description = "Prepend a value to a list stored at a key in Redis."
    category = "integration"

    @staticmethod
    def _is_placeholder_url(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("redis://your-") or "replace-me" in normalized

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
                    "description": "The list key",
                },
                "value": {
                    "type": "string",
                    "description": "The value to prepend",
                },
            },
            "required": ["url", "key", "value"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        url = parameters["url"]
        key = parameters["key"]
        value = parameters["value"]

        if self._is_placeholder_url(url):
            return ToolResult(success=False, output="", error="Redis connection URL not configured.")

        try:
            r = aioredis.from_url(url)
            length = await r.lpush(key, value)
            await r.aclose()
            return ToolResult(
                success=True,
                output=str(length),
                data={
                    "key": key,
                    "length": int(length),
                },
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Redis error: {str(e)}")