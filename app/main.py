"""FastAPI application entry point — contract management system."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.middleware.cache_control import CacheControlMiddleware
from app.models import User, Contract, Attachment, AuditLog  # noqa: F401
from app.routers import auth as auth_router
from app.routers import attachments as attachments_router
from app.routers import contracts as contracts_router
from app.routers import pages as pages_router
from app.routers import users as users_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup / shutdown lifecycle."""
    # Startup
    os.makedirs(settings.upload_dir, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _ensure_demo_accounts()
    yield
    # Shutdown (nothing to clean up)


def _ensure_demo_accounts() -> None:
    """Insert demo accounts if the users table is empty."""
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


def create_app() -> FastAPI:
    app = FastAPI(
        title="合同管理系统",
        version=settings.app_version,
        lifespan=lifespan,
    )

    # ---------- Middleware ----------
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="session_id",
        same_site="lax",
        https_only=False,
    )
    app.add_middleware(CacheControlMiddleware)

    # ---------- API routers ----------
    app.include_router(auth_router.router)
    app.include_router(users_router.router)
    app.include_router(contracts_router.router)
    app.include_router(attachments_router.router)
    app.include_router(pages_router.router)

    # ---------- Static files ----------
    app.mount(
        f"{settings.base_path}/static",
        StaticFiles(directory="app/static"),
        name="static",
    )

    # ---------- Health ----------
    @app.get(f"{settings.base_path}/healthz")
    def healthz():
        return {"status": "ok", "version": settings.app_version}

    # ---------- Global exception handlers ----------
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=404,
            content={"detail": "页面不存在"},
        )

    @app.exception_handler(500)
    async def server_error_handler(request: Request, exc):
        return JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误"},
        )

    return app


app = create_app()
