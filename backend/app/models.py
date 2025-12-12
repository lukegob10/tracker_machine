from datetime import date, datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .enums import ProjectStatus, SolutionStatus, SubcomponentStatus


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class SoftDeleteMixin:
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )


class Project(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("project_name", name="uix_project_name"),)

    project_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    project_name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    name_abbreviation: Mapped[str] = mapped_column(String(4), nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), index=True, nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)


class Solution(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "solutions"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "solution_name",
            "version",
            name="uix_solution_project_name_version",
        ),
    )

    solution_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.project_id"), index=True
    )
    solution_name: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[SolutionStatus] = mapped_column(
        Enum(SolutionStatus), index=True, nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)


class Phase(TimestampMixin, Base):
    __tablename__ = "phases"

    phase_id: Mapped[str] = mapped_column(String, primary_key=True)
    phase_group: Mapped[str] = mapped_column(String, nullable=False)
    phase_name: Mapped[str] = mapped_column(String, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, index=True, nullable=False)


class SolutionPhase(TimestampMixin, Base):
    __tablename__ = "solution_phases"
    __table_args__ = (
        UniqueConstraint("solution_id", "phase_id", name="uix_solution_phase"),
    )

    solution_phase_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    solution_id: Mapped[str] = mapped_column(
        String, ForeignKey("solutions.solution_id"), index=True
    )
    phase_id: Mapped[str] = mapped_column(
        String, ForeignKey("phases.phase_id"), nullable=False
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sequence_override: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )


class Subcomponent(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "subcomponents"
    __table_args__ = (
        UniqueConstraint(
            "solution_id", "subcomponent_name", name="uix_subcomponent_solution_name"
        ),
    )

    subcomponent_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.project_id"), index=True
    )
    solution_id: Mapped[str] = mapped_column(
        String, ForeignKey("solutions.solution_id"), index=True
    )
    subcomponent_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[SubcomponentStatus] = mapped_column(
        Enum(SubcomponentStatus), index=True, nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False, index=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    sub_phase: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    dependencies: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    work_estimate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)


class SubcomponentPhaseStatus(TimestampMixin, Base):
    __tablename__ = "subcomponent_phase_status"
    __table_args__ = (
        UniqueConstraint(
            "subcomponent_id",
            "solution_phase_id",
            name="uix_subcomponent_solution_phase",
        ),
    )

    subcomponent_phase_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    subcomponent_id: Mapped[str] = mapped_column(
        String, ForeignKey("subcomponents.subcomponent_id"), index=True
    )
    solution_phase_id: Mapped[str] = mapped_column(
        String, ForeignKey("solution_phases.solution_phase_id"), nullable=False
    )
    phase_id: Mapped[str] = mapped_column(
        String, ForeignKey("phases.phase_id"), index=True, nullable=False
    )
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
