from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloOrganizationEnrichTool(BaseTool):
    name = "apollo_organization_enrich"
    description = "Enrich data for a single organization using Apollo"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="APOLLO_API_KEY",
                description="Apollo API key",
                env_var="APOLLO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "organization_name": {
                    "type": "string",
                    "description": 'Name of the organization (e.g., "Acme Corporation") - at least one of organization_name or domain is required',
                },
                "domain": {
                    "type": "string",
                    "description": 'Company domain (e.g., "apollo.io", "acme.com") - at least one of domain or organization_name is required',
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("APOLLO_API_KEY") if context else None
        
        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Apollo API key not configured.")
        
        organization_name = parameters.get("organization_name")
        domain = parameters.get("domain")
        
        if not organization_name and not domain:
            return ToolResult(success=False, output="", error="At least one of organization_name or domain is required for organization enrichment")
        
        body: Dict[str, Any] = {}
        if organization_name:
            body["name"] = organization_name
        if domain:
            body["domain"] = domain
        
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        }
        
        url = "https://api.apollo.io/api/v1/organizations/enrich"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")