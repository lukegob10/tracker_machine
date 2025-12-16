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
    Index,
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


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uix_user_email"),
        UniqueConstraint("soeid", name="uix_user_soeid"),
    )

    user_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    soeid: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    external_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class ChangeLog(Base):
    __tablename__ = "change_log"
    __table_args__ = (
        Index("idx_change_entity_created", "entity_type", "entity_id", "created_at"),
        Index("idx_change_user_created", "user_id", "created_at"),
        Index("idx_change_request", "request_id"),
    )

    change_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    field: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    old_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    request_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


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
    success_criteria: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sponsor: Mapped[str] = mapped_column(String, nullable=False, default="")
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
    priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False, index=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    current_phase: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    success_criteria: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    owner: Mapped[str] = mapped_column(String, nullable=False, default="")
    assignee: Mapped[str] = mapped_column(String, nullable=False, default="", index=True)
    approver: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    key_stakeholder: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    blockers: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    risks: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
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
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    assignee: Mapped[str] = mapped_column(String, nullable=False, default="")
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
