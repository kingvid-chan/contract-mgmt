"""Attachment-related Pydantic schemas."""

from pydantic import BaseModel, ConfigDict


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_id: int
    original_name: str
    file_size: int
    mime_type: str
    uploaded_by: int
    uploaded_by_username: str = ""
    created_at: str
