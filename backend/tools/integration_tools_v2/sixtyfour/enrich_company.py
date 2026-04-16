from typing import Any, Dict
import httpx
import json
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class SixtyfourEnrichCompanyTool(BaseTool):
    name = "sixtyfour_enrich_company"
    description = "Enrich company data with additional information and find associated people using Sixtyfour AI."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SIXTYFOUR_API_KEY",
                description="Sixtyfour API key",
                env_var="SIXTYFOUR_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _resolve_api_key(self, context: dict | None) -> str:
        api_key = None
        if context:
            api_key = context.get("SIXTYFOUR_API_KEY") or context.get("apiKey")
        if not api_key:
            api_key = os.getenv("SIXTYFOUR_API_KEY")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "targetCompany": {
                    "type": "string",
                    "description": 'Company data as JSON object (e.g. {"name": "Acme Inc", "domain": "acme.com"})',
                },
                "struct": {
                    "type": "string",
                    "description": 'Fields to collect as JSON object. Keys are field names, values are descriptions (e.g. {"website": "Company website URL", "num_employees": "Employee count"})',
                },
                "findPeople": {
                    "type": "boolean",
                    "description": "Whether to find people associated with the company",
                },
                "fullOrgChart": {
                    "type": "boolean",
                    "description": "Whether to retrieve the full organizational chart",
                },
                "researchPlan": {
                    "type": "string",
                    "description": "Optional strategy describing how the agent should search for information",
                },
                "peopleFocusPrompt": {
                    "type": "string",
                    "description": "Description of people to find (roles, responsibilities)",
                },
                "leadStruct": {
                    "type": "string",
                    "description": "Custom schema for returned lead data as JSON object",
                },
            },
            "required": ["targetCompany", "struct"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")

        target_company_str = parameters.get("targetCompany")
        if not target_company_str:
            return ToolResult(success=False, output="", error="targetCompany is required.")
        try:
            target_company = json.loads(target_company_str)
        except json.JSONDecodeError:
            return ToolResult(success=False, output="", error="targetCompany must be valid JSON")

        struct_str = parameters.get("struct")
        if not struct_str:
            return ToolResult(success=False, output="", error="struct is required.")
        try:
            struct = json.loads(struct_str)
        except json.JSONDecodeError:
            return ToolResult(success=False, output="", error="struct must be valid JSON")

        lead_struct = None
        lead_struct_str = parameters.get("leadStruct")
        if lead_struct_str:
            try:
                lead_struct = json.loads(lead_struct_str)
            except json.JSONDecodeError:
                return ToolResult(success=False, output="", error="leadStruct must be valid JSON")

        body = {
            "target_company": target_company,
            "struct": struct,
        }
        if parameters.get("findPeople") is not None:
            body["find_people"] = parameters["findPeople"]
        if parameters.get("fullOrgChart") is not None:
            body["full_org_chart"] = parameters["fullOrgChart"]
        if parameters.get("researchPlan"):
            body["research_plan"] = parameters["researchPlan"]
        if parameters.get("peopleFocusPrompt"):
            body["people_focus_prompt"] = parameters["peopleFocusPrompt"]
        if lead_struct is not None:
            body["lead_struct"] = lead_struct

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }

        url = "https://api.sixtyfour.ai/enrich-company"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")