from typing import Any, Dict
import redis.asyncis as aioredis
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class RedisHgetTool(BaseTool):
    name = "redis_hget"
    description = "Get the value of a field in a hash stored at a key in Redis."
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Redis connection URL (e.g. redis