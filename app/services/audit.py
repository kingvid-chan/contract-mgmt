"""Unified audit logging service.

All write operations across the application funnel through ``write_audit`` to
ensure consistent audit trail records.
"""

import json

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def write_audit(
    db: Session,
    user_id: int,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    detail: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """Persist a single audit log entry.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    user_id:
        ID of the user who performed the action.
    action:
        Dot-separated action key, e.g. ``"contract.create"`` or ``"auth.login"``.
    target_type:
        Entity kind affected (``"user"``, ``"contract"``, ``"attachment"``).
    target_id:
        Primary key of the affected entity.
    detail:
        Arbitrary dict serialised to JSON for the ``detail`` column.
    ip_address:
        Client IP address (optional).
    """
    detail_json = json.dumps(detail, ensure_ascii=False) if detail else None

    log = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail_json,
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()
