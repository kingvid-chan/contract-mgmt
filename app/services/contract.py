"""Contract management service: CRUD, search, status transitions."""

import json
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.audit_log import AuditLog
from app.models.contract import Contract
from app.models.user import User
from app.schemas.contract import (
    ContractCreate,
    ContractResponse,
    ContractUpdate,
    StatusChange,
)

# ---------------------------------------------------------------------------
# Status transition map
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["pending_review", "terminated"],
    "pending_review": ["active", "draft"],
    "active": ["expired", "terminated"],
    "expired": [],
    "terminated": [],
}

EDITABLE_STATUSES = {"draft", "pending_review"}


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def _contract_to_response(c: Contract) -> ContractResponse:
    """Build a ContractResponse from an ORM object, resolving parties JSON
    and creator username."""
    try:
        parties = json.loads(c.parties) if isinstance(c.parties, str) else c.parties
    except (json.JSONDecodeError, TypeError):
        parties = []

    return ContractResponse(
        id=c.id,
        title=c.title,
        contract_no=c.contract_no,
        parties=parties,
        amount=c.amount,
        status=c.status,
        sign_date=c.sign_date,
        expiry_date=c.expiry_date,
        content=c.content,
        created_by=c.created_by,
        created_by_username=c.creator.username if c.creator else "",
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def get_contracts(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: str | None = None,
    status: str | None = None,
    created_by: int | None = None,
) -> tuple[list[ContractResponse], int]:
    """Return paginated contracts + total count, with optional filters."""
    q = db.query(Contract).options(joinedload(Contract.creator))

    if search:
        pattern = f"%{search}%"
        q = q.filter(
            or_(
                Contract.title.like(pattern),
                Contract.contract_no.like(pattern),
            )
        )
    if status:
        q = q.filter(Contract.status == status)
    if created_by is not None:
        q = q.filter(Contract.created_by == created_by)

    total = q.count()
    contracts = (
        q.order_by(Contract.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_contract_to_response(c) for c in contracts], total


def get_contract_by_id(
    db: Session, contract_id: int
) -> Contract | None:
    """Return a single contract by primary key, or None."""
    return (
        db.query(Contract)
        .options(joinedload(Contract.creator), joinedload(Contract.attachments))
        .get(contract_id)
    )


def get_contract_detail(
    db: Session, contract_id: int
) -> dict | None:
    """Return contract detail dict with attachments and allowed_transitions."""
    c = get_contract_by_id(db, contract_id)
    if c is None:
        return None
    resp = _contract_to_response(c)
    attachments = [
        {
            "id": a.id,
            "original_name": a.original_name,
            "file_size": a.file_size,
            "mime_type": a.mime_type,
            "created_at": a.created_at,
        }
        for a in c.attachments
    ]
    return {
        **resp.model_dump(),
        "attachments": attachments,
        "allowed_transitions": VALID_TRANSITIONS.get(c.status, []),
    }


def _check_contract_no_unique(db: Session, contract_no: str, exclude_id: int | None = None) -> None:
    """Raise ValueError if contract_no already exists."""
    q = db.query(Contract).filter(Contract.contract_no == contract_no)
    if exclude_id is not None:
        q = q.filter(Contract.id != exclude_id)
    if q.first():
        raise ValueError("合同编号已存在")


# ---------------------------------------------------------------------------
# Mutation helpers
# ---------------------------------------------------------------------------


def create_contract(
    db: Session, data: ContractCreate, current_user: User
) -> Contract:
    """Create a new contract (initial status = draft)."""
    _check_contract_no_unique(db, data.contract_no)

    parties_json = json.dumps(
        [p.model_dump() for p in data.parties], ensure_ascii=False
    )

    contract = Contract(
        title=data.title,
        contract_no=data.contract_no,
        parties=parties_json,
        amount=data.amount,
        status="draft",
        sign_date=data.sign_date,
        expiry_date=data.expiry_date,
        content=data.content,
        created_by=current_user.id,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)

    _write_audit(
        db, current_user.id, "contract_create", "contract", contract.id,
        {"title": contract.title, "contract_no": contract.contract_no},
    )
    return contract


def update_contract(
    db: Session, contract_id: int, data: ContractUpdate, current_user: User
) -> Contract:
    """Update a contract.  Only draft / pending_review contracts can be edited."""
    contract = get_contract_by_id(db, contract_id)
    if contract is None:
        raise LookupError("合同不存在")

    if contract.status not in EDITABLE_STATUSES:
        raise ValueError("当前状态不允许编辑")

    if data.contract_no:
        _check_contract_no_unique(db, data.contract_no, exclude_id=contract_id)

    changed: dict[str, object] = {}

    for field_name in ("title", "amount", "sign_date", "expiry_date", "content"):
        new_val = getattr(data, field_name)
        if new_val is not None and getattr(contract, field_name) != new_val:
            changed[field_name] = {"old": getattr(contract, field_name), "new": new_val}
            setattr(contract, field_name, new_val)

    if data.parties is not None:
        new_parties = json.dumps(
            [p.model_dump() for p in data.parties], ensure_ascii=False
        )
        if contract.parties != new_parties:
            changed["parties"] = True
            contract.parties = new_parties

    if changed:
        contract.updated_at = datetime.utcnow().isoformat()
        db.commit()
        db.refresh(contract)
        _write_audit(
            db, current_user.id, "contract_update", "contract", contract.id,
            {"changed": list(changed.keys())},
        )

    return contract


def delete_contract(
    db: Session, contract_id: int, current_user: User
) -> None:
    """Delete a contract.  Only admin, or the creator when status is draft."""
    contract = get_contract_by_id(db, contract_id)
    if contract is None:
        raise LookupError("合同不存在")

    # Permission: admin can always delete; creator can only delete draft
    if current_user.role != "admin":
        if contract.created_by != current_user.id:
            raise PermissionError("无权删除此合同")
        if contract.status != "draft":
            raise PermissionError("只能删除 draft 状态的合同")

    _write_audit(
        db, current_user.id, "contract_delete", "contract", contract.id,
        {"title": contract.title, "contract_no": contract.contract_no},
    )

    db.delete(contract)
    db.commit()


def change_status(
    db: Session,
    contract_id: int,
    target_status: str,
    reason: str | None,
    current_user: User,
) -> dict:
    """Transition a contract to a new status.  Returns status change summary."""
    contract = get_contract_by_id(db, contract_id)
    if contract is None:
        raise LookupError("合同不存在")

    allowed = VALID_TRANSITIONS.get(contract.status, [])
    if target_status not in allowed:
        raise ValueError(
            f"不允许从 {contract.status} 变更为 {target_status}"
        )

    previous_status = contract.status
    contract.status = target_status
    contract.updated_at = datetime.utcnow().isoformat()

    # Auto-fill dates on certain transitions
    if target_status == "active" and not contract.sign_date:
        contract.sign_date = datetime.utcnow().strftime("%Y-%m-%d")

    db.commit()
    db.refresh(contract)

    _write_audit(
        db, current_user.id, "contract_status_change", "contract", contract.id,
        {
            "previous_status": previous_status,
            "new_status": target_status,
            "reason": reason,
        },
    )

    return {
        "id": contract.id,
        "status": contract.status,
        "previous_status": previous_status,
        "message": f"状态已更新为 {target_status}",
    }


# ---------------------------------------------------------------------------
# Audit helper (to be replaced by app/services/audit.py in T015)
# ---------------------------------------------------------------------------


def _write_audit(
    db: Session,
    user_id: int,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    detail: dict | None = None,
) -> None:
    """Write an audit log entry directly to the database."""
    log = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=json.dumps(detail, ensure_ascii=False) if detail else None,
    )
    db.add(log)
    db.commit()
