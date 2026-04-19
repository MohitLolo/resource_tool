from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.processors import router as processors_router
from app.api.tasks import router as tasks_router
from app.api.ws import router as ws_router
from app.config import settings
from app.core.registry import ProcessorRegistry

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
def health() -> dict[str, str]:
    return {"status": "ok"}
