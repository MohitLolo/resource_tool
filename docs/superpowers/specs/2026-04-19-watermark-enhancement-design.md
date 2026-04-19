# 去水印功能优化设计

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**目标：** 用 LaMa 深度学习模型替换 OpenCV inpaint，提升水印修复质量；前端增加画笔涂抹交互。

**架构：** 检测层用 FFT 频域分析 + 自适应阈值定位水印区域，修复层用 LaMa onnx 模型填充遮罩区域。前端增加 canvas 画笔涂抹生成手动遮罩。

**技术栈：** LaMa (simple-lama-inpainting)、onnxruntime、OpenCV (FFT)、Canvas API

---

## 当前问题

- `_auto_detect_mask` 用固定亮度阈值，无法检测半透明水印（如"豆包AI生成"）
- `cv2.inpaint` 是像素插值修复，大面积遮罩修复后明显模糊
- 不支持全屏平铺水印检测

## 目标水印类型

| 类型 | 示例 | 检测策略 |
|------|------|----------|
| AI 生成标记 | "豆包AI生成"、"Midjourney" | 自适应阈值 + 文字轮廓筛选 |
| 平台 Logo 水印 | 右下角/居中半透明 logo | 边角区域自适应阈值 + 边缘检测 |
| 全屏平铺水印 | 斜体文字重复覆盖 | FFT 频域分析检测规律峰值 |
| 边角文字水印 | 角落半透明文字 | 边角区域检测 |

## 方案：LaMa 模型替换

### 检测层

三种策略按优先级串联执行：

**1. FFT 频域分析（平铺水印）**
- 对灰度图做傅里叶变换，检测频域中的规律峰值
- 峰值超过阈值认为存在平铺水印
- 反向定位水印空间位置，生成遮罩

**2. 边角区域检测（Logo + 文字水印）**
- 只扫描图片四角各 15% 面积区域
- 用 `cv2.adaptiveThreshold` 替代固定阈值，对半透明内容更敏感
- 结合 Canny 边缘检测确认水印轮廓

**3. 文字轮廓筛选（AI 生成标记）**
- 基于 contour 面积和长宽比筛选文字区域
- `sensitivity` 参数控制筛选严格程度

**检测流程：**
1. 先跑 FFT 检测平铺水印，检测到则直接使用
2. 未检测到则跑边角检测 + 文字检测，结果合并为最终遮罩
3. 都未检测到则返回提示"未检测到水印，请使用手动涂抹"

**手动模式：** 前端画笔涂抹的遮罩直接作为最终遮罩，跳过自动检测。

### 修复层

**模型：** `simple-lama-inpainting` 库，封装 LaMa onnx 推理。

**调用方式：**
```python
from simple_lama_inpainting import SimpleLama

simple_lama = SimpleLama()
result = simple_lama(image, mask)  # PIL Image + 黑白遮罩
```

**集成模式（跟 cutout.py 一致）：**
- 类级变量 `_session` 缓存 onnx 会话，跨任务复用
- 首次调用时下载权重（~40MB，缓存到 `~/.cache/`）
- 强制 `CPUExecutionProvider`
- `_warmup()` 用 1x1 图片触发模型初始化

**降级策略：** LaMa 加载失败时 fallback 到 OpenCV inpaint，并提示用户效果可能降低。

### 参数变更

| 参数 | 变化 | 说明 |
|------|------|------|
| `algorithm` (telea/ns) | 删除 | LaMa 替代，不再需要 |
| `sensitivity` (1-100) | 保留 | 控制自动检测灵敏度 |
| `brush_size` (1-20) | 改名为 `mask_dilate` | 控制遮罩膨胀像素数 |
| `mode` | 新增 | `auto`（自动检测）/ `manual`（手动涂抹） |
| `mask_file` | 保留 | 接收前端画笔涂抹生成的遮罩 |

### 前端画笔涂抹交互

**交互流程：**
1. 用户上传图片后，预览区显示原图
2. 选择 `mode=manual` 时，预览图上方出现画笔工具栏
3. Canvas 叠加在图片上，用户涂抹标记水印区域（白色笔迹）
4. 完成后点击"确认遮罩"，canvas 导出为黑白 PNG 随任务提交

**工具栏控件：**
- 画笔大小滑块（5-50px）
- 画笔/橡皮擦切换
- 清除全部
- 确认遮罩 / 取消

**实现方式：**
- 用原生 Canvas API，不引入第三方绘图库
- 遮罩图与原图同尺寸，涂抹区域为白色、其余透明
- 遮罩作为 `extra_files` 传给后端，key 为 `mask_file`

**自动模式下：** 画笔工具栏隐藏，预览区正常显示原图和处理结果对比。

### 文件变更

| 文件 | 变更 |
|------|------|
| `backend/app/processors/image/watermark.py` | 重写检测层，集成 LaMa 修复 |
| `backend/requirements.txt` | 新增 `simple-lama-inpainting` |
| `backend/tests/test_watermark_processor.py` | 更新测试覆盖新逻辑 |
| `frontend/src/components/MaskCanvas.vue` | 新增，canvas 画笔涂抹组件 |
| `frontend/src/views/ImageTool.vue` | 集成 MaskCanvas 组件 |
