from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from app.core.base import BaseProcessor, ProgressCallback
from app.processors.image.watermark_detect import auto_detect_mask


class WatermarkProcessor(BaseProcessor):
    """去除图片水印，支持自动检测与手动遮罩，优先使用 LaMa 修复。"""

    name = "image.watermark"
    label = "去水印"
    category = "image"
    params_schema = {
        "mode": {
            "type": "select",
            "label": "模式",
            "default": "auto",
            "options": ["auto", "manual"],
        },
        "sensitivity": {
            "type": "number",
            "label": "检测灵敏度",
            "default": 70,
            "min": 1,
            "max": 100,
        },
        "mask_dilate": {
            "type": "number",
            "label": "遮罩膨胀",
            "default": 3,
            "min": 1,
            "max": 30,
        },
        "mask_file": {
            "type": "file",
            "label": "遮罩文件",
            "required": False,
            "visible_when": {"mode": "manual"},
        },
    }

    _lama_instance: Any = None
    _lama_loaded = False
    _lama_failed = False

    def validate(self, params: dict) -> bool:
        mode = str(params.get("mode", "auto")).lower()
        if mode not in {"auto", "manual"}:
            return False

        sensitivity = self._as_int(params.get("sensitivity", 70))
        if sensitivity is None or not 1 <= sensitivity <= 100:
            return False

        mask_dilate = self._as_int(params.get("mask_dilate", 3))
        if mask_dilate is None or not 1 <= mask_dilate <= 30:
            return False

        return True

    def process(
        self,
        input_file: str,
        output_dir: str,
        params: dict,
        progress_callback: ProgressCallback,
    ) -> list[str]:
        if not self.validate(params):
            raise ValueError("参数无效")

        progress_callback(5, "读取图片")
        image = cv2.imread(input_file, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"无法读取图片: {input_file}")

        progress_callback(12, "生成遮罩")
        mode = str(params.get("mode", "auto")).lower()
        mask_dilate = self._as_int(params.get("mask_dilate", 3)) or 3

        if mode == "manual":
            mask = self._load_manual_mask(image, params)
        else:
            sensitivity = self._as_int(params.get("sensitivity", 70)) or 70
            mask = auto_detect_mask(image, sensitivity=sensitivity)

        kernel = np.ones((mask_dilate, mask_dilate), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)

        progress_callback(35, "修复水印区域")
        result = self._inpaint(image, mask)

        output_path = Path(output_dir) / f"{Path(input_file).stem}_watermark.png"
        cv2.imwrite(str(output_path), result)
        progress_callback(100, "完成")
        return [str(output_path)]

    def _inpaint(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        try:
            return self._inpaint_lama(image, mask)
        except Exception:
            return cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)

    def _inpaint_lama(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        lama = self._get_or_create_lama()
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
        pil_mask = Image.fromarray(mask).convert("L")
        result = lama(pil_image, pil_mask)

        if isinstance(result, Image.Image):
            out = np.array(result)
        else:
            out = np.array(result)

        if out.ndim == 2:
            out = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
        if out.shape[-1] == 4:
            out = cv2.cvtColor(out, cv2.COLOR_RGBA2RGB)
        return cv2.cvtColor(out, cv2.COLOR_RGB2BGR)

    def _get_or_create_lama(self):
        cls = self.__class__
        if cls._lama_loaded and cls._lama_instance is not None:
            return cls._lama_instance
        if cls._lama_failed:
            raise ImportError("simple-lama-inpainting not available")

        try:
            from simple_lama_inpainting import SimpleLama
        except Exception as exc:
            cls._lama_failed = True
            raise ImportError("simple-lama-inpainting not available") from exc

        cls._lama_instance = SimpleLama()
        cls._lama_loaded = True
        cls._lama_failed = False
        return cls._lama_instance

    def _load_manual_mask(self, image: np.ndarray, params: dict) -> np.ndarray:
        mask_path = self._resolve_mask_file(params)
        if mask_path:
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            if mask is None:
                raise ValueError(f"无法读取遮罩文件: {mask_path}")
            if mask.shape != image.shape[:2]:
                raise ValueError("遮罩尺寸必须与输入图片一致")
            return mask
        return auto_detect_mask(image, sensitivity=70)

    def _resolve_mask_file(self, params: dict) -> str | None:
        extra_files = params.get("extra_files", {})
        if not isinstance(extra_files, dict):
            return None

        mask_file_key = params.get("mask_file_key")
        if isinstance(mask_file_key, str) and mask_file_key in extra_files:
            return str(extra_files[mask_file_key])

        mask_file = params.get("mask_file")
        if isinstance(mask_file, str):
            if mask_file in extra_files:
                return str(extra_files[mask_file])
            if Path(mask_file).exists():
                return mask_file
        return None
