from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.config import settings
from app.processors.image.cutout import CutoutProcessor


def _model_path() -> Path:
    base = Path(os.getenv("U2NET_HOME", settings.U2NET_HOME))
    return base / "u2net.onnx"


def _png_bytes(mode: str = "RGB") -> bytes:
    image = Image.new(mode, (8, 8), (255, 0, 0, 255) if mode == "RGBA" else (255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_cutout_processor_metadata_and_validate() -> None:
    processor = CutoutProcessor()

    assert processor.name == "image.cutout"
    assert processor.label == "智能抠图"
    assert processor.category == "image"
    assert processor.validate({}) is True


def test_process_calls_rembg_and_writes_rgba_png(tmp_path, monkeypatch) -> None:
    processor = CutoutProcessor()
    input_file = tmp_path / "input.png"
    output_dir = tmp_path
    input_file.write_bytes(_png_bytes("RGB"))

    expected_rgba = _png_bytes("RGBA")
    calls = {"remove": 0}

    def fake_remove(data: bytes, alpha_matting: bool = False):
        calls["remove"] += 1
        assert isinstance(data, bytes)
        assert alpha_matting is True
        return expected_rgba

    monkeypatch.setattr(processor, "_remove_background", fake_remove)

    events: list[int] = []
    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(output_dir),
        params={"alpha_matting": True},
        progress_callback=lambda progress, _message: events.append(progress),
    )

    assert calls["remove"] == 1
    assert len(outputs) == 1
    output_path = Path(outputs[0])
    assert output_path.exists()
    assert output_path.suffix.lower() == ".png"

    output_image = Image.open(output_path)
    assert output_image.mode == "RGBA"
    assert events[-1] == 100


@pytest.mark.integration
def test_process_integration_with_real_rembg(tmp_path) -> None:
    model_path = _model_path()
    if not model_path.exists():
        pytest.skip(f"rembg model not found at {model_path}")

    processor = CutoutProcessor()
    input_file = tmp_path / "input.png"
    input_file.write_bytes(_png_bytes("RGB"))

    try:
        outputs = processor.process(
            input_file=str(input_file),
            output_dir=str(tmp_path),
            params={"alpha_matting": False},
            progress_callback=lambda _progress, _message: None,
        )
    except Exception as exc:  # pragma: no cover - environment/network dependent
        message = str(exc).lower()
        if "u2net.onnx" in message or "connection" in message or "download" in message:
            pytest.skip(f"rembg model unavailable in current environment: {exc}")
        raise

    assert len(outputs) == 1
    output_path = Path(outputs[0])
    assert output_path.exists()

    image = Image.open(output_path)
    assert image.mode == "RGBA"
