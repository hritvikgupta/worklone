from typing import Dict, Any
import json
from redis.asyncio import Redis
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class RedisKeysTool(BaseTool):
    name = "redis_keys"
    description = "List all keys matching a pattern in Redis. Avoid using on large databases in production; use the Redis Command tool with SCAN for large key spaces."
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
                "pattern": {
                    "type": "string",
                    "description": "Pattern to match keys (default: * for all keys)",
                },
            },
            "required": ["url"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            url = parameters["url"]
            pattern = parameters.get("pattern", "*")
            r = Redis.from_url(url, decode_responses=True)
            keys = await r.keys(pattern)
            result = {
                "pattern": pattern,
                "keys": keys,
                "count": len(keys),
            }
            await r.aclose()
            return ToolResult(
                success=True,
                output=json.dumps(result),
                data=result,
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Redis error: {str(e)}")