from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .deps import get_db, require_user
from .models import ChangeLog
from .schemas import ChangeLogRead

router = APIRouter(dependencies=[Depends(require_user)])


@router.get("/audit", response_model=List[ChangeLogRead])
def list_audit(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    field: Optional[str] = None,
    user_id: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db),
):
    query = session.query(ChangeLog)
    if entity_type:
        query = query.filter(ChangeLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(ChangeLog.entity_id == entity_id)
    if field:
        query = query.filter(ChangeLog.field == field)
    if user_id:
        query = query.filter(ChangeLog.user_id == user_id)
    if since:
        query = query.filter(ChangeLog.created_at >= since)
    if until:
        query = query.filter(ChangeLog.created_at <= until)
    rows = query.order_by(ChangeLog.created_at.desc()).limit(limit).all()
    return rows
