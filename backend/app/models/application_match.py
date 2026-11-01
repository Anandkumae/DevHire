import uuid
from datetime import datetime
from typing import Any, List, Optional, TYPE_CHECKING
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    JSON,
    Text,
    func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.application import Application


class ApplicationMatchScore(Base):
    __tablename__ = "application_match_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    skills_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    semantic_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    experience_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    matching_skills: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list
    )
    missing_skills: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list
    )
    strengths: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list
    )
    gap_analysis: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
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

    # Relationship
    application: Mapped["Application"] = relationship(
        back_populates="match_score",
        lazy="joined"
    )

    def __repr__(self) -> str:
        return f"<ApplicationMatchScore app_id={self.application_id} score={self.overall_score}%>"

