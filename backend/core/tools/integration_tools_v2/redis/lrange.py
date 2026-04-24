from typing import Dict, Any, List
import json
import redis.asyncio
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class RedisLRangeTool(BaseTool):
    name = "redis_lrange"
    description = "Get a range of elements from a list stored at a key in Redis."
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
                    "description": "The list key",
                },
                "start": {
                    "type": "number",
                    "description": "Start index (0-based)",
                },
                "stop": {
                    "type": "number",
                    "description": "Stop index (-1 for all elements)",
                },
            },
            "required": ["url", "key", "start", "stop"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            url: str = parameters["url"]
            key: str = parameters["key"]
            start: int = int(parameters["start"])
            stop: int = int(parameters["stop"])

            client = redis.asyncio.Redis.from_url(
                url,
                decode_responses=True,
                socket_connect_timeout=30.0,
                socket_timeout=30.0,
            )

            values: list[str] = await client.lrange(key, start, stop)
            await client.aclose()

            result = {
                "key": key,
                "values": values,
                "count": len(values),
            }

            return ToolResult(
                success=True,
                output=json.dumps(result),
                data=result,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Redis error: {str(e)}",
            )