from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import Session

from .deps import get_db, current_user as current_user_dep
from .models import Phase, Solution, SolutionPhase, User
from .schemas import PhaseRead, SolutionPhaseInput, SolutionPhaseRead
from .realtime import schedule_broadcast
from .audit_log import log_changes

router = APIRouter()


@router.get("/phases", response_model=List[PhaseRead])
def list_phases(session: Session = Depends(get_db)):
    phases = session.query(Phase).order_by(Phase.sequence.asc()).all()
    return phases


@router.get(
    "/solutions/{solution_id}/phases",
    response_model=List[SolutionPhaseRead],
)
def list_solution_phases(solution_id: str, session: Session = Depends(get_db)):
    _ensure_solution_exists(session, solution_id)
    return _ordered_solution_phases(session, solution_id)


@router.post(
    "/solutions/{solution_id}/phases",
    response_model=List[SolutionPhaseRead],
)
def set_solution_phases(
    solution_id: str,
    payload: dict,
    session: Session = Depends(get_db),
    tasks: BackgroundTasks = None,
    current_user: User = Depends(current_user_dep),
):
    """
    Upsert enabled phases for a solution. Payload shape:
    { "phases": [{ "phase_id": "...", "is_enabled": true/false, "sequence_override": 2 }]}
    """
    _ensure_solution_exists(session, solution_id)
    phases_data = payload.get("phases", [])
    if not isinstance(phases_data, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="phases must be a list"
        )

    now = datetime.now(timezone.utc)
    updated_items: list[SolutionPhase] = []

    for item in phases_data:
        data = SolutionPhaseInput.model_validate(item)

        phase_exists = session.query(Phase).filter(Phase.phase_id == data.phase_id).first()
        if not phase_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phase {data.phase_id} does not exist",
            )

        sp = (
            session.query(SolutionPhase)
            .filter(SolutionPhase.solution_id == solution_id)
            .filter(SolutionPhase.phase_id == data.phase_id)
            .first()
        )
        action = "update" if sp else "create"
        before_enabled = sp.is_enabled if sp else None
        before_seq = sp.sequence_override if sp else None
        if sp:
            sp.is_enabled = data.is_enabled
            sp.sequence_override = data.sequence_override
            sp.updated_at = now
        else:
            sp = SolutionPhase(
                solution_id=solution_id,
                phase_id=data.phase_id,
                is_enabled=data.is_enabled,
                sequence_override=data.sequence_override,
                created_at=now,
                updated_at=now,
            )
            session.add(sp)
            session.flush()
        log_changes(
            session,
            entity_type="solution_phase",
            entity_id=sp.solution_phase_id,
            user_id=current_user.user_id,
            action=action,
            changes={
                "is_enabled": (before_enabled, sp.is_enabled),
                "sequence_override": (before_seq, sp.sequence_override),
            },
        )
        updated_items.append(sp)
        session.commit()
    schedule_broadcast("solutions")
    return _ordered_solution_phases(session, solution_id)


def _ensure_solution_exists(session: Session, solution_id: str) -> None:
    exists = (
        session.query(Solution)
        .filter(Solution.solution_id == solution_id)
        .filter(Solution.deleted_at.is_(None))
        .first()
    )
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solution not found")


def _ordered_solution_phases(session: Session, solution_id: str) -> list[SolutionPhase]:
    sort_key = func.coalesce(SolutionPhase.sequence_override, Phase.sequence)
    items = (
        session.query(SolutionPhase)
        .join(Phase, Phase.phase_id == SolutionPhase.phase_id)
        .filter(SolutionPhase.solution_id == solution_id)
        .order_by(sort_key.asc(), Phase.sequence.asc(), SolutionPhase.solution_phase_id.asc())
        .all()
    )
    return items
