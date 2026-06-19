"""User management service: CRUD, password operations, status toggle."""

import json
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit import write_audit
from app.services.auth import hash_password, verify_password


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
) -> list[User]:
    """Return a paginated list of users, optionally filtered by search term."""
    q = db.query(User)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            or_(
                User.username.like(pattern),
                User.display_name.like(pattern),
            )
        )
    return q.order_by(User.id).offset(skip).limit(limit).all()


def count_users(db: Session, search: str | None = None) -> int:
    """Return total user count, optionally filtered."""
    q = db.query(User)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            or_(
                User.username.like(pattern),
                User.display_name.like(pattern),
            )
        )
    return q.count()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Return a single user by primary key, or None."""
    return db.query(User).get(user_id)


def get_user_by_username(db: Session, username: str) -> User | None:
    """Return a single user by username, or None."""
    return db.query(User).filter(User.username == username).first()


# ---------------------------------------------------------------------------
# Mutation helpers
# ---------------------------------------------------------------------------


def create_user(db: Session, data: UserCreate, current_user: User) -> User:
    """Create a new user with a bcrypt-hashed password.  Raises ValueError on
    duplicate username."""
    if get_user_by_username(db, data.username):
        raise ValueError("用户名已存在")

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        display_name=data.display_name,
        role=data.role,
        is_active=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    write_audit(db, current_user.id, "user_create", "user", user.id,
                 {"username": user.username, "role": user.role})
    return user


def update_user(
    db: Session, user_id: int, data: UserUpdate, current_user: User
) -> User:
    """Update display_name, role, and/or is_active of an existing user."""
    user = get_user_by_id(db, user_id)
    if user is None:
        raise LookupError("用户不存在")

    changed: dict[str, object] = {}

    if data.display_name is not None and data.display_name != user.display_name:
        changed["display_name"] = {"old": user.display_name, "new": data.display_name}
        user.display_name = data.display_name

    if data.role is not None and data.role != user.role:
        changed["role"] = {"old": user.role, "new": data.role}
        user.role = data.role

    if data.is_active is not None and data.is_active != user.is_active:
        changed["is_active"] = {"old": user.is_active, "new": data.is_active}
        user.is_active = data.is_active

    if changed:
        user.updated_at = datetime.utcnow().isoformat()
        db.commit()
        db.refresh(user)
        write_audit(db, current_user.id, "user_update", "user", user.id,
                     {"changed": changed})

    return user


def toggle_user_status(db: Session, user_id: int, current_user: User) -> User:
    """Flip the is_active flag (0↔1).  Returns the updated user."""
    user = get_user_by_id(db, user_id)
    if user is None:
        raise LookupError("用户不存在")

    new_state = 0 if user.is_active else 1
    user.is_active = new_state
    user.updated_at = datetime.utcnow().isoformat()
    db.commit()
    db.refresh(user)

    write_audit(
        db, current_user.id, "user_toggle_status", "user", user.id,
        {"is_active": new_state},
    )
    return user


def change_password(
    db: Session, user: User, old_password: str, new_password: str
) -> None:
    """Change a user's own password after verifying the current one."""
    if not verify_password(old_password, user.password_hash):
        raise ValueError("当前密码错误")

    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.utcnow().isoformat()
    db.commit()

    write_audit(db, user.id, "password_change", "user", user.id)


def reset_password(
    db: Session, user_id: int, new_password: str, current_user: User
) -> None:
    """Admin resets a user's password without verifying the old one."""
    user = get_user_by_id(db, user_id)
    if user is None:
        raise LookupError("用户不存在")

    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.utcnow().isoformat()
    db.commit()

    write_audit(
        db, current_user.id, "user_reset_password", "user", user.id,
        {"reset_by": current_user.username},
    )

