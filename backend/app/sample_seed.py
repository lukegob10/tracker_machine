import os
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from .enums import ProjectStatus, SolutionStatus, SubcomponentStatus
from .models import Project, Solution, Subcomponent


def seed_sample_data(session: Session) -> None:
    """
    Idempotent sample seed for local/dev use.
    Controlled by env var SAMPLE_SEED=true.
    """
    if os.getenv("SAMPLE_SEED", "").lower() != "true":
        return

    now = datetime.now(timezone.utc)
    project = (
        session.query(Project)
        .filter(Project.project_name == "Sample Project")
        .filter(Project.deleted_at.is_(None))
        .first()
    )
    if not project:
        project = Project(
            project_name="Sample Project",
            name_abbreviation="SAMP",
            status=ProjectStatus.active,
            description="Demo project for Jira-lite",
            created_at=now,
            updated_at=now,
        )
        session.add(project)
        session.commit()
        session.refresh(project)

    solution = (
        session.query(Solution)
        .filter(Solution.project_id == project.project_id)
        .filter(Solution.solution_name == "Demo Solution")
        .filter(Solution.version == "0.1.0")
        .filter(Solution.deleted_at.is_(None))
        .first()
    )
    if not solution:
        solution = Solution(
            project_id=project.project_id,
            solution_name="Demo Solution",
            version="0.1.0",
            status=SolutionStatus.active,
            description="Demo solution for seeding",
            created_at=now,
            updated_at=now,
        )
        session.add(solution)
        session.commit()
        session.refresh(solution)

    # Subcomponents seed
    existing = (
        session.query(Subcomponent)
        .filter(Subcomponent.solution_id == solution.solution_id)
        .filter(Subcomponent.deleted_at.is_(None))
        .all()
    )
    if existing:
        return

    subs = [
        Subcomponent(
            project_id=project.project_id,
            solution_id=solution.solution_id,
            subcomponent_name="Define RBAC roles",
            status=SubcomponentStatus.in_progress,
            priority=1,
            description="Document role matrix",
            due_date=date.today(),
            sub_phase=None,
            created_at=now,
            updated_at=now,
        ),
        Subcomponent(
            project_id=project.project_id,
            solution_id=solution.solution_id,
            subcomponent_name="Set up audit logging",
            status=SubcomponentStatus.to_do,
            priority=2,
            description="Centralized audit logging",
            due_date=None,
            sub_phase=None,
            created_at=now,
            updated_at=now,
        ),
    ]
    session.add_all(subs)
    session.commit()
