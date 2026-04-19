# GameAsset Toolkit 开发进度记录

日期：2026-04-18

## 已完成

### 计划文档修订
- WebSocket 自动断开条件已更新为：`completed/failed/canceled`

### 第 1 批（已实现部分）
- Task 1（初始化项目结构）：已完成（未提交）
  - 已创建 `backend/app/` 目录结构及各级 `__init__.py`
  - 已创建 `data/uploads/`、`data/outputs/`
  - 已创建 `backend/requirements.txt`
  - 已创建项目级 `.gitignore`
  - 已创建 `backend/tests/conftest.py` 并注册 `integration` marker

- Task 2（配置管理）：已完成（未提交）
  - 已实现 `backend/app/config.py`
  - 包含配置项：`HOST`, `PORT`, `REDIS_URL`, `DATA_DIR`, `UPLOAD_DIR`, `OUTPUT_DIR`, `MAX_FILE_SIZE`, `CORS_ORIGINS`
  - 支持 `.env` 覆盖
  - 实现 `ensure_dirs()`

- Task 3（处理器基类）：已完成（未提交）
  - 已实现 `backend/app/core/base.py`
  - 定义 `BaseProcessor` 抽象基类及 `validate/process` 抽象方法

- Task 4（处理器注册表）：已完成（未提交）
  - 已实现 `backend/app/core/registry.py`
  - 支持 `register/get/list_by_category/list_all/auto_discover/clear`
  - `auto_discover` 使用 `importlib + pkgutil + inspect` 自动发现处理器类

- Task 5（任务模型 + RedisTaskStore）：已完成（未提交）
  - 已实现 `backend/app/models/task.py`
  - 已定义 `TaskStatus`（含 `canceled`）
  - 已定义 `Task` dataclass（含 `to_dict/from_dict`）
  - 已实现 `RedisTaskStore`：`save/get/delete/list_recent`
  - 已提供全局 `task_store`

- Task 6（Celery Worker）：已完成（未提交）
  - 已实现 `backend/app/tasks/worker.py`
  - 已实现 `publish_progress`
  - 已实现 `run_process_task`
  - 已实现 Celery 任务入口 `process_task`

- Task 7（处理器查询 API）：已完成（未提交）
  - 已实现 `backend/app/api/processors.py`
  - 提供 `GET /api/processors` 与 `GET /api/processors/{category}`

- Task 8（任务 API）：已完成（未提交）
  - 已实现 `backend/app/api/tasks.py`
  - 支持多文件提交：`input_file + extra_files + processor + params`
  - 支持任务查询、下载、取消（含 `canceled` 状态与文件清理）

- Task 9（WebSocket 进度推送）：已完成（未提交）
  - 已实现 `backend/app/api/ws.py`
  - 终态自动断开：`completed/failed/canceled`

- Task 10（FastAPI 入口）：已完成（未提交）
  - 已实现 `backend/app/main.py`
  - 挂载 processors/tasks/ws 路由
  - 启动执行 `ensure_dirs()` 和 `ProcessorRegistry.auto_discover()`
  - 提供 `GET /api/health`

- Task 11（框架运行验证）：已完成（未提交）
  - 已验证：
    - `GET /api/health` 返回 `{"status":"ok"}`
    - `GET /api/processors` 返回 `[]`（当前尚未实现处理器，符合预期）
    - Celery Worker 成功连接 Redis（`Connected to redis://localhost:6379/0`）
    - `POST /api/tasks` 可成功返回 `task_id`
    - `GET /api/tasks/{id}` 可返回任务状态（示例中因处理器不存在，状态为 `failed`，符合预期）
    - `WS /ws/tasks/{id}` 通道可用，收到进度消息并在终态（`completed/failed/canceled`）断开
  - 备注：
    - 使用不存在处理器 `image.nonexistent` 做最小链路验证，失败状态是预期行为
    - 对极短任务，若 WebSocket 在任务终态后才连接，可能收不到历史消息（当前实现为实时订阅模型）

### 第 2 批（进行中）
- Task 12（去水印处理器）：已完成（未提交）
  - 已实现 `backend/app/processors/image/watermark.py`
  - 支持参数：`algorithm`（`telea/ns`）、`brush_size`、可选 `mask_file`（通过 `mask_file_key`/`extra_files` 解析）
  - 已实现自动遮罩 `_auto_detect_mask()`（灰度 -> 阈值 240 -> 膨胀）
  - 已实现 `cv2.inpaint()` 去水印与进度回调
  - 已新增 `backend/tests/test_watermark_processor.py`，覆盖：
    - 处理器元数据与 `validate`
    - 手工遮罩路径
    - 自动检测路径
- Task 13（抠图处理器）：已完成（未提交）
  - 已实现 `backend/app/processors/image/cutout.py`
  - 处理器信息：`name=image.cutout`，`label=智能抠图`，`category=image`
  - 支持参数：`alpha_matting`
  - 实现逻辑：读取输入文件字节 -> `rembg.remove()` -> 统一转 RGBA PNG 输出
  - 已处理环境兼容：`rembg` 导入遇到 numba 缓存异常时自动切换 `NUMBA_DISABLE_JIT=1` 后重试
  - 已新增 `backend/tests/test_cutout_processor.py`，覆盖：
    - 属性与 `validate`
    - mock `rembg` 的单元测试（验证 RGBA PNG 输出）
    - `@pytest.mark.integration` 真实 rembg 调用测试（含模型前置检查，模型缺失时 skip）
- Task 14（裁剪/缩放处理器）：已完成（未提交）
  - 已实现 `backend/app/processors/image/crop.py`
  - 处理器信息：`name=image.crop`，`label=裁剪/缩放`，`category=image`
  - 支持模式：`custom` / `power2` / `crop`
  - 采用可扩展分发表结构：
    - `mode -> validator`（`_validator_map`）
    - `mode -> handler`（`_handler_map`）
  - 已新增 `backend/tests/test_crop_processor.py`，覆盖属性、参数校验、三模式输出尺寸、非法参数错误
- Task 15（像素风转换处理器）：已完成（未提交）
  - 已实现 `backend/app/processors/image/pixelate.py`
  - 处理器信息：`name=image.pixelate`，`label=像素风转换`，`category=image`
  - 支持参数：`pixel_size`、`palette_colors`、`output_size`
  - 实现逻辑：
    - `NEAREST` 缩小再放大实现像素化
    - 可选调色板限制（0/8/16/32/64/128/256）
    - 可选输出尺寸（`original` / `64x64` / `128x128` / `256x256`）
  - 已新增 `backend/tests/test_pixelate_processor.py`，覆盖属性、参数校验、调色板限制、输出尺寸与错误分支
- Task 16（验证图片处理器自动注册）：已完成（未提交）
  - 验证命令：`PYTHONPATH=backend conda run -n gameasset python -c \"from app.core.registry import ProcessorRegistry; ProcessorRegistry.clear(); ProcessorRegistry.auto_discover('app.processors'); items=ProcessorRegistry.list_by_category('image'); print([i['name'] for i in items])\"`
  - 验证结果：`['image.crop', 'image.cutout', 'image.pixelate', 'image.watermark']`
  - 结论：`GET /api/processors` / `GET /api/processors/image` 预期可返回 4 个 image 处理器
- Task 17（视频截帧处理器）：已完成（未提交）
  - 已实现 `backend/app/processors/video/extract_frames.py`
  - 处理器信息：`name=video.extract_frames`，`label=视频截帧`，`category=video`
  - 支持参数：`mode`（all/range）、`fps`（1-60）、`start/end`（range 模式）、`format`（png/jpg）
  - 实现逻辑：
    - `subprocess` 调用 `ffmpeg`
    - `-vf fps=N` 按帧率截帧
    - range 模式注入 `-ss/-to`
  - 补充修正：
    - 提取 `_as_int/_as_float` 到 `BaseProcessor`，删除处理器内重复实现
    - `params_schema` 的 label 统一为中文
    - 增加输入文件存在性校验与 ffmpeg `stderr` 透传错误信息
  - 已新增 `backend/tests/test_extract_frames_processor.py`，覆盖参数校验、命令拼接、真实 ffmpeg 集成测试、缺失输入与错误透传
- Task 18（图片格式转换处理器）：已完成（未提交）
  - 已实现 `backend/app/processors/image/convert.py`
  - 处理器信息：`name=image.convert`，`label=格式转换`，`category=image`
  - 支持参数：`format`（png/jpg/webp）、`quality`（1-100）
  - 实现逻辑：
    - Pillow 读取并按目标格式保存
    - RGBA 转 JPG 时白底合成，避免透明通道丢失
    - PNG/WebP 按需保留透明通道
  - 已新增 `backend/tests/test_convert_processor.py`，覆盖 PNG->JPG/WEBP/PNG 与参数错误分支
- Task 19（验证全部 P0 处理器集成）：已完成（未提交）
  - 本地 API 验证（临时启动 uvicorn + curl）：
    - `GET /api/processors` 返回 6 个处理器
    - `GET /api/processors/image` 返回 5 个 image 处理器（含 `image.convert`）
  - 结果名称：
    - 全部：`image.convert`, `image.crop`, `image.cutout`, `image.pixelate`, `image.watermark`, `video.extract_frames`
    - image 分类：`image.convert`, `image.crop`, `image.cutout`, `image.pixelate`, `image.watermark`
  - 说明：原计划中 “image 4 个” 为 Task 18 前口径；完成 Task 18 后 image 处理器总数应为 5

## 已完成测试
- `backend/tests/test_config.py`
- `backend/tests/test_base_processor.py`
- `backend/tests/test_registry.py`
- `backend/tests/test_task_model.py`
- `backend/tests/test_worker.py`
- `backend/tests/test_api_processors.py`
- `backend/tests/test_api_tasks_utils.py`
- `backend/tests/test_main.py`
- `backend/tests/test_watermark_processor.py`
- `backend/tests/test_cutout_processor.py`
- `backend/tests/test_crop_processor.py`
- `backend/tests/test_pixelate_processor.py`
- `backend/tests/test_extract_frames_processor.py`
- `backend/tests/test_convert_processor.py`

测试结果：
- `PYTHONPATH=backend pytest -q backend/tests/test_config.py backend/tests/test_base_processor.py backend/tests/test_registry.py`
  - `5 passed`
- `conda run -n gameasset pytest -q backend/tests`
  - `19 passed, 1 skipped`（含 2 条 FastAPI `on_event` 弃用告警）
- `U2NET_HOME=/tmp/.u2net NUMBA_DISABLE_JIT=1 conda run -n gameasset pytest -q backend/tests`
  - `39 passed, 1 skipped`（含 2 条 FastAPI `on_event` 弃用告警）
  - 说明：通过代理下载 `u2net.onnx` 到 `/tmp/.u2net` 后，`test_cutout_processor.py` 的 integration 用例不再 skip

联调命令结果（Task 11）：
- `curl http://127.0.0.1:8011/api/health` -> 成功
- `curl http://127.0.0.1:8011/api/processors` -> 成功
- `POST /api/tasks` -> 成功返回 `task_id`
- `GET /api/tasks/{id}` -> 成功返回任务详情（示例状态 `failed`，原因为处理器不存在）
- WebSocket 手动发布验证 -> 成功收到 2 条消息，终态自动断开

## 前端原型设计

- 原型文件：`/home/huangnianzhi/tools/prototype.html`（浏览器直接打开预览）
- 包含完整 UI 设计：
  - 暗色/亮色主题切换（右上角按钮）
  - 顶部导航栏（图片处理 / 视频处理 / 音频处理），切换时联动处理器列表和参数面板
  - 左侧面板：文件上传（拖拽）+ 处理器卡片选择 + 动态参数表单 + 开始处理按钮
  - 右侧面板：原图/结果对比预览 + 进度条（流光动画）+ 控制台日志 + 下载按钮
  - 背景粒子动效
- **第 4 批前端开发参照说明：**
  - CSS 变量体系（`:root` 暗色 + `.light` 亮色）可直接迁移到 Vue 3 全局样式
  - 布局结构对应 Vue 组件：Header → `App.vue`，左侧面板 → 各 `*Tool.vue`，处理器卡片 → `ParamForm.vue`，进度+日志 → `ProgressPanel.vue`，预览 → `PreviewPane.vue`
  - 处理器按 `data-category` 分组过滤的逻辑与后端 `GET /api/processors/{category}` 对应
  - 主题切换可封装为 `useTheme()` composable
  - 动态参数表单根据选中处理器切换，对应 `params_schema` 驱动渲染

## 下一步
- 第 4 批 Task 20：初始化前端项目
