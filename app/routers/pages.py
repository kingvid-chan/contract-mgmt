"""Jinja2 page routes — T022."""

import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user_or_redirect, require_admin_or_redirect
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services import contract as contract_service
from app.services import user as user_service

_tpl_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "app", "templates",
)
templates = Jinja2Templates(directory=_tpl_dir)
router = APIRouter(prefix=settings.base_path)


# ---------- Root redirect ----------
@router.get("/")
def root():
    return RedirectResponse(url=f"{settings.base_path}/contracts")


# ---------- Auth pages ----------
@router.get("/login")
def login_page(request: Request, error: str = None):
    return templates.TemplateResponse(
        request, "login.html",
        {"current_user": None, "error": error},
    )


# ---------- User pages (admin) ----------
@router.get("/users")
def users_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_redirect),
):
    users = user_service.get_users(db, limit=100)
    return templates.TemplateResponse(
        request, "users/list.html",
        {"current_user": current_user, "users": users},
    )


@router.get("/users/new")
def users_new(
    request: Request,
    current_user: User = Depends(require_admin_or_redirect),
):
    return templates.TemplateResponse(
        request, "users/form.html",
        {"current_user": current_user, "user": None},
    )


@router.get("/users/{user_id}/edit")
def users_edit(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_redirect),
):
    u = user_service.get_user_by_id(db, user_id)
    if u is None:
        return templates.TemplateResponse(
            request, "login.html",
            {"current_user": current_user, "error": "用户不存在"},
            status_code=404,
        )
    return templates.TemplateResponse(
        request, "users/form.html",
        {"current_user": current_user, "user": u},
    )


# ---------- Contract pages ----------
@router.get("/contracts")
def contracts_list(
    request: Request,
    search: str = None,
    status: str = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_redirect),
):
    skip = (page - 1) * page_size
    contracts, total = contract_service.get_contracts(
        db, skip=skip, limit=page_size, search=search, status=status,
    )
    return templates.TemplateResponse(
        request, "contracts/list.html",
        {
            "current_user": current_user,
            "contracts": contracts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "search": search or "",
            "status_filter": status or "",
        },
    )


@router.get("/contracts/new")
def contracts_new(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
):
    return templates.TemplateResponse(
        request, "contracts/form.html",
        {"current_user": current_user, "contract": None},
    )


@router.get("/contracts/{contract_id}/edit")
def contracts_edit(
    contract_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_redirect),
):
    c = contract_service.get_contract_by_id(db, contract_id)
    if c is None:
        return templates.TemplateResponse(
            request, "login.html",
            {"current_user": current_user, "error": "合同不存在"},
            status_code=404,
        )
    # Redirect to detail if contract is not in editable status
    if c.status not in ("draft", "pending_review"):
        return RedirectResponse(
            url=f"{settings.base_path}/contracts/{contract_id}",
            status_code=302,
        )
    return templates.TemplateResponse(
        request, "contracts/form.html",
        {"current_user": current_user, "contract": c},
    )


@router.get("/contracts/{contract_id}")
def contracts_detail(
    contract_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_redirect),
):
    detail = contract_service.get_contract_detail(db, contract_id)
    if detail is None:
        return templates.TemplateResponse(
            request, "login.html",
            {"current_user": current_user, "error": "合同不存在"},
            status_code=404,
        )
    audit_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.target_type == "contract",
            AuditLog.target_id == contract_id,
        )
        .order_by(AuditLog.created_at.desc())
        .limit(50)
        .all()
    )
    return templates.TemplateResponse(
        request, "contracts/detail.html",
        {
            "current_user": current_user,
            "contract": detail,
            "audit_logs": audit_logs,
        },
    )
