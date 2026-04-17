"""
Auth Router - Authentication endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Header

from backend.api.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from backend.lib.auth.service import AuthService
from backend.lib.auth.session import get_current_user

router = APIRouter()
auth_service = AuthService()


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """Register a new user"""
    if len(request.password) < 6:
        return AuthResponse(
            success=False,
            error="Password must be at least 6 characters",
            error_code="AUTH_PASSWORD_TOO_SHORT",
            retryable=False,
        )

    result = auth_service.register(
        email=request.email,
        password=request.password,
        name=request.name
    )

    if not result["success"]:
        error = result["error"]
        code = "AUTH_REGISTER_FAILED"
        retryable = False
        if "already" in error.lower():
            code = "AUTH_EMAIL_IN_USE"
        return AuthResponse(success=False, error=error, error_code=code, retryable=retryable)

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
        error = result["error"]
        code = "AUTH_LOGIN_FAILED"
        if "invalid" in error.lower():
            code = "AUTH_INVALID_CREDENTIALS"
        return AuthResponse(success=False, error=error, error_code=code, retryable=False)

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
