from typing import Any, Dict
from redis.asyncio import Redis
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class RedisExpireTool(BaseTool):
    name = "redis_expire"
    description = "Set an expiration time (in seconds) on a key in Redis."
    category = "integration"

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
                    "description": "The key to set expiration on",
                },
                "seconds": {
                    "type": "number",
                    "description": "Timeout in seconds",
                },
            },
            "required": ["url", "key", "seconds"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        url: str = parameters["url"]
        key: str = parameters["key"]
        seconds: int = int(parameters["seconds"])

        try:
            r = Redis.from_url(url, decode_responses=True)
            async with r:
                result = await r.expire(key, seconds)

            return ToolResult(
                success=True,
                output=f"Expiration set on key '{key}': {result}",
                data={
                    "key": key,
                    "result": result,
                },
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))