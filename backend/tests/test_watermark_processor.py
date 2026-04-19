from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest

from app.processors.image.watermark import WatermarkProcessor


def _write_image(path: Path, value: int = 120) -> None:
    image = np.full((8, 8, 3), value, dtype=np.uint8)
    cv2.imwrite(str(path), image)


def test_watermark_processor_metadata() -> None:
    processor = WatermarkProcessor()
    assert processor.name == "image.watermark"
    assert processor.label == "去水印"
    assert processor.category == "image"


def test_validate_auto_mode() -> None:
    processor = WatermarkProcessor()
    assert processor.validate({"mode": "auto"}) is True
    assert processor.validate({"mode": "manual"}) is True
    assert processor.validate({}) is True
    assert processor.validate({"mode": "invalid"}) is False


def test_validate_sensitivity() -> None:
    processor = WatermarkProcessor()
    assert processor.validate({"sensitivity": 50}) is True
    assert processor.validate({"sensitivity": 0}) is False
    assert processor.validate({"sensitivity": 101}) is False


def test_validate_mask_dilate() -> None:
    processor = WatermarkProcessor()
    assert processor.validate({"mask_dilate": 5}) is True
    assert processor.validate({"mask_dilate": 0}) is False
    assert processor.validate({"mask_dilate": 31}) is False


def test_process_auto_mode_with_lama(tmp_path, monkeypatch) -> None:
    processor = WatermarkProcessor()
    input_file = tmp_path / "input.png"
    image = np.full((32, 32, 3), 100, dtype=np.uint8)
    image[10:22, 10:22] = 240
    cv2.imwrite(str(input_file), image)

    fake_result = np.full((32, 32, 3), 100, dtype=np.uint8)
    from PIL import Image as PILImage

    fake_pil = PILImage.fromarray(fake_result)
    mock_lama = MagicMock(return_value=fake_pil)
    monkeypatch.setattr(processor, "_get_or_create_lama", lambda: mock_lama)

    progress_events = []
    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={"mode": "auto", "sensitivity": 70},
        progress_callback=lambda p, m: progress_events.append((p, m)),
    )

    assert len(outputs) == 1
    assert Path(outputs[0]).exists()
    assert progress_events[-1][0] == 100


def test_process_manual_mode_with_mask(tmp_path, monkeypatch) -> None:
    processor = WatermarkProcessor()
    input_file = tmp_path / "input.png"
    mask_file = tmp_path / "mask.png"
    _write_image(input_file, value=100)

    mask = np.zeros((8, 8), dtype=np.uint8)
    mask[2:5, 2:5] = 255
    cv2.imwrite(str(mask_file), mask)

    from PIL import Image as PILImage

    fake_pil = PILImage.fromarray(np.full((8, 8, 3), 100, dtype=np.uint8))
    mock_lama = MagicMock(return_value=fake_pil)
    monkeypatch.setattr(processor, "_get_or_create_lama", lambda: mock_lama)

    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={
            "mode": "manual",
            "mask_file_key": "mask.png",
            "extra_files": {"mask.png": str(mask_file)},
        },
        progress_callback=lambda _p, _m: None,
    )

    assert len(outputs) == 1
    assert Path(outputs[0]).exists()
    assert mock_lama.called


def test_process_fallback_to_opencv(tmp_path, monkeypatch) -> None:
    processor = WatermarkProcessor()
    input_file = tmp_path / "input.png"
    mask_file = tmp_path / "mask.png"
    _write_image(input_file, value=100)

    mask = np.zeros((8, 8), dtype=np.uint8)
    mask[2:5, 2:5] = 255
    cv2.imwrite(str(mask_file), mask)

    def raise_import_error():
        raise ImportError("simple-lama-inpainting not available")

    monkeypatch.setattr(processor, "_get_or_create_lama", raise_import_error)

    calls = []

    def fake_inpaint(image, inpaint_mask, radius, method):
        calls.append((radius, method))
        return image

    monkeypatch.setattr("app.processors.image.watermark.cv2.inpaint", fake_inpaint)

    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={
            "mode": "manual",
            "mask_file_key": "mask.png",
            "extra_files": {"mask.png": str(mask_file)},
            "mask_dilate": 3,
        },
        progress_callback=lambda _p, _m: None,
    )

    assert len(outputs) == 1
    assert Path(outputs[0]).exists()
    assert len(calls) == 1


@pytest.mark.integration
def test_process_integration_with_opencv_fallback(tmp_path) -> None:
    processor = WatermarkProcessor()
    input_file = tmp_path / "input.png"
    mask_file = tmp_path / "mask.png"

    image = np.full((32, 32, 3), 120, dtype=np.uint8)
    image[10:22, 10:22] = 255
    cv2.imwrite(str(input_file), image)

    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[10:22, 10:22] = 255
    cv2.imwrite(str(mask_file), mask)

    progress_events = []
    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={
            "mode": "manual",
            "mask_file_key": "mask.png",
            "extra_files": {"mask.png": str(mask_file)},
            "mask_dilate": 3,
        },
        progress_callback=lambda p, m: progress_events.append(p),
    )

    assert len(outputs) == 1
    assert Path(outputs[0]).exists()
    assert progress_events[-1] == 100
