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


def get_user_provider_config(owner_id: str, model: str, force_provider: str = "") -> Dict[str, Any]:
    """Like get_provider_config but checks DB for per-user overrides first.

    If force_provider is set, uses that provider's saved credentials instead of the user's global setting.
    Falls back to the global config when no user override exists.
    """
    if not owner_id:
        return get_provider_config(model)

    try:
        from backend.db.stores.workflow_store import WorkflowStore
        store = WorkflowStore()
        user_provider = force_provider or store.get_credential(owner_id, "llm_provider") or ""
        # Per-provider key first, then legacy single-key fallback
        user_api_key = (
            store.get_credential(owner_id, f"llm_api_key_{user_provider}") if user_provider else None
        ) or store.get_credential(owner_id, "llm_api_key") or ""
        user_model = (
            store.get_credential(owner_id, f"llm_default_model_{user_provider}") if user_provider else None
        ) or store.get_credential(owner_id, "llm_default_model") or ""

        # Resolve which model to use: caller-supplied > user default > fallback
        resolved_model = model or user_model or "openai/gpt-4o"

        # If user has configured a provider, build config from it
        if user_provider and user_api_key:
            from backend.api.routers.settings import SUPPORTED_PROVIDERS
            provider_meta = SUPPORTED_PROVIDERS.get(user_provider, {})
            return {
                "provider_name": user_provider,
                "api_key": user_api_key,
                "base_url": provider_meta.get("base_url", "https://openrouter.ai/api/v1"),
                "headers": provider_meta.get("headers", {}),
                "payload_defaults": {},
                "model": resolved_model,
            }
    except Exception:
        pass

    return get_provider_config(model)
