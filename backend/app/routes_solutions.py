import csv
from datetime import date, datetime, timezone
from io import StringIO
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from .deps import get_db, current_user as current_user_dep
from .enums import ProjectStatus, SolutionStatus
from .models import Phase, Project, Solution, SolutionPhase, User
from .schemas import SolutionCreate, SolutionRead, SolutionUpdate
from .utils import (
    derive_abbreviation,
    enable_all_phases,
    normalize_status,
    normalize_str,
    parse_date,
    parse_priority,
    read_csv,
)
from .realtime import schedule_broadcast
from .audit_log import log_changes

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


def _enabled_phase_ids(session: Session, solution_id: str) -> set[str]:
    rows = (
        session.query(SolutionPhase.phase_id)
        .filter(SolutionPhase.solution_id == solution_id)
        .filter(SolutionPhase.is_enabled.is_(True))
        .all()
    )
    return {r[0] for r in rows}


def _last_enabled_phase_id(session: Session, solution_id: str) -> Optional[str]:
    sort_key = func.coalesce(SolutionPhase.sequence_override, Phase.sequence)
    row = (
        session.query(SolutionPhase.phase_id)
        .join(Phase, Phase.phase_id == SolutionPhase.phase_id)
        .filter(SolutionPhase.solution_id == solution_id)
        .filter(SolutionPhase.is_enabled.is_(True))
        .order_by(sort_key.desc(), Phase.sequence.desc(), SolutionPhase.solution_phase_id.desc())
        .first()
    )
    return row[0] if row else None


def _validate_current_phase(session: Session, solution_id: str, current_phase: Optional[str]) -> None:
    if not current_phase:
        return
    phase_exists = session.query(Phase).filter(Phase.phase_id == current_phase).first()
    if not phase_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"current_phase '{current_phase}' does not exist",
        )
    enabled = _enabled_phase_ids(session, solution_id)
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No phases enabled for this solution; current_phase must be null",
        )
    if current_phase not in enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="current_phase must be one of the enabled phases for this solution",
        )


@router.get(
    "/solutions",
    response_model=List[SolutionRead],
)
def list_all_solutions(
    project_id: Optional[str] = None,
    status_filter: Optional[SolutionStatus] = Query(None, alias="status"),
    owner: Optional[str] = None,
    assignee: Optional[str] = None,
    phase: Optional[str] = None,
    priority: Optional[int] = None,
    due_before: Optional[date] = None,
    due_after: Optional[date] = None,
    session: Session = Depends(get_db),
):
    query = _solution_query(session)
    if project_id:
        query = query.filter(Solution.project_id == project_id)
    if status_filter:
        query = query.filter(Solution.status == status_filter)
    if owner:
        query = query.filter(func.lower(Solution.owner) == owner.strip().lower())
    if assignee:
        query = query.filter(func.lower(Solution.assignee) == assignee.strip().lower())
    if phase:
        query = query.filter(Solution.current_phase == phase)
    if priority is not None:
        query = query.filter(Solution.priority == priority)
    if due_before:
        query = query.filter(Solution.due_date <= due_before)
    if due_after:
        query = query.filter(Solution.due_date >= due_after)
    return query.order_by(Solution.priority.asc(), Solution.created_at.asc()).all()


@router.get(
    "/projects/{project_id}/solutions",
    response_model=List[SolutionRead],
)
def list_solutions(
    project_id: str,
    status_filter: Optional[SolutionStatus] = Query(None, alias="status"),
    owner: Optional[str] = None,
    assignee: Optional[str] = None,
    phase: Optional[str] = None,
    priority: Optional[int] = None,
    due_before: Optional[date] = None,
    due_after: Optional[date] = None,
    session: Session = Depends(get_db),
):
    _ensure_project_exists(session, project_id)
    query = _solution_query(session).filter(Solution.project_id == project_id)
    if status_filter:
        query = query.filter(Solution.status == status_filter)
    if owner:
        query = query.filter(func.lower(Solution.owner) == owner.strip().lower())
    if assignee:
        query = query.filter(func.lower(Solution.assignee) == assignee.strip().lower())
    if phase:
        query = query.filter(Solution.current_phase == phase)
    if priority is not None:
        query = query.filter(Solution.priority == priority)
    if due_before:
        query = query.filter(Solution.due_date <= due_before)
    if due_after:
        query = query.filter(Solution.due_date >= due_after)
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

    current_phase = normalize_str(payload.current_phase) or None
    if current_phase:
        phase_exists = session.query(Phase).filter(Phase.phase_id == current_phase).first()
        if not phase_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"current_phase '{current_phase}' does not exist",
            )

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

    now = datetime.now(timezone.utc)
    completed_at = now if payload.status == SolutionStatus.complete else None
    priority_val = parse_priority(payload.priority, default=3)

    solution = Solution(
        project_id=project_id,
        solution_name=payload.solution_name,
        version=payload.version,
        status=payload.status,
        priority=priority_val,
        due_date=payload.due_date,
        current_phase=current_phase,
        description=payload.description,
        success_criteria=payload.success_criteria,
        owner=payload.owner,
        assignee=payload.assignee or "",
        approver=payload.approver,
        key_stakeholder=payload.key_stakeholder,
        blockers=payload.blockers,
        risks=payload.risks,
        completed_at=completed_at,
        created_at=now,
        updated_at=now,
        user_id=current_user.user_id,
    )
    session.add(solution)
    session.flush()
    log_changes(
        session,
        entity_type="solution",
        entity_id=solution.solution_id,
        user_id=current_user.user_id,
        action="create",
        changes={
            "solution_name": (None, solution.solution_name),
            "version": (None, solution.version),
            "status": (None, solution.status),
            "priority": (None, solution.priority),
            "due_date": (None, solution.due_date),
            "current_phase": (None, solution.current_phase),
            "description": (None, solution.description),
            "success_criteria": (None, solution.success_criteria),
            "owner": (None, solution.owner),
            "assignee": (None, solution.assignee),
            "approver": (None, solution.approver),
            "key_stakeholder": (None, solution.key_stakeholder),
            "blockers": (None, solution.blockers),
            "risks": (None, solution.risks),
            "completed_at": (None, solution.completed_at),
        },
    )
    session.commit()
    session.refresh(solution)
    enable_all_phases(session, solution.solution_id)
    session.refresh(solution)
    schedule_broadcast("solutions")
    return solution


@router.post("/solutions/import")
def import_solutions(
    csv_bytes: bytes = Body(..., media_type="text/csv"),
    session: Session = Depends(get_db),
    tasks: BackgroundTasks = None,
    current_user: User = Depends(current_user_dep),
):
    rows, errors = read_csv(csv_bytes)
    if errors:
        return {"created": 0, "updated": 0, "projects_created": 0, "errors": errors, "total_rows": 0}
    created = updated = projects_created = 0
    seen = set()
    request_id = str(uuid4())

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
        assignee = normalize_str(row.get("assignee"))
        approver = normalize_str(row.get("approver")) or None
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
            priority_val = parse_priority(row.get("priority"), default=3)
            due_date_val = parse_date(row.get("due_date"))
        except ValueError as exc:
            errors.append(f"Row {idx}: {exc}")
            continue
        description = normalize_str(row.get("description")) or None
        success_criteria = normalize_str(row.get("success_criteria")) or None
        current_phase = normalize_str(row.get("current_phase")) or None
        if current_phase:
            phase_exists = session.query(Phase).filter(Phase.phase_id == current_phase).first()
            if not phase_exists:
                errors.append(f"Row {idx}: current_phase '{current_phase}' does not exist")
                continue
        blockers = normalize_str(row.get("blockers")) or None
        risks = normalize_str(row.get("risks")) or None

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
            log_changes(
                session,
                entity_type="project",
                entity_id=project.project_id,
                user_id=current_user.user_id,
                action="create",
                changes={
                    "project_name": (None, project.project_name),
                    "name_abbreviation": (None, project.name_abbreviation),
                    "status": (None, project.status),
                    "description": (None, project.description),
                    "success_criteria": (None, project.success_criteria),
                },
                request_id=request_id,
            )

        existing = (
            _solution_query(session)
            .filter(Solution.project_id == project.project_id)
            .filter(Solution.solution_name == solution_name)
            .filter(Solution.version == version_raw)
            .first()
        )
        try:
            if existing:
                if current_phase:
                    _validate_current_phase(session, existing.solution_id, current_phase)

                before = {
                    "status": existing.status,
                    "priority": existing.priority,
                    "due_date": existing.due_date,
                    "current_phase": existing.current_phase,
                    "description": existing.description,
                    "success_criteria": existing.success_criteria,
                    "owner": existing.owner,
                    "assignee": existing.assignee,
                    "approver": existing.approver,
                    "key_stakeholder": existing.key_stakeholder,
                    "blockers": existing.blockers,
                    "risks": existing.risks,
                    "completed_at": existing.completed_at,
                }
                now = datetime.now(timezone.utc)
                existing.status = status_enum
                existing.priority = priority_val
                existing.due_date = due_date_val
                existing.current_phase = current_phase
                existing.description = description
                existing.success_criteria = success_criteria
                existing.owner = owner
                existing.assignee = assignee or ""
                existing.approver = approver
                existing.key_stakeholder = key_stakeholder or None
                existing.blockers = blockers
                existing.risks = risks
                if status_enum == SolutionStatus.complete and not existing.completed_at:
                    existing.completed_at = now
                    if not existing.current_phase:
                        existing.current_phase = _last_enabled_phase_id(session, existing.solution_id)
                existing.updated_at = now
                session.add(existing)
                log_changes(
                    session,
                    entity_type="solution",
                    entity_id=existing.solution_id,
                    user_id=current_user.user_id,
                    action="update",
                    changes={
                        "status": (before["status"], existing.status),
                        "priority": (before["priority"], existing.priority),
                        "due_date": (before["due_date"], existing.due_date),
                        "current_phase": (before["current_phase"], existing.current_phase),
                        "description": (before["description"], existing.description),
                        "success_criteria": (before["success_criteria"], existing.success_criteria),
                        "owner": (before["owner"], existing.owner),
                        "assignee": (before["assignee"], existing.assignee),
                        "approver": (before["approver"], existing.approver),
                        "key_stakeholder": (before["key_stakeholder"], existing.key_stakeholder),
                        "blockers": (before["blockers"], existing.blockers),
                        "risks": (before["risks"], existing.risks),
                        "completed_at": (before["completed_at"], existing.completed_at),
                    },
                    request_id=request_id,
                )
                updated += 1
                session.commit()
            else:
                now = datetime.now(timezone.utc)
                completed_at = now if status_enum == SolutionStatus.complete else None
                solution = Solution(
                    project_id=project.project_id,
                    solution_name=solution_name,
                    version=version_raw,
                    status=status_enum,
                    priority=priority_val,
                    due_date=due_date_val,
                    current_phase=current_phase,
                    description=description,
                    success_criteria=success_criteria,
                    owner=owner,
                    assignee=assignee or "",
                    approver=approver,
                    key_stakeholder=key_stakeholder or None,
                    blockers=blockers,
                    risks=risks,
                    completed_at=completed_at,
                    user_id=current_user.user_id,
                )
                session.add(solution)
                session.flush()
                log_changes(
                    session,
                    entity_type="solution",
                    entity_id=solution.solution_id,
                    user_id=current_user.user_id,
                    action="create",
                    changes={
                        "solution_name": (None, solution.solution_name),
                        "version": (None, solution.version),
                        "status": (None, solution.status),
                        "priority": (None, solution.priority),
                        "due_date": (None, solution.due_date),
                        "current_phase": (None, solution.current_phase),
                        "description": (None, solution.description),
                        "success_criteria": (None, solution.success_criteria),
                        "owner": (None, solution.owner),
                        "assignee": (None, solution.assignee),
                        "approver": (None, solution.approver),
                        "key_stakeholder": (None, solution.key_stakeholder),
                        "blockers": (None, solution.blockers),
                        "risks": (None, solution.risks),
                        "completed_at": (None, solution.completed_at),
                    },
                    request_id=request_id,
                )
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
    fieldnames = [
        "project_name",
        "solution_name",
        "version",
        "status",
        "priority",
        "due_date",
        "current_phase",
        "description",
        "success_criteria",
        "owner",
        "assignee",
        "approver",
        "key_stakeholder",
        "blockers",
        "risks",
        "completed_at",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for s in solutions:
        writer.writerow(
            {
                "project_name": project_map.get(s.project_id, ""),
                "solution_name": s.solution_name,
                "version": s.version,
                "status": s.status.value if hasattr(s.status, "value") else s.status,
                "priority": s.priority,
                "due_date": s.due_date.isoformat() if s.due_date else "",
                "current_phase": s.current_phase or "",
                "description": s.description or "",
                "success_criteria": s.success_criteria or "",
                "owner": s.owner or "",
                "assignee": s.assignee or "",
                "approver": s.approver or "",
                "key_stakeholder": s.key_stakeholder or "",
                "blockers": s.blockers or "",
                "risks": s.risks or "",
                "completed_at": s.completed_at.isoformat() if s.completed_at else "",
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
    current_user: User = Depends(current_user_dep),
):
    solution = _get_solution_or_404(session, solution_id)

    update_data = payload.model_dump(exclude_unset=True)
    if "priority" in update_data:
        update_data["priority"] = parse_priority(update_data["priority"], default=3)
    if "current_phase" in update_data:
        update_data["current_phase"] = normalize_str(update_data["current_phase"]) or None
        if update_data["current_phase"]:
            _validate_current_phase(session, solution.solution_id, update_data["current_phase"])

    before = {field: getattr(solution, field) for field in update_data.keys()}
    for field, value in update_data.items():
        setattr(solution, field, value)
    solution.updated_at = datetime.now(timezone.utc)

    if "status" in update_data and update_data["status"] == SolutionStatus.complete:
        solution.completed_at = solution.completed_at or datetime.now(timezone.utc)
        if not solution.current_phase:
            solution.current_phase = _last_enabled_phase_id(session, solution.solution_id)

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
    if update_data:
        log_changes(
            session,
            entity_type="solution",
            entity_id=solution.solution_id,
            user_id=current_user.user_id,
            action="update",
            changes={field: (before.get(field), getattr(solution, field)) for field in update_data.keys()},
        )
    session.commit()
    session.refresh(solution)
    schedule_broadcast("solutions")
    return solution


@router.delete("/solutions/{solution_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_solution(
    solution_id: str,
    session: Session = Depends(get_db),
    tasks: BackgroundTasks = None,
    current_user: User = Depends(current_user_dep),
):
    solution = _get_solution_or_404(session, solution_id)
    now = datetime.now(timezone.utc)
    solution.deleted_at = now
    solution.updated_at = now
    session.add(solution)
    log_changes(
        session,
        entity_type="solution",
        entity_id=solution.solution_id,
        user_id=current_user.user_id,
        action="delete",
        changes={"deleted_at": (None, now)},
    )
    session.commit()
    schedule_broadcast("solutions")
    return None
