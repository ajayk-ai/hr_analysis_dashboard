from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CallLogColumns:
    """Column layout shared by call_logs and its filtered mirror,
    preprocess_call_log."""

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    client_name: Mapped[str | None] = mapped_column(String(255))
    client_country_code: Mapped[str | None] = mapped_column(String(16))
    client_number: Mapped[str | None] = mapped_column(String(32))
    duration: Mapped[int | None] = mapped_column(Integer)
    call_type: Mapped[str | None] = mapped_column(String(32))
    call_date: Mapped[str | None] = mapped_column(String(16))
    call_time: Mapped[str | None] = mapped_column(String(16))
    note: Mapped[str | None] = mapped_column(Text)
    call_recording_url: Mapped[str | None] = mapped_column(Text)
    synced_at: Mapped[str | None] = mapped_column(String(64))
    modified_at: Mapped[str | None] = mapped_column(String(64))
    emp_name: Mapped[str | None] = mapped_column(String(255))
    emp_code: Mapped[str | None] = mapped_column(String(64))
    emp_number: Mapped[str | None] = mapped_column(String(32))
    emp_country_code: Mapped[str | None] = mapped_column(String(16))
    emp_tags: Mapped[str | None] = mapped_column(String(255))
    crm_status: Mapped[str | None] = mapped_column(String(64))
    reminder_date: Mapped[str | None] = mapped_column(String(16))
    reminder_time: Mapped[str | None] = mapped_column(String(16))
    lead_id: Mapped[str | None] = mapped_column(String(128))
    google_drive_link: Mapped[str | None] = mapped_column(Text)
    ai_transcript: Mapped[str | None] = mapped_column(Text)
    ai_feedback: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(128))
    sub_reason: Mapped[str | None] = mapped_column(Text)
    commitment: Mapped[str | None] = mapped_column(String(128))
    intimation: Mapped[str | None] = mapped_column(String(128))
    risk_level: Mapped[str | None] = mapped_column(String(32))
    valid_discussion: Mapped[str | None] = mapped_column(String(32))
    ai_analysis_confidence: Mapped[str | None] = mapped_column(String(32))
    ai_analysis_explanation: Mapped[str | None] = mapped_column(Text)
    analysis_status: Mapped[str | None] = mapped_column(String(32))
    analysis_updated_at: Mapped[str | None] = mapped_column(String(64))


class CallLog(Base, CallLogColumns):
    __tablename__ = "call_logs"


class PreprocessCallLog(Base, CallLogColumns):
    """Mirrors call_logs, excluding rows with no google_drive_link.
    Kept up to date by refresh_preprocess_call_log() after every sync."""

    __tablename__ = "preprocess_call_log"
