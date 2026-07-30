from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.filters import CallLogFilters, call_log_filters
from backend.api.schemas import CallLogOut, CallLogPage
from backend.service.models import PreprocessCallLog

router = APIRouter(prefix="/preprocess-call-logs", tags=["preprocess-call-logs"])


class CallLogSort(str, Enum):
    call_date = "call_date"
    duration = "duration"
    risk_level = "risk_level"
    category = "category"


@router.get("", response_model=CallLogPage)
def list_preprocess_call_logs(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort_by: CallLogSort = CallLogSort.call_date,
    descending: bool = True,
) -> CallLogPage:
    """Paginated call detail records, driven by the same filter set as the
    analytics endpoints so a dashboard can drill down from any widget."""
    stmt = filters.apply(select(PreprocessCallLog))

    order_col = getattr(PreprocessCallLog, sort_by.value)
    ordering = order_col.desc().nullslast() if descending else order_col.asc()

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(ordering, PreprocessCallLog.id).limit(limit).offset(offset)
    ).all()

    return CallLogPage(
        total=total,
        limit=limit,
        offset=offset,
        items=[CallLogOut.model_validate(row) for row in rows],
    )


@router.get("/{call_id}", response_model=CallLogOut)
def get_preprocess_call_log(call_id: str, db: Session = Depends(get_db)) -> CallLogOut:
    row = db.get(PreprocessCallLog, call_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Call log not found")
    return CallLogOut.model_validate(row)
