import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app.include_router(analytics.router)
app.include_router(hr_dashboard.router)
app.include_router(call_logs.router)
app.include_router(preprocess_call_logs.router)
app.include_router(sync.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
