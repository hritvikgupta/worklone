"""
LLM Provider Configuration — SDK version.
User API keys come from environment variables only (no DB lookup).
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv(override=True)


PROVIDERS: Dict[str, Dict[str, Any]] = {
    "openrouter": {
        "name": "OpenRouter",
        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "base_url": "https://openrouter.ai/api/v1",
        "headers": {"HTTP-Referer": "https://worklone.ai"},
        "payload_defaults": {},
    },
    "nvidia": {
        "name": "NVIDIA NIM",
        "api_key": os.getenv("NVIDIA_API_KEY", ""),
        "base_url": "https://integrate.api.nvidia.com/v1",
        "headers": {},
        "payload_defaults": {"top_p": 0.95},
    },
    "openai": {
        "name": "OpenAI",
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "base_url": "https://api.openai.com/v1",
        "headers": {},
        "payload_defaults": {},
    },
    "groq": {
        "name": "Groq",
        "api_key": os.getenv("GROQ_API_KEY", ""),
        "base_url": "https://api.groq.com/openai/v1",
        "headers": {},
        "payload_defaults": {},
    },
}


def detect_provider(model: str) -> str:
    if "/" in model:
        prefix = model.split("/")[0].lower()
        if prefix in ["minimaxai", "meta"]:
            return "nvidia"
    return "openrouter"


def get_provider_config(model: str) -> Dict[str, Any]:
    provider_name = detect_provider(model)
    config = PROVIDERS.get(provider_name, PROVIDERS["openrouter"]).copy()
    config["provider_name"] = provider_name
    config["model"] = model
    # Always read fresh from env (dotenv may have been loaded after module init)
    env_key_map = {
        "openrouter": "OPENROUTER_API_KEY",
        "nvidia": "NVIDIA_API_KEY",
        "openai": "OPENAI_API_KEY",
        "groq": "GROQ_API_KEY",
    }
    config["api_key"] = os.getenv(env_key_map.get(provider_name, "OPENROUTER_API_KEY"), "")
    return config


def get_api_key(model: str) -> str:
    return get_provider_config(model)["api_key"]


def get_base_url(model: str) -> str:
    return get_provider_config(model)["base_url"]


def get_headers(model: str) -> Dict[str, str]:
    return get_provider_config(model)["headers"]


def get_payload_extras(model: str) -> Dict[str, Any]:
    return get_provider_config(model)["payload_defaults"]


def get_available_providers() -> Dict[str, Dict[str, Any]]:
    result = {}
    for name, config in PROVIDERS.items():
        api_key = os.getenv(f"{name.upper()}_API_KEY", "")
        result[name] = {
            "id": name,
            "name": config["name"],
            "available": bool(api_key),
        }
    return result


def is_provider_available(provider_name: str) -> bool:
    env_key_map = {
        "openrouter": "OPENROUTER_API_KEY",
        "nvidia": "NVIDIA_API_KEY",
        "openai": "OPENAI_API_KEY",
        "groq": "GROQ_API_KEY",
    }
    return bool(os.getenv(env_key_map.get(provider_name, ""), ""))


def get_user_provider_config(owner_id: str, model: str, force_provider: str = "") -> Dict[str, Any]:
    """SDK version: reads from env vars only, no DB lookup."""
    return get_provider_config(model)
