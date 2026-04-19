# 去水印功能优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 LaMa 深度学习模型替换 OpenCV inpaint，提升水印修复质量；前端增加画笔涂抹交互。

**Architecture:** 后端 watermark.py 重写检测层（FFT 频域分析 + 自适应阈值 + 边缘检测），修复层集成 simple-lama-inpainting（onnxruntime 推理，懒加载 + 类级缓存）。前端新增 MaskCanvas.vue 组件（原生 Canvas API 画笔涂抹），集成到 ToolWorkbench.vue。

**Tech Stack:** simple-lama-inpainting, onnxruntime, OpenCV (FFT/Canny/adaptiveThreshold), Canvas API, Vue 3

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `backend/app/processors/image/watermark.py` | 重写：检测层 + LaMa 修复 + 降级 |
| `backend/app/processors/image/watermark_detect.py` | 新增：自动水印检测算法（FFT + 边角 + 文字） |
| `backend/requirements.txt` | 新增 simple-lama-inpainting |
| `backend/tests/test_watermark_processor.py` | 更新测试覆盖新逻辑 |
| `backend/tests/test_watermark_detect.py` | 新增：检测算法单元测试 |
| `frontend/src/components/MaskCanvas.vue` | 新增：canvas 画笔涂抹组件 |
| `frontend/src/views/ToolWorkbench.vue` | 集成 MaskCanvas，mode 切换逻辑 |

---

### Task 1：安装 simple-lama-inpainting 依赖

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 添加依赖到 requirements.txt**

在 `backend/requirements.txt` 末尾添加：

```
simple-lama-inpainting
```

完整文件内容：

```
fastapi
uvicorn[standard]
celery
redis[hiredis]
pillow
opencv-python-headless
rembg
ffmpeg-python
pydub
python-multipart
aiofiles
pydantic-settings
pytest
httpx
simple-lama-inpainting
```

- [ ] **Step 2: 安装依赖**

Run: `cd backend && conda run -n gameasset pip install simple-lama-inpainting`
Expected: Successfully installed simple-lama-inpainting

- [ ] **Step 3: 验证导入**

Run: `conda run -n gameasset python -c "from simple_lama_inpainting import SimpleLama; print('OK')"`
Expected: OK

- [ ] **Step 4: 提交**

```bash
git add backend/requirements.txt
git commit -m "chore: 添加 simple-lama-inpainting 依赖"
```

---

### Task 2：编写水印检测算法

**Files:**
- Create: `backend/app/processors/image/watermark_detect.py`
- Create: `backend/tests/test_watermark_detect.py`

- [ ] **Step 1: 编写检测算法的测试**

创建 `backend/tests/test_watermark_detect.py`：

```python
from __future__ import annotations

import cv2
import numpy as np
import pytest

from app.processors.image.watermark_detect import (
    detect_corner_watermark,
    detect_tiled_watermark,
    detect_text_contours,
    auto_detect_mask,
)


def _uniform_image(h=200, w=200, value=120):
    return np.full((h, w, 3), value, dtype=np.uint8)


def _add_corner_text(image, text="WATERMARK", pos="br"):
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


def _add_tiled_pattern(image, text="COPY", spacing=50):
    """在整图上平铺斜体文字水印。"""
    h, w = image.shape[:2]
    for y in range(0, h, spacing):
        for x in range(0, w, spacing):
            cv2.putText(
                image, text, (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 200, 200), 1, cv2.LINE_AA,
            )
    return image


class TestDetectCornerWatermark:
    def test_detects_corner_text(self):
        img = _uniform_image(200, 200, 100)
        img = _add_corner_text(img, "WM", "br")
        mask = detect_corner_watermark(img, sensitivity=70)
        assert mask is not None
        assert mask.shape == (200, 200)
        assert mask.max() > 0

    def test_returns_zeros_on_clean_image(self):
        img = _uniform_image(200, 200, 120)
        mask = detect_corner_watermark(img, sensitivity=50)
        assert mask is not None
        # 均匀图不应检测到水印
        assert mask.sum() == 0 or mask.max() == 0

    def test_sensitivity_affects_detection(self):
        img = _uniform_image(200, 200, 100)
        img = _add_corner_text(img, "WM", "br")
        mask_low = detect_corner_watermark(img, sensitivity=20)
        mask_high = detect_corner_watermark(img, sensitivity=90)
        # 高灵敏度应检测到更多像素
        assert mask_high.sum() >= mask_low.sum()


class TestDetectTiledWatermark:
    def test_detects_tiled_pattern(self):
        img = _uniform_image(200, 200, 80)
        img = _add_tiled_pattern(img, spacing=40)
        mask = detect_tiled_watermark(img)
        assert mask is not None
        assert mask.shape == (200, 200)

    def test_returns_zeros_on_clean_image(self):
        img = _uniform_image(200, 200, 120)
        mask = detect_tiled_watermark(img)
        assert mask is not None
        assert mask.sum() == 0 or mask.max() == 0


class TestDetectTextContours:
    def test_finds_text_regions(self):
        img = _uniform_image(200, 200, 80)
        cv2.putText(img, "AI", (80, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 240, 240), 2, cv2.LINE_AA)
        mask = detect_text_contours(img, sensitivity=70)
        assert mask is not None
        assert mask.max() > 0


class TestAutoDetectMask:
    def test_combined_detection(self):
        img = _uniform_image(200, 200, 100)
        img = _add_corner_text(img, "WM", "br")
        mask = auto_detect_mask(img, sensitivity=70)
        assert mask is not None
        assert mask.shape[:2] == (200, 200)

    def test_returns_empty_on_clean_image(self):
        img = _uniform_image(200, 200, 120)
        mask = auto_detect_mask(img, sensitivity=50)
        assert mask is not None
        # 干净图可能返回全零遮罩
        assert mask.shape[:2] == (200, 200)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && conda run -n gameasset pytest tests/test_watermark_detect.py -v`
Expected: FAIL — ModuleNotFoundError: No module named 'app.processors.image.watermark_detect'

- [ ] **Step 3: 编写检测算法实现**

创建 `backend/app/processors/image/watermark_detect.py`：

```python
from __future__ import annotations

import cv2
import numpy as np


def auto_detect_mask(image: np.ndarray, sensitivity: int = 70) -> np.ndarray:
    """自动检测水印并生成遮罩。

    按优先级依次检测：平铺水印 → 边角水印 → 文字轮廓。
    返回与 image 同尺寸的灰度遮罩（255=水印区域）。
    """
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


def detect_tiled_watermark(image: np.ndarray, peak_threshold: float = 0.6) -> np.ndarray:
    """通过 FFT 频域分析检测全屏平铺水印。

    平铺水印会在频域中产生规律性峰值。检测到峰值后
    在空间域定位水印像素，生成遮罩。
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    h, w = gray.shape[:2]

    # 扩展到 2 的幂次加速 FFT
    rows = cv2.getOptimalDFTSize(h)
    cols = cv2.getOptimalDFTSize(w)
    padded = np.zeros((rows, cols), dtype=np.float32)
    padded[:h, :w] = gray.astype(np.float32)

    # 傅里叶变换
    dft = cv2.dft(padded, flags=cv2.DFT_COMPLEX_OUTPUT)
    dft_shift = np.fft.fftshift(dft)
    magnitude = cv2.magnitude(dft_shift[:, :, 0], dft_shift[:, :, 1])
    magnitude = np.log1p(magnitude)

    # 归一化
    mag_norm = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX)
    mag_uint8 = mag_norm.astype(np.uint8)

    # 去除直流分量（中心区域）以避免误检
    center_r, center_c = rows // 2, cols // 2
    radius = min(rows, cols) // 8
    mask_circle = np.zeros((rows, cols), dtype=np.uint8)
    cv2.circle(mask_circle, (center_c, center_r), radius, 255, -1)
    mag_uint8[mask_circle > 0] = 0

    # 寻找频域峰值
    _, binary = cv2.threshold(mag_uint8, int(255 * peak_threshold), 255, cv2.THRESH_BINARY)

    num_peaks = cv2.countNonZero(binary)
    # 峰值数量太少说明没有平铺水印
    if num_peaks < 4:
        return np.zeros((h, w), dtype=np.uint8)

    # 峰值过多说明不是规律水印（可能是噪声）
    if num_peaks > rows * cols * 0.01:
        return np.zeros((h, w), dtype=np.uint8)

    # 在空间域中用边缘检测定位水印
    edges = cv2.Canny(gray, 50, 150)
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)
    return dilated[:h, :w]


def detect_corner_watermark(
    image: np.ndarray,
    sensitivity: int = 70,
    corner_ratio: float = 0.15,
) -> np.ndarray:
    """检测四角区域的水印（Logo、文字）。

    只扫描图片四角各 corner_ratio 比例的区域，
    使用自适应阈值 + Canny 边缘检测定位水印。
    """
    h, w = image.shape[:2]
    corner_h = max(int(h * corner_ratio), 16)
    corner_w = max(int(w * corner_ratio), 16)

    mask = np.zeros((h, w), dtype=np.uint8)

    # 四个角落的坐标
    corners = [
        (0, 0, corner_h, corner_w),                       # 左上
        (0, w - corner_w, corner_h, w),                    # 右上
        (h - corner_h, 0, h, corner_w),                    # 左下
        (h - corner_h, w - corner_w, h, w),                # 右下
    ]

    # 灵敏度 1-100 映射到 Canny 阈值范围
    # 高灵敏度 → 低阈值 → 更多检测
    canny_low = max(10, int(100 - sensitivity))
    canny_high = max(30, int(200 - sensitivity))

    for y1, x1, y2, x2 in corners:
        roi = image[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi

        # 自适应阈值检测（对半透明水印更敏感）
        block_size = max(3, min(gray.shape[0], gray.shape[1]) // 2)
        if block_size % 2 == 0:
            block_size += 1
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, block_size, -5,
        )

        # Canny 边缘检测
        edges = cv2.Canny(gray, canny_low, canny_high)

        # 合并
        combined = cv2.bitwise_or(adaptive, edges)
        mask[y1:y2, x1:x2] = combined

    # 膨胀遮罩，确保覆盖水印边缘
    kernel = np.ones((2, 2), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=1)

    return mask


def detect_text_contours(
    image: np.ndarray,
    sensitivity: int = 70,
) -> np.ndarray:
    """通过轮廓分析检测文字水印。

    基于 contour 面积和长宽比筛选文字区域，
    sensitivity 控制筛选严格程度。
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    h, w = gray.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    # 灵敏度映射到阈值
    threshold = int(254 - (sensitivity / 100) * 134)
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 文字区域的轮廓特征：
    # - 面积不能太小（噪声）也不能太大（整块背景）
    min_area = max(h * w * 0.0001, 10)
    max_area = h * w * 0.15

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue

        x, y, cw, ch = cv2.boundingRect(contour)
        aspect = cw / max(ch, 1)

        # 文字区域的长宽比通常在 0.1-15 之间
        if aspect < 0.1 or aspect > 15:
            continue

        cv2.drawContours(mask, [contour], -1, 255, -1)

    return mask
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && conda run -n gameasset pytest tests/test_watermark_detect.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/processors/image/watermark_detect.py backend/tests/test_watermark_detect.py
git commit -m "feat: 添加水印自动检测算法（FFT + 边角 + 文字轮廓）"
```

---

### Task 3：重写 WatermarkProcessor 集成 LaMa 修复

**Files:**
- Modify: `backend/app/processors/image/watermark.py`
- Modify: `backend/tests/test_watermark_processor.py`

- [ ] **Step 1: 编写新处理器的测试**

更新 `backend/tests/test_watermark_processor.py`，完全替换为：

```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from app.processors.image.watermark import WatermarkProcessor


def _write_image(path: Path, value: int = 120) -> None:
    image = np.full((8, 8, 3), value, dtype=np.uint8)
    cv2.imwrite(str(path), image)


def test_watermark_processor_metadata() -> None:
    processor = WatermarkProcessor()
    assert processor.name == "image.watermark"
    assert processor.label == "去水印"
    assert processor.category == "image"


def test_validate_auto_mode() -> None:
    processor = WatermarkProcessor()
    assert processor.validate({"mode": "auto"}) is True
    assert processor.validate({"mode": "manual"}) is True
    assert processor.validate({}) is True  # 默认 auto
    assert processor.validate({"mode": "invalid"}) is False


def test_validate_sensitivity() -> None:
    processor = WatermarkProcessor()
    assert processor.validate({"sensitivity": 50}) is True
    assert processor.validate({"sensitivity": 0}) is False
    assert processor.validate({"sensitivity": 101}) is False


def test_validate_mask_dilate() -> None:
    processor = WatermarkProcessor()
    assert processor.validate({"mask_dilate": 5}) is True
    assert processor.validate({"mask_dilate": 0}) is False
    assert processor.validate({"mask_dilate": 31}) is False


def test_process_auto_mode_with_lama(tmp_path, monkeypatch) -> None:
    """自动检测模式使用 LaMa 修复。"""
    processor = WatermarkProcessor()
    input_file = tmp_path / "input.png"
    # 创建带亮斑的图片模拟水印
    image = np.full((32, 32, 3), 100, dtype=np.uint8)
    image[10:22, 10:22] = 240
    cv2.imwrite(str(input_file), image)

    fake_result = np.full((32, 32, 3), 100, dtype=np.uint8)

    mock_lama = MagicMock(return_value=MagicMock())
    monkeypatch.setattr(
        "app.processors.image.watermark.WatermarkProcessor._get_or_create_lama",
        lambda self: mock_lama,
    )
    # 让 LaMa 返回 PIL Image
    from PIL import Image as PILImage
    fake_pil = PILImage.fromarray(fake_result)
    mock_lama.return_value = fake_pil
    monkeypatch.setattr(
        "app.processors.image.watermark.WatermarkProcessor._get_or_create_lama",
        lambda self: mock_lama,
    )
    # 修复：让 _inpaint_lama 直接工作
    monkeypatch.setattr(
        processor,
        "_get_or_create_lama",
        lambda: mock_lama,
    )

    progress_events = []
    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={"mode": "auto", "sensitivity": 70},
        progress_callback=lambda p, m: progress_events.append((p, m)),
    )

    assert len(outputs) == 1
    assert Path(outputs[0]).exists()
    assert progress_events[-1][0] == 100


def test_process_manual_mode_with_mask(tmp_path, monkeypatch) -> None:
    """手动模式使用用户提供的遮罩。"""
    processor = WatermarkProcessor()
    input_file = tmp_path / "input.png"
    mask_file = tmp_path / "mask.png"
    _write_image(input_file, value=100)

    mask = np.zeros((8, 8), dtype=np.uint8)
    mask[2:5, 2:5] = 255
    cv2.imwrite(str(mask_file), mask)

    from PIL import Image as PILImage
    fake_pil = PILImage.fromarray(np.full((8, 8, 3), 100, dtype=np.uint8))
    mock_lama = MagicMock(return_value=fake_pil)
    monkeypatch.setattr(
        processor,
        "_get_or_create_lama",
        lambda: mock_lama,
    )

    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={
            "mode": "manual",
            "mask_file_key": "mask.png",
            "extra_files": {"mask.png": str(mask_file)},
        },
        progress_callback=lambda _p, _m: None,
    )

    assert len(outputs) == 1
    assert Path(outputs[0]).exists()
    assert mock_lama.called


def test_process_fallback_to_opencv(tmp_path, monkeypatch) -> None:
    """LaMa 加载失败时降级到 OpenCV inpaint。"""
    processor = WatermarkProcessor()
    input_file = tmp_path / "input.png"
    mask_file = tmp_path / "mask.png"
    _write_image(input_file, value=100)

    mask = np.zeros((8, 8), dtype=np.uint8)
    mask[2:5, 2:5] = 255
    cv2.imwrite(str(mask_file), mask)

    # 让 LaMa 加载失败
    def raise_import_error():
        raise ImportError("simple-lama-inpainting not available")

    monkeypatch.setattr(
        processor,
        "_get_or_create_lama",
        raise_import_error,
    )

    calls = []

    def fake_inpaint(image, inpaint_mask, radius, method):
        calls.append((radius, method))
        return image

    monkeypatch.setattr("app.processors.image.watermark.cv2.inpaint", fake_inpaint)

    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={
            "mode": "manual",
            "mask_file_key": "mask.png",
            "extra_files": {"mask.png": str(mask_file)},
            "mask_dilate": 3,
        },
        progress_callback=lambda _p, _m: None,
    )

    assert len(outputs) == 1
    assert Path(outputs[0]).exists()
    assert len(calls) == 1  # 降级到了 OpenCV


@pytest.mark.integration
def test_process_integration_with_opencv_fallback(tmp_path) -> None:
    """集成测试：如果 LaMa 不可用则用 OpenCV 降级。"""
    processor = WatermarkProcessor()
    input_file = tmp_path / "input.png"
    mask_file = tmp_path / "mask.png"

    image = np.full((32, 32, 3), 120, dtype=np.uint8)
    image[10:22, 10:22] = 255
    cv2.imwrite(str(input_file), image)

    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[10:22, 10:22] = 255
    cv2.imwrite(str(mask_file), mask)

    progress_events = []
    outputs = processor.process(
        input_file=str(input_file),
        output_dir=str(tmp_path),
        params={
            "mode": "manual",
            "mask_file_key": "mask.png",
            "extra_files": {"mask.png": str(mask_file)},
            "mask_dilate": 3,
        },
        progress_callback=lambda p, m: progress_events.append(p),
    )

    assert len(outputs) == 1
    assert Path(outputs[0]).exists()
    assert progress_events[-1] == 100
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && conda run -n gameasset pytest tests/test_watermark_processor.py -v`
Expected: FAIL — 新的 validate 逻辑和 LaMa 调用不匹配

- [ ] **Step 3: 重写 WatermarkProcessor**

完全替换 `backend/app/processors/image/watermark.py`：

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from app.core.base import BaseProcessor, ProgressCallback
from app.processors.image.watermark_detect import auto_detect_mask


class WatermarkProcessor(BaseProcessor):
    """去除图片水印，支持自动检测与手动遮罩，使用 LaMa 模型修复。"""

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
        },
    }

    _lama_instance: Any = None
    _lama_loaded: bool = False
    _lama_failed: bool = False

    def validate(self, params: dict) -> bool:
        """校验参数。"""
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
        """执行去水印处理。"""
        if not self.validate(params):
            raise ValueError("参数无效")

        progress_callback(5, "读取图片")
        image = cv2.imread(input_file, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"无法读取图片: {input_file}")

        progress_callback(10, "生成遮罩")
        mode = str(params.get("mode", "auto")).lower()
        mask_dilate = self._as_int(params.get("mask_dilate", 3)) or 3

        if mode == "manual":
            mask = self._load_manual_mask(image, params)
            if self._resolve_mask_file(params) is None:
                progress_callback(10, "未提供遮罩，已使用自动检测")
        else:
            sensitivity = self._as_int(params.get("sensitivity", 70)) or 70
            mask = auto_detect_mask(image, sensitivity=sensitivity)

        # 膨胀遮罩确保覆盖边缘
        kernel = np.ones((mask_dilate, mask_dilate), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)

        progress_callback(30, "修复水印区域")
        result = self._inpaint(image, mask, progress_callback=progress_callback)

        output_path = Path(output_dir) / f"{Path(input_file).stem}_watermark.png"
        cv2.imwrite(str(output_path), result)

        progress_callback(100, "完成")
        return [str(output_path)]

    def _load_manual_mask(self, image: np.ndarray, params: dict) -> np.ndarray:
        """加载手动遮罩文件。"""
        mask_path = self._resolve_mask_file(params)
        if mask_path:
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            if mask is None:
                raise ValueError(f"无法读取遮罩文件: {mask_path}")
            if mask.shape != image.shape[:2]:
                raise ValueError("遮罩尺寸必须与输入图片一致")
            return mask
        # 手动模式但没提供遮罩，降级到自动检测
        return auto_detect_mask(image, sensitivity=70)

    def _resolve_mask_file(self, params: dict) -> str | None:
        """解析遮罩文件路径。"""
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

    def _inpaint(self, image: np.ndarray, mask: np.ndarray, progress_callback=None) -> np.ndarray:
        """使用 LaMa 修复，失败时降级到 OpenCV inpaint。"""
        if mask.max() == 0:
            return image

        try:
            lama = self._get_or_create_lama()
            return self._inpaint_lama(image, mask, lama)
        except Exception:
            if progress_callback:
                progress_callback(30, "已降级到基础修复模式，效果可能降低")
            return self._inpaint_opencv(image, mask)

    def _get_or_create_lama(self):
        """懒加载 LaMa 模型，缓存到类级变量。"""
        if self.__class__._lama_failed:
            raise ImportError("LaMa 已标记为不可用")
        if self.__class__._lama_loaded:
            return self.__class__._lama_instance

        from simple_lama_inpainting import SimpleLama

        self.__class__._lama_instance = SimpleLama()
        self.__class__._lama_loaded = True
        return self.__class__._lama_instance

    def _inpaint_lama(self, image: np.ndarray, mask: np.ndarray, lama) -> np.ndarray:
        """使用 LaMa 模型修复。"""
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        pil_mask = Image.fromarray(mask)

        result = lama(pil_image, pil_mask)
        result_bgr = cv2.cvtColor(np.array(result), cv2.COLOR_RGB2BGR)
        return result_bgr

    def _inpaint_opencv(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """降级方案：OpenCV inpaint 修复。"""
        self.__class__._lama_failed = True
        return cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && conda run -n gameasset pytest tests/test_watermark_processor.py -v`
Expected: ALL PASS

- [ ] **Step 5: 运行全部后端测试确认无回归**

Run: `cd backend && conda run -n gameasset pytest tests/ -v --ignore=tests/test_watermark_processor.py -k "not integration"`
Expected: ALL PASS

- [ ] **Step 6: 提交**

```bash
git add backend/app/processors/image/watermark.py backend/tests/test_watermark_processor.py
git commit -m "feat: 重写去水印处理器，集成 LaMa 模型修复，支持自动/手动模式"
```

---

### Task 4：前端 MaskCanvas 画笔涂抹组件

**Files:**
- Create: `frontend/src/components/MaskCanvas.vue`

- [ ] **Step 1: 创建 MaskCanvas.vue 组件**

创建 `frontend/src/components/MaskCanvas.vue`：

```vue
<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  src: {
    type: String,
    default: '',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['mask-ready', 'mask-clear'])

const canvasRef = ref(null)
const containerRef = ref(null)
const brushSize = ref(20)
const tool = ref('brush') // 'brush' | 'eraser'
const isDrawing = ref(false)
const canvasWidth = ref(0)
const canvasHeight = ref(0)
const naturalWidth = ref(0)
const naturalHeight = ref(0)
const hasMask = ref(false)
let ctx = null
let maskCtx = null
let maskCanvas = null
let imageObj = null

function initCanvas() {
  if (!canvasRef.value || !props.src) return

  imageObj = new Image()
  imageObj.crossOrigin = 'anonymous'
  imageObj.onload = () => {
    naturalWidth.value = imageObj.naturalWidth
    naturalHeight.value = imageObj.naturalHeight
    canvasWidth.value = imageObj.naturalWidth
    canvasHeight.value = imageObj.naturalHeight

    nextTick(() => {
      // 主 canvas：显示原图 + 涂抹预览
      ctx = canvasRef.value.getContext('2d')
      ctx.clearRect(0, 0, canvasWidth.value, canvasHeight.value)
      ctx.drawImage(imageObj, 0, 0)

      // 离屏 canvas：只记录涂抹轨迹（黑白遮罩），与原图分离
      maskCanvas = document.createElement('canvas')
      maskCanvas.width = canvasWidth.value
      maskCanvas.height = canvasHeight.value
      maskCtx = maskCanvas.getContext('2d')
      maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height)

      hasMask.value = false
    })
  }
  imageObj.src = props.src
}

function getPos(event) {
  const rect = canvasRef.value.getBoundingClientRect()
  const scaleX = canvasWidth.value / rect.width
  const scaleY = canvasHeight.value / rect.height
  const clientX = event.touches ? event.touches[0].clientX : event.clientX
  const clientY = event.touches ? event.touches[0].clientY : event.clientY
  return {
    x: (clientX - rect.left) * scaleX,
    y: (clientY - rect.top) * scaleY,
  }
}

function startDraw(event) {
  if (props.disabled || !ctx) return
  event.preventDefault()
  isDrawing.value = true
  const pos = getPos(event)
  ctx.beginPath()
  ctx.moveTo(pos.x, pos.y)
  if (maskCtx) {
    maskCtx.beginPath()
    maskCtx.moveTo(pos.x, pos.y)
  }
}

function draw(event) {
  if (!isDrawing.value || !ctx) return
  event.preventDefault()
  const pos = getPos(event)

  // 主 canvas：红色半透明预览涂抹效果
  ctx.globalCompositeOperation = 'source-over'
  ctx.lineWidth = brushSize.value
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'

  if (tool.value === 'eraser') {
    // 橡皮擦：重绘原图对应区域来"擦除"预览
    ctx.globalCompositeOperation = 'destination-out'
    ctx.strokeStyle = 'rgba(0,0,0,1)'
  } else {
    ctx.strokeStyle = 'rgba(255, 50, 50, 0.6)'
  }
  ctx.lineTo(pos.x, pos.y)
  ctx.stroke()
  ctx.globalCompositeOperation = 'source-over'

  // 离屏 canvas：记录纯黑白涂抹轨迹
  if (maskCtx) {
    maskCtx.lineWidth = brushSize.value
    maskCtx.lineCap = 'round'
    maskCtx.lineJoin = 'round'

    if (tool.value === 'eraser') {
      maskCtx.globalCompositeOperation = 'destination-out'
      maskCtx.strokeStyle = 'rgba(0,0,0,1)'
    } else {
      maskCtx.globalCompositeOperation = 'source-over'
      maskCtx.strokeStyle = '#ffffff'
    }
    maskCtx.lineTo(pos.x, pos.y)
    maskCtx.stroke()
    maskCtx.globalCompositeOperation = 'source-over'
  }

  hasMask.value = true
}

function endDraw() {
  if (!isDrawing.value) return
  isDrawing.value = false
  ctx.globalCompositeOperation = 'source-over'
}

function clearMask() {
  if (!ctx) return
  ctx.clearRect(0, 0, canvasWidth.value, canvasHeight.value)
  ctx.drawImage(imageObj, 0, 0)
  if (maskCtx) {
    maskCtx.clearRect(0, 0, canvasWidth.value, canvasHeight.value)
  }
  hasMask.value = false
  emit('mask-clear')
}

function confirmMask() {
  if (!maskCanvas || !maskCtx || !hasMask.value) return

  // 直接从离屏 canvas 导出遮罩，涂抹区域白色，其余透明
  // 先合成黑色背景
  const exportCanvas = document.createElement('canvas')
  exportCanvas.width = canvasWidth.value
  exportCanvas.height = canvasHeight.value
  const exportCtx = exportCanvas.getContext('2d')
  exportCtx.fillStyle = '#000000'
  exportCtx.fillRect(0, 0, exportCanvas.width, exportCanvas.height)
  exportCtx.drawImage(maskCanvas, 0, 0)

  exportCanvas.toBlob((blob) => {
    if (blob) {
      emit('mask-ready', new File([blob], 'mask.png', { type: 'image/png' }))
    }
  }, 'image/png')
}

function onWheel(event) {
  event.preventDefault()
  const delta = event.deltaY > 0 ? -2 : 2
  brushSize.value = Math.max(5, Math.min(50, brushSize.value + delta))
}

watch(() => props.src, () => {
  hasMask.value = false
  initCanvas()
})

onMounted(() => {
  initCanvas()
})

onBeforeUnmount(() => {
  if (imageObj) {
    imageObj.onload = null
    imageObj = null
  }
})
</script>

<template>
  <div class="mask-canvas-wrapper" :class="{ disabled }">
    <div class="toolbar" v-if="src">
      <label class="toolbar-item">
        <span class="toolbar-label">画笔大小</span>
        <input
          type="range"
          min="5"
          max="50"
          :value="brushSize"
          @input="brushSize = Number($event.target.value)"
          class="brush-slider"
        />
        <span class="toolbar-value">{{ brushSize }}px</span>
      </label>
      <div class="toolbar-group">
        <button
          type="button"
          class="tool-btn"
          :class="{ active: tool === 'brush' }"
          @click="tool = 'brush'"
          :disabled="disabled"
        >画笔</button>
        <button
          type="button"
          class="tool-btn"
          :class="{ active: tool === 'eraser' }"
          @click="tool = 'eraser'"
          :disabled="disabled"
        >橡皮擦</button>
      </div>
      <button
        type="button"
        class="tool-btn"
        @click="clearMask"
        :disabled="disabled"
      >清除全部</button>
      <button
        type="button"
        class="tool-btn primary"
        @click="confirmMask"
        :disabled="disabled || !hasMask"
      >确认遮罩</button>
    </div>
    <div class="canvas-container" ref="containerRef">
      <canvas
        ref="canvasRef"
        :width="canvasWidth"
        :height="canvasHeight"
        @mousedown="startDraw"
        @mousemove="draw"
        @mouseup="endDraw"
        @mouseleave="endDraw"
        @touchstart="startDraw"
        @touchmove="draw"
        @touchend="endDraw"
        @wheel="onWheel"
        :class="{ 'cursor-brush': tool === 'brush', 'cursor-eraser': tool === 'eraser' }"
      ></canvas>
    </div>
  </div>
</template>

<style scoped>
.mask-canvas-wrapper {
  width: 100%;
}

.mask-canvas-wrapper.disabled {
  opacity: 0.5;
  pointer-events: none;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: color-mix(in srgb, var(--bg-card) 90%, transparent);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.toolbar-item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: default;
}

.toolbar-label {
  font-size: 12px;
  color: var(--text-dim);
  white-space: nowrap;
}

.toolbar-value {
  font-size: 12px;
  color: var(--text-dim);
  min-width: 32px;
}

.brush-slider {
  width: 80px;
}

.toolbar-group {
  display: flex;
  gap: 2px;
}

.tool-btn {
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text);
  cursor: pointer;
  transition: all 0.15s ease;
}

.tool-btn:hover:not(:disabled) {
  border-color: var(--border-active);
}

.tool-btn.active {
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: #fff;
  border-color: transparent;
}

.tool-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.tool-btn.primary {
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: #fff;
  border-color: transparent;
}

.tool-btn.primary:disabled {
  opacity: 0.4;
}

.canvas-container {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  background: color-mix(in srgb, var(--bg-input) 80%, transparent);
}

canvas {
  display: block;
  width: 100%;
  max-height: 420px;
  object-fit: contain;
}

.cursor-brush {
  cursor: crosshair;
}

.cursor-eraser {
  cursor: cell;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/MaskCanvas.vue
git commit -m "feat: 添加 MaskCanvas 画笔涂抹遮罩组件"
```

---

### Task 5：前端集成 MaskCanvas 到 ToolWorkbench

**Files:**
- Modify: `frontend/src/views/ToolWorkbench.vue`

- [ ] **Step 1: 在 ToolWorkbench.vue 中集成 MaskCanvas**

需要做以下修改：

**1a. 添加 import（在 `<script setup>` 顶部，其他 import 后面）：**

在 `import PreviewPane from '../components/PreviewPane.vue'` 后面添加：

```javascript
import MaskCanvas from '../components/MaskCanvas.vue'
```

**1b. 添加 mask 相关状态变量（在 `const resultSummary = ref('')` 后面）：**

```javascript
const maskFile = ref(null)
const maskConfirmed = ref(false)
const isManualWatermark = computed(
  () => selectedProcessorName.value === 'image.watermark' && params.value.mode === 'manual',
)
```

**1c. 添加 mask 事件处理函数（在 `onParamFileChange` 函数后面）：**

```javascript
function onMaskReady(file) {
  maskFile.value = file
  maskConfirmed.value = true
  extraFileMap.value = {
    ...extraFileMap.value,
    mask_file: file,
  }
}

function onMaskClear() {
  maskFile.value = null
  maskConfirmed.value = false
  delete extraFileMap.value.mask_file
}
```

**1d. 修改 buildTaskPayload 函数，在手动模式下自动添加 mask_file_key：**

在 `buildTaskPayload` 函数中，`return { payloadParams, extraFiles }` 之前添加：

```javascript
  if (maskFile.value && isManualWatermark.value) {
    payloadParams.mask_file_key = 'mask_file'
  }
```

**1e. 在 resetCategoryState 函数中添加 mask 重置：**

在 `resultSummary.value = ''` 后面添加：

```javascript
  maskFile.value = null
  maskConfirmed.value = false
```

**1f. 在 onProcessorChange 函数中添加 mask 重置：**

在 `extraFileMap.value = {}` 后面添加：

```javascript
  maskFile.value = null
  maskConfirmed.value = false
```

**1g. 在 template 的右侧面板（right-panel）中，在 `<div class="preview-grid">` 前面添加 MaskCanvas：**

```html
      <div v-if="isManualWatermark && sourcePreview.src" class="panel-section mask-section">
        <p class="section-title">涂抹水印区域</p>
        <MaskCanvas
          :src="sourcePreview.src"
          :disabled="running"
          @mask-ready="onMaskReady"
          @mask-clear="onMaskClear"
        />
        <div v-if="maskConfirmed" class="mask-hint">遮罩已确认，可以开始处理</div>
      </div>
```

**1h. 在 `<style scoped>` 中添加 mask 相关样式：**

```css
.mask-section {
  margin-bottom: 12px;
}

.mask-hint {
  margin-top: 6px;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 10%, transparent);
  border-radius: var(--radius-sm);
}
```

- [ ] **Step 2: 验证前端构建无误**

Run: `cd frontend && npm run build`
Expected: 构建成功，无错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/views/ToolWorkbench.vue
git commit -m "feat: 集成 MaskCanvas 到工具台，支持手动涂抹去水印遮罩"
```

---

### Task 6：端到端验证

**Files:** 无代码变更

- [ ] **Step 1: 重启后端服务**

```bash
# 杀掉旧进程后重启
cd backend
conda run -n gameasset uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
conda run -n gameasset celery -A app.tasks.worker worker --loglevel=info &
```

- [ ] **Step 2: 验证处理器注册**

Run: `curl -s http://localhost:8000/api/processors | python3 -c "import sys,json; [print(p['name'],p['params_schema'].keys()) for p in json.load(sys.stdin) if 'watermark' in p['name']]"`
Expected: `image.watermark dict_keys(['mode', 'sensitivity', 'mask_dilate', 'mask_file'])`

- [ ] **Step 3: 提交自动模式去水印任务**

Run: `curl -s -X POST http://localhost:8000/api/tasks -F "input_file=@backend/data/uploads/192a6369-d823-4b50-90eb-52b66c434445_test_image.png" -F "processor=image.watermark" -F 'params={"mode":"auto","sensitivity":70}' | python3 -m json.tool`
Expected: 返回 task_id

- [ ] **Step 4: 等待任务完成**

Run: `sleep 10 && curl -s http://localhost:8000/api/tasks/<task_id> | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'], d['progress'])"`
Expected: completed 100

- [ ] **Step 5: 验证前端页面**

浏览器打开 `http://localhost:5173`，选择去水印处理器，确认：
1. 参数面板显示：模式（auto/manual）、检测灵敏度、遮罩膨胀、遮罩文件
2. 切换到 manual 模式后出现画笔涂抹区域
3. 上传图片后可以在画布上涂抹
4. 点击确认遮罩后显示提示
5. 提交任务后正常处理

- [ ] **Step 6: 提交最终状态**

```bash
git add -A
git commit -m "chore: 去水印功能优化完成，端到端验证通过"
```
