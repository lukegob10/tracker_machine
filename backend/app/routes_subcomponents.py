from datetime import datetime, timezone, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .deps import get_db
from .enums import SubcomponentStatus
from .models import Phase, Project, Solution, SolutionPhase, Subcomponent
from .schemas import (
    SubcomponentCreate,
    SubcomponentRead,
    SubcomponentUpdate,
)
from .utils import get_default_user_id

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
        created_at=now,
        updated_at=now,
        user_id=get_default_user_id(),
    )
    session.add(subcomponent)
    session.commit()
    session.refresh(subcomponent)
    return subcomponent


@router.get("/subcomponents/{subcomponent_id}", response_model=SubcomponentRead)
def get_subcomponent(subcomponent_id: str, session: Session = Depends(get_db)):
    return _get_subcomponent(session, subcomponent_id)


@router.patch("/subcomponents/{subcomponent_id}", response_model=SubcomponentRead)
def update_subcomponent(
    subcomponent_id: str,
    payload: SubcomponentUpdate,
    session: Session = Depends(get_db),
):
    subcomponent = _get_subcomponent(session, subcomponent_id)
    if "sub_phase" in payload.model_fields_set:
        _validate_sub_phase(session, subcomponent.solution_id, payload.sub_phase)

    update_data = payload.model_dump(exclude_unset=True)
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
    session.commit()
    session.refresh(subcomponent)
    return subcomponent


@router.delete("/subcomponents/{subcomponent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subcomponent(subcomponent_id: str, session: Session = Depends(get_db)):
    subcomponent = _get_subcomponent(session, subcomponent_id)
    now = datetime.now(timezone.utc)
    subcomponent.deleted_at = now
    subcomponent.updated_at = now
    session.add(subcomponent)
    session.commit()
    return None
