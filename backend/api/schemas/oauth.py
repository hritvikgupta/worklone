"""OAuth and integrations API schemas."""

from typing import List, Optional

from pydantic import BaseModel


class IntegrationStatus(BaseModel):
    id: str
    name: str
    icon: str
    connected: bool
    connected_at: Optional[str] = None
    provider_email: Optional[str] = None
    client_credentials_required: bool = False
    has_client_credentials: bool = False
    auth_type: str = "oauth"
    fields: Optional[List[dict]] = None


class IntegrationsResponse(BaseModel):
    success: bool
    integrations: List[IntegrationStatus]
    deployment_mode: str = "self_hosted"
    error: Optional[str] = None


class DisconnectResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
