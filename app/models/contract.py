"""Contract ORM model."""

from datetime import datetime

from sqlalchemy import String, Integer, Float, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    contract_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    parties: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )
    sign_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    expiry_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[str] = mapped_column(
        String(30), default=lambda: datetime.utcnow().isoformat()
    )
    updated_at: Mapped[str] = mapped_column(
        String(30), default=lambda: datetime.utcnow().isoformat()
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'pending_review', 'active', 'expired', 'terminated')",
            name="check_contract_status",
        ),
    )

    creator = relationship("User", back_populates="contracts", foreign_keys=[created_by])
    attachments = relationship(
        "Attachment", back_populates="contract", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Contract(id={self.id}, no='{self.contract_no}', status='{self.status}')>"
