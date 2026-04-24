from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongGetFolderContentTool(BaseTool):
    name = "gong_get_folder_content"
    description = "Retrieve the list of calls in a specific library folder from Gong."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="gong_access_key",
                description="Gong API Access Key",
                env_var="GONG_ACCESS_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="gong_access_key_secret",
                description="Gong API Access Key Secret",
                env_var="GONG_ACCESS_KEY_SECRET",
                required=True,
                auth_type="api_key",
            ),
        ]

    def _get_gong_credentials(self, context: Dict[str, Any] | None) -> tuple[str, str]:
        ctx = context or {}
        return ctx.get("gong_access_key", ""), ctx.get("gong_access_key_secret", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "folderId": {
                    "type": "string",
                    "description": "The library folder ID to retrieve content for",
                },
            },
            "required": ["folderId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_key, access_key_secret = self._get_gong_credentials(context)

        if self._is_placeholder_token(access_key) or self._is_placeholder_token(access_key_secret):
            return ToolResult(success=False, output="", error="Gong credentials not configured.")

        auth_str = base64.b64encode(f"{access_key}:{access_key_secret}".encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Basic {auth_str}",
            "Content-Type": "application/json",
        }

        url = f"https://api.gong.io/v2/library/folder-content?folderId={parameters['folderId']}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output=response.text, error="Invalid JSON response")

                if response.status_code not in [200, 201, 204]:
                    error_msg = "Failed to get folder content"
                    errors = data.get("errors")
                    if isinstance(errors, list) and errors:
                        error_msg = errors[0].get("message", error_msg)
                    elif isinstance(data.get("message"), str):
                        error_msg = data["message"]
                    return ToolResult(success=False, output=response.text, error=error_msg)

                calls = []
                for c in data.get("calls", []):
                    snippet = None
                    snippet_data = c.get("snippet")
                    if snippet_data:
                        snippet = {
                            "fromSec": snippet_data.get("fromSec"),
                            "toSec": snippet_data.get("toSec"),
                        }
                    calls.append({
                        "id": c.get("id", ""),
                        "title": c.get("title"),
                        "note": c.get("note"),
                        "addedBy": c.get("addedBy"),
                        "created": c.get("created"),
                        "url": c.get("url"),
                        "snippet": snippet,
                    })

                transformed = {
                    "folderId": data.get("id"),
                    "folderName": data.get("name"),
                    "createdBy": data.get("createdBy"),
                    "updated": data.get("updated"),
                    "calls": calls,
                }

                return ToolResult(success=True, output=json.dumps(transformed), data=transformed)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")