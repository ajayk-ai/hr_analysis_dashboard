from pydantic import BaseModel, ConfigDict


class CallLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_name: str | None = None
    client_country_code: str | None = None
    client_number: str | None = None
    duration: int | None = None
    call_type: str | None = None
    call_date: str | None = None
    call_time: str | None = None
    note: str | None = None
    call_recording_url: str | None = None
    synced_at: str | None = None
    modified_at: str | None = None
    emp_name: str | None = None
    emp_code: str | None = None
    emp_number: str | None = None
    emp_country_code: str | None = None
    emp_tags: str | None = None
    crm_status: str | None = None
    reminder_date: str | None = None
    reminder_time: str | None = None
    lead_id: str | None = None
    google_drive_link: str | None = None
    ai_transcript: str | None = None
    ai_feedback: str | None = None
    category: str | None = None
    sub_reason: str | None = None
    commitment: str | None = None
    intimation: str | None = None
    risk_level: str | None = None
    valid_discussion: str | None = None
    ai_analysis_confidence: str | None = None
    ai_analysis_explanation: str | None = None
    analysis_status: str | None = None
    analysis_updated_at: str | None = None


class CallLogPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[CallLogOut]


class OverviewKpis(BaseModel):
    """Headline numbers for the dashboard's KPI row."""

    total_calls: int
    unique_employees: int
    repeat_employees: int
    total_talk_time_seconds: int
    avg_duration_seconds: float
    high_risk_calls: int
    high_risk_rate: float
    valid_discussion_calls: int
    valid_discussion_rate: float
    confirmed_commitment_calls: int
    confirmed_commitment_rate: float
    intimation_gap_calls: int
    intimation_gap_rate: float
    analysed_calls: int
    analysis_coverage_rate: float
    first_call_date: str | None = None
    last_call_date: str | None = None


class BreakdownItem(BaseModel):
    label: str
    count: int
    percentage: float


class BreakdownResponse(BaseModel):
    dimension: str
    total: int
    items: list[BreakdownItem]


class TrendPoint(BaseModel):
    period: str
    calls: int
    avg_duration_seconds: float
    high_risk_calls: int
    valid_discussion_calls: int
    intimation_gap_calls: int


class TrendResponse(BaseModel):
    granularity: str
    points: list[TrendPoint]


class HourlyPoint(BaseModel):
    hour: int
    calls: int
    avg_duration_seconds: float


class HourlyResponse(BaseModel):
    points: list[HourlyPoint]


class MatrixCell(BaseModel):
    category: str
    risk_level: str
    count: int


class RiskMatrixResponse(BaseModel):
    categories: list[str]
    risk_levels: list[str]
    cells: list[MatrixCell]


class EmployeeSummary(BaseModel):
    """One absentee employee (keyed on the number HR dialled)."""

    client_number: str
    client_name: str | None = None
    total_calls: int
    first_call_date: str | None = None
    last_call_date: str | None = None
    total_talk_time_seconds: int
    avg_duration_seconds: float
    high_risk_calls: int
    valid_discussion_calls: int
    intimation_gap_calls: int
    no_commitment_calls: int
    top_category: str | None = None
    latest_risk_level: str | None = None


class EmployeePage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[EmployeeSummary]


class FilterOptions(BaseModel):
    """Dropdown options plus bounds, so the UI never hardcodes values."""

    categories: list[str]
    risk_levels: list[str]
    commitments: list[str]
    intimations: list[str]
    valid_discussions: list[str]
    ai_analysis_confidences: list[str]
    analysis_statuses: list[str]
    call_types: list[str]
    date_min: str | None = None
    date_max: str | None = None
    duration_min: int | None = None
    duration_max: int | None = None


class EffectivenessMetric(BaseModel):
    metric: str
    calls: int
    rate: float
    basis: str


class EffectivenessResponse(BaseModel):
    """Section 5 funnel. `processed_rows` counts every row in scope; the valid
    and invalid shares are of that, while commitment and risk are shares of
    valid discussions -- matching the dashboard spec."""

    processed_rows: int
    valid_discussions: int
    invalid_discussions: int
    positive_commitment: int
    high_risk_cases: int
    metrics: list[EffectivenessMetric]


class MonthPoint(BaseModel):
    month: str
    label: str
    calls: int


class MonthlyTrendResponse(BaseModel):
    anchor_month: str
    points: list[MonthPoint]


class CumulativePoint(BaseModel):
    day: int
    calls: int
    cumulative: int


class CumulativeResponse(BaseModel):
    month: str
    total: int
    points: list[CumulativePoint]


class CategoryTrend(BaseModel):
    category: str
    current_month_calls: int
    current_month_percentage: float
    monthly: list[MonthPoint]
    cumulative: list[CumulativePoint]


class CategoryTrendsResponse(BaseModel):
    anchor_month: str
    months: list[str]
    current_month_total: int
    categories: list[CategoryTrend]


class InsightBreakupItem(BaseModel):
    label: str
    count: int


class InsightArea(BaseModel):
    area: str
    breakup: list[InsightBreakupItem]
    calls: int
    percentage: float


class MdInsightsResponse(BaseModel):
    total: int
    areas: list[InsightArea]


class GroupedBreakdownResponse(BaseModel):
    """A breakdown whose raw values are folded into presentation buckets."""

    total: int
    items: list[BreakdownItem]


class HrDashboardResponse(BaseModel):
    """Everything the HR dashboard renders, in one round trip."""

    generated_for_month: str
    effectiveness: EffectivenessResponse
    monthly_valid_discussions: MonthlyTrendResponse
    current_month_cumulative: CumulativeResponse
    category_trends: CategoryTrendsResponse
    md_insights: MdInsightsResponse
    commitment: GroupedBreakdownResponse
    sub_reasons: GroupedBreakdownResponse
    intimation_compliance: GroupedBreakdownResponse
    risk_analysis: GroupedBreakdownResponse


class SyncStatus(BaseModel):
    running: bool
    interval_seconds: int
    last_synced_at: str | None = None
    last_sync_rows: int | None = None
    last_error: str | None = None


class SyncTriggerResult(BaseModel):
    synced_rows: int
