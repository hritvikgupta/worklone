"""
OAuth Router - OAuth integration endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from backend.services.auth_service import AuthService, OAUTH_PROVIDERS
from backend.lib.auth.session import get_current_user

router = APIRouter()
auth_service = AuthService()


class IntegrationStatus(BaseModel):
    id: str
    name: str
    icon: str
    connected: bool
    connected_at: Optional[str] = None
    provider_email: Optional[str] = None


class IntegrationsResponse(BaseModel):
    success: bool
    integrations: List[IntegrationStatus]
    error: Optional[str] = None


class DisconnectResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


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
        integrations=status["integrations"]
    )


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
