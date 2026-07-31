import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routers import (
    analytics,
    call_logs,
    hr_dashboard,
    preprocess_call_logs,
    sync,
)
from backend.api.sync_worker import sync_worker

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    sync_worker.start()
    try:
        yield
    finally:
        sync_worker.stop()


app = FastAPI(title="HR Analysis Dashboard API", lifespan=lifespan)

allowed_origins = os.environ.get("CORS_ALLOW_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics.router, prefix="/api")
app.include_router(hr_dashboard.router, prefix="/api")
app.include_router(call_logs.router, prefix="/api")
app.include_router(preprocess_call_logs.router, prefix="/api")
app.include_router(sync.router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Serves the built dashboard (frontend/dist) so a single `uvicorn` process
# hosts both the API and the UI. Mounted last so it only catches requests
# that don't match an API route above. Absent in dev, where Vite serves
# the frontend and proxies /api to this app instead.
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
