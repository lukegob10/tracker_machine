import csv
from datetime import datetime, timezone
from io import StringIO
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .deps import get_db, current_user as current_user_dep
from .enums import ProjectStatus, SolutionStatus
from .models import Project, Solution, User
from .schemas import SolutionCreate, SolutionRead, SolutionUpdate
from .utils import derive_abbreviation, enable_all_phases, normalize_status, normalize_str, read_csv
from .realtime import schedule_broadcast

router = APIRouter()


def _ensure_project_exists(session: Session, project_id: str) -> None:
    exists = (
        session.query(Project)
        .filter(Project.project_id == project_id)
        .filter(Project.deleted_at.is_(None))
        .first()
    )
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


def _solution_query(session: Session):
    return session.query(Solution).filter(Solution.deleted_at.is_(None))


def _get_solution_or_404(session: Session, solution_id: str) -> Solution:
    solution = (
        session.query(Solution)
        .filter(Solution.solution_id == solution_id)
        .filter(Solution.deleted_at.is_(None))
        .first()
    )
    if not solution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solution not found")
    return solution


@router.get(
    "/projects/{project_id}/solutions",
    response_model=List[SolutionRead],
)
def list_solutions(
    project_id: str,
    status_filter: Optional[SolutionStatus] = None,
    session: Session = Depends(get_db),
):
    _ensure_project_exists(session, project_id)
    query = _solution_query(session).filter(Solution.project_id == project_id)
    if status_filter:
        query = query.filter(Solution.status == status_filter)
    solutions = query.all()
    return solutions


@router.post(
    "/projects/{project_id}/solutions",
    response_model=SolutionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_solution(
    project_id: str,
    payload: SolutionCreate,
    session: Session = Depends(get_db),
    tasks: BackgroundTasks = None,
    current_user: User = Depends(current_user_dep),
):
    _ensure_project_exists(session, project_id)

    conflict = (
        _solution_query(session)
        .filter(Solution.project_id == project_id)
        .filter(Solution.solution_name == payload.solution_name)
        .filter(Solution.version == payload.version)
        .first()
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solution name and version already exist for this project",
        )

    solution = Solution(
        project_id=project_id,
        solution_name=payload.solution_name,
        version=payload.version,
        status=payload.status,
        description=payload.description,
        owner=payload.owner,
        key_stakeholder=payload.key_stakeholder,
        user_id=current_user.user_id,
    )
    session.add(solution)
    session.commit()
    session.refresh(solution)
    enable_all_phases(session, solution.solution_id)
    session.refresh(solution)
    schedule_broadcast("solutions")
    return solution


@router.post("/solutions/import")
def import_solutions(
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    tasks: BackgroundTasks = None,
    current_user: User = Depends(current_user_dep),
):
    rows, errors = read_csv(file.file.read())
    if errors:
        return {"created": 0, "updated": 0, "projects_created": 0, "errors": errors, "total_rows": 0}
    created = updated = projects_created = 0
    seen = set()

    projects_by_name = {
        p.project_name.lower(): p for p in session.query(Project).filter(Project.deleted_at.is_(None)).all()
    }
    abbrevs = {p.name_abbreviation for p in projects_by_name.values()}
    new_abbrevs = set()

    for idx, row in enumerate(rows, start=2):
        project_name = normalize_str(row.get("project_name"))
        solution_name = normalize_str(row.get("solution_name"))
        version_raw = normalize_str(row.get("version")) or "0.1.0"
        owner = normalize_str(row.get("owner"))
        key_stakeholder = normalize_str(row.get("key_stakeholder"))
        if not project_name or not solution_name or not owner:
            errors.append(f"Row {idx}: project_name, solution_name, and owner are required")
            continue
        key = (project_name.lower(), solution_name.lower(), version_raw.lower())
        if key in seen:
            errors.append(
                f"Row {idx}: duplicate solution '{solution_name}' version '{version_raw}' for project '{project_name}' in CSV (strict-first policy)"
            )
            continue
        seen.add(key)
        try:
            status_enum = normalize_status(
                row.get("status") or SolutionStatus.not_started.value, SolutionStatus
            )
        except ValueError as exc:
            errors.append(f"Row {idx}: {exc}")
            continue
        description = normalize_str(row.get("description")) or None

        project = projects_by_name.get(project_name.lower())
        if not project:
            try:
                abbr = derive_abbreviation(project_name, abbrevs | new_abbrevs)
            except ValueError as exc:
                errors.append(f"Row {idx}: {exc}")
                continue
            project = Project(
                project_name=project_name,
                name_abbreviation=abbr,
                status=ProjectStatus.not_started,
                description=None,
                user_id=current_user.user_id,
            )
            session.add(project)
            session.flush()  # ensure project_id is available
            projects_by_name[project_name.lower()] = project
            new_abbrevs.add(abbr)
            projects_created += 1

        existing = (
            _solution_query(session)
            .filter(Solution.project_id == project.project_id)
            .filter(Solution.solution_name == solution_name)
            .filter(Solution.version == version_raw)
            .first()
        )
        try:
            if existing:
                existing.status = status_enum
                existing.description = description
                existing.owner = owner
                existing.key_stakeholder = key_stakeholder or None
                existing.updated_at = datetime.now(timezone.utc)
                session.add(existing)
                updated += 1
                session.commit()
            else:
                solution = Solution(
                    project_id=project.project_id,
                    solution_name=solution_name,
                    version=version_raw,
                    status=status_enum,
                    description=description,
                    owner=owner,
                    key_stakeholder=key_stakeholder or None,
                    user_id=current_user.user_id,
                )
                session.add(solution)
                session.commit()
                enable_all_phases(session, solution.solution_id)
                created += 1
        except Exception as exc:
            session.rollback()
            errors.append(f"Row {idx}: {exc}")
    schedule_broadcast("solutions")
    return {
        "created": created,
        "updated": updated,
        "projects_created": projects_created,
        "errors": errors,
        "total_rows": len(rows),
    }


@router.get("/solutions/export")
def export_solutions(session: Session = Depends(get_db)):
    solutions = _solution_query(session).all()
    project_map = {
        p.project_id: p.project_name for p in session.query(Project).filter(Project.deleted_at.is_(None))
    }
    buffer = StringIO()
    fieldnames = ["project_name", "solution_name", "version", "status", "description", "owner", "key_stakeholder"]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for s in solutions:
        writer.writerow(
            {
                "project_name": project_map.get(s.project_id, ""),
                "solution_name": s.solution_name,
                "version": s.version,
                "status": s.status.value if hasattr(s.status, "value") else s.status,
                "description": s.description or "",
                "owner": s.owner or "",
                "key_stakeholder": s.key_stakeholder or "",
            }
        )
    buffer.seek(0)
    headers = {"Content-Disposition": 'attachment; filename=\"solutions.csv\"'}
    return StreamingResponse(buffer, media_type="text/csv", headers=headers)


@router.get("/solutions/{solution_id}", response_model=SolutionRead)
def get_solution(solution_id: str, session: Session = Depends(get_db)):
    solution = _get_solution_or_404(session, solution_id)
    return solution


@router.patch("/solutions/{solution_id}", response_model=SolutionRead)
def update_solution(
    solution_id: str,
    payload: SolutionUpdate,
    session: Session = Depends(get_db),
    tasks: BackgroundTasks = None,
):
    solution = _get_solution_or_404(session, solution_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(solution, field, value)
    solution.updated_at = datetime.now(timezone.utc)

    if any(k in update_data for k in ("solution_name", "version")):
        conflict = (
            _solution_query(session)
            .filter(Solution.project_id == solution.project_id)
            .filter(Solution.solution_name == solution.solution_name)
            .filter(Solution.version == solution.version)
            .filter(Solution.solution_id != solution.solution_id)
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solution name and version already exist for this project",
            )

    session.add(solution)
    session.commit()
    session.refresh(solution)
    schedule_broadcast("solutions")
    return solution


@router.delete("/solutions/{solution_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_solution(solution_id: str, session: Session = Depends(get_db), tasks: BackgroundTasks = None):
    solution = _get_solution_or_404(session, solution_id)
    now = datetime.now(timezone.utc)
    solution.deleted_at = now
    solution.updated_at = now
    session.add(solution)
    session.commit()
    schedule_broadcast("solutions")
    return None
