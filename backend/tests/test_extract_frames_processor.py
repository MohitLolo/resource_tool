from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from app.processors.video.extract_frames import ExtractFramesProcessor


def test_extract_frames_metadata_and_validate() -> None:
    processor = ExtractFramesProcessor()

    assert processor.name == "video.extract_frames"
    assert processor.label == "视频截帧"
    assert processor.category == "video"

    assert processor.validate({"mode": "all", "fps": 10, "format": "png"}) is True
    assert processor.validate(
        {"mode": "range", "fps": 8, "start": 0.2, "end": 0.8, "format": "jpg"}
    ) is True

    assert processor.validate({"mode": "bad", "fps": 10, "format": "png"}) is False
    assert processor.validate({"mode": "all", "fps": 0, "format": "png"}) is False
    assert processor.validate({"mode": "all", "fps": 99, "format": "png"}) is False
    assert processor.validate({"mode": "range", "fps": 10, "start": 1.0, "end": 0.5, "format": "png"}) is False
    assert processor.validate({"mode": "all", "fps": 10, "format": "bmp"}) is False


def test_process_builds_ffmpeg_command_for_range_mode(tmp_path, monkeypatch) -> None:
    processor = ExtractFramesProcessor()
    input_file = tmp_path / "input.mp4"
    input_file.write_bytes(b"fake")

    captured: list[list[str]] = []

    def fake_run(cmd, check, capture_output, text):
        assert check is False
        assert capture_output is True
        assert text is True
        captured.append(cmd)
        pattern = Path(cmd[-1])
        frame1 = Path(str(pattern).replace("%05d", "00001"))
        frame2 = Path(str(pattern).replace("%05d", "00002"))
        frame1.parent.mkdir(parents=True, exist_ok=True)
        frame1.write_bytes(b"x")
        frame2.write_bytes(b"x")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr("app.processors.video.extract_frames.subprocess.run", fake_run)

    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={"mode": "range", "fps": 5, "start": 0.2, "end": 0.8, "format": "jpg"},
        progress_callback=lambda _progress, _message: None,
    )

    assert len(captured) == 1
    cmd = captured[0]
    assert cmd[0] == "ffmpeg"
    assert "-ss" in cmd and "0.2" in cmd
    assert "-to" in cmd and "0.8" in cmd
    assert "-vf" in cmd and "fps=5" in cmd
    assert cmd[-1].endswith("frame_%05d.jpg")

    assert len(outputs) == 2
    assert outputs[0].endswith(".jpg")
    assert "extract_frames_" in outputs[0]


def test_process_does_not_include_historical_frames(tmp_path, monkeypatch) -> None:
    processor = ExtractFramesProcessor()
    input_file = tmp_path / "input.mp4"
    input_file.write_bytes(b"fake")
    # 历史任务遗留文件，不应被本次输出计入。
    (tmp_path / "frame_99999.jpg").write_bytes(b"old")

    def fake_run(cmd, check, capture_output, text):
        pattern = Path(cmd[-1])
        frame = Path(str(pattern).replace("%05d", "00001"))
        frame.parent.mkdir(parents=True, exist_ok=True)
        frame.write_bytes(b"new")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr("app.processors.video.extract_frames.subprocess.run", fake_run)

    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={"mode": "all", "fps": 5, "format": "jpg"},
        progress_callback=lambda _progress, _message: None,
    )

    assert len(outputs) == 1
    assert outputs[0].endswith("frame_00001.jpg")
    assert outputs[0] != str(tmp_path / "frame_99999.jpg")


def test_process_raises_when_input_file_missing(tmp_path) -> None:
    processor = ExtractFramesProcessor()

    with pytest.raises(FileNotFoundError, match="Input video not found"):
        processor.process(
            input_file=str(tmp_path / "missing.mp4"),
            output_dir=str(tmp_path),
            params={"mode": "all", "fps": 5, "format": "png"},
            progress_callback=lambda _progress, _message: None,
        )


def test_process_surfaces_ffmpeg_stderr(tmp_path, monkeypatch) -> None:
    processor = ExtractFramesProcessor()
    input_file = tmp_path / "input.mp4"
    input_file.write_bytes(b"fake")

    def fake_run(cmd, check, capture_output, text):
        return subprocess.CompletedProcess(cmd, 1, "", "bad codec")

    monkeypatch.setattr("app.processors.video.extract_frames.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="bad codec"):
        processor.process(
            input_file=str(input_file),
            output_dir=str(tmp_path),
            params={"mode": "all", "fps": 5, "format": "png"},
            progress_callback=lambda _progress, _message: None,
        )


@pytest.mark.integration
def test_process_integration_with_real_ffmpeg(tmp_path) -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not available")

    processor = ExtractFramesProcessor()
    input_file = tmp_path / "sample.mp4"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=160x120:d=1",
            str(input_file),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={"mode": "all", "fps": 5, "format": "png"},
        progress_callback=lambda _progress, _message: None,
    )

    assert len(outputs) >= 3
    for item in outputs:
        assert item.endswith(".png")
        assert Path(item).exists()
