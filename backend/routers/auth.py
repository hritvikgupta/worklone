"""
Auth Router - Authentication endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional
from backend.services.auth_service import AuthService

router = APIRouter()
auth_service = AuthService()


# Request/Response models
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


class UserResponse(BaseModel):
    success: bool
    user: Optional[dict] = None


def get_current_user(authorization: str = Header(None)):
    """Dependency to get current user from token"""
    if not authorization:
        return None

    token = authorization.replace("Bearer ", "")
    user = auth_service.get_current_user(token)
    return user


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """Register a new user"""
    if len(request.password) < 6:
        return AuthResponse(success=False, error="Password must be at least 6 characters")

    result = auth_service.register(
        email=request.email,
        password=request.password,
        name=request.name
    )

    if not result["success"]:
        return AuthResponse(success=False, error=result["error"])

    return AuthResponse(
        success=True,
        token=result["token"],
        user=result["user"]
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login user"""
    result = auth_service.login(
        email=request.email,
        password=request.password
    )

    if not result["success"]:
        return AuthResponse(success=False, error=result["error"])

    return AuthResponse(
        success=True,
        token=result["token"],
        user=result["user"]
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user=Depends(get_current_user)):
    """Get current user"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return UserResponse(success=True, user=user)


@router.post("/logout")
async def logout(authorization: str = Header(None)):
    """Logout user"""
    if authorization:
        token = authorization.replace("Bearer ", "")
        auth_service.logout(token)

    return {"success": True, "message": "Logged out successfully"}
