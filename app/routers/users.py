"""User management API routes (admin-only except password change)."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas.user import (
    PasswordChange,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services import user as user_service

router = APIRouter(prefix=f"{settings.base_path}/api/users", tags=["users"])


# ---------------------------------------------------------------------------
# Admin-only endpoints
# ---------------------------------------------------------------------------


@router.get("/", response_model=dict)
def list_users(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """List users with optional search and pagination (admin only)."""
    skip = (page - 1) * page_size
    users = user_service.get_users(db, skip=skip, limit=page_size, search=search)
    total = user_service.count_users(db, search=search)
    return {
        "users": [UserResponse.model_validate(u).model_dump() for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Get a single user by id (admin only)."""
    user = user_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new user (admin only)."""
    try:
        user = user_service.create_user(db, body, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    # Re-query to get fresh data with relationships loaded
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update user fields (admin only)."""
    try:
        user = user_service.update_user(db, user_id, body, current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return user


@router.put("/{user_id}/status", response_model=dict)
def toggle_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Toggle a user's active/inactive status (admin only)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能禁用自己",
        )
    try:
        user = user_service.toggle_user_status(db, user_id, current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    state_label = "启用" if user.is_active else "禁用"
    return {
        "id": user.id,
        "is_active": user.is_active,
        "message": f"用户已{state_label}",
    }


# ---------------------------------------------------------------------------
# Self-service endpoints
# ---------------------------------------------------------------------------


@router.put("/me/password", response_model=dict)
def change_own_password(
    body: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change the current user's password (requires old password)."""
    try:
        user_service.change_password(
            db, current_user, body.old_password, body.new_password
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"message": "密码修改成功"}
