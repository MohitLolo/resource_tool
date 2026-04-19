# 像素画/风格转换功能设计

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**目标：** 新增 `image.stylize` 处理器，将任意图片转换为游戏美术风格（水墨、像素、剪纸、素描、油画），全部 CPU 可运行，零 AI 依赖。

**架构：** 独立处理器 `stylize.py` 做参数校验和调度，每种风格作为 `styles/` 下的独立纯函数模块。调色板映射作为公共组件。

**技术栈：** PIL (Pillow)、OpenCV、NumPy

---

## 背景

独立游戏开发者（特别是程序员出身）最大的痛点是把现有图片变成游戏可用的美术素材。本处理器提供五种游戏常用风格转换，全部基于传统图像处理，CPU 即可运行，为后续 sprite sheet 切帧、瓦片集拼接、Godot 导出等流程提供素材基础。

## 处理器定义

- **name:** `image.stylize`
- **label:** 风格转换
- **category:** image

### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `style` | select | `ink_wash` | 风格选择：`ink_wash`（水墨）、`pixel`（像素）、`paper_cut`（剪纸）、`sketch`（素描）、`oil_painting`（油画） |
| `intensity` | number | 50 | 风格强度 1-100 |
| `preserve_color` | checkbox | false | 是否保留原色 |
| `edge_width` | number | 2 | 线条粗细 1-5 |
| `palette` | select | `original` | 调色板：`original`（原色）、`ink`（水墨黑白灰）、`cinnabar`（朱砂红黑金）、`porcelain`（青花蓝白） |

## 五种风格实现

### 1. 水墨风（ink_wash）

灰度化 → 直方图均衡化（增强墨色层次）→ 高斯模糊模拟晕染 → Sobel 边缘提取做线条 → 叠加宣纸纹理（用噪点模拟）。

- `intensity` 控制模糊强度和线条粗细
- `preserve_color=false` 时纯黑白，`true` 时保留淡彩

### 2. 像素风（pixel）

复用现有 pixelate 逻辑（缩小+最近邻放大）+ 调色板量化 + 边缘抗锯齿。

- `intensity` 映射到像素块大小（强度越高块越大）
- 先做像素化再做一次边缘平滑

### 3. 剪纸风（paper_cut）

色彩量化（减少到 4-8 个色阶）→ 查找边缘做硬边轮廓 → 色块填充 → 添加阴影效果（轻微偏移叠加）。

- `intensity` 控制色阶数量
- `edge_width` 控制轮廓粗细

### 4. 素描/线稿（sketch）

灰度化 → 反色 → 高斯模糊 → 与原图做颜色减淡混合（dodge blend）→ 得到铅笔素描效果。

- `intensity` 控制模糊半径
- `edge_width` 控制线条深浅

### 5. 油画风（oil_painting）

高斯模糊做底 → 色彩饱和度增强 → 叠加笔触纹理（用方向性噪点模拟）→ 边缘柔化。

- `intensity` 控制模糊和笔触强度

## 调色板映射

每种风格处理完后，如果选了非 `original` 的调色板，做颜色映射替换。

| 调色板 | 颜色范围 | 适合风格 |
|--------|----------|----------|
| `original` | 保留原色 | 全部 |
| `ink` | 黑/灰/白梯度 | 水墨、素描 |
| `cinnabar` | 朱红/黑/金 | 剪纸、水墨（中国元素） |
| `porcelain` | 青蓝/白/淡灰 | 水墨、油画（青花瓷感） |

## 文件结构

```
backend/app/processors/image/
├── pixelate.py              # 保留原样
├── stylize.py               # 新增：风格化处理器主类
└── styles/                  # 新增：风格模块目录
    ├── __init__.py
    ├── ink_wash.py          # 水墨风
    ├── pixel.py             # 像素风
    ├── paper_cut.py         # 剪纸风
    ├── sketch.py            # 素描/线稿
    ├── oil_painting.py      # 油画风
    └── palette.py           # 调色板映射
```

### 职责划分

- `stylize.py`：参数校验、进度回调、调度风格函数、保存输出
- `styles/xxx.py`：每个文件暴露 `apply(image: PIL.Image, params: dict) -> PIL.Image` 纯函数
- `styles/palette.py`：暴露 `apply_palette(image, palette_name) -> PIL.Image`

### 前端

处理器的 `params_schema` 已定义好参数类型和选项，前端 ParamForm 组件自动渲染表单，不需要额外前端改动。

## 测试策略

- 每种风格独立测试：输入固定图片 → 验证输出尺寸/模式/非空
- 调色板映射测试：验证颜色数量符合预期
- 集成测试：通过 API 提交完整任务，验证端到端流程
- 参数校验测试：验证非法参数被拒绝

## 后续扩展

风格转换是游戏素材工作流的起点。后续可串联：
- sprite sheet 切帧处理器（角色动画）
- 瓦片集拼接处理器（地图素材）
- Godot `.tres` 资源导出
- 管线串联（风格化 → 切帧 → 导出 一键完成）
