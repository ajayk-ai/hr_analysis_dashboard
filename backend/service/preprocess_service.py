from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .db import SessionLocal
from .models import CallLog, PreprocessCallLog

_COLUMNS = [c.name for c in CallLog.__table__.columns]


def refresh_preprocess_call_log() -> int:
    """Mirrors call_logs into preprocess_call_log, keeping only rows that
    have a google_drive_link. Rows whose link is missing (or was cleared
    since the last refresh) are removed from preprocess_call_log."""
    with SessionLocal() as session:
        keep_ids = select(CallLog.id).where(CallLog.google_drive_link.is_not(None))
        session.execute(
            delete(PreprocessCallLog).where(PreprocessCallLog.id.not_in(keep_ids))
        )

        source_rows = session.execute(
            select(*(getattr(CallLog, col) for col in _COLUMNS)).where(
                CallLog.google_drive_link.is_not(None)
            )
        ).all()

        if source_rows:
            values = [dict(zip(_COLUMNS, row)) for row in source_rows]
            stmt = pg_insert(PreprocessCallLog).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={col: stmt.excluded[col] for col in _COLUMNS if col != "id"},
            )
            session.execute(stmt)

        session.commit()
        return len(source_rows)


if __name__ == "__main__":
    count = refresh_preprocess_call_log()
    print(f"Preprocessed {count} rows into 'preprocess_call_log'")
