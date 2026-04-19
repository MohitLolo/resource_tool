from __future__ import annotations

import cv2
import numpy as np

from app.processors.image.watermark_detect import (
    auto_detect_mask,
    detect_corner_watermark,
    detect_text_contours,
    detect_tiled_watermark,
)


def _uniform_image(h: int = 200, w: int = 200, value: int = 120) -> np.ndarray:
    return np.full((h, w, 3), value, dtype=np.uint8)


def _add_corner_text(image: np.ndarray, text: str = "WATERMARK", pos: str = "br") -> np.ndarray:
    """在指定角落叠加半透明白色文字。"""
    h, w = image.shape[:2]
    overlay = image.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.4
    thickness = 1
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
    margin = 10
    if pos == "br":
        origin = (w - tw - margin, h - margin)
    elif pos == "bl":
        origin = (margin, h - margin)
    elif pos == "tr":
        origin = (w - tw - margin, margin + th)
    else:
        origin = (margin, margin + th)
    cv2.putText(overlay, text, origin, font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.5, image, 0.5, 0, image)
    return image


def _add_tiled_pattern(image: np.ndarray, text: str = "COPY", spacing: int = 50) -> np.ndarray:
    """在整图上平铺斜体文字水印。"""
    h, w = image.shape[:2]
    for y in range(0, h, spacing):
        for x in range(0, w, spacing):
            cv2.putText(
                image,
                text,
                (x, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.3,
                (200, 200, 200),
                1,
                cv2.LINE_AA,
            )
    return image


class TestDetectCornerWatermark:
    def test_detects_corner_text(self) -> None:
        img = _uniform_image(200, 200, 100)
        img = _add_corner_text(img, "WM", "br")
        mask = detect_corner_watermark(img, sensitivity=70)
        assert mask is not None
        assert mask.shape == (200, 200)
        assert mask.max() > 0

    def test_returns_zeros_on_clean_image(self) -> None:
        img = _uniform_image(200, 200, 120)
        mask = detect_corner_watermark(img, sensitivity=50)
        assert mask is not None
        assert mask.sum() == 0 or mask.max() == 0

    def test_sensitivity_affects_detection(self) -> None:
        img = _uniform_image(200, 200, 100)
        img = _add_corner_text(img, "WM", "br")
        mask_low = detect_corner_watermark(img, sensitivity=20)
        mask_high = detect_corner_watermark(img, sensitivity=90)
        assert mask_high.sum() >= mask_low.sum()


class TestDetectTiledWatermark:
    def test_detects_tiled_pattern(self) -> None:
        img = _uniform_image(200, 200, 80)
        img = _add_tiled_pattern(img, spacing=40)
        mask = detect_tiled_watermark(img)
        assert mask is not None
        assert mask.shape == (200, 200)

    def test_returns_zeros_on_clean_image(self) -> None:
        img = _uniform_image(200, 200, 120)
        mask = detect_tiled_watermark(img)
        assert mask is not None
        assert mask.sum() == 0 or mask.max() == 0


class TestDetectTextContours:
    def test_finds_text_regions(self) -> None:
        img = _uniform_image(200, 200, 80)
        cv2.putText(img, "AI", (80, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 240, 240), 2, cv2.LINE_AA)
        mask = detect_text_contours(img, sensitivity=70)
        assert mask is not None
        assert mask.max() > 0


class TestAutoDetectMask:
    def test_combined_detection(self) -> None:
        img = _uniform_image(200, 200, 100)
        img = _add_corner_text(img, "WM", "br")
        mask = auto_detect_mask(img, sensitivity=70)
        assert mask is not None
        assert mask.shape[:2] == (200, 200)

    def test_returns_empty_on_clean_image(self) -> None:
        img = _uniform_image(200, 200, 120)
        mask = auto_detect_mask(img, sensitivity=50)
        assert mask is not None
        assert mask.shape[:2] == (200, 200)
