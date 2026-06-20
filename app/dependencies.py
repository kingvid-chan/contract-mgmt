"""FastAPI dependencies for auth extraction and role checks."""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User


class LoginRequired(Exception):
    """Raised by page-route auth dependencies when the user is not logged in.
    An exception handler in main.py converts this into a 302 redirect to /login."""


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Extract current user from session cookie.  Raises 401 if not logged in.

    For API routes — returns JSON 401 on auth failure.
    For page routes, use get_current_user_or_redirect instead (returns 302)."""
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录，请先登录",
        )
    user = db.query(User).get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )
    return user


def get_current_user_or_redirect(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Extract current user from session cookie for page routes.

    Raises LoginRequired (→ 302 redirect to /login) when not logged in
    or when the user no longer exists.  Raises 403 when the account is disabled."""
    user_id = request.session.get("user_id")
    if user_id is None:
        raise LoginRequired()
    user = db.query(User).get(user_id)
    if user is None:
        raise LoginRequired()
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )
    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the current user to have admin role.  Raises 403 otherwise.

    For API routes — returns JSON 403 on role failure.
    For page routes, use require_admin_or_redirect instead (302 on auth failure)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


def require_admin_or_redirect(
    current_user: User = Depends(get_current_user_or_redirect),
) -> User:
    """Require the current user to have admin role (page-route version).

    Redirects to /login when not authenticated (via get_current_user_or_redirect).
    Raises 403 JSON when authenticated but not admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user
