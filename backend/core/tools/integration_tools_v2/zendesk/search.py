from typing import Any, Dict
import httpx
import base64
from urllib.parse import urlencode, urlparse, parse_qs
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskSearchTool(BaseTool):
    name = "zendesk_search"
    description = "Unified search across tickets, users, and organizations in Zendesk"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="zendesk_email",
                description="Your Zendesk email address",
                env_var="ZENDESK_EMAIL",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="zendesk_api_token",
                description="Zendesk API token",
                env_var="ZENDESK_API_TOKEN",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="zendesk_subdomain",
                description="Your Zendesk subdomain",
                env_var="ZENDESK_SUBDOMAIN",
                required=True,
                auth_type="api_key",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": 'Search query string using Zendesk search syntax (e.g., "type:ticket status:open")',
                },
                "filterType": {
                    "type": "string",
                    "description": 'Resource type to search for: "ticket", "user", "organization", or "group"',
                },
                "perPage": {
                    "type": "string",
                    "description": 'Results per page as a number string (default: "100", max: "100")',
                },
                "pageAfter": {
                    "type": "string",
                    "description": 'Cursor from a previous response to fetch the next page of results',
                },
            },
            "required": ["query", "filterType"],
        }

    def _extract_paging(self, data: Dict[str, Any]) -> Dict[str, Any]:
        next_page = data.get("next_page")
        after_cursor = None
        if next_page:
            parsed = urlparse(next_page)
            qs = parse_qs(parsed.query)
            after_cursor = qs.get("page_after", [None])[0]
        return {
            "after_cursor": after_cursor,
            "has_more": data.get("has_more", False),
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        email = context.get("zendesk_email") if context else None
        api_token = context.get("zendesk_api_token") if context else None
        subdomain = context.get("zendesk_subdomain") if context else None

        if (
            self._is_placeholder_token(email)
            or self._is_placeholder_token(api_token)
            or self._is_placeholder_token(subdomain)
        ):
            return ToolResult(success=False, output="", error="Zendesk credentials not configured.")

        credentials_str = f"{email}/token:{api_token}"
        auth_b64 = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
        }

        query = parameters["query"]
        filter_type = parameters["filterType"]
        per_page = parameters.get("perPage")
        page_after = parameters.get("pageAfter")

        params_dict: Dict[str, str] = {
            "query": query,
            "filter[type]": filter_type,
        }
        if per_page:
            params_dict["per_page"] = per_page
        if page_after:
            params_dict["page_after"] = page_after

        query_string = urlencode(params_dict)
        url = f"https://{subdomain}.zendesk.com/api/v2/search/export?{query_string}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    data: Dict[str, Any] = response.json()
                    results = data.get("results", [])
                    paging = self._extract_paging(data)
                    output_data = {
                        "results": results,
                        "paging": paging,
                        "metadata": {
                            "total_returned": len(results),
                            "has_more": paging["has_more"],
                        },
                        "success": True,
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    try:
                        error_data = response.json()
                    except Exception:
                        error_data = response.text
                    return ToolResult(
                        success=False, output="", error=str(error_data)
                    )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")