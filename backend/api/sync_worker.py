import logging
import os
import threading
from datetime import UTC, datetime

from backend.service.preprocess_service import refresh_preprocess_call_log
from backend.service.sheets_sync_service import sync_sheet_to_postgres

logger = logging.getLogger("backend.api.sync_worker")


class SheetSyncWorker:
    """Runs sync_sheet_to_postgres() on a fixed interval in a background
    thread, keeping the call_logs table live-synced with the Google Sheet."""

    def __init__(self, interval_seconds: int) -> None:
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self.last_synced_at: str | None = None
        self.last_sync_rows: int | None = None
        self.last_error: str | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def sync_once(self) -> int:
        with self._lock:
            rows = sync_sheet_to_postgres()
            refresh_preprocess_call_log()
            self.last_synced_at = datetime.now(UTC).isoformat()
            self.last_sync_rows = rows
            self.last_error = None
            return rows

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                rows = self.sync_once()
                logger.info("Synced %d rows from Google Sheet", rows)
            except Exception as exc:  # noqa: BLE001 - keep loop alive on any sync failure
                self.last_error = str(exc)
                logger.exception("Sheet sync failed")
            self._stop_event.wait(self.interval_seconds)


sync_worker = SheetSyncWorker(
    interval_seconds=int(os.environ.get("SYNC_INTERVAL_SECONDS", "60"))
)
