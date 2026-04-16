"""
Centralized LLM Provider Configuration Service

All agents (Katy, Employee ReAct, Harry/Coworker) import model & provider settings from here.
To add a new provider in the future, just update this file.

Supported providers:
- openrouter: https://openrouter.ai/
- nvidia: https://build.nvidia.com/
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv(override=True)


# ─── Provider Configuration Registry ───

PROVIDERS: Dict[str, Dict[str, Any]] = {
    "openrouter": {
        "name": "OpenRouter",
        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "base_url": "https://openrouter.ai/api/v1",
        "headers": {
            "HTTP-Referer": "https://ceo-agent.local",
        },
        "payload_defaults": {},
    },
    "nvidia": {
        "name": "NVIDIA NIM",
        "api_key": os.getenv("NVIDIA_API_KEY", ""),
        "base_url": "https://integrate.api.nvidia.com/v1",
        "headers": {},
        "payload_defaults": {
            "top_p": 0.95,
        },
    },
}


# ─── Helper Functions ───

def detect_provider(model: str) -> str:
    """Detect provider from model name prefix.
    
    Examples:
    - minimaxai/minimax-m2.7 → nvidia
    - meta/llama-3.1-405b → nvidia
    - openai/gpt-4o → openrouter
    - anthropic/claude-3 → openrouter
    """
    if "/" in model:
        prefix = model.split("/")[0].lower()
        if prefix in ["minimaxai", "meta"]:
            return "nvidia"
    return "openrouter"


def get_provider_config(model: str) -> Dict[str, Any]:
    """Get provider configuration for a given model name.
    
    Returns dict with:
    - provider_name: "openrouter" or "nvidia"
    - api_key: the API key
    - base_url: the API endpoint
    - headers: extra headers to include
    - payload_defaults: extra payload fields
    - model: the model name
    """
    provider_name = detect_provider(model)
    config = PROVIDERS[provider_name].copy()
    config["provider_name"] = provider_name
    config["model"] = model
    return config


def get_api_key(model: str) -> str:
    """Get the API key for a given model."""
    return get_provider_config(model)["api_key"]


def get_base_url(model: str) -> str:
    """Get the base URL for a given model."""
    return get_provider_config(model)["base_url"]


def get_headers(model: str) -> Dict[str, str]:
    """Get extra headers for a given model."""
    return get_provider_config(model)["headers"]


def get_payload_extras(model: str) -> Dict[str, Any]:
    """Get extra payload fields for a given model (e.g., top_p for NVIDIA)."""
    return get_provider_config(model)["payload_defaults"]


def get_available_providers() -> Dict[str, Dict[str, Any]]:
    """Return all providers with their availability status."""
    result = {}
    for name, config in PROVIDERS.items():
        result[name] = {
            "id": name,
            "name": config["name"],
            "description": f"{config['name']} API",
            "available": bool(config["api_key"]),
            **({} if config["api_key"] else {"message": f"{name.upper()}_API_KEY not set"}),
        }
    return result


def is_provider_available(provider_name: str) -> bool:
    """Check if a specific provider is configured."""
    config = PROVIDERS.get(provider_name)
    return bool(config) and bool(config.get("api_key"))
