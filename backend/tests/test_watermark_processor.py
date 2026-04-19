from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.processors.image.watermark import WatermarkProcessor


def _write_image(path: Path, value: int = 120) -> None:
    image = np.full((8, 8, 3), value, dtype=np.uint8)
    cv2.imwrite(str(path), image)


def test_watermark_processor_metadata_and_validate() -> None:
    processor = WatermarkProcessor()

    assert processor.name == "image.watermark"
    assert processor.label == "去水印"
    assert processor.category == "image"
    assert processor.validate({"algorithm": "telea"}) is True
    assert processor.validate({"algorithm": "ns"}) is True
    assert processor.validate({"algorithm": "invalid"}) is False


def test_process_with_manual_mask_uses_supplied_mask(tmp_path, monkeypatch) -> None:
    processor = WatermarkProcessor()
    input_file = tmp_path / "input.png"
    mask_file = tmp_path / "mask.png"
    _write_image(input_file, value=100)

    mask = np.zeros((8, 8), dtype=np.uint8)
    mask[2:5, 2:5] = 255
    cv2.imwrite(str(mask_file), mask)

    calls: list[tuple[int, int]] = []

    def fake_inpaint(image, inpaint_mask, radius, method):
        calls.append((radius, method))
        assert image.shape[:2] == inpaint_mask.shape
        assert int(inpaint_mask.max()) == 255
        return image

    monkeypatch.setattr("app.processors.image.watermark.cv2.inpaint", fake_inpaint)

    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={
            "algorithm": "telea",
            "brush_size": 5,
            "mask_file_key": "mask.png",
            "extra_files": {"mask.png": str(mask_file)},
        },
        progress_callback=lambda _p, _m: None,
    )

    assert len(outputs) == 1
    assert Path(outputs[0]).exists()
    assert calls == [(5, cv2.INPAINT_TELEA)]


def test_process_without_mask_calls_auto_detect(tmp_path, monkeypatch) -> None:
    processor = WatermarkProcessor()
    input_file = tmp_path / "input.png"
    _write_image(input_file, value=150)

    auto_mask = np.zeros((8, 8), dtype=np.uint8)
    auto_mask[1:3, 1:3] = 255

    state = {"auto_detect_called": False, "inpaint_called": False}

    def fake_auto_detect(image):
        state["auto_detect_called"] = True
        assert image.shape == (8, 8, 3)
        return auto_mask

    def fake_inpaint(image, inpaint_mask, radius, method):
        state["inpaint_called"] = True
        assert inpaint_mask is auto_mask
        assert method == cv2.INPAINT_NS
        return image

    monkeypatch.setattr(processor, "_auto_detect_mask", fake_auto_detect)
    monkeypatch.setattr("app.processors.image.watermark.cv2.inpaint", fake_inpaint)

    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={"algorithm": "ns", "brush_size": 3},
        progress_callback=lambda _p, _m: None,
    )

    assert len(outputs) == 1
    assert Path(outputs[0]).exists()
    assert state["auto_detect_called"] is True
    assert state["inpaint_called"] is True


@pytest.mark.integration
def test_process_integration_with_real_opencv_inpaint(tmp_path) -> None:
    processor = WatermarkProcessor()
    input_file = tmp_path / "input.png"
    mask_file = tmp_path / "mask.png"

    image = np.full((32, 32, 3), 120, dtype=np.uint8)
    image[10:22, 10:22] = 255
    cv2.imwrite(str(input_file), image)

    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[10:22, 10:22] = 255
    cv2.imwrite(str(mask_file), mask)

    progress_events: list[int] = []
    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={
            "algorithm": "telea",
            "brush_size": 3,
            "mask_file_key": "mask.png",
            "extra_files": {"mask.png": str(mask_file)},
        },
        progress_callback=lambda progress, _message: progress_events.append(progress),
    )

    assert len(outputs) == 1
    output_path = Path(outputs[0])
    assert output_path.exists()
    assert progress_events[-1] == 100

    output = cv2.imread(str(output_path), cv2.IMREAD_COLOR)
    assert output is not None
    # Inpaint should reduce the bright masked block toward surrounding background.
    assert int(output[16, 16, 0]) < 250
