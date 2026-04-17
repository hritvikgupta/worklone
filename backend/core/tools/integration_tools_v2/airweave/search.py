from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AirweaveSearchTool(BaseTool):
    name = "airweave_search"
    description = "Search your synced data collections using Airweave. Supports semantic search with hybrid, neural, or keyword retrieval strategies. Optionally generate AI-powered answers from search results."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="AIRWEAVE_API_KEY",
                description="Airweave API Key for authentication",
                env_var="AIRWEAVE_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "collectionId": {
                    "type": "string",
                    "description": "The readable ID of the collection to search",
                },
                "query": {
                    "type": "string",
                    "description": "The search query text",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of results to return (default: 100)",
                },
                "retrievalStrategy": {
                    "type": "string",
                    "description": "Retrieval strategy: hybrid (default), neural, or keyword",
                },
                "expandQuery": {
                    "type": "boolean",
                    "description": "Generate query variations to improve recall",
                },
                "rerank": {
                    "type": "boolean",
                    "description": "Reorder results for improved relevance using LLM",
                },
                "generateAnswer": {
                    "type": "boolean",
                    "description": "Generate a natural-language answer to the query",
                },
            },
            "required": ["collectionId", "query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("AIRWEAVE_API_KEY") if context else None
        
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Airweave API key not configured.")
        
        url = f"https://api.airweave.ai/collections/{parameters['collectionId']}/search"
        
        body: Dict[str, Any] = {
            "query": parameters["query"],
        }
        if "limit" in parameters:
            body["limit"] = parameters["limit"]
        retrieval_strategy = parameters.get("retrievalStrategy")
        if retrieval_strategy:
            body["retrieval_strategy"] = retrieval_strategy
        if "expandQuery" in parameters:
            body["expand_query"] = parameters["expandQuery"]
        if "rerank" in parameters:
            body["rerank"] = parameters["rerank"]
        if "generateAnswer" in parameters:
            body["generate_answer"] = parameters["generateAnswer"]
        
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    try:
                        error_data = response.json()
                        error_msg = (
                            error_data.get("detail")
                            or error_data.get("message")
                            or response.text
                        )
                    except Exception:
                        error_msg = response.text
                    return ToolResult(
                        success=False, output="", error=error_msg
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")