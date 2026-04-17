from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from redis.asyncio import Redis
from redis.exceptions import RedisError

class RedisSetTool(BaseTool):
    name = "redis_set"
    description = "Set the value of a key in Redis with an optional expiration time in seconds."
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
                    "description": "The key to set",
                },
                "value": {
                    "type": "string",
                    "description": "The value to store",
                },
                "ex": {
                    "type": "number",
                    "description": "Expiration time in seconds (optional)",
                },
            },
            "required": ["url", "key", "value"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        url = parameters["url"]
        key = parameters["key"]
        value = parameters["value"]
        ex = parameters.get("ex")
        if ex is not None:
            ex = int(ex)

        if self._is_placeholder_url(url):
            return ToolResult(success=False, output="", error="Redis connection URL not configured.")

        try:
            async with Redis.from_url(url, decode_responses=True) as client:
                result = await client.set(key, value, ex=ex)
            result_str = str(result) if result is not None else "OK"
            data = {
                "key": key,
                "result": result_str,
            }
            return ToolResult(success=True, output=result_str, data=data)
        except RedisError as e:
            return ToolResult(success=False, output="", error=f"Redis error: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Unexpected error: {str(e)}")