"""Endpoints shaped to the HR absentee follow-up dashboard layout.

Section numbers in the docstrings refer to the dashboard spec:
1 six-month trend + current-month cumulative, 2 per-category trends,
3 critical insights to MD, 4 return commitment, 5 effectiveness funnel,
6 reason-wise breakdown, 7 intimation compliance, 8 attrition risk.
"""

import calendar

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.filters import CallLogFilters, Scope, call_log_filters
from backend.api.schemas import (
    BreakdownItem,
    CallActivityResponse,
    CategoryTrend,
    CategoryTrendsResponse,
    CumulativePoint,
    CumulativeResponse,
    EffectivenessMetric,
    EffectivenessResponse,
    GroupedBreakdownResponse,
    HrDashboardResponse,
    InsightArea,
    InsightBreakupItem,
    MdInsightsResponse,
    MonthlyTrendResponse,
    MonthPoint,
)
from backend.service.models import CallLog as L
from backend.service.sub_reason_themes import theme_expression

router = APIRouter(prefix="/hr-dashboard", tags=["hr-dashboard"])

HIGH_RISK = "High Risk"
VALID_YES = "Yes"
CONFIRMED_COMMITMENT = "Confirmed / Specific Return"
PENDING_COMMITMENT = "Pending / Approximate Return"
NO_COMMITMENT = "No Clear Commitment"
INTIMATION_GAP = "No Proper Intimation / Gap"
SUPERVISOR_INTIMATION = "Supervisor / Manager Informed"
INDIRECT_INTIMATION = "Indirect / Informal Intimation"
UNSPECIFIED = "Unspecified"

MONTH_EXPR = func.substr(L.call_date, 1, 7)
DAY_EXPR = cast(func.substr(L.call_date, 9, 2), Integer)

# Shared by the Query defaults and the composite endpoint below, which calls the
# handlers directly and so must pass real values rather than Query objects.
DEFAULT_MONTHS = 6
DEFAULT_BREAKUP_LIMIT = 4
DEFAULT_SUB_REASON_LIMIT = 20


def _count_if(condition):
    return func.count().filter(condition)


def _pct(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 2) if whole else 0.0


def _month_window(anchor: str, count: int) -> list[str]:
    """The `count` months ending at `anchor`, oldest first."""
    year, mon = int(anchor[:4]), int(anchor[5:7])
    window = []
    for back in range(count - 1, -1, -1):
        y, m = year, mon - back
        while m <= 0:
            m += 12
            y -= 1
        window.append(f"{y:04d}-{m:02d}")
    return window


def _month_label(month: str) -> str:
    return calendar.month_abbr[int(month[5:7])]


def _anchor_month(db: Session, filters: CallLogFilters) -> str:
    """The dashboard's 'current month': the newest month in the filtered data,
    so the Month filter selects which month the widgets centre on."""
    latest = db.scalar(
        select(func.max(MONTH_EXPR)).select_from(L).where(*filters.conditions())
    )
    if latest:
        return latest
    fallback = db.scalar(select(func.max(MONTH_EXPR)).select_from(L))
    return fallback or "1970-01"


def _grouped(rows: list[tuple[str | None, int]]) -> GroupedBreakdownResponse:
    total = sum(count for _, count in rows)
    return GroupedBreakdownResponse(
        total=total,
        items=[
            BreakdownItem(
                label=label or UNSPECIFIED, count=count, percentage=_pct(count, total)
            )
            for label, count in rows
        ],
    )


@router.get("/call-activity", response_model=CallActivityResponse)
def get_call_activity(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
) -> CallActivityResponse:
    """HR dialling effort, read from `call_logs` rather than the analysed
    mirror: how many calls HR made, and how many were actually picked up.

    Deliberately date-filtered only. An unanswered call never reaches the AI
    pipeline, so it has no category, risk level or valid_discussion -- honouring
    those filters here would drop every unanswered row and report a 100%
    answer rate.
    """
    answered = func.coalesce(L.duration, 0) > 0
    # The same rule that builds preprocess_call_log, so analysed_calls
    # reconciles with the effectiveness funnel under scope=all.
    analysed = L.google_drive_link.is_not(None)

    row = db.execute(
        select(
            func.count().label("total"),
            _count_if(answered).label("answered"),
            _count_if(analysed).label("analysed"),
        )
        .select_from(L)
        .where(*filters.date_conditions(L))
    ).one()

    return CallActivityResponse(
        total_calls=row.total,
        answered_calls=row.answered,
        unanswered_calls=row.total - row.answered,
        analysed_calls=row.analysed,
        answer_rate=_pct(row.answered, row.total),
    )


@router.get("/effectiveness", response_model=EffectivenessResponse)
def get_effectiveness(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
) -> EffectivenessResponse:
    """Section 5. Counts every processed call, then the valid share of it."""
    # Deliberately scope-free: this endpoint reports the valid share itself.
    conds = filters.conditions(include_scope=False)

    # This funnel measures conversation quality, which only exists for calls the
    # AI actually analysed -- so it stays on those even under scope=total_calls.
    # Counting a call nobody answered as "processed" would be wrong twice over:
    # it never was, and processed - valid would file it under "Invalid / No
    # Discussion" when there was no discussion to judge. HR's dialling effort is
    # reported by /call-activity instead.
    if filters.scope is Scope.total_calls:
        conds.append(L.google_drive_link.is_not(None))

    row = db.execute(
        select(
            func.count().label("processed"),
            _count_if(L.valid_discussion == VALID_YES).label("valid"),
            _count_if(
                (L.valid_discussion == VALID_YES)
                & (L.commitment == CONFIRMED_COMMITMENT)
            ).label("commitment"),
            _count_if(
                (L.valid_discussion == VALID_YES) & (L.risk_level == HIGH_RISK)
            ).label("high_risk"),
        )
        .select_from(L)
        .where(*conds)
    ).one()

    processed, valid = row.processed, row.valid
    invalid = processed - valid

    return EffectivenessResponse(
        processed_rows=processed,
        valid_discussions=valid,
        invalid_discussions=invalid,
        positive_commitment=row.commitment,
        high_risk_cases=row.high_risk,
        metrics=[
            EffectivenessMetric(
                metric="Processed Calls", calls=processed, rate=100.0, basis="processed"
            ),
            EffectivenessMetric(
                metric="Valid Discussions",
                calls=valid,
                rate=_pct(valid, processed),
                basis="processed",
            ),
            EffectivenessMetric(
                metric="Invalid / No Discussion",
                calls=invalid,
                rate=_pct(invalid, processed),
                basis="processed",
            ),
            EffectivenessMetric(
                metric="Positive Commitment",
                calls=row.commitment,
                rate=_pct(row.commitment, valid),
                basis="valid",
            ),
            EffectivenessMetric(
                metric="High Risk Cases",
                calls=row.high_risk,
                rate=_pct(row.high_risk, valid),
                basis="valid",
            ),
        ],
    )


@router.get("/monthly-trend", response_model=MonthlyTrendResponse)
def get_monthly_trend(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
    months: int = Query(DEFAULT_MONTHS, ge=1, le=24),
) -> MonthlyTrendResponse:
    """Section 1 bar chart: valid discussions per month over a rolling window."""
    anchor = _anchor_month(db, filters)
    window = _month_window(anchor, months)

    # Dates excluded so the month filter picks the window's end, not its width.
    counts = dict(
        db.execute(
            select(MONTH_EXPR.label("month"), func.count())
            .select_from(L)
            .where(
                *filters.conditions(include_dates=False),
                MONTH_EXPR.in_(window),
            )
            .group_by(MONTH_EXPR)
        ).all()
    )

    return MonthlyTrendResponse(
        anchor_month=anchor,
        points=[
            MonthPoint(month=m, label=_month_label(m), calls=counts.get(m, 0))
            for m in window
        ],
    )


def _cumulative_points(
    db: Session, filters: CallLogFilters, month: str, extra_conds=()
) -> list[CumulativePoint]:
    """Per-day counts for a month, carried into a running total across every
    calendar day so the line never breaks on a day with no calls."""
    per_day = dict(
        db.execute(
            select(DAY_EXPR.label("day"), func.count())
            .select_from(L)
            .where(
                *filters.conditions(include_dates=False),
                *extra_conds,
                MONTH_EXPR == month,
            )
            .group_by(DAY_EXPR)
        ).all()
    )

    days = calendar.monthrange(int(month[:4]), int(month[5:7]))[1]
    points, running = [], 0
    for day in range(1, days + 1):
        calls = per_day.get(day, 0)
        running += calls
        points.append(CumulativePoint(day=day, calls=calls, cumulative=running))
    return points


@router.get("/cumulative", response_model=CumulativeResponse)
def get_current_month_cumulative(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
) -> CumulativeResponse:
    """Section 1 line graph: cumulative calls through the current month."""
    anchor = _anchor_month(db, filters)
    points = _cumulative_points(db, filters, anchor)
    return CumulativeResponse(
        month=anchor,
        total=points[-1].cumulative if points else 0,
        points=points,
    )


@router.get("/category-trends", response_model=CategoryTrendsResponse)
def get_category_trends(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
    months: int = Query(DEFAULT_MONTHS, ge=1, le=24),
) -> CategoryTrendsResponse:
    """Section 2: per absence category, a monthly bar series plus a cumulative
    line for the current month."""
    anchor = _anchor_month(db, filters)
    window = _month_window(anchor, months)
    base = filters.conditions(include_dates=False)

    rows = db.execute(
        select(L.category, MONTH_EXPR.label("month"), func.count().label("calls"))
        .select_from(L)
        .where(*base, MONTH_EXPR.in_(window))
        .group_by(L.category, MONTH_EXPR)
    ).all()

    by_category: dict[str, dict[str, int]] = {}
    for category, month, calls in rows:
        by_category.setdefault(category or UNSPECIFIED, {})[month] = calls

    current_total = sum(months_.get(anchor, 0) for months_ in by_category.values())

    categories = []
    for category, monthly in sorted(
        by_category.items(), key=lambda kv: kv[1].get(anchor, 0), reverse=True
    ):
        # Null categories are stored as NULL, not the display label.
        cond = L.category.is_(None) if category == UNSPECIFIED else L.category == category
        current = monthly.get(anchor, 0)
        categories.append(
            CategoryTrend(
                category=category,
                current_month_calls=current,
                current_month_percentage=_pct(current, current_total),
                monthly=[
                    MonthPoint(
                        month=m, label=_month_label(m), calls=monthly.get(m, 0)
                    )
                    for m in window
                ],
                cumulative=_cumulative_points(db, filters, anchor, extra_conds=(cond,)),
            )
        )

    return CategoryTrendsResponse(
        anchor_month=anchor,
        months=window,
        current_month_total=current_total,
        categories=categories,
    )


@router.get("/md-insights", response_model=MdInsightsResponse)
def get_md_insights(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
    breakup_limit: int = Query(DEFAULT_BREAKUP_LIMIT, ge=1, le=10),
) -> MdInsightsResponse:
    """Section 3: each absence category with its leading sub-reason themes, plus
    a risk row -- the 'Surgery 30 + fever 25 + ENT 16' style break-up."""
    theme = theme_expression(L.sub_reason)
    conds = filters.conditions()

    rows = db.execute(
        select(L.category, theme.label("theme"), func.count().label("calls"))
        .select_from(L)
        .where(*conds)
        .group_by(L.category, theme)
    ).all()

    total = sum(calls for _, _, calls in rows)

    grouped: dict[str, dict[str, int]] = {}
    for category, theme_label, calls in rows:
        grouped.setdefault(category or UNSPECIFIED, {})[theme_label] = calls

    areas = []
    for category, themes in sorted(
        grouped.items(), key=lambda kv: sum(kv[1].values()), reverse=True
    ):
        calls = sum(themes.values())
        top = sorted(themes.items(), key=lambda kv: kv[1], reverse=True)[:breakup_limit]
        areas.append(
            InsightArea(
                area=category,
                breakup=[
                    InsightBreakupItem(label=label, count=count) for label, count in top
                ],
                calls=calls,
                percentage=_pct(calls, total),
            )
        )

    high_risk = db.scalar(
        select(func.count()).select_from(L).where(*conds, L.risk_level == HIGH_RISK)
    ) or 0
    gap = db.scalar(
        select(func.count()).select_from(L).where(*conds, L.intimation == INTIMATION_GAP)
    ) or 0
    areas.append(
        InsightArea(
            area="Risk & Intimation",
            breakup=[
                InsightBreakupItem(label="High risk employees", count=high_risk),
                InsightBreakupItem(label="No proper intimation", count=gap),
            ],
            calls=high_risk,
            percentage=_pct(high_risk, total),
        )
    )

    return MdInsightsResponse(total=total, areas=areas)


@router.get("/sub-reasons", response_model=GroupedBreakdownResponse)
def get_sub_reason_breakdown(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
    limit: int = Query(DEFAULT_SUB_REASON_LIMIT, ge=1, le=50),
) -> GroupedBreakdownResponse:
    """Section 6: free-text sub_reason folded into keyword themes."""
    theme = theme_expression(L.sub_reason)
    rows = db.execute(
        select(theme.label("theme"), func.count().label("calls"))
        .select_from(L)
        .where(*filters.conditions())
        .group_by(theme)
        .order_by(func.count().desc())
        .limit(limit)
    ).all()
    return _grouped([(theme_label, calls) for theme_label, calls in rows])


@router.get("/commitment", response_model=GroupedBreakdownResponse)
def get_commitment_tracking(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
) -> GroupedBreakdownResponse:
    """Section 4: return commitment, in the dashboard's three buckets."""
    bucket = func.coalesce(L.commitment, UNSPECIFIED)
    rows = db.execute(
        select(bucket.label("bucket"), func.count().label("calls"))
        .select_from(L)
        .where(*filters.conditions())
        .group_by(bucket)
    ).all()

    order = [CONFIRMED_COMMITMENT, PENDING_COMMITMENT, NO_COMMITMENT, UNSPECIFIED]
    counts = {label: calls for label, calls in rows}
    return _grouped([(label, counts[label]) for label in order if label in counts])


@router.get("/intimation-compliance", response_model=GroupedBreakdownResponse)
def get_intimation_compliance(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
) -> GroupedBreakdownResponse:
    """Section 7: intimation channels, with the long tail of minor channels
    (contractor, co-worker) folded into one bucket."""
    rows = db.execute(
        select(L.intimation, func.count().label("calls"))
        .select_from(L)
        .where(*filters.conditions())
        .group_by(L.intimation)
    ).all()

    named = {
        SUPERVISOR_INTIMATION: "Supervisor Direct",
        INDIRECT_INTIMATION: "Indirect / Informal",
        INTIMATION_GAP: "No Proper Intimation",
    }
    buckets: dict[str, int] = {}
    for value, calls in rows:
        label = named.get(value, "Other Minor Channels") if value else UNSPECIFIED
        buckets[label] = buckets.get(label, 0) + calls

    order = [
        "Supervisor Direct",
        "Indirect / Informal",
        "No Proper Intimation",
        "Other Minor Channels",
        UNSPECIFIED,
    ]
    return _grouped([(label, buckets[label]) for label in order if label in buckets])


@router.get("/risk-analysis", response_model=GroupedBreakdownResponse)
def get_risk_analysis(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
) -> GroupedBreakdownResponse:
    """Section 8: attrition risk levels, ordered low to high."""
    bucket = func.coalesce(L.risk_level, UNSPECIFIED)
    rows = db.execute(
        select(bucket.label("bucket"), func.count().label("calls"))
        .select_from(L)
        .where(*filters.conditions())
        .group_by(bucket)
    ).all()

    order = ["Low Risk", "Medium Risk", HIGH_RISK, UNSPECIFIED]
    counts = {label: calls for label, calls in rows}
    return _grouped([(label, counts[label]) for label in order if label in counts])


@router.get("", response_model=HrDashboardResponse)
def get_hr_dashboard(
    db: Session = Depends(get_db),
    filters: CallLogFilters = Depends(call_log_filters),
    months: int = Query(DEFAULT_MONTHS, ge=1, le=24),
) -> HrDashboardResponse:
    """Every dashboard section in one round trip, so the UI loads atomically
    and no widget can disagree with another about the filter state."""
    return HrDashboardResponse(
        generated_for_month=_anchor_month(db, filters),
        call_activity=get_call_activity(db, filters),
        effectiveness=get_effectiveness(db, filters),
        monthly_valid_discussions=get_monthly_trend(db, filters, months),
        current_month_cumulative=get_current_month_cumulative(db, filters),
        category_trends=get_category_trends(db, filters, months),
        md_insights=get_md_insights(db, filters, DEFAULT_BREAKUP_LIMIT),
        commitment=get_commitment_tracking(db, filters),
        sub_reasons=get_sub_reason_breakdown(db, filters, DEFAULT_SUB_REASON_LIMIT),
        intimation_compliance=get_intimation_compliance(db, filters),
        risk_analysis=get_risk_analysis(db, filters),
    )
