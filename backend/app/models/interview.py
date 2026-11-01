import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


class Interview(Base):
    __tablename__ = "interviews"
    __table_args__ = (
        CheckConstraint(
            "status IN ('scheduled', 'rescheduled', 'completed', 'cancelled')",
            name="check_interview_status"
        ),
        CheckConstraint(
            "duration_minutes > 0",
            name="check_interview_duration_positive"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    round_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    interview_type: Mapped[str] = mapped_column(
        String(50),
        default="video",
        server_default="video",
        nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        default=60,
        server_default="60",
        nullable=False
    )
    meeting_link: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    interviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="scheduled",
        server_default="scheduled",
        nullable=False,
        index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(
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

    # Relationships
    application: Mapped["Application"] = relationship(foreign_keys=[application_id], lazy="joined")
    interviewer: Mapped[Optional["User"]] = relationship(foreign_keys=[interviewer_id], lazy="joined")
    feedback: Mapped[Optional["InterviewFeedback"]] = relationship(
        back_populates="interview",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined"
    )

    def __repr__(self) -> str:
        return f"<Interview id={self.id} round={self.round_name} status={self.status}>"


class InterviewFeedback(Base):
    __tablename__ = "interview_feedback"
    __table_args__ = (
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="check_feedback_rating_range"
        ),
        CheckConstraint(
            "recommendation IN ('strong_hire', 'hire', 'no_hire', 'strong_no_hire')",
            name="check_feedback_recommendation"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    interviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    technical_skills: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    soft_skills: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    overall_feedback: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    recommendation: Mapped[str] = mapped_column(
        String(30),
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
    interview: Mapped["Interview"] = relationship(back_populates="feedback")
    interviewer: Mapped["User"] = relationship(foreign_keys=[interviewer_id], lazy="joined")

    def __repr__(self) -> str:
        return f"<InterviewFeedback interview_id={self.interview_id} rating={self.rating} recommendation={self.recommendation}>"

