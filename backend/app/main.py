from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.processors import router as processors_router
from app.api.tasks import router as tasks_router
from app.api.ws import router as ws_router
from app.config import settings
from app.core.registry import ProcessorRegistry
from app.tasks.worker import celery_app, redis_client

app = FastAPI(title="GameAsset Toolkit")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(processors_router)
app.include_router(tasks_router)
app.include_router(ws_router)


@app.on_event("startup")
async def startup_event() -> None:
    settings.ensure_dirs()
    ProcessorRegistry.auto_discover()


@app.get("/api/health")
def health() -> dict[str, str | int]:
    redis_ready = _redis_is_ready()
    worker_ready = _worker_is_ready()
    overall = "ok" if redis_ready and worker_ready else "degraded"
    return {
        "status": overall,
        "api": "ok",
        "redis": "ok" if redis_ready else "down",
        "worker": "ok" if worker_ready else "down",
    }


def _redis_is_ready() -> bool:
    try:
        return bool(redis_client.ping())
    except Exception:
        return False


def _worker_is_ready() -> bool:
    try:
        result = celery_app.control.ping(timeout=0.5)
    except Exception:
        return False
    if not isinstance(result, list):
        return False
    return len(result) > 0
