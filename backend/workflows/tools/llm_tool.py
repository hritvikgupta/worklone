"""
LLM Tool — Call LLM providers (OpenAI, Anthropic, Google via OpenRouter).
"""

from typing import Any
import httpx
import os
import json
from backend.workflows.tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.workflows.logger import get_logger

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
                required=True,
                example="sk-or-v1-...",
                auth_type="api_key",
                auth_url="https://openrouter.ai/keys",
                auth_provider="openrouter",
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
        if not api_key:
            logger.error("OPENROUTER_API_KEY not found in environment")
            return ToolResult(
                success=False,
                output="",
                error="OPENROUTER_API_KEY environment variable not set",
            )
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://ceo-agent.local",
                        "X-Title": "CEO Agent Workflow Engine",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
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
