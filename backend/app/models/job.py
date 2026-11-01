import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    Numeric,
    CheckConstraint,
    Table,
    Column,
    func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.skill import Skill

job_skills = Table(
    "job_skills",
    Base.metadata,
    Column(
        "job_id",
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "skill_id",
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True
    )
)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'archived', 'closed')",
            name="check_job_status"
        ),
        CheckConstraint(
            "salary_min IS NULL OR salary_min >= 0",
            name="check_salary_min_non_negative"
        ),
        CheckConstraint(
            "(salary_min IS NULL OR salary_max IS NULL) OR (salary_max >= salary_min)",
            name="check_salary_max_greater_than_min"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    location: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True
    )
    employment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    salary_min: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True
    )
    salary_max: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True
    )
    experience_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        server_default="draft",
        nullable=False,
        index=True
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
    company: Mapped["Company"] = relationship(back_populates="jobs", lazy="joined")
    skills: Mapped[List["Skill"]] = relationship(
        secondary=job_skills,
        back_populates="jobs",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Job {self.title} company_id={self.company_id} status={self.status}>"

