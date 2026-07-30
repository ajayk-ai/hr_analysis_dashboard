from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter

from backend.api.schemas import SyncStatus, SyncTriggerResult
from backend.api.sync_worker import sync_worker

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/status", response_model=SyncStatus)
def get_sync_status() -> SyncStatus:
    return SyncStatus(
        running=sync_worker.running,
        interval_seconds=sync_worker.interval_seconds,
        last_synced_at=sync_worker.last_synced_at,
        last_sync_rows=sync_worker.last_sync_rows,
        last_error=sync_worker.last_error,
    )


@router.post("/trigger", response_model=SyncTriggerResult)
async def trigger_sync() -> SyncTriggerResult:
    rows = await run_in_threadpool(sync_worker.sync_once)
    return SyncTriggerResult(synced_rows=rows)
