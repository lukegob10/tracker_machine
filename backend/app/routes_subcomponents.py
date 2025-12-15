import csv
from datetime import datetime, timezone, date
from io import StringIO
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .deps import get_db, current_user as current_user_dep
from .enums import ProjectStatus, SolutionStatus, SubcomponentStatus
from .models import Phase, Project, Solution, SolutionPhase, Subcomponent, User
from .schemas import (
    SubcomponentCreate,
    SubcomponentRead,
    SubcomponentUpdate,
)
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


def _ensure_solution(session: Session, solution_id: str) -> Solution:
    solution = (
        session.query(Solution)
        .filter(Solution.solution_id == solution_id)
        .filter(Solution.deleted_at.is_(None))
        .first()
    )
    if not solution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solution not found")
    return solution


def _get_subcomponent(session: Session, subcomponent_id: str) -> Subcomponent:
    sc = (
        session.query(Subcomponent)
        .filter(Subcomponent.subcomponent_id == subcomponent_id)
        .filter(Subcomponent.deleted_at.is_(None))
        .first()
    )
    if not sc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subcomponent not found")
    return sc


def _enabled_phase_ids(session: Session, solution_id: str) -> list[str]:
    rows = (
        session.query(SolutionPhase.phase_id)
        .filter(SolutionPhase.solution_id == solution_id)
        .filter(SolutionPhase.is_enabled.is_(True))
        .all()
    )
    return [r[0] for r in rows]


def _validate_sub_phase(session: Session, solution_id: str, sub_phase: Optional[str]):
    enabled_ids = _enabled_phase_ids(session, solution_id)
    if not enabled_ids and sub_phase:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No phases enabled for this solution; sub_phase must be null",
        )
    if sub_phase and sub_phase not in enabled_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sub_phase must be one of the enabled phases for this solution",
        )


@router.get(
    "/solutions/{solution_id}/subcomponents",
    response_model=List[SubcomponentRead],
)
def list_subcomponents(
    solution_id: str,
    status_filter: Optional[SubcomponentStatus] = Query(None, alias="status"),
    priority: Optional[int] = None,
    sub_phase: Optional[str] = None,
    due_before: Optional[date] = None,
    due_after: Optional[date] = None,
    owner: Optional[str] = None,
    assignee: Optional[str] = None,
    session: Session = Depends(get_db),
):
    _ensure_solution(session, solution_id)
    query = (
        session.query(Subcomponent)
        .filter(Subcomponent.solution_id == solution_id)
        .filter(Subcomponent.deleted_at.is_(None))
    )
    if status_filter:
        query = query.filter(Subcomponent.status == status_filter)
    if priority is not None:
        query = query.filter(Subcomponent.priority == priority)
    if sub_phase:
        query = query.filter(Subcomponent.sub_phase == sub_phase)
    if due_before:
        query = query.filter(Subcomponent.due_date <= due_before)
    if due_after:
        query = query.filter(Subcomponent.due_date >= due_after)
    if owner:
        query = query.filter(Subcomponent.owner == owner)
    if assignee:
        query = query.filter(Subcomponent.assignee == assignee)
    # optional search could be added later
    return query.order_by(Subcomponent.priority.asc(), Subcomponent.created_at.asc()).all()


@router.post(
    "/solutions/{solution_id}/subcomponents",
    response_model=SubcomponentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_subcomponent(
    solution_id: str,
    payload: SubcomponentCreate,
    session: Session = Depends(get_db),
    tasks: BackgroundTasks = None,
    current_user: User = Depends(current_user_dep),
):
    solution = _ensure_solution(session, solution_id)
    _validate_sub_phase(session, solution_id, payload.sub_phase)

    conflict = (
        session.query(Subcomponent)
        .filter(Subcomponent.solution_id == solution_id)
        .filter(Subcomponent.subcomponent_name == payload.subcomponent_name)
        .filter(Subcomponent.deleted_at.is_(None))
        .first()
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subcomponent name already exists in this solution",
        )

    now = datetime.now(timezone.utc)
    completed_at = now if payload.status == SubcomponentStatus.complete else None

    subcomponent = Subcomponent(
        project_id=solution.project_id,
        solution_id=solution_id,
        subcomponent_name=payload.subcomponent_name,
        status=payload.status,
        priority=payload.priority,
        due_date=payload.due_date,
        sub_phase=payload.sub_phase,
        description=payload.description,
        notes=payload.notes,
        category=payload.category,
        dependencies=payload.dependencies,
        work_estimate=payload.work_estimate,
        completed_at=completed_at,
        owner=payload.owner,
        assignee=payload.assignee,
        approver=payload.approver,
        created_at=now,
        updated_at=now,
        user_id=current_user.user_id,
    )
    session.add(subcomponent)
    session.flush()
    log_changes(
        session,
        entity_type="subcomponent",
        entity_id=subcomponent.subcomponent_id,
        user_id=current_user.user_id,
        action="create",
        changes={
            "subcomponent_name": (None, subcomponent.subcomponent_name),
            "status": (None, subcomponent.status),
            "priority": (None, subcomponent.priority),
            "due_date": (None, subcomponent.due_date),
            "sub_phase": (None, subcomponent.sub_phase),
            "owner": (None, subcomponent.owner),
            "assignee": (None, subcomponent.assignee),
            "approver": (None, subcomponent.approver),
        },
    )
    session.commit()
    session.refresh(subcomponent)
    schedule_broadcast("subcomponents")
    return subcomponent


@router.post("/subcomponents/import")
def import_subcomponents(
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    tasks: BackgroundTasks = None,
    current_user: User = Depends(current_user_dep),
):
    rows, errors = read_csv(file.file.read())
    if errors:
        return {
            "created": 0,
            "updated": 0,
            "projects_created": 0,
            "solutions_created": 0,
            "errors": errors,
            "total_rows": 0,
        }
    created = updated = projects_created = solutions_created = 0
    seen = set()
    request_id = str(uuid4())

    projects_by_name = {
        p.project_name.lower(): p for p in session.query(Project).filter(Project.deleted_at.is_(None)).all()
    }
    abbrevs = {p.name_abbreviation for p in projects_by_name.values()}
    new_abbrevs = set()
    solutions_by_key = {
        (s.project_id, s.solution_name.lower(), s.version.lower()): s
        for s in session.query(Solution).filter(Solution.deleted_at.is_(None)).all()
    }

    for idx, row in enumerate(rows, start=2):
        project_name = normalize_str(row.get("project_name"))
        solution_name = normalize_str(row.get("solution_name"))
        sub_name = normalize_str(row.get("subcomponent_name"))
        version_raw = normalize_str(row.get("version")) or "0.1.0"
        owner_val = normalize_str(row.get("owner"))
        assignee_val = normalize_str(row.get("assignee"))
        approver_val = normalize_str(row.get("approver")) or None
        if not project_name or not solution_name or not sub_name or not owner_val or not assignee_val:
            errors.append(
                f"Row {idx}: project_name, solution_name, subcomponent_name, owner, and assignee are required"
            )
            continue
        key = (project_name.lower(), solution_name.lower(), version_raw.lower(), sub_name.lower())
        if key in seen:
            errors.append(
                f"Row {idx}: duplicate subcomponent '{sub_name}' for solution '{solution_name}' in project '{project_name}' (strict-first policy)"
            )
            continue
        seen.add(key)

        try:
            status_enum = normalize_status(
                row.get("status") or SubcomponentStatus.to_do.value, SubcomponentStatus
            )
            priority_val = parse_priority(row.get("priority"), default=3)
            due_val = parse_date(row.get("due_date"))
        except ValueError as exc:
            errors.append(f"Row {idx}: {exc}")
            continue

        description = normalize_str(row.get("description")) or None
        notes = normalize_str(row.get("notes")) or None
        category = normalize_str(row.get("category")) or None
        dependencies = normalize_str(row.get("dependencies")) or None
        work_estimate_raw = normalize_str(row.get("work_estimate"))
        work_estimate = None
        if work_estimate_raw:
            try:
                work_estimate = float(work_estimate_raw)
            except ValueError:
                errors.append(f"Row {idx}: work_estimate must be numeric")
                continue

        project = projects_by_name.get(project_name.lower())
        if not project:
            try:
                abbr = derive_abbreviation(project_name, abbrevs | new_abbrevs)
            except ValueError as exc:
                errors.append(f"Row {idx}: {exc}")
                continue
            sponsor_val = owner_val or "Auto-created"
            project = Project(
                project_name=project_name,
                name_abbreviation=abbr,
                status=ProjectStatus.not_started,
                description=None,
                sponsor=sponsor_val,
                user_id=current_user.user_id,
            )
            session.add(project)
            session.flush()  # ensure project_id available
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
                    "sponsor": (None, project.sponsor),
                },
                request_id=request_id,
            )

        solution_key = (project.project_id, solution_name.lower(), version_raw.lower())
        solution = solutions_by_key.get(solution_key)
        if not solution:
            try:
                solution = Solution(
                    project_id=project.project_id,
                    solution_name=solution_name,
                    version=version_raw,
                    status=SolutionStatus.not_started,
                    description=None,
                    owner=owner_val or "Auto-created",
                    key_stakeholder=None,
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
                        "description": (None, solution.description),
                        "owner": (None, solution.owner),
                        "key_stakeholder": (None, solution.key_stakeholder),
                    },
                    request_id=request_id,
                )
                session.commit()
                enable_all_phases(session, solution.solution_id)
                solutions_by_key[solution_key] = solution
                solutions_created += 1
            except Exception as exc:
                session.rollback()
                errors.append(f"Row {idx}: {exc}")
                continue

        try:
            enabled_phase_ids = _enabled_phase_ids(session, solution.solution_id)
            sub_phase = normalize_str(row.get("sub_phase")) or None
            if sub_phase and sub_phase not in enabled_phase_ids:
                raise ValueError(f"sub_phase '{sub_phase}' is not enabled for solution '{solution.solution_name}'")

            existing = (
                session.query(Subcomponent)
                .filter(Subcomponent.solution_id == solution.solution_id)
                .filter(Subcomponent.subcomponent_name == sub_name)
                .filter(Subcomponent.deleted_at.is_(None))
                .first()
            )
            if existing:
                before = {
                    "status": existing.status,
                    "priority": existing.priority,
                    "due_date": existing.due_date,
                    "sub_phase": existing.sub_phase,
                    "description": existing.description,
                    "notes": existing.notes,
                    "category": existing.category,
                    "dependencies": existing.dependencies,
                    "work_estimate": existing.work_estimate,
                    "owner": existing.owner,
                    "assignee": existing.assignee,
                    "approver": existing.approver,
                    "completed_at": existing.completed_at,
                }
                existing.status = status_enum
                existing.priority = priority_val
                existing.due_date = due_val
                existing.sub_phase = sub_phase
                existing.description = description
                existing.notes = notes
                existing.category = category
                existing.dependencies = dependencies
                existing.work_estimate = work_estimate
                existing.owner = owner_val
                existing.assignee = assignee_val
                existing.approver = approver_val
                existing.updated_at = datetime.now(timezone.utc)
                if status_enum == SubcomponentStatus.complete and not existing.completed_at:
                    existing.completed_at = datetime.now(timezone.utc)
                session.add(existing)
                log_changes(
                    session,
                    entity_type="subcomponent",
                    entity_id=existing.subcomponent_id,
                    user_id=current_user.user_id,
                    action="update",
                    changes={
                        "status": (before["status"], existing.status),
                        "priority": (before["priority"], existing.priority),
                        "due_date": (before["due_date"], existing.due_date),
                        "sub_phase": (before["sub_phase"], existing.sub_phase),
                        "description": (before["description"], existing.description),
                        "notes": (before["notes"], existing.notes),
                        "category": (before["category"], existing.category),
                        "dependencies": (before["dependencies"], existing.dependencies),
                        "work_estimate": (before["work_estimate"], existing.work_estimate),
                        "owner": (before["owner"], existing.owner),
                        "assignee": (before["assignee"], existing.assignee),
                        "approver": (before["approver"], existing.approver),
                        "completed_at": (before["completed_at"], existing.completed_at),
                    },
                    request_id=request_id,
                )
                session.commit()
                updated += 1
            else:
                completed_at = (
                    datetime.now(timezone.utc) if status_enum == SubcomponentStatus.complete else None
                )
                subcomponent = Subcomponent(
                    project_id=project.project_id,
                    solution_id=solution.solution_id,
                    subcomponent_name=sub_name,
                    status=status_enum,
                    priority=priority_val,
                    due_date=due_val,
                    sub_phase=sub_phase,
                    description=description,
                    notes=notes,
                    category=category,
                    dependencies=dependencies,
                    work_estimate=work_estimate,
                    owner=owner_val,
                    assignee=assignee_val,
                    approver=approver_val,
                    completed_at=completed_at,
                    user_id=current_user.user_id,
                )
                session.add(subcomponent)
                session.flush()
                log_changes(
                    session,
                    entity_type="subcomponent",
                    entity_id=subcomponent.subcomponent_id,
                    user_id=current_user.user_id,
                    action="create",
                    changes={
                        "subcomponent_name": (None, subcomponent.subcomponent_name),
                        "status": (None, subcomponent.status),
                        "priority": (None, subcomponent.priority),
                        "due_date": (None, subcomponent.due_date),
                        "sub_phase": (None, subcomponent.sub_phase),
                        "description": (None, subcomponent.description),
                        "notes": (None, subcomponent.notes),
                        "category": (None, subcomponent.category),
                        "dependencies": (None, subcomponent.dependencies),
                        "work_estimate": (None, subcomponent.work_estimate),
                        "owner": (None, subcomponent.owner),
                        "assignee": (None, subcomponent.assignee),
                        "approver": (None, subcomponent.approver),
                        "completed_at": (None, subcomponent.completed_at),
                    },
                    request_id=request_id,
                )
                session.commit()
                created += 1
        except ValueError as exc:
            session.rollback()
            errors.append(f"Row {idx}: {exc}")
        except Exception as exc:
            session.rollback()
            errors.append(f"Row {idx}: {exc}")

    schedule_broadcast("subcomponents")
    return {
        "created": created,
        "updated": updated,
        "projects_created": projects_created,
        "solutions_created": solutions_created,
        "errors": errors,
        "total_rows": len(rows),
    }


@router.get("/subcomponents/export")
def export_subcomponents(session: Session = Depends(get_db)):
    subs = (
        session.query(Subcomponent)
        .filter(Subcomponent.deleted_at.is_(None))
        .order_by(Subcomponent.created_at.asc())
        .all()
    )
    project_map = {p.project_id: p.project_name for p in session.query(Project).filter(Project.deleted_at.is_(None))}
    solution_map = {
        s.solution_id: (s.solution_name, s.version)
        for s in session.query(Solution).filter(Solution.deleted_at.is_(None))
    }
    buffer = StringIO()
    fieldnames = [
        "project_name",
        "solution_name",
        "version",
        "subcomponent_name",
        "status",
        "priority",
        "due_date",
        "sub_phase",
        "description",
        "notes",
        "category",
        "dependencies",
        "work_estimate",
        "owner",
        "assignee",
        "approver",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for sc in subs:
        sol_name, sol_version = solution_map.get(sc.solution_id, ("", ""))
        writer.writerow(
            {
                "project_name": project_map.get(sc.project_id, ""),
                "solution_name": sol_name,
                "version": sol_version,
                "subcomponent_name": sc.subcomponent_name,
                "status": sc.status.value if hasattr(sc.status, "value") else sc.status,
                "priority": sc.priority,
                "due_date": sc.due_date.isoformat() if sc.due_date else "",
                "sub_phase": sc.sub_phase or "",
                "description": sc.description or "",
                "notes": sc.notes or "",
                "category": sc.category or "",
                "dependencies": sc.dependencies or "",
                "work_estimate": sc.work_estimate if sc.work_estimate is not None else "",
                "owner": sc.owner or "",
                "assignee": sc.assignee or "",
                "approver": sc.approver or "",
            }
        )
    buffer.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="subcomponents.csv"'}
    return StreamingResponse(buffer, media_type="text/csv", headers=headers)


@router.get("/subcomponents/{subcomponent_id}", response_model=SubcomponentRead)
def get_subcomponent(subcomponent_id: str, session: Session = Depends(get_db)):
    return _get_subcomponent(session, subcomponent_id)


@router.patch("/subcomponents/{subcomponent_id}", response_model=SubcomponentRead)
def update_subcomponent(
    subcomponent_id: str,
    payload: SubcomponentUpdate,
    session: Session = Depends(get_db),
    tasks: BackgroundTasks = None,
    current_user: User = Depends(current_user_dep),
):
    subcomponent = _get_subcomponent(session, subcomponent_id)
    if "sub_phase" in payload.model_fields_set:
        _validate_sub_phase(session, subcomponent.solution_id, payload.sub_phase)

    update_data = payload.model_dump(exclude_unset=True)
    before = {field: getattr(subcomponent, field) for field in update_data.keys()}
    for field, value in update_data.items():
        setattr(subcomponent, field, value)

    if "status" in update_data and update_data["status"] == SubcomponentStatus.complete:
        subcomponent.completed_at = subcomponent.completed_at or datetime.now(timezone.utc)

    subcomponent.updated_at = datetime.now(timezone.utc)

    if "subcomponent_name" in update_data and update_data["subcomponent_name"]:
        conflict = (
            session.query(Subcomponent)
            .filter(Subcomponent.solution_id == subcomponent.solution_id)
            .filter(Subcomponent.subcomponent_name == update_data["subcomponent_name"])
            .filter(Subcomponent.subcomponent_id != subcomponent.subcomponent_id)
            .filter(Subcomponent.deleted_at.is_(None))
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subcomponent name already exists in this solution",
            )

    session.add(subcomponent)
    if update_data:
        log_changes(
            session,
            entity_type="subcomponent",
            entity_id=subcomponent.subcomponent_id,
            user_id=current_user.user_id,
            action="update",
            changes={field: (before.get(field), getattr(subcomponent, field)) for field in update_data.keys()},
        )
    session.commit()
    session.refresh(subcomponent)
    schedule_broadcast("subcomponents")
    return subcomponent


@router.delete("/subcomponents/{subcomponent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subcomponent(
    subcomponent_id: str,
    session: Session = Depends(get_db),
    current_user: User = Depends(current_user_dep),
):
    subcomponent = _get_subcomponent(session, subcomponent_id)
    now = datetime.now(timezone.utc)
    subcomponent.deleted_at = now
    subcomponent.updated_at = now
    session.add(subcomponent)
    log_changes(
        session,
        entity_type="subcomponent",
        entity_id=subcomponent.subcomponent_id,
        user_id=current_user.user_id,
        action="delete",
        changes={"deleted_at": (None, now)},
    )
    session.commit()
    schedule_broadcast("subcomponents")
    return None
