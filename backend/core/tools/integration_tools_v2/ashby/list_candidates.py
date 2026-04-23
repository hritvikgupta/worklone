from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyListCandidatesTool(BaseTool):
    name = "ashby_list_candidates"
    description = "Lists all candidates in an Ashby organization with cursor-based pagination."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ASHBY_API_KEY",
                description="Ashby API Key",
                env_var="ASHBY_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        return (context.get("ASHBY_API_KEY") if context else "") or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "cursor": {
                    "type": "string",
                    "description": "Opaque pagination cursor from a previous response nextCursor value",
                },
                "perPage": {
                    "type": "number",
                    "description": "Number of results per page (default 100)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Ashby API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
        }

        body: dict[str, Any] = {}
        cursor = parameters.get("cursor")
        if cursor:
            body["cursor"] = cursor
        per_page = parameters.get("perPage")
        if per_page is not None:
            body["limit"] = per_page

        url = "https://api.ashbyhq.com/candidate.list"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if not data.get("success", False):
                    error_msg = data.get("errorInfo", {}).get("message", "Failed to list candidates")
                    return ToolResult(success=False, output="", error=error_msg)

                candidates = []
                for c in data.get("results", []):
                    primary_email_address = c.get("primaryEmailAddress")
                    pe = None
                    if primary_email_address:
                        pe = {
                            "value": primary_email_address.get("value", ""),
                            "type": primary_email_address.get("type", "Other"),
                            "isPrimary": primary_email_address.get("isPrimary", True),
                        }
                    primary_phone_number = c.get("primaryPhoneNumber")
                    pp = None
                    if primary_phone_number:
                        pp = {
                            "value": primary_phone_number.get("value", ""),
                            "type": primary_phone_number.get("type", "Other"),
                            "isPrimary": primary_phone_number.get("isPrimary", True),
                        }
                    cand = {
                        "id": c.get("id"),
                        "name": c.get("name"),
                        "primaryEmailAddress": pe,
                        "primaryPhoneNumber": pp,
                        "createdAt": c.get("createdAt"),
                        "updatedAt": c.get("updatedAt"),
                    }
                    candidates.append(cand)

                transformed = {
                    "candidates": candidates,
                    "moreDataAvailable": data.get("moreDataAvailable", False),
                    "nextCursor": data.get("nextCursor"),
                }

                output_str = json.dumps(transformed)

                return ToolResult(success=True, output=output_str, data=transformed)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")