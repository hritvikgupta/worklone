from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class EvernoteListTagsTool(BaseTool):
    name = "evernote_list_tags"
    description = "List all tags in an Evernote account"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "apiKey": {
                    "type": "string",
                    "description": "Evernote developer token",
                },
            },
            "required": ["apiKey"],
        }

    async def _get_note_store_url(self, client: httpx.AsyncClient, api_key: str) -> str:
        base_url = "https://sandbox.evernote.com" if api_key.startswith("S=") else "https://www.evernote.com"
        userstore_url = f"{base_url}/edam/user"
        headers = {"Content-Type": "application/json"}
        body = {
            "jsonProtocolVersion": 1,
            "request": {
                "method": "UserStore.getNoteStoreUrl",
                "parameters": [{"authenticationToken": api_key}],
            },
        }
        response = await client.post(userstore_url, headers=headers, json=body)
        if response.status_code != 200:
            raise ValueError(f"Failed to get note store URL: {response.text}")
        data = response.json()
        if "badResponse" in data:
            err_data = data["badResponse"]
            error_msg = (
                err_data.get("badData", {}).get("message", "EDAM error")
                if isinstance(err_data.get("badData"), dict)
                else str(err_data)
            )
            raise ValueError(error_msg)
        return data["response"]["result"]["noteStoreUrl"]

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = (parameters.get("apiKey") or "").strip()
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Evernote developer token not configured.")

        headers = {"Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                note_store_url = await self._get_note_store_url(client, api_key)
                body = {
                    "jsonProtocolVersion": 1,
                    "request": {
                        "method": "NoteStore.listTags",
                        "parameters": [{"authenticationToken": api_key}],
                    },
                }
                response = await client.post(note_store_url, headers=headers, json=body)

                if response.status_code != 200:
                    return ToolResult(
                        success=False, output="", error=f"Evernote API error {response.status_code}: {response.text}"
                    )

                data = response.json()
                if "badResponse" in data:
                    err_data = data["badResponse"]
                    error_msg = (
                        err_data.get("badData", {}).get("message", "EDAM error")
                        if isinstance(err_data.get("badData"), dict)
                        else str(err_data)
                    )
                    return ToolResult(success=False, output="", error=error_msg)

                tags = data["response"]["result"]
                result = {"tags": tags}
                return ToolResult(success=True, output=result, data=result)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")