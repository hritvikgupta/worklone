"""
LLM Tool — Call LLM providers (OpenAI, Anthropic, Google via OpenRouter).
"""

from typing import Any
import httpx
import os
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.core.logging import get_logger

logger = get_logger("llm_tool")


class LLMTool(BaseTool):
    """Call an LLM to generate text, analyze data, or make decisions."""
    
    name = "call_llm"
    description = "Call an LLM (OpenAI, Anthropic, Google) to generate text, analyze data, summarize, or make decisions."
    category = "core"
    
    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="OPENROUTER_API_KEY",
                description="OpenRouter API key for accessing LLM models (OpenAI, Anthropic, Google)",
                env_var="OPENROUTER_API_KEY",
                required=False,  # Now optional since NVIDIA is also supported
                example="sk-or-v1-...",
                auth_type="api_key",
                auth_url="https://openrouter.ai/keys",
                auth_provider="openrouter",
            ),
            CredentialRequirement(
                key="NVIDIA_API_KEY",
                description="NVIDIA NIM API key for accessing models (MiniMax, Llama, etc.)",
                env_var="NVIDIA_API_KEY",
                required=False,
                example="nvapi-...",
                auth_type="api_key",
                auth_url="https://build.nvidia.com/",
                auth_provider="nvidia",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The prompt to send to the LLM",
                },
                "system_prompt": {
                    "type": "string",
                    "description": "System prompt (optional)",
                },
                "model": {
                    "type": "string",
                    "description": "Model to use (e.g., openai/gpt-4o, anthropic/claude-3-5-sonnet)",
                },
                "temperature": {
                    "type": "number",
                    "description": "Temperature (0.0 to 1.0, default 0.7)",
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens to generate",
                },
            },
            "required": ["prompt"],
        }
    
    async def execute(
        self,
        parameters: dict,
        context: dict = None,
    ) -> ToolResult:
        prompt = parameters.get("prompt")
        system_prompt = parameters.get("system_prompt", "")
        model = parameters.get("model", "openai/gpt-4o")
        temperature = parameters.get("temperature", 0.7)
        max_tokens = parameters.get("max_tokens", 4096)

        logger.info(f"LLMTool called: model={model}, prompt_length={len(prompt) if prompt else 0}")

        if not prompt:
            return ToolResult(
                success=False,
                output="",
                error="Prompt is required",
            )

        api_key = os.getenv("OPENROUTER_API_KEY", "")
        nvidia_api_key = os.getenv("NVIDIA_API_KEY", "")

        # Detect provider from model prefix using centralized config
        from backend.services.llm_config import get_provider_config, detect_provider, get_headers, get_payload_extras
        
        provider_name = detect_provider(model)
        llm_config = get_provider_config(model)
        effective_api_key = llm_config["api_key"]
        base_url = llm_config["base_url"]

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            payload.update(get_payload_extras(model))
            
            headers = {
                "Authorization": f"Bearer {effective_api_key}",
                "Content-Type": "application/json",
                **get_headers(model),
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                
                if response.status_code != 200:
                    logger.error(f"LLM API error {response.status_code}: {response.text[:300]}")
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"LLM API error {response.status_code}: {response.text[:300]}",
                    )
                
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                usage = data.get("usage", {})
                
                return ToolResult(
                    success=True,
                    output=content,
                    data={
                        "content": content,
                        "model": model,
                        "usage": usage,
                    },
                )
        
        except Exception as e:
            logger.exception("LLM call failed")
            return ToolResult(
                success=False,
                output="",
                error=f"LLM call failed: {str(e)}",
            )
