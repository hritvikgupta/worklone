"""
Agent Block Handler — executes LLM agent blocks.
"""

import os
import httpx
import json
import time
from backend.workflows.types import Block
from backend.workflows.engine.handlers.base import BaseBlockHandler
from backend.workflows.logger import get_logger

logger = get_logger("agent_handler")


class AgentBlockHandler(BaseBlockHandler):
    """Execute an LLM agent block."""
    
    async def handle(self, block: Block) -> dict:
        config = block.config
        prompt = config.params.get("prompt", "")
        system_prompt = config.system_prompt or config.params.get("system_prompt", "")
        model = config.model or config.params.get("model", "openai/gpt-4o")
        temperature = config.params.get("temperature", 0.7)
        max_tokens = config.params.get("max_tokens", 4096)
        
        # Resolve templates
        prompt = self.resolver.resolve(prompt)
        system_prompt = self.resolver.resolve(system_prompt)
        
        if not prompt:
            return {
                "success": False,
                "error": "No prompt provided",
                "content": "",
            }
        
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            return {
                "success": False,
                "error": "OPENROUTER_API_KEY not set",
                "content": "",
            }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            start = time.time()
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://ceo-agent.local",
                        "X-Title": "Workflow Engine",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                
                elapsed = time.time() - start
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"LLM error {response.status_code}: {response.text}",
                        "content": "",
                        "execution_time": elapsed,
                    }
                
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                logger.info(f"Agent block '{block.id}' completed in {elapsed:.2f}s")
                
                return {
                    "success": True,
                    "content": content,
                    "model": model,
                    "usage": data.get("usage", {}),
                    "execution_time": elapsed,
                }
        
        except Exception as e:
            logger.exception(f"Agent block '{block.id}' failed")
            return {
                "success": False,
                "error": f"Agent execution failed: {str(e)}",
                "content": "",
            }
