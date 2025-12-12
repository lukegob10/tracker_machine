from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .deps import get_db
from .enums import ProjectStatus
from .models import Project
from .schemas import ProjectCreate, ProjectRead, ProjectUpdate
from .utils import get_default_user_id

router = APIRouter()


def _project_query(session: Session):
    return session.query(Project).filter(Project.deleted_at.is_(None))


def _get_project_or_404(session: Session, project_id: str) -> Project:
    project = (
        session.query(Project)
        .filter(Project.project_id == project_id)
        .filter(Project.deleted_at.is_(None))
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get("", response_model=List[ProjectRead])
@router.get("/", response_model=List[ProjectRead])
def list_projects(
    status_filter: Optional[ProjectStatus] = None,
    session: Session = Depends(get_db),
):
    query = _project_query(session)
    if status_filter:
        query = query.filter(Project.status == status_filter)
    projects = query.all()
    return projects


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, session: Session = Depends(get_db)):
    existing = (
        session.query(Project)
        .filter(Project.project_name == payload.project_name)
        .filter(Project.deleted_at.is_(None))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Project name already exists"
        )

    project = Project(
        project_name=payload.project_name,
        name_abbreviation=payload.name_abbreviation,
        status=payload.status,
        description=payload.description,
        user_id=get_default_user_id(),
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, session: Session = Depends(get_db)):
    project = _get_project_or_404(session, project_id)
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(project_id: str, payload: ProjectUpdate, session: Session = Depends(get_db)):
    project = _get_project_or_404(session, project_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    project.updated_at = datetime.now(timezone.utc)

    if "project_name" in update_data and update_data["project_name"]:
        conflict = (
            session.query(Project)
            .filter(Project.project_name == update_data["project_name"])
            .filter(Project.project_id != project.project_id)
            .filter(Project.deleted_at.is_(None))
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Project name already exists"
            )

    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, session: Session = Depends(get_db)):
    project = _get_project_or_404(session, project_id)
    now = datetime.now(timezone.utc)
    project.deleted_at = now
    project.updated_at = now
    session.add(project)
    session.commit()
    return None
