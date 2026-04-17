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


class IntegrationsResponse(BaseModel):
    success: bool
    integrations: List[IntegrationStatus]
    error: Optional[str] = None


class DisconnectResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
