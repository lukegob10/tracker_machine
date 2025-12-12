from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .deps import get_db
from .enums import SolutionStatus
from .models import Project, Solution, Phase, SolutionPhase
from .schemas import SolutionCreate, SolutionRead, SolutionUpdate
from .utils import get_default_user_id

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
        user_id=get_default_user_id(),
    )
    session.add(solution)
    session.commit()
    session.refresh(solution)
    _enable_all_phases(session, solution.solution_id)
    session.refresh(solution)
    return solution


@router.get("/solutions/{solution_id}", response_model=SolutionRead)
def get_solution(solution_id: str, session: Session = Depends(get_db)):
    solution = _get_solution_or_404(session, solution_id)
    return solution


@router.patch("/solutions/{solution_id}", response_model=SolutionRead)
def update_solution(
    solution_id: str,
    payload: SolutionUpdate,
    session: Session = Depends(get_db),
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
    return solution


@router.delete("/solutions/{solution_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_solution(solution_id: str, session: Session = Depends(get_db)):
    solution = _get_solution_or_404(session, solution_id)
    now = datetime.now(timezone.utc)
    solution.deleted_at = now
    solution.updated_at = now
    session.add(solution)
    session.commit()
    return None


def _enable_all_phases(session: Session, solution_id: str) -> None:
    phases = session.query(Phase).order_by(Phase.sequence.asc()).all()
    now = datetime.now(timezone.utc)
    for ph in phases:
        exists = (
            session.query(SolutionPhase)
            .filter(SolutionPhase.solution_id == solution_id)
            .filter(SolutionPhase.phase_id == ph.phase_id)
            .first()
        )
        if exists:
            exists.is_enabled = True
            exists.sequence_override = None
            exists.updated_at = now
            session.add(exists)
        else:
            session.add(
                SolutionPhase(
                    solution_id=solution_id,
                    phase_id=ph.phase_id,
                    is_enabled=True,
                    sequence_override=None,
                    created_at=now,
                    updated_at=now,
                )
            )
    session.commit()
