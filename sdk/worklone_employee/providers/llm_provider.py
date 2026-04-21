"""
LLM Provider Abstraction Layer
Supports OpenRouter, NVIDIA NIM, OpenAI, Groq
"""

import os
import json
import httpx
from typing import AsyncGenerator, Dict, Any, Optional, List
from abc import ABC, abstractmethod


class LLMProvider(ABC):

    @abstractmethod
    async def chat_completion_stream(
        self, model: str, messages: List[Dict], temperature: float = 0.7,
        max_tokens: int = 4096, tools: Optional[List[Dict]] = None, **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        pass

    @abstractmethod
    async def chat_completion(
        self, model: str, messages: List[Dict], temperature: float = 0.7,
        max_tokens: int = 4096, tools: Optional[List[Dict]] = None, **kwargs
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_models(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass


class OpenRouterProvider(LLMProvider):

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1"
        self.provider_name = "openrouter"

    def get_provider_name(self) -> str:
        return self.provider_name

    async def chat_completion_stream(self, model, messages, temperature=0.7, max_tokens=4096, tools=None, **kwargs):
        if not self.api_key:
            yield {"type": "error", "message": "OPENROUTER_API_KEY not set"}
            return
        payload = {"model": model, "messages": messages, "temperature": temperature,
                   "max_tokens": max_tokens, "stream": True}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        payload.update(kwargs)
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json",
                         "HTTP-Referer": "https://worklone.ai", "X-Title": "Worklone Employee"},
                json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield {"type": "error", "message": f"HTTP {response.status_code}: {error_text.decode()}"}
                    return
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            continue

    async def chat_completion(self, model, messages, temperature=0.7, max_tokens=4096, tools=None, **kwargs):
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY not set")
        payload = {"model": model, "messages": messages, "temperature": temperature,
                   "max_tokens": max_tokens, "stream": False}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        payload.update(kwargs)
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json",
                         "HTTP-Referer": "https://worklone.ai", "X-Title": "Worklone Employee"},
                json=payload)
            response.raise_for_status()
            return response.json()

    async def get_models(self) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"})
            response.raise_for_status()
            return response.json().get("data", [])


class NVIDIAProvider(LLMProvider):

    def __init__(self):
        self.api_key = os.getenv("NVIDIA_API_KEY", "")
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.provider_name = "nvidia"

    def get_provider_name(self) -> str:
        return self.provider_name

    async def chat_completion_stream(self, model, messages, temperature=0.7, max_tokens=4096, tools=None, **kwargs):
        if not self.api_key:
            yield {"type": "error", "message": "NVIDIA_API_KEY not set"}
            return
        payload = {"model": model, "messages": messages, "temperature": temperature,
                   "top_p": 0.95, "max_tokens": max_tokens, "stream": True}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        payload.update(kwargs)
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield {"type": "error", "message": f"HTTP {response.status_code}: {error_text.decode()}"}
                    return
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            continue

    async def chat_completion(self, model, messages, temperature=0.7, max_tokens=4096, tools=None, **kwargs):
        if not self.api_key:
            raise RuntimeError("NVIDIA_API_KEY not set")
        payload = {"model": model, "messages": messages, "temperature": temperature,
                   "top_p": 0.95, "max_tokens": max_tokens, "stream": False}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        payload.update(kwargs)
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload)
            response.raise_for_status()
            return response.json()

    async def get_models(self) -> List[Dict[str, Any]]:
        return [
            {"id": "minimaxai/minimax-m2.7", "name": "MiniMax M2.7", "provider": "MiniMax"},
            {"id": "meta/llama-3.1-405b-instruct", "name": "Llama 3.1 405B", "provider": "Meta"},
        ]


class OpenAIProvider(LLMProvider):

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = "https://api.openai.com/v1"
        self.provider_name = "openai"

    def get_provider_name(self) -> str:
        return self.provider_name

    async def chat_completion_stream(self, model, messages, temperature=0.7, max_tokens=4096, tools=None, **kwargs):
        yield {"type": "error", "message": "use react_agent directly"}

    async def chat_completion(self, model, messages, temperature=0.7, max_tokens=4096, tools=None, **kwargs):
        return {}

    async def get_models(self) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"})
            response.raise_for_status()
            data = response.json().get("data", [])
            chat = [m for m in data if any(x in m.get("id", "").lower() for x in ["gpt", "o1", "o3"])]
            return [{"id": m["id"], "name": m["id"], "provider": "openai"} for m in sorted(chat, key=lambda x: x["id"])]


class GroqProvider(LLMProvider):

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.base_url = "https://api.groq.com/openai/v1"
        self.provider_name = "groq"

    def get_provider_name(self) -> str:
        return self.provider_name

    async def chat_completion_stream(self, model, messages, temperature=0.7, max_tokens=4096, tools=None, **kwargs):
        yield {"type": "error", "message": "use react_agent directly"}

    async def chat_completion(self, model, messages, temperature=0.7, max_tokens=4096, tools=None, **kwargs):
        return {}

    async def get_models(self) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"})
            response.raise_for_status()
            data = response.json().get("data", [])
            return [{"id": m["id"], "name": m.get("id", ""), "provider": "groq"}
                    for m in sorted(data, key=lambda x: x.get("id", ""))]


class LLMProviderFactory:
    _providers: Dict[str, LLMProvider] = {}

    @classmethod
    def initialize(cls):
        cls._providers = {
            "openrouter": OpenRouterProvider(),
            "nvidia": NVIDIAProvider(),
            "openai": OpenAIProvider(),
            "groq": GroqProvider(),
        }

    @classmethod
    def get_provider(cls, provider_name: str) -> Optional[LLMProvider]:
        if not cls._providers:
            cls.initialize()
        return cls._providers.get(provider_name)

    @classmethod
    def get_available_providers(cls) -> Dict[str, LLMProvider]:
        if not cls._providers:
            cls.initialize()
        return cls._providers

    @classmethod
    def get_default_provider(cls) -> LLMProvider:
        if not cls._providers:
            cls.initialize()
        return cls._providers["openrouter"]


LLMProviderFactory.initialize()
