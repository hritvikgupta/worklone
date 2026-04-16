from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftPlannerUpdateBucketTool(BaseTool):
    name = "microsoft_planner_update_bucket"
    description = "Update a bucket in Microsoft Planner"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_PLANNER_ACCESS_TOKEN",
                description="Access token for the Microsoft Planner API",
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
                    "description": 'The ID of the bucket to update (e.g., "hsOf2dhOJkC6Fey9VjDg1JgAC9Rq")',
                },
                "name": {
                    "type": "string",
                    "description": "The new name of the bucket",
                },
                "etag": {
                    "type": "string",
                    "description": "The ETag value from the bucket to update (If-Match header)",
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
            return ToolResult(success=False, output="", error="Bucket ID is required")
        
        etag = parameters.get("etag")
        if not etag:
            return ToolResult(success=False, output="", error="ETag is required for update operations")
        
        cleaned_etag = etag.strip()
        while cleaned_etag.startswith('"') and cleaned_etag.endswith('"'):
            cleaned_etag = cleaned_etag[1:-1]
        if '\\"' in cleaned_etag:
            cleaned_etag = cleaned_etag.replace('\\"', '"')
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "If-Match": cleaned_etag,
        }
        
        body: Dict[str, Any] = {}
        name = parameters.get("name")
        if name:
            body["name"] = name
        
        if not body:
            return ToolResult(success=False, output="", error="At least one field must be provided to update")
        
        url = f"https://graph.microsoft.com/v1.0/planner/buckets/{bucket_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")