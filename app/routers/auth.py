"""Auth API routes: login, logout, current-user."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.schemas.user import UserResponse
from app.services.auth import authenticate_user, login_user, logout_user

router = APIRouter(prefix=f"{settings.base_path}/api/auth", tags=["auth"])


@router.post("/login", response_model=dict)
def login(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticate user and create a signed session cookie."""
    user = authenticate_user(db, body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )
    login_user(request, user)
    return {
        "user": UserResponse.model_validate(user).model_dump(),
        "message": "登录成功",
    }


@router.post("/logout", response_model=dict)
def logout(request: Request):
    """Clear the session cookie."""
    logout_user(request)
    return {"message": "已登出"}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Return the currently logged-in user profile."""
    return current_user
