from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GuardrailsValidateTool(BaseTool):
    name = "guardrails_validate"
    description = "Validate content using guardrails (JSON, regex, hallucination check, or PII detection)"
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Content to validate (from wired block)",
                },
                "validationType": {
                    "type": "string",
                    "description": "Type of validation: json, regex, hallucination, or pii",
                    "enum": ["json", "regex", "hallucination", "pii"],
                },
                "regex": {
                    "type": "string",
                    "description": "Regex pattern (required for regex validation)",
                },
                "knowledgeBaseId": {
                    "type": "string",
                    "description": "Knowledge base ID (required for hallucination check)",
                },
                "threshold": {
                    "type": "string",
                    "description": "Confidence threshold (0-10 scale, default: 3, scores below fail)",
                },
                "topK": {
                    "type": "string",
                    "description": "Number of chunks to retrieve from knowledge base (default: 10)",
                },
                "model": {
                    "type": "string",
                    "description": "LLM model for confidence scoring (default: gpt-4o-mini)",
                },
                "apiKey": {
                    "type": "string",
                    "description": "API key for LLM provider (optional if using hosted)",
                },
                "piiEntityTypes": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": "PII entity types to detect (empty = detect all)",
                },
                "piiMode": {
                    "type": "string",
                    "description": "PII action mode: block or mask (default: block)",
                },
                "piiLanguage": {
                    "type": "string",
                    "description": "Language for PII detection (default: en)",
                },
            },
            "required": ["input", "validationType"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        headers = {
            "Content-Type": "application/json",
        }
        url = "/api/guardrails/validate"

        body: Dict[str, Any] = {
            "input": parameters.get("input"),
            "validationType": parameters.get("validationType"),
            "regex": parameters.get("regex"),
            "knowledgeBaseId": parameters.get("knowledgeBaseId"),
            "threshold": parameters.get("threshold"),
            "topK": parameters.get("topK"),
            "model": parameters.get("model"),
            "apiKey": parameters.get("apiKey"),
            "azureEndpoint": parameters.get("azureEndpoint"),
            "azureApiVersion": parameters.get("azureApiVersion"),
            "vertexProject": parameters.get("vertexProject"),
            "vertexLocation": parameters.get("vertexLocation"),
            "vertexCredential": parameters.get("vertexCredential"),
            "bedrockAccessKeyId": parameters.get("bedrockAccessKeyId"),
            "bedrockSecretKey": parameters.get("bedrockSecretKey"),
            "bedrockRegion": parameters.get("bedrockRegion"),
            "piiEntityTypes": parameters.get("piiEntityTypes"),
            "piiMode": parameters.get("piiMode"),
            "piiLanguage": parameters.get("piiLanguage"),
        }
        _context = parameters.get("_context")
        if isinstance(_context, dict):
            body["workflowId"] = _context.get("workflowId")
            body["workspaceId"] = _context.get("workspaceId")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")