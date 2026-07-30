import os

from sqlalchemy.dialects.postgresql import insert as pg_insert

from .db import SessionLocal
from .models import CallLog
from .preprocess_service import refresh_preprocess_call_log
from .sheets_client import get_sheets_client

# Maps raw Google Sheet header text -> call_logs column name.
# Headers that already match the column name 1:1 are listed for clarity;
# anything not listed here (e.g. the sheet's blank header column) is dropped.
HEADER_MAP = {
    "id": "id",
    "client_name": "client_name",
    "client_country_code": "client_country_code",
    "client_number": "client_number",
    "duration": "duration",
    "call_type": "call_type",
    "call_date": "call_date",
    "call_time": "call_time",
    "note": "note",
    "call_recording_url": "call_recording_url",
    "synced_at": "synced_at",
    "modified_at": "modified_at",
    "emp_name": "emp_name",
    "emp_code": "emp_code",
    "emp_number": "emp_number",
    "emp_country_code": "emp_country_code",
    "emp_tags": "emp_tags",
    "crm_status": "crm_status",
    "reminder_date": "reminder_date",
    "reminder_time": "reminder_time",
    "lead_id": "lead_id",
    "Google Drive Link": "google_drive_link",
    "AI Transcript": "ai_transcript",
    "AI Feedback": "ai_feedback",
    "Category": "category",
    "Sub Reason": "sub_reason",
    "Commitment": "commitment",
    "Intimation": "intimation",
    "Risk Level": "risk_level",
    "Valid Discussion": "valid_discussion",
    "AI Analysis Confidence": "ai_analysis_confidence",
    "AI Analysis Explanation": "ai_analysis_explanation",
    "Analysis Status": "analysis_status",
    "Analysis Updated At": "analysis_updated_at",
}


def _row_from_record(record: dict) -> dict:
    row = {}
    for sheet_header, column in HEADER_MAP.items():
        value = record.get(sheet_header, "")
        row[column] = value if value != "" else None
    if row["duration"] is not None:
        row["duration"] = int(row["duration"])
    return row


def sync_sheet_to_postgres() -> int:
    """Upserts every row from the configured worksheet into call_logs,
    keyed on the sheet's `id` column. Existing rows are updated in place;
    new rows are inserted. Rows without an `id` are skipped."""
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    worksheet_name = os.environ.get("GOOGLE_WORKSHEET_NAME", "Sheet1")

    client = get_sheets_client()
    worksheet = client.open_by_key(sheet_id).worksheet(worksheet_name)
    records = worksheet.get_all_records()

    rows = [_row_from_record(r) for r in records if r.get("id")]
    if not rows:
        return 0

    # Dedupe by id (keeping the last occurrence) since Postgres rejects an
    # upsert batch that targets the same row twice.
    rows = list({row["id"]: row for row in rows}.values())

    update_columns = {
        column: column for column in HEADER_MAP.values() if column != "id"
    }

    with SessionLocal() as session:
        stmt = pg_insert(CallLog).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={col: stmt.excluded[col] for col in update_columns},
        )
        session.execute(stmt)
        session.commit()

    return len(rows)


if __name__ == "__main__":
    synced = sync_sheet_to_postgres()
    print(f"Synced {synced} rows into 'call_logs'")
    preprocessed = refresh_preprocess_call_log()
    print(f"Preprocessed {preprocessed} rows into 'preprocess_call_log'")
