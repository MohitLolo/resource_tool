from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.processors.image.convert import ConvertProcessor


def _write_rgba_png(path: Path) -> None:
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    pixels = image.load()
    for y in range(16):
        for x in range(16):
            pixels[x, y] = (255, 0, 0, 255) if (x + y) % 2 == 0 else (0, 255, 0, 0)
    image.save(path, format="PNG")


def test_convert_processor_metadata_and_validate() -> None:
    processor = ConvertProcessor()

    assert processor.name == "image.convert"
    assert processor.label == "格式转换"
    assert processor.category == "image"

    assert processor.validate({"format": "png", "quality": 90}) is True
    assert processor.validate({"format": "jpg", "quality": 80}) is True
    assert processor.validate({"format": "webp", "quality": 75}) is True

    assert processor.validate({"format": "gif", "quality": 90}) is False
    assert processor.validate({"format": "jpg", "quality": 0}) is False
    assert processor.validate({"format": "webp", "quality": 101}) is False


def test_process_png_to_jpg_flattens_alpha(tmp_path) -> None:
    processor = ConvertProcessor()
    input_file = tmp_path / "input.png"
    _write_rgba_png(input_file)

    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={"format": "jpg", "quality": 85},
        progress_callback=lambda _progress, _message: None,
    )

    assert len(outputs) == 1
    output_path = Path(outputs[0])
    assert output_path.suffix.lower() == ".jpg"

    image = Image.open(output_path)
    assert image.mode == "RGB"


def test_process_png_to_webp_with_quality(tmp_path) -> None:
    processor = ConvertProcessor()
    input_file = tmp_path / "input.png"
    _write_rgba_png(input_file)

    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={"format": "webp", "quality": 70},
        progress_callback=lambda _progress, _message: None,
    )

    output_path = Path(outputs[0])
    assert output_path.suffix.lower() == ".webp"

    image = Image.open(output_path)
    assert image.format == "WEBP"


def test_process_png_to_png_keeps_alpha(tmp_path) -> None:
    processor = ConvertProcessor()
    input_file = tmp_path / "input.png"
    _write_rgba_png(input_file)

    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={"format": "png", "quality": 90},
        progress_callback=lambda _progress, _message: None,
    )

    output_path = Path(outputs[0])
    assert output_path.suffix.lower() == ".png"

    image = Image.open(output_path)
    assert image.mode == "RGBA"


def test_process_raises_for_invalid_params(tmp_path) -> None:
    processor = ConvertProcessor()
    input_file = tmp_path / "input.png"
    _write_rgba_png(input_file)

    with pytest.raises(ValueError, match="Invalid params"):
        processor.process(
            input_file=str(input_file),
            output_dir=str(tmp_path),
            params={"format": "gif", "quality": 90},
            progress_callback=lambda _progress, _message: None,
        )
