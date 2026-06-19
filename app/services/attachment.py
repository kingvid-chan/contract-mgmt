"""Attachment service: upload, download, delete with validation."""

import json
import os
import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.models.attachment import Attachment
from app.models.contract import Contract
from app.services.audit import write_audit

# ---------------------------------------------------------------------------
# Validation constants
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",                                                  # .doc
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
}


def _max_size_bytes() -> int:
    return settings.max_upload_size_mb * 1024 * 1024


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_attachment(file: UploadFile) -> None:
    """Raise ValueError if the uploaded file fails type or size checks."""

    # --- extension check ---
    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"不支持的文件类型 ({ext})，仅允许 PDF、DOC、DOCX"
        )

    # --- MIME type check ---
    content_type = (file.content_type or "").lower()
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        # Some browsers / OS may send generic octet-stream; allow if extension
        # is valid but log a warning.
        if content_type not in ("application/octet-stream", ""):
            raise ValueError(
                f"不支持的文件格式 ({content_type})，仅允许 PDF、DOC、DOCX"
            )


def validate_file_size(file: UploadFile) -> None:
    """Raise ValueError if the file exceeds the max upload size.

    Reads the file content into memory momentarily to determine real size
    (UploadFile.size may be absent in some frameworks).  The caller is
    responsible for re-winding or replacing the file handle afterwards.
    """
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)

    if size > _max_size_bytes():
        raise ValueError(
            f"文件大小超过 {settings.max_upload_size_mb}MB 限制"
        )


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def get_attachments(db: Session, contract_id: int) -> list[Attachment]:
    """Return all attachments for a contract."""
    return (
        db.query(Attachment)
        .filter(Attachment.contract_id == contract_id)
        .order_by(Attachment.created_at.desc())
        .all()
    )


def get_attachment_by_id(db: Session, attachment_id: int) -> Attachment | None:
    """Return a single attachment by primary key, or None."""
    return db.query(Attachment).get(attachment_id)


def get_attachment_filepath(filename: str) -> str:
    """Return the absolute filesystem path for a stored attachment filename."""
    return os.path.join(settings.upload_dir, filename)


# ---------------------------------------------------------------------------
# Mutation helpers
# ---------------------------------------------------------------------------


def save_attachment(
    db: Session,
    file: UploadFile,
    contract_id: int,
    user_id: int,
) -> Attachment:
    """Validate, persist to disk, and create the DB record for one attachment."""

    # Check contract exists
    contract = db.query(Contract).get(contract_id)
    if contract is None:
        raise LookupError("合同不存在")

    # Validate type and size
    validate_attachment(file)
    validate_file_size(file)

    # Generate storage filename
    _, ext = os.path.splitext(file.filename or "")
    storage_name = uuid.uuid4().hex + ext.lower()

    # Read content and write to disk
    content = file.file.read()
    disk_path = get_attachment_filepath(storage_name)
    os.makedirs(os.path.dirname(disk_path) or settings.upload_dir, exist_ok=True)
    with open(disk_path, "wb") as f:
        f.write(content)

    real_size = len(content)
    if real_size > _max_size_bytes():
        # Clean up the written file
        try:
            os.remove(disk_path)
        except OSError:
            pass
        raise ValueError(
            f"文件大小超过 {settings.max_upload_size_mb}MB 限制"
        )

    # Determine MIME type (prefer content_type from upload)
    mime = _resolve_mime_type(file, ext)

    # Persist DB record
    attachment = Attachment(
        contract_id=contract_id,
        filename=storage_name,
        original_name=file.filename or "unknown",
        file_size=real_size,
        mime_type=mime,
        uploaded_by=user_id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    write_audit(
        db, user_id, "attachment_upload", "attachment", attachment.id,
        {
            "contract_id": contract_id,
            "original_name": attachment.original_name,
            "file_size": attachment.file_size,
        },
    )
    return attachment


def delete_attachment(
    db: Session, attachment_id: int, user_id: int, user_role: str
) -> None:
    """Delete an attachment (file on disk + DB record).

    Permission: admin always; regular users only if they uploaded it.
    """
    attachment = get_attachment_by_id(db, attachment_id)
    if attachment is None:
        raise LookupError("附件不存在")

    # Permission check
    if user_role != "admin" and attachment.uploaded_by != user_id:
        raise PermissionError("无权删除此附件")

    # Delete from disk
    disk_path = get_attachment_filepath(attachment.filename)
    try:
        os.remove(disk_path)
    except OSError:
        pass  # File already gone — still allow DB cleanup

    write_audit(
        db, user_id, "attachment_delete", "attachment", attachment.id,
        {
            "contract_id": attachment.contract_id,
            "original_name": attachment.original_name,
        },
    )

    db.delete(attachment)
    db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_mime_type(file: UploadFile, ext: str) -> str:
    """Return an appropriate MIME type based on content_type and extension."""
    ct = (file.content_type or "").lower()
    if ct and ct != "application/octet-stream":
        return ct
    # Fallback mapping
    mime_map = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    return mime_map.get(ext, "application/octet-stream")
