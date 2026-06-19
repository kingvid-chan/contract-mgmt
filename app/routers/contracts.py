"""Contract management API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.contract import (
    ContractCreate,
    ContractListResponse,
    ContractResponse,
    ContractUpdate,
    StatusChange,
)
from app.services import contract as contract_service

router = APIRouter(prefix=f"{settings.base_path}/api/contracts", tags=["contracts"])


@router.get("/", response_model=dict)
def list_contracts(
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List contracts with optional search, status filter, and pagination."""
    skip = (page - 1) * page_size
    contracts, total = contract_service.get_contracts(
        db, skip=skip, limit=page_size, search=search, status=status
    )
    return {
        "contracts": [c.model_dump() for c in contracts],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
def create_contract(
    body: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new contract (initial status = draft)."""
    try:
        contract = contract_service.create_contract(db, body, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    # Build response with parties deserialized
    return _build_contract_response(contract, db)


@router.get("/{contract_id}", response_model=dict)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get contract detail including attachments and allowed transitions."""
    detail = contract_service.get_contract_detail(db, contract_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="合同不存在"
        )
    return detail


@router.put("/{contract_id}", response_model=dict)
def update_contract(
    contract_id: int,
    body: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a contract (only draft / pending_review)."""
    try:
        contract = contract_service.update_contract(db, contract_id, body, current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return _build_contract_response(contract, db).model_dump()


@router.delete("/{contract_id}", response_model=dict)
def delete_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a contract (admin, or draft creator)."""
    try:
        contract_service.delete_contract(db, contract_id, current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return {"message": "合同已删除"}


@router.post("/{contract_id}/status", response_model=dict)
def change_contract_status(
    contract_id: int,
    body: StatusChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change a contract's status (validated against transition rules)."""
    try:
        result = contract_service.change_status(
            db, contract_id, body.status, body.reason, current_user
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return result


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _build_contract_response(contract, db: Session) -> ContractResponse:
    """Build a ContractResponse with parties deserialized and creator name."""
    import json

    try:
        parties = (
            json.loads(contract.parties)
            if isinstance(contract.parties, str)
            else contract.parties
        )
    except (json.JSONDecodeError, TypeError):
        parties = []

    creator_name = ""
    if contract.creator:
        creator_name = contract.creator.username
    else:
        from app.models.user import User
        creator = db.query(User).get(contract.created_by)
        if creator:
            creator_name = creator.username

    return ContractResponse(
        id=contract.id,
        title=contract.title,
        contract_no=contract.contract_no,
        parties=parties,
        amount=contract.amount,
        status=contract.status,
        sign_date=contract.sign_date,
        expiry_date=contract.expiry_date,
        content=contract.content,
        created_by=contract.created_by,
        created_by_username=creator_name,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )
