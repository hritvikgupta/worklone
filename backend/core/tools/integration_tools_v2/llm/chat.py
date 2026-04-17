from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class LLMChatTool(BaseTool):
    name = "llm_chat"
    description = "Send a chat completion request to any supported LLM provider"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    @staticmethod
    def _get_provider_from_model(model: str) -> str:
        model_lower = model.lower()
        if any(prefix in model_lower for prefix in ["gpt-", "o1."]):
            return "openai"
        elif "claude" in model_lower:
            return "anthropic"
        elif "gemini" in model_lower:
            return "vertex"
        else:
            raise ValueError(f"Unable to determine provider for model '{model}'. Provide specific credentials or use a supported model prefix.")

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "The model to use (e.g., gpt-4o, claude-sonnet-4-5, gemini-2.0-flash)"
                },
                "systemPrompt": {
                    "type": "string",
                    "description": "System prompt to set the behavior of the assistant"
                },
                "context": {
                    "type": "string",
                    "description": "The user message or context to send to the model"
                },
                "apiKey": {
                    "type": "string",
                    "description": "API key for the provider (uses platform key if not provided for hosted models)"
                },
                "temperature": {
                    "type": "number",
                    "description": "Temperature for response generation (0-2)"
                },
                "maxTokens": {
                    "type": "number",
                    "description": "Maximum tokens in the response"
                },
                "azureEndpoint": {
                    "type": "string",
                    "description": "Azure OpenAI endpoint URL"
                },
                "azureApiVersion": {
                    "type": "string",
                    "description": "Azure OpenAI API version"
                },
                "vertexProject": {
                    "type": "string",
                    "description": "Google Cloud project ID for Vertex AI"
                },
                "vertexLocation": {
                    "type": "string",
                    "description": "Google Cloud location for Vertex AI (defaults to us-central1)"
                },
                "vertexCredential": {
                    "type": "string",
                    "description": "Google Cloud OAuth credential ID for Vertex AI"
                },
                "bedrockAccessKeyId": {
                    "type": "string",
                    "description": "AWS Access Key ID for Bedrock"
                },
                "bedrockSecretKey": {
                    "type": "string",
                    "description": "AWS Secret Access Key for Bedrock"
                },
                "bedrockRegion": {
                    "type": "string",
                    "description": "AWS region for Bedrock (defaults to us-east-1)"
                }
            },
            "required": ["model", "context"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            model = parameters["model"]
            system_prompt = parameters.get("systemPrompt", "")
            user_content = parameters["context"]
            temperature = parameters.get("temperature")
            max_tokens = parameters.get("maxTokens")
            api_key = parameters.get("apiKey", "")
            azure_endpoint = parameters.get("azureEndpoint", "").strip()
            azure_api_version = parameters.get("azureApiVersion", "2024-02-15-preview")
            vertex_project = parameters.get("vertexProject", "")
            vertex_location = parameters.get("vertexLocation", "us-central1")
            vertex_credential = parameters.get("vertexCredential", "")
            bedrock_access_key_id = parameters.get("bedrockAccessKeyId", "")
            bedrock_secret_key = parameters.get("bedrockSecretKey", "")
            bedrock_region = parameters.get("bedrockRegion", "us-east-1")

            # Determine provider with priority to specific parameters
            if azure_endpoint:
                provider = "azure"
            elif vertex_project or vertex_credential:
                provider = "vertex"
            elif bedrock_access_key_id and bedrock_secret_key:
                provider = "bedrock"
            else:
                provider = self._get_provider_from_model(model)

            if provider == "bedrock":
                return ToolResult(success=False, output="", error="Bedrock support not implemented in this tool.")

            # Validate credentials
            if provider == "vertex":
                if self._is_placeholder_token(vertex_credential):
                    return ToolResult(success=False, output="", error="Invalid Vertex credential.")
            else:
                if self._is_placeholder_token(api_key):
                    return ToolResult(success=False, output="", error="Invalid API key.")

            # Provider-specific request setup
            headers: Dict[str, str] = {"Content-Type": "application/json"}
            json_body: Dict[str, Any] = {}
            url: str = ""

            if provider == "openai":
                url = "https://api.openai.com/v1/chat/completions"
                headers["Authorization"] = f"Bearer {api_key}"
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": user_content})
                json_body = {
                    "model": model,
                    "messages": messages,
                }
                if temperature is not None:
                    json_body["temperature"] = temperature
                if max_tokens is not None:
                    json_body["max_tokens"] = max_tokens

            elif provider == "anthropic":
                url = "https://api.anthropic.com/v1/messages"
                headers["x-api-key"] = api_key
                headers["anthropic-version"] = "2023-06-01"
                json_body = {
                    "model": model,
                    "messages": [{"role": "user", "content": user_content}],
                }
                if temperature is not None:
                    json_body["temperature"] = temperature
                if max_tokens is not None:
                    json_body["max_tokens"] = max_tokens
                if system_prompt:
                    json_body["system"] = system_prompt

            elif provider == "azure":
                if not azure_endpoint.startswith(("http://", "https://")):
                    return ToolResult(success=False, output="", error="Invalid Azure endpoint.")
                url = f"{azure_endpoint.rstrip('/')}/openai/deployments/{model}/chat/completions?api-version={azure_api_version}"
                headers["api-key"] = api_key
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": user_content})
                json_body = {
                    "messages": messages,
                }
                if temperature is not None:
                    json_body["temperature"] = temperature
                if max_tokens is not None:
                    json_body["max_tokens"] = max_tokens

            elif provider == "vertex":
                if not vertex_project:
                    return ToolResult(success=False, output="", error="Vertex project required.")
                url = f"https://{vertex_location}-aiplatform.googleapis.com/v1/projects/{vertex_project}/locations/{vertex_location}/publishers/google/models/{model}:generateContent"
                headers["Authorization"] = f"Bearer {vertex_credential}"
                contents = []
                if system_prompt:
                    contents.append({"role": "user", "parts": [{"text": system_prompt}]})
                contents.append({"role": "user", "parts": [{"text": user_content}]})
                json_body = {"contents": contents}
                gen_config: Dict[str, Any] = {}
                if temperature is not None:
                    gen_config["temperature"] = temperature
                if max_tokens is not None:
                    gen_config["maxOutputTokens"] = max_tokens
                if gen_config:
                    json_body["generation_config"] = gen_config

            else:
                return ToolResult(success=False, output="", error=f"Provider '{provider}' not supported.")

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=json_body)

                if response.status_code == 200:
                    data = response.json()
                    # Extract content based on provider
                    if provider in ("openai", "azure"):
                        content = data["choices"][0]["message"]["content"]
                    elif provider == "anthropic":
                        content = data["content"][0]["text"]
                    elif provider == "vertex":
                        content = data["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        content = data.get("content", str(data))
                    model_used = data.get("model", model)
                    tokens = data.get("usage", data.get("usage_metadata", {}))
                    output_data = {
                        "content": content,
                        "model": model_used,
                        "tokens": tokens,
                    }
                    return ToolResult(success=True, output=content, data=output_data)
                else:
                    error_msg = response.text
                    try:
                        err_data = response.json()
                        error_msg = err_data.get("error", {}).get("message", error_msg) if isinstance(err_data.get("error"), dict) else str(err_data)
                    except ValueError:
                        pass
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"LLM API error ({response.status_code}): {error_msg}"
                    )
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")