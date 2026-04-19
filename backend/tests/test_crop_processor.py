from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.processors.image.crop import CropProcessor


def _write_input(path: Path, size: tuple[int, int] = (100, 60)) -> None:
    image = Image.new("RGB", size, (220, 100, 80))
    image.save(path, format="PNG")


def test_crop_processor_metadata_and_validate() -> None:
    processor = CropProcessor()

    assert processor.name == "image.crop"
    assert processor.label == "裁剪/缩放"
    assert processor.category == "image"

    assert processor.validate({"mode": "custom", "width": 64, "height": 32}) is True
    assert processor.validate({"mode": "power2", "power2_size": 128}) is True
    assert processor.validate(
        {"mode": "crop", "x": 10, "y": 5, "crop_width": 20, "crop_height": 10}
    ) is True

    assert processor.validate({"mode": "custom", "width": 64}) is False
    assert processor.validate({"mode": "power2", "power2_size": 100}) is False
    assert processor.validate({"mode": "crop", "x": 1, "y": 2, "crop_width": 0, "crop_height": 10}) is False
    assert processor.validate({"mode": "unknown"}) is False


def test_process_custom_mode_resizes_to_target(tmp_path) -> None:
    processor = CropProcessor()
    input_file = tmp_path / "input.png"
    _write_input(input_file)

    events: list[int] = []
    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={"mode": "custom", "width": 40, "height": 24},
        progress_callback=lambda progress, _message: events.append(progress),
    )

    assert len(outputs) == 1
    output_path = Path(outputs[0])
    assert output_path.exists()

    output = Image.open(output_path)
    assert output.size == (40, 24)
    assert events[-1] == 100


def test_process_power2_mode_resizes_to_square(tmp_path) -> None:
    processor = CropProcessor()
    input_file = tmp_path / "input.png"
    _write_input(input_file)

    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={"mode": "power2", "power2_size": 64},
        progress_callback=lambda _progress, _message: None,
    )

    output = Image.open(outputs[0])
    assert output.size == (64, 64)


def test_process_crop_mode_crops_region(tmp_path) -> None:
    processor = CropProcessor()
    input_file = tmp_path / "input.png"
    _write_input(input_file)

    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={"mode": "crop", "x": 15, "y": 8, "crop_width": 30, "crop_height": 12},
        progress_callback=lambda _progress, _message: None,
    )

    output = Image.open(outputs[0])
    assert output.size == (30, 12)


def test_process_raises_when_params_invalid(tmp_path) -> None:
    processor = CropProcessor()
    input_file = tmp_path / "input.png"
    _write_input(input_file)

    try:
        processor.process(
            input_file=str(input_file),
            output_dir=str(tmp_path),
            params={"mode": "power2", "power2_size": 100},
            progress_callback=lambda _progress, _message: None,
        )
    except ValueError as exc:
        assert "invalid params" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError for invalid params")
