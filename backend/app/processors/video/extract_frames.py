from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from app.core.base import BaseProcessor, ProgressCallback


class ExtractFramesProcessor(BaseProcessor):
    """按帧率从视频提取图片序列。"""

    name = "video.extract_frames"
    label = "视频截帧"
    category = "video"
    params_schema = {
        "mode": {
            "type": "select",
            "label": "模式",
            "default": "all",
            "options": ["all", "range"],
        },
        "fps": {
            "type": "number",
            "label": "帧率",
            "default": 5,
            "min": 1,
            "max": 60,
        },
        "start": {
            "type": "number",
            "label": "开始时间",
            "default": 0,
            "visible_when": {"mode": "range"},
        },
        "end": {
            "type": "number",
            "label": "结束时间",
            "default": 1,
            "visible_when": {"mode": "range"},
        },
        "format": {
            "type": "select",
            "label": "输出格式",
            "default": "png",
            "options": ["png", "jpg"],
        },
    }

    _FORMAT_ALLOWED = {"png", "jpg"}

    def validate(self, params: dict) -> bool:
        """校验截帧参数。"""
        mode = str(params.get("mode", "all")).lower()
        fps = self._as_int(params.get("fps", 5))
        output_format = str(params.get("format", "png")).lower()

        if mode not in {"all", "range"}:
            return False
        if fps is None or fps < 1 or fps > 60:
            return False
        if output_format not in self._FORMAT_ALLOWED:
            return False

        if mode == "range":
            start = self._as_float(params.get("start"))
            end = self._as_float(params.get("end"))
            if start is None or end is None:
                return False
            if start < 0 or end <= start:
                return False

        return True

    def process(
        self,
        input_file: str,
        output_dir: str,
        params: dict,
        progress_callback: ProgressCallback,
    ) -> list[str]:
        """执行视频截帧。"""
        if not self.validate(params):
            raise ValueError("Invalid params for video.extract_frames")
        if not Path(input_file).exists():
            raise FileNotFoundError(f"Input video not found: {input_file}")

        mode = str(params.get("mode", "all")).lower()
        fps = int(params.get("fps", 5))
        output_format = str(params.get("format", "png")).lower()

        output_dir_path = Path(output_dir)
        run_dir = output_dir_path / f"extract_frames_{uuid.uuid4().hex[:8]}"
        run_dir.mkdir(parents=True, exist_ok=True)
        output_pattern = run_dir / f"frame_%05d.{output_format}"

        command = ["ffmpeg", "-y"]
        if mode == "range":
            start = float(params.get("start", 0))
            end = float(params.get("end", 1))
            command.extend(["-ss", str(start), "-to", str(end)])

        command.extend(
            [
                "-i",
                input_file,
                "-vf",
                f"fps={fps}",
                str(output_pattern),
            ]
        )

        progress_callback(10, "提取视频帧")
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            message = stderr or "ffmpeg execution failed"
            raise RuntimeError(f"ffmpeg failed: {message}")

        frames = sorted(run_dir.glob(f"frame_*.{output_format}"))
        progress_callback(100, "完成")
        return [str(path) for path in frames]
