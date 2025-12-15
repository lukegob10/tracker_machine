from datetime import datetime, timezone
from typing import List, Optional

import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .deps import get_db, current_user as current_user_dep
from .enums import ProjectStatus
from .models import Project, User
from .schemas import ProjectCreate, ProjectRead, ProjectUpdate
from .utils import derive_abbreviation, normalize_status, normalize_str, read_csv
from .realtime import schedule_broadcast

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
def create_project(
    payload: ProjectCreate,
    session: Session = Depends(get_db),
    tasks: BackgroundTasks = None,
    current_user: User = Depends(current_user_dep),
):
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
        sponsor=payload.sponsor,
        user_id=current_user.user_id,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    schedule_broadcast("projects")
    return project


@router.post("/import")
def import_projects(
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    tasks: BackgroundTasks = None,
    current_user: User = Depends(current_user_dep),
):
    rows, errors = read_csv(file.file.read())
    if errors:
        return {"created": 0, "updated": 0, "errors": errors, "total_rows": 0}
    created = updated = 0
    seen = set()
    existing_abbrevs = {p.name_abbreviation for p in _project_query(session).all()}
    new_abbrevs = set()

    for idx, row in enumerate(rows, start=2):  # header is row 1
        name = normalize_str(row.get("project_name"))
        sponsor = normalize_str(row.get("sponsor"))
        if not name:
            errors.append(f"Row {idx}: project_name is required")
            continue
        if not sponsor:
            errors.append(f"Row {idx}: sponsor is required")
            continue
        key = name.lower()
        if key in seen:
            errors.append(f"Row {idx}: duplicate project_name '{name}' in CSV (strict-first policy)")
            continue
        seen.add(key)

        abbr_raw = normalize_str(row.get("name_abbreviation"))
        try:
            if len(abbr_raw) == 4:
                abbr = abbr_raw
            else:
                abbr = derive_abbreviation(name, existing_abbrevs | new_abbrevs)
            status_enum = normalize_status(
                row.get("status") or ProjectStatus.not_started.value, ProjectStatus
            )
        except ValueError as exc:
            errors.append(f"Row {idx}: {exc}")
            continue

        description = normalize_str(row.get("description")) or None
        existing = _project_query(session).filter(Project.project_name == name).first()
        try:
            if existing:
                existing.name_abbreviation = abbr
                existing.status = status_enum
                existing.description = description
                existing.sponsor = sponsor
                existing.updated_at = datetime.now(timezone.utc)
                session.add(existing)
                updated += 1
            else:
                project = Project(
                    project_name=name,
                    name_abbreviation=abbr,
                    status=status_enum,
                    description=description,
                    sponsor=sponsor,
                    user_id=current_user.user_id,
                )
                session.add(project)
                created += 1
                new_abbrevs.add(abbr)
            session.commit()
        except Exception as exc:
            session.rollback()
            errors.append(f"Row {idx}: {exc}")
    schedule_broadcast("projects")
    return {"created": created, "updated": updated, "errors": errors, "total_rows": len(rows)}


@router.get("/export")
def export_projects(session: Session = Depends(get_db)):
    projects = _project_query(session).all()
    buffer = StringIO()
    fieldnames = ["project_name", "name_abbreviation", "status", "description", "sponsor"]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for p in projects:
        writer.writerow(
            {
                "project_name": p.project_name,
                "name_abbreviation": p.name_abbreviation,
                "status": p.status.value if hasattr(p.status, "value") else p.status,
                "description": p.description or "",
                "sponsor": p.sponsor or "",
            }
        )
    buffer.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="projects.csv"'}
    return StreamingResponse(buffer, media_type="text/csv", headers=headers)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, session: Session = Depends(get_db)):
    project = _get_project_or_404(session, project_id)
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(project_id: str, payload: ProjectUpdate, session: Session = Depends(get_db), tasks: BackgroundTasks = None):
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
    schedule_broadcast("projects")
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, session: Session = Depends(get_db), tasks: BackgroundTasks = None):
    project = _get_project_or_404(session, project_id)
    now = datetime.now(timezone.utc)
    project.deleted_at = now
    project.updated_at = now
    session.add(project)
    session.commit()
    schedule_broadcast("projects")
    return None
