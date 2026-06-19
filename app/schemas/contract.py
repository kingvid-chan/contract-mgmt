"""Contract-related Pydantic schemas."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class PartyItem(BaseModel):
    """A single signing party."""
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., min_length=1, max_length=50)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ContractCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    contract_no: str = Field(..., min_length=1, max_length=50)
    parties: list[PartyItem] = Field(..., min_length=2)
    amount: float = Field(..., ge=0)
    sign_date: Optional[str] = Field(default=None, max_length=30)
    expiry_date: Optional[str] = Field(default=None, max_length=30)
    content: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def check_dates(self):
        if self.sign_date and self.expiry_date:
            try:
                s = date.fromisoformat(self.sign_date)
                e = date.fromisoformat(self.expiry_date)
                if s >= e:
                    raise ValueError("签订日期必须早于到期日期")
            except ValueError as exc:
                if "must be" not in str(exc):
                    raise
                raise ValueError("日期格式无效，请使用 YYYY-MM-DD 格式") from exc
        return self


class ContractUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    parties: Optional[list[PartyItem]] = Field(default=None, min_length=2)
    amount: Optional[float] = Field(default=None, ge=0)
    sign_date: Optional[str] = Field(default=None, max_length=30)
    expiry_date: Optional[str] = Field(default=None, max_length=30)
    content: Optional[str] = Field(default=None)


class StatusChange(BaseModel):
    status: str = Field(
        ...,
        pattern=r"^(draft|pending_review|active|expired|terminated)$",
    )
    reason: Optional[str] = Field(default=None)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    contract_no: str
    parties: list[PartyItem]
    amount: float
    status: str
    sign_date: Optional[str] = None
    expiry_date: Optional[str] = None
    content: Optional[str] = None
    created_by: int
    created_by_username: str = ""
    created_at: str
    updated_at: str


class ContractListResponse(BaseModel):
    contracts: list[ContractResponse]
    total: int
    page: int
    page_size: int
