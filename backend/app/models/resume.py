import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    s3_key: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        nullable=False,
        index=True
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        default="application/pdf",
        server_default="application/pdf",
        nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    candidate: Mapped["User"] = relationship(foreign_keys=[candidate_id], lazy="joined")

    def __repr__(self) -> str:
        return f"<Resume candidate_id={self.candidate_id} file_name={self.file_name} primary={self.is_primary}>"
