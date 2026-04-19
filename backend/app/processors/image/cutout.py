from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.base import BaseProcessor


class CutoutProcessor(BaseProcessor):
    name = "image.cutout"
    label = "智能抠图"
    category = "image"
    params_schema = {
        "alpha_matting": {
            "type": "checkbox",
            "label": "精细边缘 (Alpha Matting)",
            "default": False,
        }
    }

    def validate(self, params: dict) -> bool:
        return True

    def process(
        self,
        input_file: str,
        output_dir: str,
        params: dict,
        progress_callback,
    ) -> list[str]:
        progress_callback(10, "读取图片")
        input_bytes = Path(input_file).read_bytes()

        progress_callback(60, "移除背景")
        alpha_matting = bool(params.get("alpha_matting", False))
        result = self._remove_background(input_bytes, alpha_matting=alpha_matting)

        progress_callback(85, "编码 PNG")
        png_bytes = self._ensure_rgba_png_bytes(result)

        output_path = Path(output_dir) / f"{Path(input_file).stem}_cutout.png"
        output_path.write_bytes(png_bytes)

        progress_callback(100, "完成")
        return [str(output_path)]

    def _ensure_rgba_png_bytes(self, result: bytes | Image.Image | np.ndarray) -> bytes:
        if isinstance(result, bytes):
            image = Image.open(BytesIO(result)).convert("RGBA")
        elif isinstance(result, Image.Image):
            image = result.convert("RGBA")
        else:
            image = Image.fromarray(result).convert("RGBA")

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def _remove_background(self, input_bytes: bytes, alpha_matting: bool):
        # Some environments package pymatting in a way that breaks numba cache init.
        try:
            from rembg import remove as rembg_remove
        except RuntimeError as exc:
            if "cannot cache function" not in str(exc):
                raise
            os.environ["NUMBA_DISABLE_JIT"] = "1"
            from rembg import remove as rembg_remove

        return rembg_remove(input_bytes, alpha_matting=alpha_matting)
