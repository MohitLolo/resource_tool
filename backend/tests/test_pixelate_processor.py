from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.processors.image.pixelate import PixelateProcessor


def _write_gradient(path: Path, size: tuple[int, int] = (32, 32)) -> None:
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(size[1]):
        for x in range(size[0]):
            pixels[x, y] = ((x * 7) % 256, (y * 9) % 256, ((x + y) * 5) % 256)
    image.save(path, format="PNG")


def _color_count(image: Image.Image) -> int:
    converted = image.convert("RGB")
    raw = converted.tobytes()
    return len({raw[index : index + 3] for index in range(0, len(raw), 3)})


def test_pixelate_processor_metadata_and_validate() -> None:
    processor = PixelateProcessor()

    assert processor.name == "image.pixelate"
    assert processor.label == "像素风转换"
    assert processor.category == "image"

    assert processor.validate({"pixel_size": 2, "palette_colors": 0, "output_size": "original"}) is True
    assert processor.validate({"pixel_size": 8, "palette_colors": 16, "output_size": "64x64"}) is True

    assert processor.validate({"pixel_size": 1, "palette_colors": 0, "output_size": "original"}) is False
    assert processor.validate({"pixel_size": 8, "palette_colors": 12, "output_size": "original"}) is False
    assert processor.validate({"pixel_size": 8, "palette_colors": 16, "output_size": "80x80"}) is False


def test_process_applies_palette_limit_and_reports_progress(tmp_path) -> None:
    processor = PixelateProcessor()
    input_file = tmp_path / "input.png"
    _write_gradient(input_file)

    events: list[int] = []
    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={"pixel_size": 4, "palette_colors": 8, "output_size": "original"},
        progress_callback=lambda progress, _message: events.append(progress),
    )

    assert len(outputs) == 1
    output_path = Path(outputs[0])
    assert output_path.exists()

    output = Image.open(output_path)
    assert output.size == (32, 32)
    assert _color_count(output) <= 8
    assert events[-1] == 100


def test_process_resizes_to_target_output_size(tmp_path) -> None:
    processor = PixelateProcessor()
    input_file = tmp_path / "input.png"
    _write_gradient(input_file, size=(48, 24))

    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={"pixel_size": 3, "palette_colors": 0, "output_size": "128x128"},
        progress_callback=lambda _progress, _message: None,
    )

    output = Image.open(outputs[0])
    assert output.size == (128, 128)


def test_process_raises_for_invalid_params(tmp_path) -> None:
    processor = PixelateProcessor()
    input_file = tmp_path / "input.png"
    _write_gradient(input_file)

    with pytest.raises(ValueError, match="Invalid params"):
        processor.process(
            input_file=str(input_file),
            output_dir=str(tmp_path),
            params={"pixel_size": 1, "palette_colors": 0, "output_size": "original"},
            progress_callback=lambda _progress, _message: None,
        )
