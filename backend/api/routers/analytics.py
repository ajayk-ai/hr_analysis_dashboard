from datetime import date, timedelta
from enum import Enum

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Integer, String, cast, distinct, func, select, type_coerce
from sqlalchemy.dialects.postgresql import ARRAY, aggregate_order_by
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.filters import CallLogFilters, call_log_filters
from backend.api.schemas import (
    BreakdownItem,
    BreakdownResponse,
    EmployeePage,
    EmployeeSummary,
    FilterOptions,
    HourlyPoint,
    HourlyResponse,
    MatrixCell,
    OverviewKpis,
    RiskMatrixResponse,
    TrendPoint,
    TrendResponse,
)
from backend.service.models import CallLog as L

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Domain label values, as they appear in the AI-analysed sheet data.
HIGH_RISK = "High Risk"
VALID_DISCUSSION_YES = "Yes"
CONFIRMED_COMMITMENT = "Confirmed / Specific Return"
NO_COMMITMENT = "No Clear Commitment"
INTIMATION_GAP = "No Proper Intimation / Gap"
ANALYSED = "Gemini analysed"

UNSPECIFIED = "Unspecified"

# Rows whose call_time is 'HH:MM' as well as 'HH:MM:SS' both yield the hour.
HOUR_EXPR = cast(func.nullif(func.split_part(L.call_time, ":", 1), ""), Integer)


class BreakdownDimension(str, Enum):
    """Low-cardinality columns worth charting. `sub_reason` is deliberately
    excluded: it is free-text AI narrative (440 distinct values in 716 rows)."""

    category = "category"
    risk_level = "risk_level"
    commitment = "commitment"
    intimation = "intimation"
    valid_discussion = "valid_discussion"
    ai_analysis_confidence = "ai_analysis_confidence"
    analysis_status = "analysis_status"
    call_type = "call_type"


class Granularity(str, Enum):
    day = "day"
    week = "week"
    month = "month"


class EmployeeSort(str, Enum):
    total_calls = "total_calls"
    high_risk_calls = "high_risk_calls"
    intimation_gap_calls = "intimation_gap_calls"
    last_call_date = "last_call_date"
    avg_duration_seconds = "avg_duration_seconds"


def _count_if(condition):
    """COUNT of rows matching `condition` within an aggregate query."""
    return func.count().filter(condition)


def _pct(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 2) if whole else 0.0


def _period_expr(granularity: Granularity):
    if granularity is Granularity.day:
        return L.call_date
    if granularity is Granularity.month:
        return func.substr(L.call_date, 1, 7)
    # Week buckets are labelled by their Monday.
    return func.to_char(
        func.date_trunc("week", func.to_date(L.call_date, "YYYY-MM-DD")), "YYYY-MM-DD"
    )


@router.get("/overview", response_model=OverviewKpis)
def get_overview(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
) -> OverviewKpis:
    """Headline KPIs for the dashboard's top row."""
    conds = filters.conditions()

    row = db.execute(
        select(
            func.count().label("total_calls"),
            func.count(distinct(L.client_number)).label("unique_employees"),
            func.coalesce(func.sum(L.duration), 0).label("talk_time"),
            func.coalesce(func.avg(L.duration), 0).label("avg_duration"),
            _count_if(L.risk_level == HIGH_RISK).label("high_risk"),
            _count_if(L.valid_discussion == VALID_DISCUSSION_YES).label("valid"),
            _count_if(L.commitment == CONFIRMED_COMMITMENT).label("confirmed"),
            _count_if(L.intimation == INTIMATION_GAP).label("gap"),
            _count_if(L.analysis_status == ANALYSED).label("analysed"),
            func.min(L.call_date).label("first_date"),
            func.max(L.call_date).label("last_date"),
        )
        .select_from(L)
        .where(*conds)
    ).one()

    repeat_subq = (
        select(L.client_number)
        .select_from(L)
        .where(*conds)
        .group_by(L.client_number)
        .having(func.count() > 1)
        .subquery()
    )
    repeat_employees = db.scalar(select(func.count()).select_from(repeat_subq)) or 0

    total = row.total_calls
    return OverviewKpis(
        total_calls=total,
        unique_employees=row.unique_employees,
        repeat_employees=repeat_employees,
        total_talk_time_seconds=int(row.talk_time),
        avg_duration_seconds=round(float(row.avg_duration), 2),
        high_risk_calls=row.high_risk,
        high_risk_rate=_pct(row.high_risk, total),
        valid_discussion_calls=row.valid,
        valid_discussion_rate=_pct(row.valid, total),
        confirmed_commitment_calls=row.confirmed,
        confirmed_commitment_rate=_pct(row.confirmed, total),
        intimation_gap_calls=row.gap,
        intimation_gap_rate=_pct(row.gap, total),
        analysed_calls=row.analysed,
        analysis_coverage_rate=_pct(row.analysed, total),
        first_call_date=row.first_date,
        last_call_date=row.last_date,
    )


@router.get("/breakdown/{dimension}", response_model=BreakdownResponse)
def get_breakdown(
    dimension: BreakdownDimension,
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
) -> BreakdownResponse:
    """Counts and shares per value of a categorical column (pie / bar charts)."""
    column = getattr(L, dimension.value)

    rows = db.execute(
        filters.apply(
            select(column, func.count().label("count"))
            .select_from(L)
            .group_by(column)
            .order_by(func.count().desc())
        )
    ).all()

    total = sum(count for _, count in rows)
    return BreakdownResponse(
        dimension=dimension.value,
        total=total,
        items=[
            BreakdownItem(
                label=label or UNSPECIFIED,
                count=count,
                percentage=_pct(count, total),
            )
            for label, count in rows
        ],
    )


@router.get("/trend", response_model=TrendResponse)
def get_trend(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
    granularity: Granularity = Granularity.day,
) -> TrendResponse:
    """Call volume and quality signals over time (line / area charts)."""
    period = _period_expr(granularity)

    rows = db.execute(
        select(
            period.label("period"),
            func.count().label("calls"),
            func.coalesce(func.avg(L.duration), 0).label("avg_duration"),
            _count_if(L.risk_level == HIGH_RISK).label("high_risk"),
            _count_if(L.valid_discussion == VALID_DISCUSSION_YES).label("valid"),
            _count_if(L.intimation == INTIMATION_GAP).label("gap"),
        )
        .select_from(L)
        .where(*filters.conditions(), L.call_date.is_not(None))
        .group_by(period)
        .order_by(period)
    ).all()

    points = [
        TrendPoint(
            period=row.period,
            calls=row.calls,
            avg_duration_seconds=round(float(row.avg_duration), 2),
            high_risk_calls=row.high_risk,
            valid_discussion_calls=row.valid,
            intimation_gap_calls=row.gap,
        )
        for row in rows
    ]

    if granularity is Granularity.day:
        points = _fill_missing_days(points)

    return TrendResponse(granularity=granularity.value, points=points)


def _fill_missing_days(points: list[TrendPoint]) -> list[TrendPoint]:
    """Insert zero points for days with no calls so line charts stay continuous.
    Skipped for spans wide enough that the padding would dominate the payload."""
    if len(points) < 2:
        return points

    start = date.fromisoformat(points[0].period)
    end = date.fromisoformat(points[-1].period)
    span = (end - start).days
    if span <= 0 or span > 400:
        return points

    by_period = {p.period: p for p in points}
    filled: list[TrendPoint] = []
    for offset in range(span + 1):
        key = (start + timedelta(days=offset)).isoformat()
        filled.append(
            by_period.get(
                key,
                TrendPoint(
                    period=key,
                    calls=0,
                    avg_duration_seconds=0.0,
                    high_risk_calls=0,
                    valid_discussion_calls=0,
                    intimation_gap_calls=0,
                ),
            )
        )
    return filled


@router.get("/hourly", response_model=HourlyResponse)
def get_hourly_distribution(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
) -> HourlyResponse:
    """Call volume by hour of day — shows when follow-ups actually happen."""
    rows = db.execute(
        select(
            HOUR_EXPR.label("hour"),
            func.count().label("calls"),
            func.coalesce(func.avg(L.duration), 0).label("avg_duration"),
        )
        .select_from(L)
        .where(*filters.conditions(), L.call_time.is_not(None))
        .group_by(HOUR_EXPR)
        .order_by(HOUR_EXPR)
    ).all()

    counts = {
        row.hour: (row.calls, float(row.avg_duration))
        for row in rows
        if row.hour is not None and 0 <= row.hour <= 23
    }
    return HourlyResponse(
        points=[
            HourlyPoint(
                hour=hour,
                calls=counts.get(hour, (0, 0.0))[0],
                avg_duration_seconds=round(counts.get(hour, (0, 0.0))[1], 2),
            )
            for hour in range(24)
        ]
    )


@router.get("/risk-matrix", response_model=RiskMatrixResponse)
def get_risk_matrix(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
) -> RiskMatrixResponse:
    """Absence category cross-tabbed against risk level (heatmap)."""
    rows = db.execute(
        filters.apply(
            select(L.category, L.risk_level, func.count().label("count"))
            .select_from(L)
            .group_by(L.category, L.risk_level)
        )
    ).all()

    cells = [
        MatrixCell(
            category=category or UNSPECIFIED,
            risk_level=risk or UNSPECIFIED,
            count=count,
        )
        for category, risk, count in rows
    ]

    totals: dict[str, int] = {}
    for cell in cells:
        totals[cell.category] = totals.get(cell.category, 0) + cell.count

    risk_order = [HIGH_RISK, "Medium Risk", "Low Risk", UNSPECIFIED]
    present_risks = {cell.risk_level for cell in cells}

    return RiskMatrixResponse(
        categories=sorted(totals, key=lambda c: totals[c], reverse=True),
        risk_levels=[r for r in risk_order if r in present_risks]
        + sorted(present_risks - set(risk_order)),
        cells=cells,
    )


@router.get("/employees", response_model=EmployeePage)
def list_employee_summaries(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
    limit: int = Query(25, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort_by: EmployeeSort = EmployeeSort.total_calls,
    descending: bool = True,
    min_calls: int = Query(1, ge=1, description="Only employees with >= this many calls"),
) -> EmployeePage:
    """Per-employee follow-up history, keyed on the number HR dialled.

    This is the repeat-absentee watchlist: sort by `total_calls` to surface
    employees contacted most often, or by `high_risk_calls` for escalations.
    """
    conds = filters.conditions()

    # Latest call's risk level: Postgres arrays are 1-indexed.
    latest_risk = type_coerce(
        func.array_agg(
            aggregate_order_by(L.risk_level, L.call_date.desc().nullslast())
        ),
        ARRAY(String),
    )[1]

    total_calls = func.count().label("total_calls")
    high_risk = _count_if(L.risk_level == HIGH_RISK).label("high_risk_calls")
    gap = _count_if(L.intimation == INTIMATION_GAP).label("intimation_gap_calls")
    last_call = func.max(L.call_date).label("last_call_date")
    avg_duration = func.coalesce(func.avg(L.duration), 0).label("avg_duration_seconds")

    sortable = {
        EmployeeSort.total_calls: total_calls,
        EmployeeSort.high_risk_calls: high_risk,
        EmployeeSort.intimation_gap_calls: gap,
        EmployeeSort.last_call_date: last_call,
        EmployeeSort.avg_duration_seconds: avg_duration,
    }
    order_col = sortable[sort_by]
    ordering = order_col.desc().nullslast() if descending else order_col.asc()

    stmt = (
        select(
            L.client_number,
            func.max(L.client_name).label("client_name"),
            total_calls,
            func.min(L.call_date).label("first_call_date"),
            last_call,
            func.coalesce(func.sum(L.duration), 0).label("talk_time"),
            avg_duration,
            high_risk,
            _count_if(L.valid_discussion == VALID_DISCUSSION_YES).label("valid"),
            gap,
            _count_if(L.commitment == NO_COMMITMENT).label("no_commitment"),
            func.mode().within_group(L.category).label("top_category"),
            latest_risk.label("latest_risk_level"),
        )
        .select_from(L)
        .where(*conds)
        .group_by(L.client_number)
        .having(func.count() >= min_calls)
        .order_by(ordering, L.client_number)
        .limit(limit)
        .offset(offset)
    )

    count_subq = (
        select(L.client_number)
        .select_from(L)
        .where(*conds)
        .group_by(L.client_number)
        .having(func.count() >= min_calls)
        .subquery()
    )
    total = db.scalar(select(func.count()).select_from(count_subq)) or 0

    return EmployeePage(
        total=total,
        limit=limit,
        offset=offset,
        items=[
            EmployeeSummary(
                client_number=row.client_number,
                client_name=row.client_name,
                total_calls=row.total_calls,
                first_call_date=row.first_call_date,
                last_call_date=row.last_call_date,
                total_talk_time_seconds=int(row.talk_time),
                avg_duration_seconds=round(float(row.avg_duration_seconds), 2),
                high_risk_calls=row.high_risk_calls,
                valid_discussion_calls=row.valid,
                intimation_gap_calls=row.intimation_gap_calls,
                no_commitment_calls=row.no_commitment,
                top_category=row.top_category,
                latest_risk_level=row.latest_risk_level,
            )
            for row in db.execute(stmt).all()
        ],
    )


@router.get("/filters", response_model=FilterOptions)
def get_filter_options(db: Session = Depends(get_db)) -> FilterOptions:
    """Distinct values and bounds, so the dashboard's controls are data-driven."""

    def options(column) -> list[str]:
        return [
            value
            for (value,) in db.execute(
                select(distinct(column)).where(column.is_not(None)).order_by(column)
            ).all()
        ]

    bounds = db.execute(
        select(
            func.min(L.call_date),
            func.max(L.call_date),
            func.min(L.duration),
            func.max(L.duration),
        ).select_from(L)
    ).one()

    return FilterOptions(
        categories=options(L.category),
        risk_levels=options(L.risk_level),
        commitments=options(L.commitment),
        intimations=options(L.intimation),
        valid_discussions=options(L.valid_discussion),
        ai_analysis_confidences=options(L.ai_analysis_confidence),
        analysis_statuses=options(L.analysis_status),
        call_types=options(L.call_type),
        date_min=bounds[0],
        date_max=bounds[1],
        duration_min=bounds[2],
        duration_max=bounds[3],
    )
