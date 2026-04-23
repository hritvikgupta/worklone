from typing import Any, Dict, List, Optional
import httpx
import base64
import json
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class PipedriveGetFilesTool(BaseTool):
    name = "pipedrive_get_files"
    description = "Retrieve files from Pipedrive with optional filters"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PIPEDRIVE_ACCESS_TOKEN",
                description="Access token for the Pipedrive API",
                env_var="PIPEDRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "pipedrive",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("PIPEDRIVE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "sort": {
                    "type": "string",
                    "description": 'Sort files by field (supported: "id", "update_time")',
                },
                "limit": {
                    "type": "string",
                    "description": "Number of results to return (e.g., \"50\", default: 100, max: 100)",
                },
                "start": {
                    "type": "string",
                    "description": "Pagination start offset (0-based index of the first item to return)",
                },
                "downloadFiles": {
                    "type": "boolean",
                    "description": "Download file contents into file outputs",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        base_url = "https://api.pipedrive.com/v1/files"
        query_params: Dict[str, str] = {}
        sort = parameters.get("sort")
        if sort:
            query_params["sort"] = sort
        limit = parameters.get("limit")
        if limit:
            query_params["limit"] = limit
        start = parameters.get("start")
        if start:
            query_params["start"] = start
        query_string = urlencode(query_params)
        url = f"{base_url}?{query_string}" if query_string else base_url
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if not data.get("success", False):
                    return ToolResult(success=False, output="", error=data.get("error", "Failed to fetch files from Pipedrive"))
                
                files: List[Dict[str, Any]] = data.get("data", [])
                pagination = data.get("additional_data", {}).get("pagination", {})
                has_more = pagination.get("more_items_in_collection", False)
                next_start = pagination.get("next_start")
                total_items = len(files)
                
                downloaded_files: List[Dict[str, Any]] = []
                download_files = parameters.get("downloadFiles", False)
                if download_files:
                    for file_info in files:
                        file_url = file_info.get("url")
                        if not file_url:
                            continue
                        try:
                            file_headers = {"Authorization": f"Bearer {access_token}"}
                            file_resp = await client.get(file_url, headers=file_headers)
                            if file_resp.status_code != 200:
                                continue
                            content = await file_resp.aread()
                            b64_data = base64.b64encode(content).decode("utf-8")
                            content_type = file_resp.headers.get("content-type", "application/octet-stream")
                            mime_type = content_type.split(";")[0].strip()
                            file_name = file_info.get("name") or f"pipedrive-file-{file_info.get('id', 'unknown')}"
                            downloaded_files.append({
                                "name": file_name,
                                "mimeType": mime_type,
                                "data": b64_data,
                                "size": len(content),
                            })
                        except Exception:
                            continue
                
                output_data = {
                    "files": files,
                    "total_items": total_items,
                    "has_more": has_more,
                }
                if next_start is not None:
                    output_data["next_start"] = next_start
                if downloaded_files:
                    output_data["downloadedFiles"] = downloaded_files
                output_data["success"] = True
                
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")