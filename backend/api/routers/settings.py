"""
Settings Router — user-scoped LLM provider config and account settings.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.db.stores.workflow_store import WorkflowStore
from backend.lib.auth.session import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])
_store = WorkflowStore()

SUPPORTED_PROVIDERS = {
    "openrouter": {"name": "OpenRouter", "base_url": "https://openrouter.ai/api/v1", "headers": {"HTTP-Referer": "https://ceo-agent.local"}},
    "openai":     {"name": "OpenAI",     "base_url": "https://api.openai.com/v1",    "headers": {}},
    "groq":       {"name": "Groq",       "base_url": "https://api.groq.com/openai/v1","headers": {}},
    "nvidia":     {"name": "NVIDIA NIM", "base_url": "https://integrate.api.nvidia.com/v1", "headers": {}},
}

_CRED_PROVIDER = "llm_provider"
_CRED_MODEL = "llm_default_model"


def _api_key_cred(provider: str) -> str:
    return f"llm_api_key_{provider}"


def _model_cred(provider: str) -> str:
    return f"llm_default_model_{provider}"


def _require(user):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ─── Providers metadata (no auth needed) ───────────────────────────────────

@router.get("/llm/providers")
async def list_providers():
    return {
        "providers": [
            {"id": pid, "name": cfg["name"]}
            for pid, cfg in SUPPORTED_PROVIDERS.items()
        ]
    }


# ─── LLM settings ──────────────────────────────────────────────────────────

@router.get("/llm")
async def get_llm_settings(user=Depends(get_current_user)):
    _require(user)
    owner_id = user["id"]
    provider = _store.get_credential(owner_id, _CRED_PROVIDER) or ""
    model = (
        (_store.get_credential(owner_id, _model_cred(provider)) if provider else None)
        or _store.get_credential(owner_id, _CRED_MODEL)
        or ""
    )
    # Per-provider key status (also accepts legacy single-key fallback for migration)
    legacy_key = _store.get_credential(owner_id, "llm_api_key") or ""
    provider_keys = {
        pid: bool(
            _store.get_credential(owner_id, _api_key_cred(pid))
            or (pid == provider and legacy_key)
        )
        for pid in SUPPORTED_PROVIDERS
    }
    has_key = provider_keys.get(provider, False) if provider else False
    return {
        "provider": provider,
        "default_model": model,
        "has_api_key": has_key,
        "provider_keys": provider_keys,
    }


@router.get("/llm/provider/{provider_id}")
async def get_provider_settings(provider_id: str, user=Depends(get_current_user)):
    """Return saved model + key-status for one specific provider."""
    _require(user)
    if provider_id not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_id}")
    owner_id = user["id"]
    model = (
        _store.get_credential(owner_id, _model_cred(provider_id))
        or _store.get_credential(owner_id, _CRED_MODEL)
        or ""
    )
    legacy_saved_provider = _store.get_credential(owner_id, _CRED_PROVIDER) or ""
    legacy_key = _store.get_credential(owner_id, "llm_api_key") or ""
    has_key = bool(
        _store.get_credential(owner_id, _api_key_cred(provider_id))
        or (provider_id == legacy_saved_provider and legacy_key)
    )
    return {"provider": provider_id, "default_model": model, "has_api_key": has_key}


class LLMSettingsRequest(BaseModel):
    provider: str
    api_key: str
    default_model: str


@router.put("/llm")
async def save_llm_settings(body: LLMSettingsRequest, user=Depends(get_current_user)):
    _require(user)
    if body.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {body.provider}")
    owner_id = user["id"]
    _store.set_credential(owner_id, _CRED_PROVIDER, body.provider, "LLM provider")
    if body.api_key:
        _store.set_credential(owner_id, _api_key_cred(body.provider), body.api_key, f"LLM API key ({body.provider})")
    if body.default_model:
        _store.set_credential(owner_id, _model_cred(body.provider), body.default_model, f"LLM model ({body.provider})")
        _store.set_credential(owner_id, _CRED_MODEL, body.default_model, "LLM default model")
    return {"success": True}


# ─── Password change ────────────────────────────────────────────────────────

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


@router.put("/password")
async def change_password(body: PasswordChangeRequest, user=Depends(get_current_user)):
    _require(user)
    from backend.db.stores.auth_store import AuthDB
    db = AuthDB()
    ok = db.change_password(user["id"], body.current_password, body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    return {"success": True}


# ─── Mandatory onboarding ────────────────────────────────────────────────────

COMPANY_TYPE_OPTIONS = {
    "startup",
    "smb",
    "enterprise",
    "agency",
    "consultancy",
    "nonprofit",
    "government",
    "education",
    "other",
}


class OnboardingStatusResponse(BaseModel):
    onboarded: bool
    profile: dict


class OnboardingProfileRequest(BaseModel):
    profession: str
    company_description: str
    company_type: str


@router.get("/onboarding", response_model=OnboardingStatusResponse)
async def get_onboarding_status(user=Depends(get_current_user)):
    _require(user)
    owner_id = user["id"]
    profile = _store.get_user_profile(owner_id) or {}
    profession = profile.get("role", "") or ""
    company_description = profile.get("company_description", "") or ""
    company_type = profile.get("industry", "") or ""
    return {
        "onboarded": bool(profile.get("onboarded", False)),
        "profile": {
            "profession": profession,
            "company_description": company_description,
            "company_type": company_type,
        },
    }


@router.put("/onboarding")
async def save_onboarding_profile(body: OnboardingProfileRequest, user=Depends(get_current_user)):
    _require(user)
    owner_id = user["id"]
    profession = (body.profession or "").strip()
    company_description = (body.company_description or "").strip()
    company_type = (body.company_type or "").strip().lower()

    if not profession:
        raise HTTPException(status_code=400, detail="Profession is required")
    if not company_description:
        raise HTTPException(status_code=400, detail="Company description is required")
    if company_type not in COMPANY_TYPE_OPTIONS:
        raise HTTPException(status_code=400, detail="Invalid company type")

    _store.save_user_profile(
        owner_id,
        role=profession,
        company_description=company_description,
        industry=company_type,
        onboarded=1,
    )
    return {"success": True, "onboarded": True}
