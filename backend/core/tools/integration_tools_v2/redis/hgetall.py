from typing import Any, Dict
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from redis.asyncio import Redis

class RedisHGetAllTool(BaseTool):
    name = "redis_hgetall"
    description = "Get all fields and values of a hash stored at a key in Redis."
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
                    "description": "The hash key",
                },
            },
            "required": ["url", "key"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        url: str = parameters["url"]
        key: str = parameters["key"]
        try:
            async with Redis.from_url(url, decode_responses=True) as client:
                fields: Dict[str, str] = await client.hgetall(key)
            field_count: int = len(fields)
            data = {
                "key": key,
                "fields": fields,
                "fieldCount": field_count,
            }
            output = json.dumps(data)
            return ToolResult(success=True, output=output, data=data)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))