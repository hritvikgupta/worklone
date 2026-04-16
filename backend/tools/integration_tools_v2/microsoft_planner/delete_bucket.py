from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftPlannerDeleteBucketTool(BaseTool):
    name = "microsoft_planner_delete_bucket"
    description = "Delete a bucket from Microsoft Planner"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def _clean_etag(self, etag: str) -> str:
        cleaned = etag.strip()
        while cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]
        cleaned = cleaned.replace('\\"', '"')
        return cleaned

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_PLANNER_ACCESS_TOKEN",
                description="Access token for Microsoft Planner API",
                env_var="MICROSOFT_PLANNER_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-planner",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("MICROSOFT_PLANNER_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "bucketId": {
                    "type": "string",
                    "description": "The ID of the bucket to delete (e.g., \"hsOf2dhOJkC6Fey9VjDg1JgAC9Rq\")",
                },
                "etag": {
                    "type": "string",
                    "description": "The ETag value from the bucket to delete (If-Match header)",
                },
            },
            "required": ["bucketId", "etag"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        bucket_id = parameters.get("bucketId")
        if not bucket_id:
            return ToolResult(success=False, output="", error="Bucket ID is required.")
        
        etag = parameters.get("etag")
        if not etag:
            return ToolResult(success=False, output="", error="ETag is required.")
        
        cleaned_etag = self._clean_etag(etag)
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "If-Match": cleaned_etag,
        }
        
        url = f"https://graph.microsoft.com/v1.0/planner/buckets/{bucket_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 204]:
                    return ToolResult(
                        success=True,
                        output="Bucket deleted successfully",
                        data={"deleted": True, "metadata": {}},
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")