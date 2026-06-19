"""Authentication service: password hashing, session helpers, login logic."""

from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from app.models.user import User


def hash_password(plain: str) -> str:
    """Return bcrypt hash of a plain-text password."""
    return bcrypt.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return bcrypt.verify(plain, hashed)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Return the authenticated User, or None if credentials are invalid."""
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def login_user(request, user: User) -> None:
    """Persist user_id in the Starlette session (signed cookie)."""
    request.session["user_id"] = user.id


def logout_user(request) -> None:
    """Clear the session data."""
    request.session.clear()
