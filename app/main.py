"""FastAPI application entry point."""

import os

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base
from app.middleware.cache_control import CacheControlMiddleware
from app.routers import auth as auth_router
from app.routers import users as users_router
from app.routers import contracts as contracts_router
from app.routers import attachments as attachments_router
from app.routers import pages as pages_router
from app.models import User, Contract, Attachment, AuditLog  # noqa: F401


def create_app() -> FastAPI:
    app = FastAPI(
        title="合同管理系统",
        version=settings.app_version,
    )

    # Middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="session_id",
    )
    app.add_middleware(CacheControlMiddleware)

    # Routers
    app.include_router(auth_router.router)
    app.include_router(users_router.router)
    app.include_router(contracts_router.router)
    app.include_router(attachments_router.router)
    app.include_router(pages_router.router)

    # Static files
    app.mount(
        f"{settings.base_path}/static",
        StaticFiles(directory="app/static"),
        name="static",
    )

    # Health check
    @app.get(f"{settings.base_path}/healthz")
    def healthz():
        return {"status": "ok", "version": settings.app_version}

    # Startup: init database
    @app.on_event("startup")
    def startup():
        os.makedirs(settings.upload_dir, exist_ok=True)
        Base.metadata.create_all(bind=engine)
        # Ensure demo accounts exist
        from app.database import SessionLocal
        from passlib.hash import bcrypt
        db = SessionLocal()
        try:
            if db.query(User).count() == 0:
                db.add_all([
                    User(
                        username="admin",
                        password_hash=bcrypt.hash("admin123"),
                        display_name="管理员",
                        role="admin",
                        is_active=1,
                    ),
                    User(
                        username="user",
                        password_hash=bcrypt.hash("user123"),
                        display_name="普通用户",
                        role="user",
                        is_active=1,
                    ),
                ])
                db.commit()
        finally:
            db.close()

    return app


app = create_app()
