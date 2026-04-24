"""
OAuth Router - OAuth integration endpoints
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from backend.api.schemas.oauth import DisconnectResponse, IntegrationsResponse
from backend.lib.auth.service import AuthService, OAUTH_PROVIDERS
from backend.lib.oauth.providers import API_KEY_PROVIDERS
from backend.lib.auth.session import get_current_user

router = APIRouter()
auth_service = AuthService()


class OAuthProviderCredentialsRequest(BaseModel):
    provider: str
    client_id: str
    client_secret: str


class ApiKeyProviderRequest(BaseModel):
    provider: str
    fields: dict  # {field_key: value}

@router.get("/authorize")
async def authorize_integration(
    provider: str,
    frontend_url: str = Query(..., description="Frontend URL for callback"),
    user=Depends(get_current_user)
):
    """Get OAuth authorization URL for a provider"""
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    auth_result = auth_service.get_oauth_url(provider, frontend_url, user_id=user["id"])
    if not auth_result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=auth_result.get("error") or "Failed to generate auth URL",
        )

    return {"success": True, "auth_url": auth_result.get("auth_url")}


@router.get("/callback")
async def oauth_callback(
    provider: str = Query(...),
    code: str = Query(...),
    state: str = Query(...),
    redirect_uri: Optional[str] = Query(None),
):
    """Handle OAuth callback"""
    result = await auth_service.handle_oauth_callback(
        provider,
        code,
        state,
        redirect_uri=redirect_uri,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    # Redirect to frontend with success
    return {
        "success": True,
        "provider": result["provider"],
        "message": result["message"]
    }


@router.get("/", response_model=IntegrationsResponse)
async def get_integrations(user=Depends(get_current_user)):
    """Get all integration statuses"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    status = auth_service.get_integration_status(user["id"])
    return IntegrationsResponse(
        success=True,
        integrations=status["integrations"],
        deployment_mode=status.get("deployment_mode", "self_hosted"),
    )


@router.get("/credentials/{provider}")
async def get_oauth_provider_credentials_status(
    provider: str,
    user=Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = auth_service.get_oauth_provider_credentials_status(user["id"], provider)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Failed to fetch credentials status")
    return result


@router.put("/credentials")
async def save_oauth_provider_credentials(
    body: OAuthProviderCredentialsRequest,
    user=Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = auth_service.set_oauth_provider_credentials(
        user_id=user["id"],
        provider=body.provider,
        client_id=body.client_id,
        client_secret=body.client_secret,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Failed to save credentials")
    return {"success": True}


@router.post("/api-key")
async def save_api_key_integration(
    body: ApiKeyProviderRequest,
    user=Depends(get_current_user),
):
    """Save API key credentials for an API-key-based integration"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if body.provider not in API_KEY_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown API key provider: {body.provider}")
    result = auth_service.save_provider_api_keys(user["id"], body.provider, body.fields)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Failed to save API keys")
    return {"success": True}


@router.post("/{provider}/disconnect", response_model=DisconnectResponse)
async def disconnect_integration(
    provider: str,
    user=Depends(get_current_user)
):
    """Disconnect an integration"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = auth_service.disconnect_integration(user["id"], provider)
    return DisconnectResponse(
        success=result["success"],
        message=result.get("message"),
        error=result.get("error")
    )
