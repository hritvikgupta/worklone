from typing import Any, Dict
import httpx
import base64
from urllib.parse import quote
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class CursorDownloadArtifactTool(BaseTool):
    name = "cursor_download_artifact"
    description = "Download a generated artifact file from a cloud agent. Returns the file for execution storage."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="cursor_api_key",
                description="Cursor API key",
                env_var="CURSOR_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "cursor",
            context=context,
            context_token_keys=("cursor_api_key",),
            env_token_keys=("CURSOR_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "agentId": {
                    "type": "string",
                    "description": "Unique identifier for the cloud agent (e.g., bc_abc123)",
                },
                "path": {
                    "type": "string",
                    "description": "Absolute path of the artifact to download (e.g., /src/index.ts)",
                },
            },
            "required": ["agentId", "path"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        agent_id = (parameters.get("agentId") or "").strip()
        path = (parameters.get("path") or "").strip()
        
        url = f"https://api.cursor.com/v0/agents/{quote(agent_id)}/artifacts/download?path={quote(path)}"
        
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{access_token}:'.encode('utf-8')).decode('utf-8')}",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code not in [200]:
                    error_text = (await response.aread()).decode('utf-8')
                    error = error_text or f"Failed to get artifact URL ({response.status_code})"
                    return ToolResult(success=False, output="", error=error)
                
                artifact_data = response.json()
                download_url = (
                    artifact_data.get("url")
                    or artifact_data.get("downloadUrl")
                    or artifact_data.get("presignedUrl")
                )
                
                if not download_url:
                    return ToolResult(success=False, output="", error="No download URL returned for artifact")
                
                download_response = await client.get(download_url)
                
                if not download_response.is_success:
                    error_text = (await download_response.aread()).decode('utf-8')
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to download artifact content ({download_response.status_code}: {error_text or download_response.text})",
                    )
                
                content_type = download_response.headers.get("content-type", "application/octet-stream")
                content = await download_response.aread()
                file_name = path.split("/")[-1] or "artifact"
                file_b64 = base64.b64encode(content).decode("utf-8")
                size = len(content)
                
                result_data = {
                    "success": True,
                    "output": {
                        "file": {
                            "name": file_name,
                            "mimeType": content_type,
                            "data": file_b64,
                            "size": size,
                        }
                    },
                }
                
                return ToolResult(
                    success=True,
                    output=f"Downloaded artifact: {file_name}",
                    data=result_data,
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")