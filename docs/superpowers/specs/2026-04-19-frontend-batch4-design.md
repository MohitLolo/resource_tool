# 前端第 4 批（Task 20-27）设计

> 原型参考：`/home/huangnianzhi/tools/prototype.html`

## 核心原则

**直接将 prototype.html 拆分为 Vue 3 组件，1:1 还原视觉效果和交互。**

## 技术决策

| 决策 | 选择 |
|------|------|
| 页面结构 | 单页 Tab 切换（无 Vue Router） |
| 状态管理 | Composables（reactive/ref） |
| UI 控件 | 完全自定义（原型 CSS 风格） |
| Element Plus | 仅引入 ElMessage / ElMessageBox / ElLoading |
| 装饰效果 | 全部还原（粒子、流光、渐变） |
| 后端对接 | axios 封装 + WebSocket per-task |

## 文件结构

```
frontend/
├── index.html
├── vite.config.js
├── package.json
└── src/
    ├── main.js
    ├── App.vue
    ├── assets/styles/
    │   ├── variables.css      # CSS 变量（暗色 / 亮色，直接取自原型）
    │   ├── reset.css          # 基础重置 + 滚动条
    │   └── global.css         # 粒子、流光、渐变等装饰动画
    ├── components/
    │   ├── Particles.vue
    │   ├── AppHeader.vue
    │   ├── FileUpload.vue
    │   ├── ProcessorGrid.vue
    │   ├── ParamForm.vue
    │   ├── PreviewArea.vue
    │   ├── ProcessingOverlay.vue
    │   ├── ProgressBar.vue
    │   ├── ConsoleLog.vue
    │   └── DownloadBar.vue
    ├── composables/
    │   ├── useTheme.js
    │   ├── useProcessors.js
    │   ├── useTask.js
    │   └── useUpload.js
    └── api/
        └── index.js
```

## 组件对应关系（原型 → Vue）

| 原型 HTML 区块 | Vue 组件 | 职责 |
|----------------|----------|------|
| `.particles` | Particles.vue | 20 个浮动粒子，JS 生成 DOM |
| `.header` | AppHeader.vue | Logo + NavTabs + ThemeToggle |
| `.upload-zone` + `.file-card` | FileUpload.vue | 拖拽上传 + 文件预览卡片 |
| `.processor-grid` + `.processor-card` | ProcessorGrid.vue | 2 列卡片，按 category 过滤 |
| `#params-*` 各面板 | ParamForm.vue | 根据 params_schema 动态渲染 |
| `.preview-area` + `.preview-compare` | PreviewArea.vue | 原图/结果对比 + 空状态 |
| `.processing-overlay` | ProcessingOverlay.vue | Spinner + 百分比 + 步骤文字 |
| `.progress-bar-wrap` | ProgressBar.vue | 4px 流光进度条 |
| `.log-panel` | ConsoleLog.vue | 160px 可滚动日志区 |
| `.download-bar` | DownloadBar.vue | 下载按钮 + 文件信息 |

## 数据流

1. App.vue 加载 → `useProcessors()` 调用 `GET /api/processors` → 缓存到 reactive
2. 点击 Tab → category 变化 → ProcessorGrid 过滤 → ParamForm 加载首个处理器的 params_schema
3. 上传文件 → `useUpload()` 管理文件状态 → FileUpload 显示预览卡片
4. 调整参数 → ParamForm emit params 对象
5. 点击"开始处理" → `useTask().create()` → `POST /api/tasks` → 获得 task_id
6. `useTask().connectWs(task_id)` → `WS /ws/tasks/{id}` → 实时更新 progress/message/status
7. ProgressBar / ConsoleLog / ProcessingOverlay 响应状态变化
8. 完成 → PreviewArea 显示结果，DownloadBar 出现

## 后端 API

| 接口 | 用途 |
|------|------|
| `GET /api/processors` | 获取全部处理器列表 |
| `GET /api/processors/{category}` | 按分类获取 |
| `POST /api/tasks` | 创建任务（FormData: input_file, extra_files, processor, params） |
| `GET /api/tasks/{id}` | 查询任务状态 |
| `GET /api/tasks/{id}/download` | 下载结果（单文件直下，多文件 ZIP） |
| `DELETE /api/tasks/{id}` | 取消/删除任务 |
| `WS /ws/tasks/{id}` | 实时进度推送 |
