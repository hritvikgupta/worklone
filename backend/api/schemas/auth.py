"""Authentication API schemas."""

from typing import Optional

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    user: Optional[dict] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    retryable: Optional[bool] = None


class UserResponse(BaseModel):
    success: bool
    user: Optional[dict] = None
