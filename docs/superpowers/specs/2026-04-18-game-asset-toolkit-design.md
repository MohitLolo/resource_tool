# GameAsset Toolkit — 设计文档

> 面向独立游戏开发的素材处理 Web 工具

## 1. 项目背景

独立游戏开发者通过 AI 对话工具生成图片和短视频素材，需要一套工具链来处理这些原始素材，使其可直接用于游戏引擎。本项目提供一个本地启动、浏览器操作的 Web 工具，覆盖从原始素材到游戏可用素材的完整处理流程。

**目标游戏引擎**：Godot。工具的导出格式、元数据结构和命名规范优先适配 Godot 工作流。

## 2. 技术选型

| 层级 | 技术方案 | 说明 |
|------|---------|------|
| 后端框架 | Python FastAPI + Uvicorn | 高性能异步 Web 框架 |
| 任务队列 | Celery + Redis | 异步处理耗时任务，支持进度回调 |
| 图像处理 | Pillow, OpenCV | 基础图像操作、去水印（inpainting） |
| 抠图 | rembg (U2-Net) | 自动背景去除，模型约 170MB |
| 视频处理 | ffmpeg-python | 截帧、裁剪、提取音频 |
| 音频处理 | pydub + FFmpeg | 音效截取、拼接、格式转换 |
| 前端框架 | Vue 3 + Element Plus + Vite | 组件丰富，适合工具型界面 |
| 实时通信 | FastAPI WebSocket | 处理进度实时推送到浏览器 |
| 部署 | Docker Compose | FastAPI + Celery Worker + Redis 一键启动 |

## 3. 架构设计

```
浏览器 (Vue 3 + Element Plus)
    │
    │  REST API + WebSocket
    ▼
FastAPI 后端
├── API 路由层（接收请求、返回结果、WebSocket 推送进度）
├── 处理器注册表（自动发现、统一接口）
├── Celery 任务层（异步执行处理任务）
└── 处理引擎层
    ├── image/    图片处理模块
    ├── video/    视频处理模块
    └── audio/    音频处理模块
         │
         ▼
    Redis（任务队列 + 进度缓存 + Pub/Sub）
```

### 任务处理流程

1. 用户在浏览器上传文件 + 选择处理器 + 设置参数
2. FastAPI 接收请求 → 保存临时文件 → 创建 Celery 任务 → 返回 task_id
3. Celery Worker 执行：
   - 通过 ProcessorRegistry 查找对应处理器
   - validate() 校验参数
   - process() 执行处理，通过 progress_callback 上报进度
   - 进度经 Redis Pub/Sub → WebSocket → 浏览器实时显示
4. 任务完成 → 前端收到通知 → 显示结果预览和下载链接
5. 用户下载处理结果

## 4. 项目结构

```
tools/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI 入口
│   │   ├── config.py                # 配置管理（端口、存储路径、文件大小限制等）
│   │   ├── api/
│   │   │   ├── tasks.py             # REST API: 任务提交/查询/下载/取消
│   │   │   ├── processors.py        # REST API: 处理器列表查询
│   │   │   └── ws.py                # WebSocket: 进度推送
│   │   ├── core/
│   │   │   ├── base.py              # 处理器基类
│   │   │   └── registry.py          # 处理器注册表（自动发现模块）
│   │   ├── processors/
│   │   │   ├── image/
│   │   │   │   ├── watermark.py         # 去水印（OpenCV inpainting）
│   │   │   │   ├── cutout.py            # 抠图（rembg）
│   │   │   │   ├── crop.py              # 裁剪/缩放（含 2 的幂次标准尺寸）
│   │   │   │   ├── pixelate.py          # 像素风转换
│   │   │   │   ├── frame_gen.py         # 静态图生成多帧
│   │   │   │   ├── sprite_sheet.py      # 精灵图拼接 + JSON 元数据
│   │   │   │   ├── tileset.py           # 瓦片图拼接
│   │   │   │   ├── edge_clean.py        # 边缘抗锯齿清理
│   │   │   │   ├── convert.py           # 格式转换（PNG/JPG/WebP）
│   │   │   │   └── batch.py             # 批量处理 + 命名规范
│   │   │   ├── video/
│   │   │   │   ├── extract_frames.py    # 视频截帧
│   │   │   │   ├── trim.py              # 视频裁剪
│   │   │   │   └── extract_audio.py     # 提取音频
│   │   │   └── audio/
│   │   │       ├── cut.py               # 音效截取
│   │   │       ├── merge.py             # 音频拼接/混合
│   │   │       └── convert.py           # 格式转换/音量标准化
│   │   ├── tasks/
│   │   │   └── worker.py                # Celery Worker 定义
│   │   └── models/
│   │       └── task.py                  # 任务数据模型
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── ImageTool.vue            # 图片处理页
│   │   │   ├── VideoTool.vue            # 视频处理页
│   │   │   └── AudioTool.vue            # 音频处理页
│   │   ├── components/
│   │   │   ├── FileUpload.vue           # 文件上传（拖拽 + 点击）
│   │   │   ├── ProgressPanel.vue        # 进度条 + 日志面板
│   │   │   ├── PreviewPane.vue          # 预览（图片/视频/音频/动画帧）
│   │   │   ├── ParamForm.vue            # 动态参数表单（根据处理器定义渲染）
│   │   │   └── PipelineEditor.vue       # 处理流水线编辑器
│   │   ├── api/
│   │   │   └── index.js                 # 后端 API 封装
│   │   ├── router/
│   │   │   └── index.js                 # Vue Router
│   │   ├── App.vue
│   │   └── main.js
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml                   # 一键启动所有服务
└── README.md
```

## 5. 核心设计

### 5.1 处理器基类（`core/base.py`）

```python
class BaseProcessor(ABC):
    name: str           # 唯一标识，如 "image.watermark"
    label: str          # 显示名称，如 "去水印"
    category: str       # 分类：image / video / audio
    params_schema: dict # 参数 JSON Schema，前端据此动态渲染表单

    @abstractmethod
    def validate(self, params: dict) -> bool:
        """校验输入参数"""

    @abstractmethod
    def process(self, input_file: str, output_dir: str, params: dict,
                progress_callback: Callable[[int, str], None]) -> list[str]:
        """执行处理，通过 callback 上报进度，返回输出文件路径列表"""
```

### 5.2 处理器注册表（`core/registry.py`）

```python
class ProcessorRegistry:
    _processors: dict[str, type[BaseProcessor]] = {}

    @classmethod
    def register(cls, processor_class):
        cls._processors[processor_class.name] = processor_class

    @classmethod
    def get(cls, name: str) -> BaseProcessor:
        return cls._processors[name]()

    @classmethod
    def list_by_category(cls, category: str) -> list[dict]:
        """返回指定分类的所有处理器信息，含 params_schema"""

    @classmethod
    def list_all(cls) -> list[dict]:
        """返回所有处理器信息"""
```

启动时自动扫描 `processors/` 目录，所有继承 `BaseProcessor` 的类自动注册。新增处理器只需添加文件，无需修改其他代码。

### 5.3 动态参数表单

每个处理器通过 `params_schema` 定义自己的参数，例如去水印处理器：

```python
params_schema = {
    "mode": {
        "type": "select",
        "label": "去水印模式",
        "options": ["手动涂抹", "自动检测"],
        "default": "手动涂抹"
    },
    "algorithm": {
        "type": "select",
        "label": "修复算法",
        "options": ["Telea", "Navier-Stokes"],
        "default": "Telea"
    },
    "brush_size": {
        "type": "slider",
        "label": "笔刷大小",
        "min": 1, "max": 50, "default": 10
    }
}
```

前端 `ParamForm.vue` 读取 schema 动态渲染对应的表单控件（下拉框、滑块、输入框、复选框等）。新增处理器时前端无需修改。

### 5.4 处理流水线

支持将多个处理步骤串联执行，例如：

```
去水印 → 抠图 → 缩放到 128x128 → 导出 PNG
```

流水线定义为一个有序的处理器列表，每个步骤的输出作为下一步的输入。前端通过 `PipelineEditor.vue` 拖拽编排步骤。

## 6. API 设计

### REST API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/processors` | GET | 获取所有处理器列表及参数定义 |
| `/api/processors/{category}` | GET | 获取指定分类的处理器列表 |
| `/api/tasks` | POST | 提交处理任务（文件 + 处理器名称 + 参数） |
| `/api/tasks/pipeline` | POST | 提交流水线任务（文件 + 处理器列表 + 各步骤参数） |
| `/api/tasks/{id}` | GET | 查询任务状态和进度 |
| `/api/tasks/{id}/download` | GET | 下载处理结果（单文件或 ZIP） |
| `/api/tasks/{id}` | DELETE | 取消/删除任务 |

### WebSocket

```
ws://host/ws/tasks/{id}
→ 进度推送：{"progress": 45, "message": "正在修复区域 3/7..."}
→ 完成通知：{"status": "completed", "files": ["output_1.png", "output_2.png"]}
→ 错误通知：{"status": "failed", "error": "文件格式不支持"}
```

## 7. 前端页面设计

### 整体布局

- 顶部导航栏：Logo + 三个功能页签（图片处理 / 视频处理 / 音频处理）
- 左右分栏布局：
  - 左侧：文件上传区 + 处理类型选择 + 动态参数面板 + 操作按钮
  - 右侧：预览/播放区 + 进度条 + 日志输出 + 下载按钮
- 暗色调主题，贴合游戏开发氛围

### 关键交互

- **文件上传**：支持拖拽和点击上传，显示文件信息（名称、大小、格式）
- **预览区**：
  - 图片：支持原图/结果对比，缩放查看
  - 视频：播放器 + 时间轴，支持选择截帧区间
  - 音频：波形显示 + 播放控制
  - 动画帧：逐帧预览 + 播放动画（可调 FPS）
- **进度反馈**：进度条 + 实时日志滚动
- **下载**：单文件直接下载，多文件自动打包为 ZIP

## 8. 功能优先级

### P0 — 第一版（MVP）

| 功能 | 处理器 | 实现方式 |
|------|--------|---------|
| 去水印 | image.watermark | OpenCV inpainting（Telea / Navier-Stokes），支持手动涂抹和自动检测 |
| 抠图 | image.cutout | rembg（U2-Net 模型），自动去除背景 |
| 裁剪/缩放 | image.crop | Pillow，支持自定义尺寸和 2 的幂次标准尺寸（32/64/128/256/512） |
| 像素风转换 | image.pixelate | Pillow，可配置像素块大小、调色板颜色数量 |
| 视频截帧 | video.extract_frames | ffmpeg-python，支持按帧率/时间区间截取 |
| 格式转换 | image.convert | Pillow，支持 PNG（带透明）/ JPG / WebP |

### P1 — 紧随其后

| 功能 | 处理器 | 实现方式 |
|------|--------|---------|
| 静态图生成多帧 | image.frame_gen | 基础变换（翻转、旋转、缩放、位移），可配置帧数 |
| 动画帧预览 | 前端组件 | Canvas 逐帧播放，可调 FPS |
| 精灵图拼接 | image.sprite_sheet | Pillow，输出 sprite sheet + JSON 元数据（帧坐标、尺寸） |
| 瓦片图拼接 | image.tileset | Pillow，生成可无缝平铺的瓦片集 |
| 边缘抗锯齿清理 | image.edge_clean | OpenCV，清理抠图后的杂边和半透明像素 |
| 音效截取 | audio.cut | pydub，波形可视化 + 区间选择 |
| 音频拼接/混合 | audio.merge | pydub，多轨混合 |
| 处理流水线 | Pipeline | 多步骤串联执行 |
| 批量处理 | image.batch | 遍历文件列表，应用同一处理器和参数 |
| 命名规范导出 | 批量处理附带 | 按模板命名（如 `{name}_{action}_{index:03d}.png`） |

### P2 — 增强功能

| 功能 | 说明 |
|------|------|
| AI 增强去水印 | 接入 lama-cleaner 模型 |
| AI 动画生成 | 接入视频生成模型，静态图生成连贯动画 |
| 法线贴图生成 | 从纹理图生成法线贴图，用于 2D 光照 |
| 素材管理 | 分类、标签、搜索、收藏 |
| 9-patch 图片 | UI 元素的 .9 图生成 |
| Godot 精灵帧资源 | 导出 `.tres` AnimatedTexture/SpriteFrames 资源文件 |
| Godot TileSet 资源 | 导出 `.tres` TileSet 资源，直接拖入 Godot 使用 |
| 音频格式适配 | 音效导出 WAV，背景音乐导出 OGG（Godot 推荐格式） |

## 9. 文件与存储

### 临时文件

- 上传的原始文件存放在 `{DATA_DIR}/uploads/`
- 处理结果存放在 `{DATA_DIR}/outputs/`
- `{DATA_DIR}` 默认为项目根目录下 `data/`，可通过配置修改

### 清理策略

- 任务完成后原始文件和结果默认保留 24 小时
- 可通过配置调整保留时间
- 提供手动清理接口

### 后期扩展

- 存储层抽象为接口，当前实现为本地文件系统
- 后期可切换为 OSS/MinIO 等对象存储，无需修改业务代码

## 10. 部署方案

### 本地开发

```bash
# 后端（使用 Miniconda 管理环境）
conda create -n gameasset python=3.11 -y
conda activate gameasset
cd backend && pip install -r requirements.txt

# 启动 Redis（conda 安装或系统安装）
conda install redis -c conda-forge   # 或系统自带
redis-server

# 启动 FastAPI
uvicorn app.main:app --reload --port 8000

# 启动 Celery Worker（另开终端，同样激活 gameasset 环境）
celery -A app.tasks.worker worker --loglevel=info

# 前端
cd frontend && npm install && npm run dev
```

### Docker 一键部署

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
  api:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [redis]
  worker:
    build: ./backend
    command: celery -A app.tasks.worker worker --loglevel=info
    depends_on: [redis]
  frontend:
    build: ./frontend
    ports: ["3000:80"]
    depends_on: [api]
```

## 11. 可扩展性设计

1. **处理器插件化**：继承 BaseProcessor + 添加文件 = 自动注册可用，前端自动适配
2. **存储层抽象**：接口统一，可切换本地/OSS/MinIO
3. **流水线机制**：功能可自由组合，不需要为每个组合写代码
4. **参数 Schema 驱动**：前端表单由后端定义驱动，新增处理器前端零改动
5. **WebSocket 统一进度**：所有处理器共享进度推送机制
6. **Godot 适配**：导出格式和元数据优先适配 Godot 引擎规范

## 12. Godot 适配设计

### 12.1 图片导出

- 精灵图（Sprite Sheet）导出时同时生成 `.tres` 资源文件（Godot 的 TextureAtlas 或 SpriteFrames 格式）
- JSON 元数据格式与 Godot 的 `load_frames` 约定对齐
- 默认使用 PNG 格式（Godot 原生支持，支持透明通道）

### 12.2 TileSet 导出

- 瓦片图集导出为 Godot 4.x 的 TileSet `.tres` 资源格式
- 包含瓦片尺寸、间距、碰撞形状等元数据
- 导出后可直接拖入 Godot 项目使用

### 12.3 音频导出

- 音效（短音频）默认导出为 `.wav` 格式（Godot 推荐用于 SFX）
- 背景音乐（长音频）默认导出为 `.ogg` 格式（Godot 推荐用于 BGM，支持流式播放）
- 自动处理采样率和声道数，适配 Godot 导入设置

### 12.4 目录结构导出

导出时可选择按 Godot 项目结构组织文件：

```
export/
├── sprites/
│   ├── characters/
│   │   └── player/
│   │       ├── player_idle.png
│   │       └── player_idle.tres
│   └── props/
├── tiles/
│   ├── tileset.png
│   └── tileset.tres
├── audio/
│   ├── sfx/
│   │   └── jump.wav
│   └── music/
│       └── theme.ogg
└── textures/
```
