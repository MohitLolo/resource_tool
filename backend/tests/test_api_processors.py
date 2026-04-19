import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.processors import get_processors, get_processors_by_category, router as processors_router
from app.core.registry import ProcessorRegistry


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_get_all_processors(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.processors.ProcessorRegistry.list_all",
        lambda: [{"name": "image.crop", "label": "Crop", "category": "image", "params_schema": {}}],
    )

    data = get_processors()
    assert data[0]["name"] == "image.crop"


def test_get_processors_by_category(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.processors.ProcessorRegistry.list_by_category",
        lambda category: [{"name": "video.extract_frames", "category": category}],
    )

    data = get_processors_by_category("video")
    assert data[0]["category"] == "video"


@pytest.mark.integration
@pytest.mark.anyio
@pytest.mark.skip(reason="暂时搁置：该异步 API 集成用例在当前环境存在事件循环阻塞，后续单独处理")
async def test_processors_api_returns_discovered_image_processors() -> None:
    ProcessorRegistry.clear()
    ProcessorRegistry.auto_discover("app.processors")

    test_app = FastAPI()
    test_app.include_router(processors_router)
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/processors/image")

    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert {"image.watermark", "image.cutout", "image.crop", "image.pixelate"}.issubset(names)
