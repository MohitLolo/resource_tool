from __future__ import annotations

import inspect
from pathlib import Path

import cv2
import numpy as np

from app.core.base import BaseProcessor, ProgressCallback


class WatermarkProcessor(BaseProcessor):
    """去除图片水印，支持手动遮罩与自动检测遮罩。"""

    name = "image.watermark"
    label = "去水印"
    category = "image"
    params_schema = {
        "algorithm": {
            "type": "select",
            "label": "算法",
            "default": "telea",
            "options": ["telea", "ns"],
        },
        "sensitivity": {
            "type": "number",
            "label": "检测灵敏度",
            "default": 70,
            "min": 1,
            "max": 100,
        },
        "brush_size": {
            "type": "number",
            "label": "修复半径",
            "default": 3,
            "min": 1,
            "max": 20,
        },
        "mask_file": {
            "type": "file",
            "label": "遮罩文件",
            "required": False,
        },
    }

    def validate(self, params: dict) -> bool:
        """校验算法参数。"""
        algorithm = str(params.get("algorithm", "telea")).lower()
        if algorithm not in {"telea", "ns"}:
            return False

        sensitivity = self._as_int(params.get("sensitivity", 70))
        if sensitivity is None or not 1 <= sensitivity <= 100:
            return False

        brush_size = self._as_int(params.get("brush_size", 3))
        if brush_size is None or not 1 <= brush_size <= 20:
            return False

        return True

    def process(
        self,
        input_file: str,
        output_dir: str,
        params: dict,
        progress_callback: ProgressCallback,
    ) -> list[str]:
        """执行去水印处理。"""
        if not self.validate(params):
            raise ValueError("Invalid algorithm. Allowed values: telea, ns")

        progress_callback(10, "读取图片")
        image = cv2.imread(input_file, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Failed to read input image: {input_file}")

        sensitivity = self._resolve_sensitivity(params)
        mask = self._load_mask(image, params, sensitivity=sensitivity)
        progress_callback(70, "修复水印区域")

        brush_size = self._resolve_brush_size(params)
        method = self._resolve_method(str(params.get("algorithm", "telea")))
        output = cv2.inpaint(image, mask, brush_size, method)

        output_path = Path(output_dir) / f"{Path(input_file).stem}_watermark.png"
        cv2.imwrite(str(output_path), output)

        progress_callback(100, "完成")
        return [str(output_path)]

    def _resolve_method(self, algorithm: str) -> int:
        return cv2.INPAINT_NS if algorithm.lower() == "ns" else cv2.INPAINT_TELEA

    def _load_mask(self, image: np.ndarray, params: dict, sensitivity: int = 70) -> np.ndarray:
        mask_file = self._resolve_mask_file(params)
        if mask_file:
            mask = cv2.imread(mask_file, cv2.IMREAD_GRAYSCALE)
            if mask is None:
                raise ValueError(f"Failed to read mask file: {mask_file}")
            if mask.shape != image.shape[:2]:
                raise ValueError("Mask shape must match input image size")
            return mask
        auto_detect_params = inspect.signature(self._auto_detect_mask).parameters
        if len(auto_detect_params) >= 2:
            return self._auto_detect_mask(image, sensitivity=sensitivity)
        return self._auto_detect_mask(image)

    def _resolve_sensitivity(self, params: dict) -> int:
        sensitivity = self._as_int(params.get("sensitivity", 70))
        if sensitivity is None or not 1 <= sensitivity <= 100:
            raise ValueError("Invalid sensitivity. Allowed range: 1-100")
        return sensitivity

    def _resolve_brush_size(self, params: dict) -> int:
        brush_size = self._as_int(params.get("brush_size", 3))
        if brush_size is None or not 1 <= brush_size <= 20:
            raise ValueError("Invalid brush_size. Allowed range: 1-20")
        return brush_size

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

    def _auto_detect_mask(self, image: np.ndarray, sensitivity: int = 70) -> np.ndarray:
        # 灵敏度 1-100 映射到阈值 254-120，灵敏度越高阈值越低，检测范围越广
        threshold = int(254 - (sensitivity / 100) * 134)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        kernel = np.ones((3, 3), np.uint8)
        return cv2.dilate(mask, kernel, iterations=1)
