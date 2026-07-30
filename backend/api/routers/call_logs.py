from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas import CallLogOut, CallLogPage
from backend.service.models import CallLog

router = APIRouter(prefix="/call-logs", tags=["call-logs"])


@router.get("", response_model=CallLogPage)
def list_call_logs(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    emp_code: str | None = None,
    crm_status: str | None = None,
    category: str | None = None,
) -> CallLogPage:
    stmt = select(CallLog)
    if emp_code:
        stmt = stmt.where(CallLog.emp_code == emp_code)
    if crm_status:
        stmt = stmt.where(CallLog.crm_status == crm_status)
    if category:
        stmt = stmt.where(CallLog.category == category)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(CallLog.call_date.desc()).limit(limit).offset(offset)).all()

    return CallLogPage(
        total=total,
        limit=limit,
        offset=offset,
        items=[CallLogOut.model_validate(row) for row in rows],
    )


@router.get("/{call_id}", response_model=CallLogOut)
def get_call_log(call_id: str, db: Session = Depends(get_db)) -> CallLogOut:
    row = db.get(CallLog, call_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Call log not found")
    return CallLogOut.model_validate(row)
