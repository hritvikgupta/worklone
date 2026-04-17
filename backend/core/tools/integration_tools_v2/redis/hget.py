import json

from redis.asyncio import Redis

from backend.core.tools.system_tools.base import BaseTool, CredentialRequirement, ToolResult


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
                    "description": "Redis connection URL (e.g. redis://user:password@host:port)",
                },
                "key": {
                    "type": "string",
                    "description": "The hash key",
                },
                "field": {
                    "type": "string",
                    "description": "The field name to retrieve",
                },
            },
            "required": ["url", "key", "field"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        url = parameters["url"]
        key = parameters["key"]
        field = parameters["field"]

        try:
            async with Redis.from_url(url, decode_responses=True) as client:
                value = await client.hget(key, field)

            data = {
                "key": key,
                "field": field,
                "value": value,
            }
            output = json.dumps(data)
            return ToolResult(success=True, output=output, data=data)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Redis error: {str(e)}")
