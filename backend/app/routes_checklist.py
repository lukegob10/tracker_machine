from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .deps import get_db
from .models import (
    Phase,
    Solution,
    SolutionPhase,
    Subcomponent,
    SubcomponentPhaseStatus,
)
from .schemas import SubcomponentPhaseRead, SubcomponentPhaseUpdate

router = APIRouter()


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


def _enabled_solution_phases(session: Session, solution_id: str) -> list[SolutionPhase]:
    phases = (
        session.query(SolutionPhase)
        .join(Phase, Phase.phase_id == SolutionPhase.phase_id)
        .filter(SolutionPhase.solution_id == solution_id)
        .filter(SolutionPhase.is_enabled.is_(True))
        .order_by(
            SolutionPhase.sequence_override.asc().nulls_last(),
            Phase.sequence.asc(),
            SolutionPhase.solution_phase_id.asc(),
        )
        .all()
    )
    return phases


def _sync_checklist(session: Session, subcomponent: Subcomponent) -> list[SubcomponentPhaseStatus]:
    enabled = _enabled_solution_phases(session, subcomponent.solution_id)
    enabled_ids = {sp.solution_phase_id: sp for sp in enabled}
    existing = {
        row.solution_phase_id: row
        for row in session.query(SubcomponentPhaseStatus)
        .filter(SubcomponentPhaseStatus.subcomponent_id == subcomponent.subcomponent_id)
        .all()
    }

    now = datetime.now(timezone.utc)
    results: list[SubcomponentPhaseStatus] = []

    # Upsert rows for enabled phases
    for sp_id, sp in enabled_ids.items():
        row = existing.get(sp_id)
        if row:
            results.append(row)
        else:
            row = SubcomponentPhaseStatus(
                subcomponent_id=subcomponent.subcomponent_id,
                solution_phase_id=sp.solution_phase_id,
                phase_id=sp.phase_id,
                is_complete=False,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            results.append(row)

    # Remove rows for disabled phases
    for sp_id, row in existing.items():
        if sp_id not in enabled_ids:
            session.delete(row)

    session.commit()
    for row in results:
        session.refresh(row)
    return results


@router.get(
    "/subcomponents/{subcomponent_id}/phases",
    response_model=List[SubcomponentPhaseRead],
)
def get_checklist(subcomponent_id: str, session: Session = Depends(get_db)):
    subcomponent = _get_subcomponent(session, subcomponent_id)
    items = _sync_checklist(session, subcomponent)
    return items


@router.post(
    "/subcomponents/{subcomponent_id}/phases/bulk",
    response_model=List[SubcomponentPhaseRead],
)
def bulk_update_checklist(
    subcomponent_id: str,
    payload: dict,
    session: Session = Depends(get_db),
):
    subcomponent = _get_subcomponent(session, subcomponent_id)
    updates = payload.get("updates", [])
    if not isinstance(updates, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="updates must be a list"
        )

    items = _sync_checklist(session, subcomponent)
    items_by_sp = {item.solution_phase_id: item for item in items}

    now = datetime.now(timezone.utc)
    for upd in updates:
        data = SubcomponentPhaseUpdate.model_validate(upd)
        if data.solution_phase_id not in items_by_sp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phase {data.solution_phase_id} is not enabled for this subcomponent",
            )
        row = items_by_sp[data.solution_phase_id]
        row.is_complete = data.is_complete
        row.completed_at = now if data.is_complete else None
        row.updated_at = now
        session.add(row)

    session.commit()
    # refresh
    for row in items:
        session.refresh(row)
    return items
