from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.base import BaseProcessor, ProgressCallback


class CutoutProcessor(BaseProcessor):
    """移除图片背景并输出透明 PNG。"""

    name = "image.cutout"
    label = "智能抠图"
    category = "image"
    params_schema = {
        "alpha_matting": {
            "type": "checkbox",
            "label": "精细边缘",
            "default": False,
        }
    }

    def validate(self, params: dict) -> bool:
        """抠图处理器当前无强约束参数。"""
        return True

    def process(
        self,
        input_file: str,
        output_dir: str,
        params: dict,
        progress_callback: ProgressCallback,
    ) -> list[str]:
        """执行抠图处理。"""
        progress_callback(5, "加载模型")
        self._warmup_rembg()

        progress_callback(10, "读取图片")
        input_bytes = Path(input_file).read_bytes()

        progress_callback(30, "移除背景")
        alpha_matting = bool(params.get("alpha_matting", False))
        result = self._remove_background(input_bytes, alpha_matting=alpha_matting)

        progress_callback(85, "编码 PNG")
        png_bytes = self._ensure_rgba_png_bytes(result)

        output_path = Path(output_dir) / f"{Path(input_file).stem}_cutout.png"
        output_path.write_bytes(png_bytes)

        progress_callback(100, "完成")
        return [str(output_path)]

    def _warmup_rembg(self) -> None:
        """首次调用时预加载模型，后续调用走缓存不耗时。"""
        if self.__class__._model_loaded:
            return
        from rembg import remove as rembg_remove
        # 用 1x1 透明 PNG 触发模型下载和初始化
        dummy = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        buf = BytesIO()
        dummy.save(buf, format="PNG")
        rembg_remove(buf.getvalue())
        self.__class__._model_loaded = True

    _model_loaded = False

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

    def _remove_background(
        self,
        input_bytes: bytes,
        alpha_matting: bool,
    ) -> bytes | Image.Image | np.ndarray:
        # 部分环境下 pymatting 会触发 numba 缓存初始化异常，这里降级关闭 JIT 重试。
        try:
            from rembg import remove as rembg_remove
        except RuntimeError as exc:
            if "cannot cache function" not in str(exc):
                raise
            os.environ["NUMBA_DISABLE_JIT"] = "1"
            from rembg import remove as rembg_remove

        return rembg_remove(input_bytes, alpha_matting=alpha_matting)
