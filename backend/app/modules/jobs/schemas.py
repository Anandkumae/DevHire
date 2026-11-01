from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

EmploymentType = Literal[
    "full_time",
    "full-time",
    "part_time",
    "part-time",
    "contract",
    "internship"
]
ExperienceLevel = Literal[
    "fresher",
    "entry",
    "mid",
    "senior",
    "lead"
]
JobStatus = Literal[
    "draft",
    "published",
    "closed"
]


class SkillResponse(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class JobCreate(BaseModel):
    # Admin must provide company_id.
    # Recruiters use their own registered company.
    company_id: UUID | None = None
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=20)
    location: str = Field(min_length=2, max_length=150)
    employment_type: EmploymentType
    experience_level: ExperienceLevel
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    status: JobStatus = "draft"
    skills: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_salaries(self):
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("salary_min cannot exceed salary_max")
        return self


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=150)
    description: str | None = Field(default=None, min_length=20)
    location: str | None = Field(default=None, min_length=2)
    employment_type: EmploymentType | None = None
    experience_level: ExperienceLevel | None = None
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    status: JobStatus | None = None
    skills: list[str] | None = None

    @model_validator(mode="after")
    def validate_fields(self):
        # Reject explicit null values for required string/enum fields
        for field in ["title", "description", "location", "employment_type", "experience_level"]:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")

        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("salary_min cannot exceed salary_max")
        return self


class JobResponse(BaseModel):
    id: UUID
    company_id: UUID
    title: str
    description: str
    location: str
    employment_type: str
    experience_level: str
    salary_min: Decimal | None
    salary_max: Decimal | None
    status: str
    created_at: datetime
    updated_at: datetime
    skills: list[SkillResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
