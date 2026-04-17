from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class SixtyfourEnrichLeadTool(BaseTool):
    name = "Sixtyfour Enrich Lead"
    description = "Enrich lead information with contact details, social profiles, and company data using Sixtyfour AI."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
                description="Sixtyfour API key",
                env_var="SIXTYFOUR_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "apiKey": {
                    "type": "string",
                    "description": "Sixtyfour API key",
                },
                "leadInfo": {
                    "type": "string",
                    "description": "Lead information as JSON object with key-value pairs (e.g. name, company, title, linkedin)",
                },
                "struct": {
                    "type": "string",
                    "description": "Fields to collect as JSON object. Keys are field names, values are descriptions (e.g. {\"email\": \"The individual's email address\", \"phone\": \"Phone number\"})",
                },
                "researchPlan": {
                    "type": "string",
                    "description": "Optional research plan to guide enrichment strategy",
                },
            },
            "required": ["apiKey", "leadInfo", "struct"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = (context or {}).get("apiKey")
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Sixtyfour API key not configured.")

        try:
            lead_info = json.loads(parameters["leadInfo"])
        except json.JSONDecodeError as e:
            return ToolResult(success=False, output="", error=f"leadInfo must be valid JSON: {str(e)}")

        try:
            struct = json.loads(parameters["struct"])
        except json.JSONDecodeError as e:
            return ToolResult(success=False, output="", error=f"struct must be valid JSON: {str(e)}")

        body = {
            "lead_info": lead_info,
            "struct": struct,
        }
        research_plan = parameters.get("researchPlan")
        if research_plan:
            body["research_plan"] = research_plan

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }
        url = "https://api.sixtyfour.ai/enrich-lead"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                try:
                    resp_data = response.json()
                except:
                    resp_data = {}

                if response.status_code >= 400:
                    error_msg = (
                        resp_data.get("error")
                        or resp_data.get("message")
                        or resp_data.get("detail")
                        or f"API error: {response.status_code}"
                    )
                    return ToolResult(success=False, output="", error=error_msg)

                output_data = {
                    "notes": resp_data.get("notes"),
                    "structuredData": resp_data.get("structured_data", {}),
                    "references": resp_data.get("references", {}),
                    "confidenceScore": resp_data.get("confidence_score"),
                }
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")