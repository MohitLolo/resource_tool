from __future__ import annotations

from fastapi import APIRouter

from app.core.registry import ProcessorRegistry

router = APIRouter(prefix="/api/processors", tags=["processors"])


@router.get("")
def get_processors() -> list[dict]:
    return ProcessorRegistry.list_all()


@router.get("/{category}")
def get_processors_by_category(category: str) -> list[dict]:
    return ProcessorRegistry.list_by_category(category)
