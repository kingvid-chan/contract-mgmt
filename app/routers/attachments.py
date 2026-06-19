"""Attachment API routes: upload, list, download, delete."""

import os

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.attachment import AttachmentResponse
from app.services import attachment as attachment_service

API = f"{settings.base_path}/api"

router = APIRouter(prefix=API, tags=["attachments"])


# ---------------------------------------------------------------------------
# Upload & list (scoped under /contracts/{contract_id}/attachments)
# ---------------------------------------------------------------------------


@router.post(
    "/contracts/{contract_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    contract_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload an attachment (PDF/DOC/DOCX, ≤10MB)."""
    try:
        attachment = attachment_service.save_attachment(
            db, file, contract_id, current_user.id
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return _build_attachment_response(attachment, db)


@router.get(
    "/contracts/{contract_id}/attachments",
    response_model=list[AttachmentResponse],
)
def list_attachments(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List attachments for a contract."""
    attachments = attachment_service.get_attachments(db, contract_id)
    return [_build_attachment_response(a, db) for a in attachments]


# ---------------------------------------------------------------------------
# Download & delete (scoped under /attachments/{attachment_id})
# ---------------------------------------------------------------------------


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download an attachment by id."""
    attachment = attachment_service.get_attachment_by_id(db, attachment_id)
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="附件不存在"
        )

    file_path = attachment_service.get_attachment_filepath(attachment.filename)
    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="附件文件不存在"
        )

    return FileResponse(
        path=file_path,
        filename=attachment.original_name,
        media_type=attachment.mime_type or "application/octet-stream",
    )


@router.delete("/attachments/{attachment_id}", response_model=dict)
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an attachment (admin or uploader)."""
    try:
        attachment_service.delete_attachment(
            db, attachment_id, current_user.id, current_user.role
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return {"message": "附件已删除"}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _build_attachment_response(attachment, db: Session) -> AttachmentResponse:
    username = ""
    if attachment.uploader:
        username = attachment.uploader.username
    else:
        from app.models.user import User
        u = db.query(User).get(attachment.uploaded_by)
        if u:
            username = u.username
    return AttachmentResponse(
        id=attachment.id,
        contract_id=attachment.contract_id,
        original_name=attachment.original_name,
        file_size=attachment.file_size,
        mime_type=attachment.mime_type,
        uploaded_by=attachment.uploaded_by,
        uploaded_by_username=username,
        created_at=attachment.created_at,
    )
