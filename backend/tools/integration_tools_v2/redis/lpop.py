from typing import Dict, Any
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from redis.asyncio import Redis

class RedisLPopTool(BaseTool):
    name = "Redis LPOP"
    description = "Remove and return the first element of a list stored at a key in Redis."
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
            },
            "required": ["url", "key"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        url: str = parameters["url"]
        key: str = parameters["key"]

        try:
            client = Redis.from_url(url)
            result = await client.lpop(key)
            await client.aclose()

            value = result.decode("utf-8") if result else None
            data = {
                "key": key,
                "value": value,
            }
            output = str(value) if value is not None else "null"
            return ToolResult(success=True, output=output, data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Redis error: {str(e)}")