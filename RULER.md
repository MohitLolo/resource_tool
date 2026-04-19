# GameAsset Toolkit 编码规范

本文件为项目统一编码标准，适用于 Codex（AI 编码）和人工开发。

---

## 1. 命名规范

| 对象 | 风格 | 示例 |
|------|------|------|
| 变量 / 函数 | snake_case | `output_dir`, `process_task()` |
| 类 | PascalCase | `WatermarkProcessor`, `RedisTaskStore` |
| 常量 | UPPER_SNAKE_CASE | `_POWER2_SIZES`, `_FORMAT_ALLOWED` |
| 文件名 | snake_case.py | `extract_frames.py`, `test_crop_processor.py` |
| 私有方法 | `_` 前缀 | `_auto_detect_mask()`, `_flatten_alpha()` |
| 处理器标识 | `{category}.{action}` | `image.crop`, `video.extract_frames` |
| 测试文件 | `test_{module}.py` | `test_watermark_processor.py` |
| 测试函数 | `test_{功能}_{场景}_{预期}` | `test_process_raises_for_invalid_params` |

---

## 2. 代码格式

- 行宽上限 120 字符
- 4 空格缩进，不使用 Tab
- 引号不强制单双，文件内保持一致
- import 顺序：标准库 → 第三方 → 本项目（`app.*`），各组之间一个空行
- 所有函数参数和返回值加类型注解
- 文件头部使用 `from __future__ import annotations`

```python
# 正确
from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.core.base import BaseProcessor
```

---

## 3. 语言规范（中英文）

| 场景 | 语言 | 示例 |
|------|------|------|
| 变量名 / 函数名 / 类名 | 英文 | `task_store`, `CropProcessor` |
| 代码注释 | 中文 | `# 阈值过高时自动检测会漏掉浅色水印` |
| Docstring | 中文 | `"""校验参数合法性"""` |
| 处理器 label | 中文 | `"裁剪/缩放"`, `"视频截帧"` |
| params_schema label | 中文 | `"像素块大小"`, `"输出格式"` |
| 进度消息（progress_callback） | 中文 | `"读取图片"`, `"正在处理"`, `"完成"` |
| 错误消息（raise） | 中文 | `"输入视频不存在: {path}"` |
| Git commit message | 中文 | `"feat: 实现像素风转换处理器"` |

---

## 4. 注释规范

### 4.1 必须有注释的情况

- 类：中文 docstring，说明用途
- 公共方法：中文 docstring，说明参数和返回值
- 非显而易见的逻辑：行内注释解释"为什么"

### 4.2 不需要注释的情况

- 代码本身能自解释的"是什么"
- 显而易见的参数赋值

### 4.3 正反例

```python
# 错误 — 没有注释，不知道为什么用 240
_, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)

# 正确 — 解释阈值选择的原因
# 阈值 240 可匹配大多数浅色水印，过高会漏掉，过低会误伤正常区域
_, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
```

```python
# 错误 — 注释重复了代码
# 将图片调整为 256x256
image = image.resize((256, 256))

# 正确 — 不需要注释，代码已自解释
image = image.resize((256, 256), Image.Resampling.LANCZOS)
```

```python
# 错误 — 英文注释
# Retry with JIT disabled when numba cache is broken
os.environ["NUMBA_DISABLE_JIT"] = "1"

# 正确 — 中文注释
# numba 缓存损坏时禁用 JIT 重试
os.environ["NUMBA_DISABLE_JIT"] = "1"
```

### 4.4 TODO 格式

```python
# TODO: 支持非正方形的 power2 模式（如 256x128）
```

---

## 5. 测试规范

- **单元测试**：mock 所有外部依赖（rembg、ffmpeg、cv2.inpaint、Pillow 操作）
- **集成测试**：标记 `@pytest.mark.integration`，加环境前置检查
- 环境不可用时使用 `pytest.skip`，不让测试失败
- 使用 `tmp_path` fixture，不污染文件系统
- 测试文件与实现文件一一对应

```python
# 集成测试示例
@pytest.mark.integration
def test_process_with_real_ffmpeg(tmp_path) -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg 未安装")
```

---

## 6. Git 提交规范

### 提交时机

- 每完成一个 Task 提交一次
- 不要积攒多个 Task 一次提交

### 提交格式

```
type: 中文描述
```

### type 清单

| type | 用途 | 示例 |
|------|------|------|
| feat | 新功能 | `feat: 实现视频截帧处理器` |
| fix | 修复问题 | `fix: 修复 RGBA 图片转 JPG 丢失透明通道` |
| refactor | 重构 | `refactor: 将 _as_int 提取到 BaseProcessor 基类` |
| docs | 文档 | `docs: 更新进度文档，标记 Task 14 完成` |
| test | 测试 | `test: 新增裁剪处理器单元测试和集成测试` |
| chore | 杂项 | `chore: 更新 requirements.txt 添加依赖` |

### 描述要求

- 简洁明确，说明改了什么
- 不要写"更新代码"、"修改文件"这种无意义描述

```
# 错误
fix: 修复bug
update: 代码更新

# 正确
fix: 修复 power2 模式非法尺寸未拒绝的问题
feat: 实现去水印处理器，支持手动遮罩和自动检测
```
