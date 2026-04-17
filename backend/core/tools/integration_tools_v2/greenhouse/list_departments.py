from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GreenhouseListDepartmentsTool(BaseTool):
    name = "greenhouse_list_departments"
    description = "Lists all departments configured in Greenhouse"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GREENHOUSE_API_KEY",
                description="Greenhouse Harvest API key",
                env_var="GREENHOUSE_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "per_page": {
                    "type": "number",
                    "description": "Number of results per page (1-500, default 100)",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("GREENHOUSE_API_KEY") if context else None
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Greenhouse API key not configured.")

        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode()).decode()}",
            "Content-Type": "application/json",
        }

        url = "https://harvest.greenhouse.io/v1/departments"
        query_params = {}
        per_page = parameters.get("per_page")
        if per_page is not None:
            query_params["per_page"] = per_page
        page = parameters.get("page")
        if page is not None:
            query_params["page"] = page

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code == 200:
                    data = response.json()
                    departments = []
                    if isinstance(data, list):
                        for d in data:
                            dept = {
                                "id": int(d.get("id") or 0),
                                "name": d.get("name"),
                                "parent_id": int(d.get("parent_id")) if d.get("parent_id") is not None else None,
                                "child_ids": [int(cid) for cid in d.get("child_ids", [])],
                                "external_id": d.get("external_id"),
                            }
                            departments.append(dept)
                    output = {"departments": departments, "count": len(departments)}
                    return ToolResult(success=True, output=str(output), data=output)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")