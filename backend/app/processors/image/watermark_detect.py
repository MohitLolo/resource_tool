from __future__ import annotations

import cv2
import numpy as np


def auto_detect_mask(image: np.ndarray, sensitivity: int = 70) -> np.ndarray:
    """自动检测水印并生成遮罩。"""
    h, w = image.shape[:2]
    tiled_mask = detect_tiled_watermark(image)
    if tiled_mask is not None and tiled_mask.max() > 0:
        return tiled_mask

    corner_mask = detect_corner_watermark(image, sensitivity=sensitivity)
    text_mask = detect_text_contours(image, sensitivity=sensitivity)

    combined = np.zeros((h, w), dtype=np.uint8)
    if corner_mask is not None:
        combined = cv2.bitwise_or(combined, corner_mask)
    if text_mask is not None:
        combined = cv2.bitwise_or(combined, text_mask)
    return combined


def detect_tiled_watermark(image: np.ndarray, peak_threshold: float = 0.78) -> np.ndarray:
    """通过 FFT 频域峰值检测平铺水印。"""
    gray = _to_gray(image)
    h, w = gray.shape

    rows = cv2.getOptimalDFTSize(h)
    cols = cv2.getOptimalDFTSize(w)
    padded = np.zeros((rows, cols), dtype=np.float32)
    padded[:h, :w] = gray.astype(np.float32)

    dft = cv2.dft(padded, flags=cv2.DFT_COMPLEX_OUTPUT)
    dft_shift = np.fft.fftshift(dft)
    magnitude = cv2.magnitude(dft_shift[:, :, 0], dft_shift[:, :, 1])
    magnitude = np.log1p(magnitude)

    mag_norm = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    center_r, center_c = rows // 2, cols // 2
    radius = min(rows, cols) // 8
    cv2.circle(mag_norm, (center_c, center_r), radius, 0, -1)

    threshold = int(255 * peak_threshold)
    _, peaks = cv2.threshold(mag_norm, threshold, 255, cv2.THRESH_BINARY)
    num_peaks = cv2.countNonZero(peaks)

    if num_peaks < 4 or num_peaks > rows * cols * 0.01:
        return np.zeros((h, w), dtype=np.uint8)

    edges = cv2.Canny(gray, 50, 140)
    kernel = np.ones((3, 3), np.uint8)
    return cv2.dilate(edges, kernel, iterations=1)[:h, :w]


def detect_corner_watermark(
    image: np.ndarray,
    sensitivity: int = 70,
    corner_ratio: float = 0.15,
) -> np.ndarray:
    """检测四角区域水印。"""
    gray = _to_gray(image)
    h, w = gray.shape
    corner_h = max(int(h * corner_ratio), 16)
    corner_w = max(int(w * corner_ratio), 16)
    mask = np.zeros((h, w), dtype=np.uint8)

    corners = [
        (0, 0, corner_h, corner_w),
        (0, w - corner_w, corner_h, w),
        (h - corner_h, 0, h, corner_w),
        (h - corner_h, w - corner_w, h, w),
    ]

    canny_low = 45
    canny_high = 150
    block_size = 31 if sensitivity < 40 else 25 if sensitivity < 70 else 21

    for y1, x1, y2, x2 in corners:
        roi = gray[y1:y2, x1:x2]
        if roi.size == 0:
            continue

        edges = cv2.Canny(roi, canny_low, canny_high)

        bright_threshold = min(250, int(float(np.mean(roi)) + max(6, (110 - sensitivity) * 0.8)))
        _, bright = cv2.threshold(roi, bright_threshold, 255, cv2.THRESH_BINARY)
        combined = cv2.bitwise_or(edges, bright)

        combined = _filter_small_components(combined, min_area=5)
        kernel = np.ones((2, 2), np.uint8)
        combined = cv2.dilate(combined, kernel, iterations=1)
        mask[y1:y2, x1:x2] = cv2.bitwise_or(mask[y1:y2, x1:x2], combined)

    return mask


def detect_text_contours(image: np.ndarray, sensitivity: int = 70) -> np.ndarray:
    """检测文字轮廓区域。"""
    gray = _to_gray(image)
    h, w = gray.shape
    mask = np.zeros((h, w), dtype=np.uint8)

    block_size = 29 if sensitivity < 40 else 23 if sensitivity < 70 else 19
    adaptive = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        2,
    )
    bright_threshold = min(250, int(float(np.mean(gray)) + max(10, (110 - sensitivity) * 1.1)))
    _, bright = cv2.threshold(gray, bright_threshold, 255, cv2.THRESH_BINARY)
    edges = cv2.Canny(gray, 45, 150)
    binary = cv2.bitwise_or(cv2.bitwise_or(adaptive, edges), bright)
    binary = _filter_small_components(binary, min_area=5 if sensitivity >= 70 else 8)

    kernel = np.ones((2, 2), np.uint8)
    mask = cv2.dilate(binary, kernel, iterations=1)
    return mask


def _to_gray(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def _filter_small_components(binary: np.ndarray, min_area: int) -> np.ndarray:
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = np.zeros_like(binary)
    for contour in contours:
        if cv2.contourArea(contour) >= min_area:
            cv2.drawContours(out, [contour], -1, 255, -1)
    return out
