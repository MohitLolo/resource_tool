# GameAsset Toolkit 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建面向独立游戏开发的素材处理 Web 工具 MVP，覆盖图片去水印、抠图、裁剪/缩放、像素风转换、视频截帧、格式转换六大核心功能。

**Architecture:** FastAPI 后端 + Celery 异步任务队列 + Redis 消息中间件 + Vue 3 前端。处理器插件系统通过 BaseProcessor + ProcessorRegistry 实现自动注册和动态参数表单。

**Tech Stack:** Python 3.11, FastAPI, Celery, Redis, Pillow, OpenCV, rembg, ffmpeg-python, pydub, Vue 3, Element Plus, Vite

**设计文档:** `docs/superpowers/specs/2026-04-18-game-asset-toolkit-design.md`

---

## 实现计划总览

| 批次 | 内容 | 产出 |
|------|------|------|
| 第 1 批 | 项目骨架 + 核心框架 | 后端基础运行 + 处理器插件系统 |
| 第 2 批 | P0 图片处理器（4个） | 去水印、抠图、裁剪、像素风 |
| 第 3 批 | P0 视频/格式处理器（2个） | 视频截帧、格式转换 |
| 第 4 批 | 前端界面 + 对接 | Vue 界面能跑通完整流程 |
| 第 5 批 | Docker 部署 + 收尾 | 一键启动可用 |

---

## 第 1 批：项目骨架 + 核心框架

### Task 1: 初始化项目结构

- [ ] 创建 `backend/app/` 目录结构：`api/`, `core/`, `processors/image/`, `processors/video/`, `processors/audio/`, `tasks/`, `models/`，各目录含 `__init__.py`
- [ ] 创建 `backend/requirements.txt`，包含：fastapi, uvicorn[standard], celery, redis[hiredis], pillow, opencv-python-headless, rembg, ffmpeg-python, pydub, python-multipart, aiofiles, pydantic-settings
- [ ] 创建 `data/uploads/` 和 `data/outputs/` 目录
- [ ] 创建 `.gitignore`（data/, __pycache__/, .env, node_modules/, dist/, .superpowers/）
- [ ] 创建 `backend/tests/conftest.py`：定义 `@pytest.mark.integration` 标记，注册 pytest markers

### Task 2: 配置管理 (`backend/app/config.py`)

- [ ] 使用 pydantic `BaseSettings` 实现配置管理
- [ ] 配置项：`HOST`, `PORT`, `REDIS_URL`, `DATA_DIR`, `UPLOAD_DIR`, `OUTPUT_DIR`, `MAX_FILE_SIZE`（500MB）, `CORS_ORIGINS`
- [ ] `ensure_dirs()` 方法启动时自动创建目录
- [ ] 支持 `.env` 文件覆盖
- [ ] 提交

### Task 3: 处理器基类 (`backend/app/core/base.py`)

- [ ] 定义 `BaseProcessor` 抽象基类，包含属性：`name`, `label`, `category`, `params_schema`
- [ ] 抽象方法：`validate(params) -> bool`、`process(input_file, output_dir, params, progress_callback) -> list[str]`
- [ ] 编写单元测试：mock process 抽象方法，验证子类属性、validate、process 调用流程
- [ ] 提交

### Task 4: 处理器注册表 (`backend/app/core/registry.py`)

- [ ] 实现 `ProcessorRegistry`，方法：`register()`, `get()`, `list_by_category()`, `list_all()`
- [ ] `auto_discover()`：使用 `importlib` + `pkgutil` 自动扫描 `processors/` 目录下所有模块，将继承 `BaseProcessor` 的类自动注册
- [ ] `list_all()` 返回包含 `name`, `label`, `category`, `params_schema` 的字典列表，供前端动态渲染
- [ ] 编写单元测试：注册/获取/按分类查询/自动发现（mock importlib 扫描）
- [ ] 提交

### Task 5: 任务模型 (`backend/app/models/task.py`)

- [ ] `TaskStatus` 枚举：pending, processing, completed, failed, canceled
- [ ] `Task` dataclass：id(uuid), status, processor_name, params, input_file, output_files, extra_files(dict), progress, message, created_at
- [ ] `to_dict()` / `from_dict()` 方法
- [ ] `RedisTaskStore`（Redis Hash 存储，key 前缀 `task:`）：save, get, delete, list_recent
  - 使用 `redis.hset(key, mapping=task.to_dict())` 持久化
  - 使用 `redis.hgetall(key)` 读取
  - `list_recent` 使用 Redis Sorted Set（按 created_at 排序）
- [ ] 全局单例 `task_store`（注入 Redis 连接）
- [ ] 编写单元测试（mock Redis 客户端）
- [ ] 提交

### Task 6: Celery Worker (`backend/app/tasks/worker.py`)

- [ ] 创建 Celery app 实例，连接 Redis 作为 broker 和 backend
- [ ] Worker 内初始化 `RedisTaskStore`（共用同一 Redis 实例，不同 key 前缀）
- [ ] `publish_progress(task_id, progress, message, status)`：通过 Redis Pub/Sub 发布进度
- [ ] `process_task` Celery 任务：查找处理器 → validate → process（传入 progress_callback）→ 通过 RedisTaskStore 更新状态 → 发布完成/失败消息
- [ ] 提交

### Task 7: REST API — 处理器查询 (`backend/app/api/processors.py`)

- [ ] `GET /api/processors` — 返回所有处理器列表
- [ ] `GET /api/processors/{category}` — 返回指定分类的处理器
- [ ] 提交

### Task 8: REST API — 任务操作 (`backend/app/api/tasks.py`)

- [ ] `POST /api/tasks` — 多文件上传（multipart），字段：
  - `input_file`：主文件（必填）
  - `extra_files`：附加文件列表（可选，如 mask_file）
  - `processor`：处理器名（form 字段）
  - `params`：JSON 字符串（form 字段），params 中通过 `mask_file_key` 等引用附加文件
  - 后端统一保存所有文件，处理器通过文件映射读取
- [ ] `GET /api/tasks/{id}` — 从 RedisTaskStore 返回任务状态/进度
- [ ] `GET /api/tasks/{id}/download` — 单文件直接下载，多文件打 ZIP 返回
- [ ] `DELETE /api/tasks/{id}` — 取消任务：`revoke(task_id, terminate=True)` → 状态设为 `canceled` → 清理上传文件和输出文件
- [ ] 提交

### Task 9: WebSocket 进度推送 (`backend/app/api/ws.py`)

- [ ] `WS /ws/tasks/{task_id}` — 订阅 Redis Pub/Sub 频道 `task:{id}`
- [ ] 实时转发进度消息到浏览器：`{"progress": N, "message": "...", "status": "..."}`
- [ ] 收到 completed/failed/canceled 后自动断开
- [ ] 提交

### Task 10: FastAPI 入口 (`backend/app/main.py`)

- [ ] 创建 FastAPI app，挂载 processors、tasks、ws 路由
- [ ] 配置 CORS 中间件（允许前端 localhost:5173）
- [ ] startup 事件：`ensure_dirs()` + `ProcessorRegistry.auto_discover()`
- [ ] `GET /api/health` 健康检查
- [ ] 启动验证：`/api/health` 返回 ok，`/api/processors` 返回空列表
- [ ] 提交

### Task 11: 验证框架可运行

- [ ] 运行全部测试：`pytest tests/ -v`
- [ ] 启动 Redis + FastAPI + Celery Worker 三端
- [ ] 验证：`GET /api/health`、`GET /api/processors`、`POST /api/tasks` 上传、`GET /api/tasks/{id}` 查询、WebSocket 连接
- [ ] 提交

---

## 第 2 批：P0 图片处理器

> 依赖：第 1 批全部完成，BaseProcessor 和 ProcessorRegistry 可用

### Task 12: 去水印处理器 (`backend/app/processors/image/watermark.py`)

- [ ] 继承 `BaseProcessor`，name=`image.watermark`，category=`image`
- [ ] params_schema：algorithm（Telea/Navier-Stokes）、mask_file（可选遮罩图）、brush_size（自动检测灵敏度）
- [ ] validate：校验 algorithm 合法性
- [ ] process：OpenCV 读取图片 → 如有 mask_file 直接使用，否则 `_auto_detect_mask()` 自动检测高亮区域 → `cv2.inpaint()` 修复 → 保存输出
- [ ] `_auto_detect_mask()`：灰度化 → 阈值 240 二值化 → 膨胀
- [ ] 编写单元测试：mock cv2.inpaint，覆盖属性校验、validate、手动遮罩处理、自动检测处理
- [ ] 提交

### Task 13: 抠图处理器 (`backend/app/processors/image/cutout.py`)

- [ ] 继承 `BaseProcessor`，name=`image.cutout`，category=`image`
- [ ] params_schema：alpha_matting（checkbox，更精细边缘）
- [ ] validate：始终通过
- [ ] process：读取文件二进制 → `rembg.remove()` 去除背景 → 保存为 PNG（RGBA 透明背景）
- [ ] 编写单元测试：mock rembg.remove，验证输出为 RGBA 模式 PNG
- [ ] 集成测试（标记 `@pytest.mark.integration`）：真实 rembg 调用，需环境前置检查
- [ ] 提交

### Task 14: 裁剪/缩放处理器 (`backend/app/processors/image/crop.py`)

- [ ] 继承 `BaseProcessor`，name=`image.crop`，category=`image`
- [ ] params_schema：mode（custom/power2/crop）、width/height、power2_size（32/64/128/256/512/1024）、x/y/crop_width/crop_height
- [ ] validate：根据 mode 检查对应参数完整性
- [ ] process：三种模式 — custom 缩放到指定尺寸、power2 缩放到 2 的幂次、crop 按坐标裁剪区域
- [ ] 使用 Pillow `Image.resize()` / `Image.crop()`，LANCZOS 插值
- [ ] 编写单元测试：mock Pillow 操作，覆盖三种模式的尺寸验证
- [ ] 提交

### Task 15: 像素风转换处理器 (`backend/app/processors/image/pixelate.py`)

- [ ] 继承 `BaseProcessor`，name=`image.pixelate`，category=`image`
- [ ] params_schema：pixel_size（2-32）、palette_colors（0=不限/8/16/32/64/128/256）、output_size（original/64x64/128x128/256x256）
- [ ] validate：pixel_size >= 2
- [ ] process：缩小到 `(w/pixel_size, h/pixel_size)` → NEAREST 放大回原尺寸 → 可选 `quantize()` 限制调色板 → 可选缩放到目标尺寸
- [ ] 编写单元测试：mock Pillow 操作，验证像素化效果、调色板限制、进度回调
- [ ] 提交

### Task 16: 验证图片处理器自动注册

- [ ] 启动 FastAPI，`GET /api/processors` 应返回 4 个 image 类处理器
- [ ] `GET /api/processors/image` 返回同样 4 个
- [ ] 运行全部测试通过
- [ ] 提交

---

## 第 3 批：P0 视频/格式处理器

> 依赖：第 1 批完成。与第 2 批无依赖，可并行。

### Task 17: 视频截帧处理器 (`backend/app/processors/video/extract_frames.py`)

- [ ] 继承 `BaseProcessor`，name=`video.extract_frames`，category=`video`
- [ ] params_schema：mode（all/range）、fps（1-60）、start/end（秒，range 模式用）、format（png/jpg）
- [ ] validate：mode 合法，fps 范围，range 模式 start < end
- [ ] process：调用 `ffmpeg` 命令行（subprocess），`-vf fps=N` 按帧率提取，range 模式加 `-ss`/`-to`，输出帧序列图片
- [ ] 编写单元测试：mock subprocess.run，验证 ffmpeg 命令参数拼接
- [ ] 集成测试（标记 `@pytest.mark.integration`）：需 ffmpeg 可用，用 `color=c=red:s=160x120:d=1` 生成测试视频验证帧数量
- [ ] 提交

### Task 18: 图片格式转换处理器 (`backend/app/processors/image/convert.py`)

- [ ] 继承 `BaseProcessor`，name=`image.convert`，category=`image`
- [ ] params_schema：format（png/jpg/webp）、quality（1-100，JPG/WebP 用）
- [ ] validate：format 在允许列表内
- [ ] process：Pillow 打开图片 → RGBA 转 JPG 时白底合成 → 按 format + quality 保存
- [ ] 编写单元测试：mock Pillow 保存操作，PNG→JPG、PNG→WebP、PNG 保持 RGBA
- [ ] 提交

### Task 19: 验证全部 P0 处理器集成

- [ ] `GET /api/processors` 应返回 6 个处理器（4 image + 1 video + 1 image.convert）
- [ ] 运行全部测试通过
- [ ] 提交

---

## 第 4 批：前端界面 + 对接

> 依赖：第 1-3 批后端完成。使用 Vue 3 + Element Plus + Vite。

### Task 20: 初始化前端项目

- [ ] `cd /home/huangnianzhi/tools && npm create vite@latest frontend -- --template vue`
- [ ] 安装依赖：`cd frontend && npm install element-plus @element-plus/icons-vue vue-router@4 axios`
- [ ] 配置 `vite.config.js`：API 代理 `/api` → `http://localhost:8000`，WebSocket 代理 `/ws` → `ws://localhost:8000`
- [ ] 配置暗色主题：Element Plus dark 模式 + 全局 CSS 变量定义游戏工具风格配色
- [ ] 入口 `main.js`：注册 Element Plus、Router、全局样式
- [ ] 提交

### Task 21: 路由 + 布局框架

- [ ] `router/index.js`：三个路由 `/image`、`/video`、`/audio`，默认重定向 `/image`
- [ ] `App.vue`：顶部导航栏（Logo + 三个页签），`<router-view>` 主体区域
- [ ] 暗色调导航栏，激活态高亮
- [ ] 提交

### Task 22: API 封装层

- [ ] `api/index.js`：基于 axios 封装后端 API 调用
  - `getProcessors(category?)` — GET /api/processors
  - `createTask(file, processor, params)` — POST /api/tasks（FormData）
  - `getTask(taskId)` — GET /api/tasks/{id}
  - `downloadResult(taskId)` — GET /api/tasks/{id}/download
  - `deleteTask(taskId)` — DELETE /api/tasks/{id}
- [ ] `useWebSocket(taskId)` composable：封装 WebSocket 连接，返回 `{ progress, message, status, connect, disconnect }`
- [ ] 提交

### Task 23: 通用组件

- [ ] `FileUpload.vue`：Element Plus `el-upload`，支持拖拽，显示文件名/大小，限制 500MB
- [ ] `ParamForm.vue`：核心组件。接收 `paramsSchema` prop，根据 type 动态渲染：
  - `select` → `el-select`
  - `slider` → `el-slider`
  - `number` → `el-input-number`
  - `checkbox` → `el-switch`
  - `file` → `el-upload`（单个文件）
  - 输出 v-model 绑定的 params 对象
- [ ] `ProgressPanel.vue`：进度条 `el-progress` + 日志输出区域（可滚动）
- [ ] `PreviewPane.vue`：根据文件类型显示预览（图片用 `<img>`、视频用 `<video>`、音频用 `<audio>`），未上传时显示占位
- [ ] 提交

### Task 24: 图片处理页 `ImageTool.vue`

- [ ] 左右分栏布局
- [ ] 左侧：FileUpload + 处理类型选择（从 API 获取 `category=image` 的处理器列表）+ ParamForm + 开始处理按钮
- [ ] 右侧：PreviewPane（原图 + 结果对比）+ ProgressPanel + 下载按钮
- [ ] 交互流程：上传文件 → 选处理器 → 填参数 → 提交任务 → WebSocket 监听进度 → 完成 → 预览 + 下载
- [ ] 提交

### Task 25: 视频处理页 `VideoTool.vue`

- [ ] 与 ImageTool 结构一致，`category=video`
- [ ] 视频预览区使用 `<video>` 标签 + 基础播放控制
- [ ] 截帧结果展示为缩略图网格
- [ ] 提交

### Task 26: 音频处理页 `AudioTool.vue`

- [ ] 与 ImageTool 结构一致，`category=audio`（MVP 阶段音频处理器在 P1，此页面先搭建框架）
- [ ] 音频预览使用 `<audio>` 标签
- [ ] 提交

### Task 27: 端到端联调

- [ ] `pytest tests/ -v` 运行全部单元测试（默认跳过 integration 标记）
- [ ] `pytest tests/ -v -m integration` 运行集成测试（需 Redis + ffmpeg + rembg 可用）
- [ ] 启动全部服务（Redis + FastAPI + Celery + Vite dev）
- [ ] 测试完整流程：上传图片 → 选择去水印 → 提交 → 看进度 → 下载结果
- [ ] 测试抠图、裁剪、像素风、格式转换、视频截帧
- [ ] 修复联调问题
- [ ] 提交

---

## 第 5 批：Docker 部署 + 收尾

> 依赖：第 4 批前端对接完成。

### Task 28: 后端 Dockerfile

- [ ] `backend/Dockerfile`：基于 `python:3.11-slim`，安装系统依赖（ffmpeg、libgl），pip install，暴露 8000 端口
- [ ] `.dockerignore`：排除 `__pycache__`、`data/`、`tests/`
- [ ] 本地构建测试：`docker build -t gameasset-api ./backend`
- [ ] 提交

### Task 29: 前端 Dockerfile

- [ ] `frontend/Dockerfile`：多阶段构建，`node:20-alpine` 构建 → `nginx:alpine` 运行
- [ ] `nginx.conf`：配置 SPA 路由 fallback + API 代理
- [ ] `.dockerignore`
- [ ] 本地构建测试：`docker build -t gameasset-web ./frontend`
- [ ] 提交

### Task 30: Docker Compose 一键部署

- [ ] `docker-compose.yml`：4 个服务（redis、api、worker、frontend）
- [ ] volume 挂载 `data/` 目录持久化
- [ ] 环境变量配置（REDIS_URL、CORS_ORIGINS 等）
- [ ] `docker compose up -d` 一键启动验证
- [ ] 提交

### Task 31: README + 收尾

- [ ] `README.md`：项目介绍、快速启动（本地开发 + Docker 两种方式）、技术栈说明、目录结构
- [ ] 确认 `.gitignore` 完整
- [ ] 最终全量测试
- [ ] 提交

---

## MVP 完成标准

- [ ] 后端 6 个 P0 处理器全部可用
- [ ] 前端可上传文件、选择处理器、设置参数、提交任务
- [ ] WebSocket 实时显示处理进度
- [ ] 处理完成后可预览和下载结果
- [ ] `docker compose up` 一键启动
- [ ] 全部测试通过
