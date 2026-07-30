import calendar
import re
from dataclasses import dataclass
from datetime import date
from enum import Enum

from fastapi import HTTPException, Query
from sqlalchemy import ColumnElement, or_

from backend.service.models import PreprocessCallLog

# Enforces the exact YYYY-MM-DD shape; date.fromisoformat alone would also
# accept forms like '20260730' that break string comparison against call_date.
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

VALID_DISCUSSION_YES = "Yes"


class Scope(str, Enum):
    """Which rows the analytics denominators cover.

    `valid_only` matches the HR dashboard spec: every distribution is a share of
    valid discussions, with total processed rows reported separately in the
    effectiveness funnel.
    """

    valid_only = "valid_only"
    all = "all"

# Free-text columns scanned by the `search` parameter.
_SEARCH_COLUMNS = (
    "client_name",
    "client_number",
    "sub_reason",
    "ai_transcript",
    "ai_analysis_explanation",
)


def _validate_date(value: str | None, name: str) -> str | None:
    if value is None:
        return None
    if not _ISO_DATE.match(value):
        raise HTTPException(
            status_code=422, detail=f"{name} must be an ISO date (YYYY-MM-DD)"
        )
    try:
        date.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status_code=422, detail=f"{name} is not a valid calendar date"
        ) from None
    return value


def _month_bounds(month: str) -> tuple[str, str]:
    """First and last calendar day of a YYYY-MM month, as ISO strings."""
    year, mon = int(month[:4]), int(month[5:7])
    last_day = calendar.monthrange(year, mon)[1]
    return f"{month}-01", f"{month}-{last_day:02d}"


@dataclass(frozen=True)
class CallLogFilters:
    """Filter set shared by the call-log listing and every analytics endpoint,
    so a dashboard can apply one set of controls across all its widgets.

    `call_date` is stored as an ISO `YYYY-MM-DD` string, so lexicographic
    comparison is a correct date-range filter.
    """

    scope: Scope = Scope.valid_only
    month: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    category: list[str] | None = None
    risk_level: list[str] | None = None
    commitment: list[str] | None = None
    intimation: list[str] | None = None
    valid_discussion: list[str] | None = None
    ai_analysis_confidence: list[str] | None = None
    analysis_status: list[str] | None = None
    call_type: list[str] | None = None
    client_number: str | None = None
    emp_number: str | None = None
    min_duration: int | None = None
    max_duration: int | None = None
    search: str | None = None

    def conditions(
        self,
        model=PreprocessCallLog,
        *,
        include_scope: bool = True,
        include_dates: bool = True,
    ) -> list[ColumnElement[bool]]:
        """Filter conditions for this model.

        `include_scope=False` is for the effectiveness funnel, which must count
        all processed rows to report the valid share. `include_dates=False` is
        for the rolling 6-month series, where the month filter selects the
        window's end rather than clipping the window itself.
        """
        conds: list[ColumnElement[bool]] = []

        # An explicit valid_discussion filter beats the coarse scope switch.
        if (
            include_scope
            and self.scope is Scope.valid_only
            and not self.valid_discussion
        ):
            conds.append(model.valid_discussion == VALID_DISCUSSION_YES)

        if include_dates:
            if self.date_from:
                conds.append(model.call_date >= self.date_from)
            if self.date_to:
                conds.append(model.call_date <= self.date_to)

        multi = {
            "category": self.category,
            "risk_level": self.risk_level,
            "commitment": self.commitment,
            "intimation": self.intimation,
            "valid_discussion": self.valid_discussion,
            "ai_analysis_confidence": self.ai_analysis_confidence,
            "analysis_status": self.analysis_status,
            "call_type": self.call_type,
        }
        for column, values in multi.items():
            if values:
                conds.append(getattr(model, column).in_(values))

        if self.client_number:
            conds.append(model.client_number == self.client_number)
        if self.emp_number:
            conds.append(model.emp_number == self.emp_number)
        if self.min_duration is not None:
            conds.append(model.duration >= self.min_duration)
        if self.max_duration is not None:
            conds.append(model.duration <= self.max_duration)

        if self.search:
            term = f"%{self.search}%"
            conds.append(
                or_(*(getattr(model, c).ilike(term) for c in _SEARCH_COLUMNS))
            )

        return conds

    def apply(self, stmt, model=PreprocessCallLog, **kwargs):
        conds = self.conditions(model, **kwargs)
        return stmt.where(*conds) if conds else stmt


def call_log_filters(
    scope: Scope = Query(
        Scope.valid_only,
        description="valid_only (dashboard default) counts only valid discussions",
    ),
    month: str | None = Query(
        None, description="Convenience month filter, YYYY-MM; overrides date bounds"
    ),
    date_from: str | None = Query(None, description="Inclusive start date, YYYY-MM-DD"),
    date_to: str | None = Query(None, description="Inclusive end date, YYYY-MM-DD"),
    category: list[str] | None = Query(None, description="Repeatable"),
    risk_level: list[str] | None = Query(None, description="Repeatable"),
    commitment: list[str] | None = Query(None, description="Repeatable"),
    intimation: list[str] | None = Query(None, description="Repeatable"),
    valid_discussion: list[str] | None = Query(None, description="Yes / No"),
    ai_analysis_confidence: list[str] | None = Query(None, description="High/Medium/Low"),
    analysis_status: list[str] | None = Query(None, description="Repeatable"),
    call_type: list[str] | None = Query(None, description="Incoming / Outgoing"),
    client_number: str | None = Query(None, description="Absentee employee's number"),
    emp_number: str | None = Query(None, description="HR caller's number"),
    min_duration: int | None = Query(None, ge=0, description="Min call duration (s)"),
    max_duration: int | None = Query(None, ge=0, description="Max call duration (s)"),
    search: str | None = Query(None, description="Free-text search across call fields"),
) -> CallLogFilters:
    if month is not None:
        if not _ISO_MONTH.match(month):
            raise HTTPException(
                status_code=422, detail="month must be YYYY-MM with a month of 01-12"
            )
        date_from, date_to = _month_bounds(month)

    date_from = _validate_date(date_from, "date_from")
    date_to = _validate_date(date_to, "date_to")
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=422, detail="date_from must not be after date_to"
        )
    if (
        min_duration is not None
        and max_duration is not None
        and min_duration > max_duration
    ):
        raise HTTPException(
            status_code=422, detail="min_duration must not exceed max_duration"
        )

    return CallLogFilters(
        scope=scope,
        month=month,
        date_from=date_from,
        date_to=date_to,
        category=category,
        risk_level=risk_level,
        commitment=commitment,
        intimation=intimation,
        valid_discussion=valid_discussion,
        ai_analysis_confidence=ai_analysis_confidence,
        analysis_status=analysis_status,
        call_type=call_type,
        client_number=client_number,
        emp_number=emp_number,
        min_duration=min_duration,
        max_duration=max_duration,
        search=search,
    )
