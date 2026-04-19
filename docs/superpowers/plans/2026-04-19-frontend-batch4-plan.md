# 前端第 4 批 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `prototype.html` 原型 1:1 转为 Vue 3 组件化前端，对接后端 API 实现完整交互流程。

**Architecture:** 单页 Tab 切换（无 Vue Router），Composables 管理状态，自定义 CSS 控件（不使用 Element Plus 组件），Element Plus 仅引入 ElMessage/ElMessageBox/ElLoading 功能性 API。axios 封装后端 REST API，WebSocket per-task 接收实时进度。

**Tech Stack:** Vue 3, Vite, axios, Element Plus（仅功能性 API）

**设计文档:** `docs/superpowers/specs/2026-04-19-frontend-batch4-design.md`
**原型参考:** `/home/huangnianzhi/tools/prototype.html`

---

## 文件结构总览

```
frontend/
├── index.html
├── vite.config.js
├── package.json
└── src/
    ├── main.js                       # 入口
    ├── App.vue                       # 根组件
    ├── assets/styles/
    │   ├── variables.css             # CSS 变量（暗色/亮色）
    │   ├── reset.css                 # 重置 + 滚动条
    │   └── global.css                # 粒子、流光、渐变动画
    ├── components/
    │   ├── Particles.vue             # 背景粒子
    │   ├── AppHeader.vue             # 导航栏
    │   ├── FileUpload.vue            # 上传区 + 文件卡片
    │   ├── ProcessorGrid.vue         # 处理器卡片网格
    │   ├── ParamForm.vue             # 动态参数表单
    │   ├── PreviewArea.vue           # 原图/结果预览
    │   ├── ProcessingOverlay.vue     # 处理中遮罩
    │   ├── ProgressBar.vue           # 流光进度条
    │   ├── ConsoleLog.vue            # 控制台日志
    │   └── DownloadBar.vue           # 下载栏
    ├── composables/
    │   ├── useTheme.js               # 主题切换
    │   ├── useProcessors.js          # 处理器列表
    │   ├── useTask.js                # 任务 + WebSocket
    │   └── useUpload.js              # 文件上传
    └── api/
        └── index.js                  # axios 封装
```

---

## Task 20: 初始化前端项目 + CSS 基础

**Files:**
- Create: `frontend/` (Vite 项目)
- Create: `frontend/src/assets/styles/variables.css`
- Create: `frontend/src/assets/styles/reset.css`
- Create: `frontend/src/assets/styles/global.css`
- Create: `frontend/vite.config.js`
- Create: `frontend/src/main.js`

- [ ] **Step 1: 创建 Vite 项目**

```bash
cd /home/huangnianzhi/tools
npm create vite@latest frontend -- --template vue
cd frontend
npm install
```

- [ ] **Step 2: 安装依赖**

```bash
cd /home/huangnianzhi/tools/frontend
npm install axios element-plus @element-plus/icons-vue
```

不安装 vue-router（单页 Tab，不需要路由）。

- [ ] **Step 3: 配置 vite.config.js**

覆盖 `frontend/vite.config.js`，配置 API 代理和 WebSocket 代理：

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

- [ ] **Step 4: 创建 CSS 变量文件**

创建 `frontend/src/assets/styles/variables.css`，直接从 prototype.html 第 10-51 行提取：

```css
:root {
  --bg-deep: #0a0e17;
  --bg-panel: #111827;
  --bg-card: #1a2236;
  --bg-input: #0f1729;
  --border: #1e293b;
  --border-active: #6366f1;
  --accent: #818cf8;
  --accent2: #c084fc;
  --accent-glow: rgba(129,140,248,.35);
  --text: #e2e8f0;
  --text-dim: #94a3b8;
  --success: #34d399;
  --danger: #f87171;
  --warn: #fbbf24;
  --radius: 12px;
  --radius-sm: 8px;
  --header-bg: linear-gradient(135deg, rgba(99,102,241,.12) 0%, rgba(192,132,252,.08) 100%);
  --grid-line: rgba(99,102,241,.03);
  --glow-soft: rgba(99,102,241,.06);
  --particle-opacity: .15;
}
:root.light {
  --bg-deep: #f1f5f9;
  --bg-panel: #ffffff;
  --bg-card: #f8fafc;
  --bg-input: #f1f5f9;
  --border: #e2e8f0;
  --border-active: #6366f1;
  --accent: #6366f1;
  --accent2: #8b5cf6;
  --accent-glow: rgba(99,102,241,.2);
  --text: #1e293b;
  --text-dim: #64748b;
  --success: #10b981;
  --danger: #ef4444;
  --warn: #f59e0b;
  --header-bg: linear-gradient(135deg, rgba(99,102,241,.06) 0%, rgba(192,132,252,.04) 100%);
  --grid-line: rgba(99,102,241,.04);
  --glow-soft: rgba(99,102,241,.04);
  --particle-opacity: .08;
}
```

- [ ] **Step 5: 创建 reset.css**

创建 `frontend/src/assets/styles/reset.css`，从 prototype.html 第 9、52-58 行提取：

```css
*, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
html, body { height:100%; font-family:'Inter','Segoe UI',system-ui,sans-serif; background:var(--bg-deep); color:var(--text); overflow:hidden; }
a { color:var(--accent); text-decoration:none; }
::-webkit-scrollbar { width:6px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:#334155; border-radius:3px; }
```

- [ ] **Step 6: 创建 global.css**

创建 `frontend/src/assets/styles/global.css`，从 prototype.html 提取所有装饰动画（粒子、流光进度条、Spinner 旋转）。包含 `@keyframes float`、`@keyframes shimmer`、`@keyframes spin` 以及所有组件的 CSS 类。

这个文件内容较多，完整 CSS 从 prototype.html 的 `<style>` 标签中提取以下区块（按行号）：
- Layout (`.app`, `.main`, `.left-panel`, `.right-panel`, `.panel-section`, `.section-title`): 行 61-117
- Upload (`.upload-zone`, `.file-card`, `.file-thumb`, `.file-info`, `.file-remove`): 行 119-158
- Processor selector (`.processor-grid`, `.processor-card`): 行 160-174
- Param form (`.form-group`, `.form-label`, `.form-select`, `.form-input`, `.slider-*`, `.toggle-*`): 行 176-213
- Action button (`.action-btn`): 行 215-235
- Preview area (`.preview-area`, `.preview-empty`, `.preview-content`, `.preview-compare`, `.preview-side`, `.preview-label`): 行 240-292
- Progress bar (`.progress-bar-wrap`, `.progress-bar-fill`, `@keyframes shimmer`): 行 294-307
- Log panel (`.log-panel`, `.log-header`, `.log-body`, `.log-line`, `.log-msg`): 行 309-335
- Download bar (`.download-bar`, `.download-btn`, `.download-info`): 行 337-351
- Processing overlay (`.processing-overlay`, `.spinner`, `@keyframes spin`): 行 353-381
- Particles (`.particles`, `.particle`, `@keyframes float`): 行 383-398

全部 CSS 类原样复制到 global.css，不做修改。

- [ ] **Step 7: 配置 main.js**

覆盖 `frontend/src/main.js`：

```js
import { createApp } from 'vue'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'
import 'element-plus/es/components/loading/style/css'
import './assets/styles/variables.css'
import './assets/styles/reset.css'
import './assets/styles/global.css'
import App from './App.vue'

const app = createApp(App)
app.config.globalProperties.$message = ElMessage
app.config.globalProperties.$messageBox = ElMessageBox
app.config.globalProperties.$loading = ElLoading.service
app.mount('#app')
```

- [ ] **Step 8: 清理模板文件**

删除 Vite 生成的多余文件：
```bash
rm -f frontend/src/components/HelloWorld.vue
rm -f frontend/src/assets/vue.svg
rm -f frontend/public/vite.svg
```

将 `frontend/src/App.vue` 替换为最小占位：

```vue
<template>
  <div class="app">
    <p style="padding:40px;color:var(--text);">前端项目已初始化</p>
  </div>
</template>
```

- [ ] **Step 9: 启动验证**

```bash
cd /home/huangnianzhi/tools/frontend && npm run dev
```

打开 http://localhost:5173，确认页面显示"前端项目已初始化"，暗色背景和 CSS 变量生效。

- [ ] **Step 10: 提交**

```bash
cd /home/huangnianzhi/tools
git add frontend/
git commit -m "feat: 初始化前端项目，配置 Vite + CSS 变量体系"
```

---

## Task 21: App.vue 壳 + AppHeader + Particles + useTheme

**Files:**
- Create: `frontend/src/composables/useTheme.js`
- Create: `frontend/src/components/Particles.vue`
- Create: `frontend/src/components/AppHeader.vue`
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: 创建 useTheme composable**

创建 `frontend/src/composables/useTheme.js`：

```js
import { ref, watchEffect } from 'vue'

const isDark = ref(true)

// 初始化时读取 localStorage
const saved = localStorage.getItem('theme')
if (saved === 'light') {
  isDark.value = false
}

watchEffect(() => {
  const root = document.documentElement
  if (isDark.value) {
    root.classList.remove('light')
  } else {
    root.classList.add('light')
  }
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
})

export function useTheme() {
  const toggle = () => {
    isDark.value = !isDark.value
  }
  return { isDark, toggle }
}
```

- [ ] **Step 2: 创建 Particles.vue**

创建 `frontend/src/components/Particles.vue`，从 prototype.html 第 402-410 行和 699-710 行转换：

```vue
<template>
  <div class="particles" ref="container"></div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const container = ref(null)

onMounted(() => {
  for (let i = 0; i < 20; i++) {
    const p = document.createElement('div')
    p.className = 'particle'
    const s = Math.random() * 4 + 2
    p.style.cssText = `width:${s}px;height:${s}px;left:${Math.random()*100}%;animation-duration:${Math.random()*15+10}s;animation-delay:${Math.random()*10}s;background:${Math.random()>.5?'var(--accent)':'var(--accent2)'}`
    container.value.appendChild(p)
  }
})
</script>
```

样式已在 global.css 中定义（`.particles`、`.particle`、`@keyframes float`），组件不需要 `<style>` 块。

- [ ] **Step 3: 创建 AppHeader.vue**

创建 `frontend/src/components/AppHeader.vue`，从 prototype.html 第 407-437 行转换：

```vue
<template>
  <header class="header">
    <div class="logo">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"/>
        <line x1="12" y1="22" x2="12" y2="15.5"/>
        <polyline points="22 8.5 12 15.5 2 8.5"/>
        <polyline points="2 15.5 12 8.5 22 15.5"/>
        <line x1="12" y1="2" x2="12" y2="8.5"/>
      </svg>
      GameAsset 素材工具箱
    </div>
    <nav class="nav-tabs">
      <div
        v-for="tab in tabs"
        :key="tab.category"
        class="nav-tab"
        :class="{ active: currentCategory === tab.category }"
        @click="$emit('update:currentCategory', tab.category)"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" v-html="tab.svgPath"></svg>
        {{ tab.label }}
      </div>
    </nav>
    <div class="header-actions">
      <div class="icon-btn" title="切换主题" @click="toggle">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <template v-if="isDark">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
          </template>
          <template v-else>
            <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
          </template>
        </svg>
      </div>
    </div>
  </header>
</template>

<script setup>
import { useTheme } from '../composables/useTheme.js'

defineProps({
  currentCategory: { type: String, default: 'image' },
})

defineEmits(['update:currentCategory'])

const { isDark, toggle } = useTheme()

const tabs = [
  {
    category: 'image',
    label: '图片处理',
    svgPath: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/>',
  },
  {
    category: 'video',
    label: '视频处理',
    svgPath: '<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/>',
  },
  {
    category: 'audio',
    label: '音频处理',
    svgPath: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
  },
]
</script>
```

样式已在 global.css 中（`.header`、`.logo`、`.nav-tabs`、`.nav-tab`、`.icon-btn`）。

- [ ] **Step 4: 创建 App.vue 壳**

覆盖 `frontend/src/App.vue`：

```vue
<template>
  <Particles />
  <div class="app">
    <AppHeader
      :currentCategory="currentCategory"
      @update:currentCategory="currentCategory = $event"
    />
    <div class="main">
      <div class="left-panel">
        <div class="panel-section">
          <p style="color:var(--text-dim);">上传区占位</p>
        </div>
      </div>
      <div class="right-panel">
        <p style="color:var(--text-dim);padding:40px;">预览区占位</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Particles from './components/Particles.vue'
import AppHeader from './components/AppHeader.vue'

const currentCategory = ref('image')
</script>
```

- [ ] **Step 5: 启动验证**

```bash
cd /home/huangnianzhi/tools/frontend && npm run dev
```

验证：
- 暗色背景 + 粒子动画浮动
- Header 显示 Logo + 三个 Tab + 主题切换按钮
- 点击 Tab 切换 active 状态（紫蓝渐变高亮）
- 点击月亮图标切换到亮色主题，所有颜色切换
- 刷新页面后主题保持（localStorage）

- [ ] **Step 6: 提交**

```bash
cd /home/huangnianzhi/tools
git add frontend/
git commit -m "feat: 实现 App 壳、导航栏、粒子动画、主题切换"
```

---

## Task 22: API 封装层 + Composables

**Files:**
- Create: `frontend/src/api/index.js`
- Create: `frontend/src/composables/useProcessors.js`
- Create: `frontend/src/composables/useUpload.js`
- Create: `frontend/src/composables/useTask.js`

- [ ] **Step 1: 创建 API 封装**

创建 `frontend/src/api/index.js`：

```js
import axios from 'axios'

const http = axios.create({
  baseURL: '',
  timeout: 30000,
})

export async function getProcessors(category) {
  const url = category ? `/api/processors/${category}` : '/api/processors'
  const { data } = await http.get(url)
  return data
}

export async function createTask({ inputFile, extraFiles, processor, params }) {
  const form = new FormData()
  form.append('input_file', inputFile)
  if (extraFiles) {
    for (const file of extraFiles) {
      form.append('extra_files', file)
    }
  }
  form.append('processor', processor)
  form.append('params', JSON.stringify(params))
  const { data } = await http.post('/api/tasks', form)
  return data
}

export async function getTask(taskId) {
  const { data } = await http.get(`/api/tasks/${taskId}`)
  return data
}

export async function downloadResult(taskId) {
  const { data } = await http.get(`/api/tasks/${taskId}/download`, {
    responseType: 'blob',
  })
  return data
}

export async function deleteTask(taskId) {
  const { data } = await http.delete(`/api/tasks/${taskId}`)
  return data
}
```

- [ ] **Step 2: 创建 useProcessors composable**

创建 `frontend/src/composables/useProcessors.js`：

```js
import { ref } from 'vue'
import { getProcessors } from '../api/index.js'

const allProcessors = ref([])
const loading = ref(false)
let loaded = false

export function useProcessors() {
  const fetchAll = async () => {
    if (loaded) return
    loading.value = true
    try {
      allProcessors.value = await getProcessors()
      loaded = true
    } finally {
      loading.value = false
    }
  }

  const getByCategory = (category) => {
    return allProcessors.value.filter(p => p.category === category)
  }

  return { allProcessors, loading, fetchAll, getByCategory }
}
```

- [ ] **Step 3: 创建 useUpload composable**

创建 `frontend/src/composables/useUpload.js`：

```js
import { ref, computed } from 'vue'

export function useUpload() {
  const file = ref(null)
  const previewUrl = ref('')

  const fileInfo = computed(() => {
    if (!file.value) return null
    const f = file.value
    const sizeMB = (f.size / 1024 / 1024).toFixed(1)
    const ext = f.name.split('.').pop().toUpperCase()
    return {
      name: f.name,
      size: `${sizeMB} MB`,
      ext,
    }
  })

  const setFile = (newFile) => {
    file.value = newFile
    if (previewUrl.value) {
      URL.revokeObjectURL(previewUrl.value)
    }
    if (newFile) {
      previewUrl.value = URL.createObjectURL(newFile)
    } else {
      previewUrl.value = ''
    }
  }

  const clear = () => {
    if (previewUrl.value) {
      URL.revokeObjectURL(previewUrl.value)
    }
    file.value = null
    previewUrl.value = ''
  }

  return { file, previewUrl, fileInfo, setFile, clear }
}
```

- [ ] **Step 4: 创建 useTask composable**

创建 `frontend/src/composables/useTask.js`：

```js
import { ref, reactive } from 'vue'
import { createTask as apiCreateTask, getTask as apiGetTask } from '../api/index.js'

export function useTask() {
  const taskId = ref(null)
  const status = ref('idle')  // idle | pending | processing | completed | failed | canceled
  const progress = ref(0)
  const message = ref('')
  const outputFiles = ref([])
  let ws = null

  const connectWs = (id) => {
    if (ws) {
      ws.close()
    }
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    ws = new WebSocket(`${protocol}//${location.host}/ws/tasks/${id}`)

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      progress.value = data.progress ?? 0
      message.value = data.message ?? ''
      status.value = data.status ?? status.value

      if (data.status === 'completed') {
        // 获取完整任务信息（含 output_files）
        apiGetTask(id).then(task => {
          outputFiles.value = task.output_files ?? []
        })
        ws.close()
        ws = null
      }
      if (data.status === 'failed' || data.status === 'canceled') {
        ws.close()
        ws = null
      }
    }

    ws.onerror = () => {
      status.value = 'failed'
      message.value = 'WebSocket 连接失败'
      ws = null
    }
  }

  const create = async ({ inputFile, extraFiles, processor, params }) => {
    status.value = 'pending'
    progress.value = 0
    message.value = '任务已创建'
    outputFiles.value = []

    const result = await apiCreateTask({ inputFile, extraFiles, processor, params })
    taskId.value = result.task_id
    connectWs(result.task_id)
    return result
  }

  const reset = () => {
    if (ws) {
      ws.close()
      ws = null
    }
    taskId.value = null
    status.value = 'idle'
    progress.value = 0
    message.value = ''
    outputFiles.value = []
  }

  return {
    taskId, status, progress, message, outputFiles,
    create, reset,
  }
}
```

- [ ] **Step 5: 提交**

```bash
cd /home/huangnianzhi/tools
git add frontend/src/api/ frontend/src/composables/
git commit -m "feat: 实现 API 封装层和 useProcessors/useUpload/useTask composables"
```

---

## Task 23: 左面板组件 — FileUpload + ProcessorGrid

**Files:**
- Create: `frontend/src/components/FileUpload.vue`
- Create: `frontend/src/components/ProcessorGrid.vue`

- [ ] **Step 1: 创建 FileUpload.vue**

创建 `frontend/src/components/FileUpload.vue`，从 prototype.html 第 446-465 行转换：

```vue
<template>
  <div class="panel-section">
    <div class="section-title">上传文件</div>
    <input
      ref="fileInput"
      type="file"
      style="display:none"
      :accept="acceptTypes"
      @change="handleFileSelect"
    />
    <div
      class="upload-zone"
      :class="{ dragover: isDragging }"
      @click="$refs.fileInput.click()"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <div class="icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
      </div>
      <p>拖拽文件到此处，或点击选择</p>
      <p class="hint">{{ hintText }}</p>
    </div>
    <div class="file-card" v-if="fileInfo">
      <div class="file-thumb">
        <img v-if="previewUrl" :src="previewUrl" alt="thumb" />
      </div>
      <div class="file-info">
        <div class="file-name">{{ fileInfo.name }}</div>
        <div class="file-meta">{{ fileInfo.size }}</div>
      </div>
      <button class="file-remove" title="移除" @click="handleRemove">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  category: { type: String, default: 'image' },
  fileInfo: { type: Object, default: null },
  previewUrl: { type: String, default: '' },
})

const emit = defineEmits(['select', 'clear'])

const isDragging = ref(false)
const fileInput = ref(null)

const acceptTypes = computed(() => {
  const map = {
    image: '.png,.jpg,.jpeg,.webp',
    video: '.mp4,.avi,.mov,.webm',
    audio: '.wav,.mp3,.ogg,.flac',
  }
  return map[props.category] || '*'
})

const hintText = computed(() => {
  const map = {
    image: '支持 PNG、JPG、WebP — 最大 500 MB',
    video: '支持 MP4、AVI、MOV、WebM — 最大 500 MB',
    audio: '支持 WAV、MP3、OGG、FLAC — 最大 500 MB',
  }
  return map[props.category] || ''
})

const handleFileSelect = (e) => {
  const file = e.target.files[0]
  if (file) emit('select', file)
}

const handleDrop = (e) => {
  isDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) emit('select', file)
}

const handleRemove = () => {
  if (fileInput.value) fileInput.value.value = ''
  emit('clear')
}
</script>
```

样式已在 global.css 中（`.upload-zone`、`.file-card`、`.file-thumb`、`.file-info`、`.file-remove`）。

- [ ] **Step 2: 创建 ProcessorGrid.vue**

创建 `frontend/src/components/ProcessorGrid.vue`，从 prototype.html 第 467-519 行转换：

```vue
<template>
  <div class="panel-section">
    <div class="section-title">选择处理器</div>
    <div class="processor-grid">
      <div
        v-for="proc in processors"
        :key="proc.name"
        class="processor-card"
        :class="{ active: selectedName === proc.name }"
        @click="$emit('update:selectedName', proc.name)"
      >
        <div class="proc-icon">{{ proc.icon || '🔧' }}</div>
        <div class="proc-name">{{ proc.label }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  processors: { type: Array, default: () => [] },
  selectedName: { type: String, default: '' },
})

defineEmits(['update:selectedName'])
</script>
```

样式已在 global.css 中（`.processor-grid`、`.processor-card`）。

注意：处理器 `icon` 字段需要后端支持。目前后端 `list_all()` 只返回 `name/label/category/params_schema`。如果后端还没加 `icon` 字段，前端用 fallback emoji `'🔧'`。后续后端加 `icon` 字段后自动生效。

- [ ] **Step 3: 提交**

```bash
cd /home/huangnianzhi/tools
git add frontend/src/components/FileUpload.vue frontend/src/components/ProcessorGrid.vue
git commit -m "feat: 实现 FileUpload 拖拽上传和 ProcessorGrid 处理器卡片"
```

---

## Task 24: ParamForm 动态参数表单

**Files:**
- Create: `frontend/src/components/ParamForm.vue`

这是核心组件 — 根据后端 `params_schema` 动态渲染表单控件。原型中每个分类有静态参数面板（prototype.html 第 522-614 行），实际由 `params_schema` 驱动。

后端 `params_schema` 格式（以 image.crop 为例）：

```json
{
  "mode": {
    "type": "select",
    "label": "模式",
    "default": "power2",
    "options": ["power2", "custom", "crop"]
  },
  "pixel_size": {
    "type": "number",
    "label": "像素块大小",
    "default": 8,
    "min": 2,
    "max": 32
  },
  "alpha_matting": {
    "type": "checkbox",
    "label": "精细边缘",
    "default": false
  }
}
```

- [ ] **Step 1: 创建 ParamForm.vue**

创建 `frontend/src/components/ParamForm.vue`：

```vue
<template>
  <div class="panel-section" v-if="schema && Object.keys(schema).length > 0">
    <div class="section-title">参数设置</div>
    <div v-for="(field, key) in schema" :key="key" class="form-group">
      <!-- select 类型 -->
      <template v-if="field.type === 'select'">
        <label class="form-label">{{ field.label }}</label>
        <select
          class="form-select"
          :value="params[key] ?? field.default"
          @change="updateParam(key, $event.target.value)"
        >
          <option
            v-for="opt in field.options"
            :key="opt"
            :value="opt"
          >{{ formatOption(opt) }}</option>
        </select>
      </template>

      <!-- number 类型（带 slider） -->
      <template v-else-if="field.type === 'number'">
        <label class="form-label">{{ field.label }}</label>
        <div class="slider-wrap">
          <div
            class="slider-track"
            ref="sliderTrack"
            @mousedown="startSliderDrag($event, key, field)"
          >
            <div class="slider-fill" :style="{ width: sliderPercent(key, field) + '%' }"></div>
            <div class="slider-thumb" :style="{ left: sliderPercent(key, field) + '%' }"></div>
          </div>
          <span class="slider-value">{{ params[key] ?? field.default }}</span>
        </div>
      </template>

      <!-- checkbox 类型 -->
      <template v-else-if="field.type === 'checkbox'">
        <div class="toggle-wrap">
          <label class="form-label" style="margin:0">{{ field.label }}</label>
          <div
            class="toggle"
            :class="{ active: params[key] ?? field.default }"
            @click="updateParam(key, !(params[key] ?? field.default))"
          ></div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { watch } from 'vue'

const props = defineProps({
  schema: { type: Object, default: () => ({}) },
  params: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:params'])

// 初始化默认值
watch(() => props.schema, (schema) => {
  const defaults = {}
  for (const [key, field] of Object.entries(schema)) {
    if (props.params[key] === undefined && field.default !== undefined) {
      defaults[key] = field.default
    }
  }
  if (Object.keys(defaults).length > 0) {
    emit('update:params', { ...props.params, ...defaults })
  }
}, { immediate: true })

const updateParam = (key, value) => {
  emit('update:params', { ...props.params, [key]: value })
}

const sliderPercent = (key, field) => {
  const val = Number(props.params[key] ?? field.default ?? 0)
  const min = field.min ?? 0
  const max = field.max ?? 100
  return ((val - min) / (max - min)) * 100
}

const startSliderDrag = (event, key, field) => {
  const track = event.currentTarget
  const min = field.min ?? 0
  const max = field.max ?? 100

  const update = (e) => {
    const rect = track.getBoundingClientRect()
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    const val = Math.round(min + ratio * (max - min))
    updateParam(key, val)
  }

  update(event)

  const onMove = (e) => update(e)
  const onUp = () => {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

const formatOption = (opt) => {
  // 将 snake_case 的 option 值转为可读形式
  return String(opt).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}
</script>
```

样式已在 global.css 中（`.form-group`、`.form-label`、`.form-select`、`.slider-*`、`.toggle-*`）。

- [ ] **Step 2: 提交**

```bash
cd /home/huangnianzhi/tools
git add frontend/src/components/ParamForm.vue
git commit -m "feat: 实现 ParamForm 动态参数表单，支持 select/number/checkbox"
```

---

## Task 25: 右面板组件 — Preview + Progress + Console + Download

**Files:**
- Create: `frontend/src/components/PreviewArea.vue`
- Create: `frontend/src/components/ProcessingOverlay.vue`
- Create: `frontend/src/components/ProgressBar.vue`
- Create: `frontend/src/components/ConsoleLog.vue`
- Create: `frontend/src/components/DownloadBar.vue`

- [ ] **Step 1: 创建 ProcessingOverlay.vue**

创建 `frontend/src/components/ProcessingOverlay.vue`，从 prototype.html 第 653-658 行：

```vue
<template>
  <div class="processing-overlay" :class="{ show: visible }">
    <div class="spinner"></div>
    <div class="processing-pct">{{ progress }}%</div>
    <div class="processing-text">{{ message }}</div>
  </div>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: false },
  progress: { type: Number, default: 0 },
  message: { type: String, default: '' },
})
</script>
```

- [ ] **Step 2: 创建 ProgressBar.vue**

创建 `frontend/src/components/ProgressBar.vue`，从 prototype.html 第 661-664 行：

```vue
<template>
  <div class="progress-bar-wrap" :class="{ complete: status === 'completed' }">
    <div class="progress-bar-fill" :style="{ width: progress + '%' }"></div>
  </div>
</template>

<script setup>
defineProps({
  progress: { type: Number, default: 0 },
  status: { type: String, default: '' },
})
</script>
```

- [ ] **Step 3: 创建 ConsoleLog.vue**

创建 `frontend/src/components/ConsoleLog.vue`，从 prototype.html 第 666-684 行：

```vue
<template>
  <div class="log-panel">
    <div class="log-header">
      <span class="title">控制台</span>
      <span
        class="log-status"
        :class="statusClass"
      >{{ statusText }}</span>
    </div>
    <div class="log-body" ref="logBody">
      <div
        v-for="(log, i) in logs"
        :key="i"
        class="log-line"
      >
        <span class="log-time">{{ log.time }}</span>
        <span class="log-msg" :class="log.type">{{ log.text }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  logs: { type: Array, default: () => [] },
  status: { type: String, default: 'idle' },
})

const logBody = ref(null)

const statusClass = computed(() => {
  if (props.status === 'processing' || props.status === 'pending') return 'processing'
  if (props.status === 'completed') return 'completed'
  if (props.status === 'failed') return 'failed'
  return ''
})

const statusText = computed(() => {
  const map = {
    idle: '就绪',
    pending: '等待中',
    processing: '处理中',
    completed: '已完成',
    failed: '失败',
    canceled: '已取消',
  }
  return map[props.status] || ''
})

// 新日志自动滚到底部
watch(() => props.logs.length, async () => {
  await nextTick()
  if (logBody.value) {
    logBody.value.scrollTop = logBody.value.scrollHeight
  }
})
</script>
```

- [ ] **Step 4: 创建 PreviewArea.vue**

创建 `frontend/src/components/PreviewArea.vue`，从 prototype.html 第 630-658 行：

```vue
<template>
  <div class="preview-area">
    <!-- 空状态 -->
    <div class="preview-empty" v-if="!originalUrl && !resultUrl">
      <div class="icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>
      </div>
      <p>预览将在此处显示</p>
      <p class="sub">上传文件并选择处理器即可开始</p>
    </div>

    <!-- 有内容时 -->
    <div class="preview-content" :class="{ show: originalUrl || resultUrl }">
      <div class="preview-compare">
        <div class="preview-side" v-if="originalUrl">
          <span class="preview-label original">原图</span>
          <img :src="originalUrl" alt="原图" />
        </div>
        <div class="preview-side" v-if="resultUrl">
          <span class="preview-label result">结果</span>
          <img :src="resultUrl" alt="结果" />
        </div>
      </div>
    </div>

    <ProcessingOverlay
      :visible="isProcessing"
      :progress="progress"
      :message="progressMessage"
    />
  </div>
</template>

<script setup>
import ProcessingOverlay from './ProcessingOverlay.vue'

defineProps({
  originalUrl: { type: String, default: '' },
  resultUrl: { type: String, default: '' },
  isProcessing: { type: Boolean, default: false },
  progress: { type: Number, default: 0 },
  progressMessage: { type: String, default: '' },
})
</script>
```

- [ ] **Step 5: 创建 DownloadBar.vue**

创建 `frontend/src/components/DownloadBar.vue`，从 prototype.html 第 686-693 行：

```vue
<template>
  <div class="download-bar" v-if="show">
    <button class="download-btn" @click="$emit('download')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
      下载结果
    </button>
    <span class="download-info">{{ info }}</span>
  </div>
</template>

<script setup>
defineProps({
  show: { type: Boolean, default: false },
  info: { type: String, default: '' },
})

defineEmits(['download'])
</script>
```

- [ ] **Step 6: 提交**

```bash
cd /home/huangnianzhi/tools
git add frontend/src/components/PreviewArea.vue frontend/src/components/ProcessingOverlay.vue frontend/src/components/ProgressBar.vue frontend/src/components/ConsoleLog.vue frontend/src/components/DownloadBar.vue
git commit -m "feat: 实现右面板组件（预览、进度条、控制台、下载栏）"
```

---

## Task 26: 组装 App.vue — 完整数据流集成

**Files:**
- Modify: `frontend/src/App.vue`

这是关键任务 — 将所有组件连接到 composables，实现完整的交互流程。

- [ ] **Step 1: 完整覆盖 App.vue**

```vue
<template>
  <Particles />
  <div class="app">
    <AppHeader
      :currentCategory="currentCategory"
      @update:currentCategory="handleCategoryChange"
    />
    <div class="main">
      <!-- 左面板 -->
      <div class="left-panel">
        <FileUpload
          :category="currentCategory"
          :fileInfo="upload.fileInfo.value"
          :previewUrl="upload.previewUrl.value"
          @select="upload.setFile"
          @clear="upload.clear"
        />
        <ProcessorGrid
          :processors="currentProcessors"
          :selectedName="selectedProcessorName"
          @update:selectedName="handleProcessorChange"
        />
        <ParamForm
          :schema="currentSchema"
          :params="params"
          @update:params="params = $event"
        />
        <div class="panel-section">
          <button
            class="action-btn"
            :disabled="!canSubmit"
            @click="handleSubmit"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            开始处理
          </button>
        </div>
      </div>

      <!-- 右面板 -->
      <div class="right-panel">
        <PreviewArea
          :originalUrl="upload.previewUrl.value"
          :resultUrl="resultUrl"
          :isProcessing="task.status.value === 'processing'"
          :progress="task.progress.value"
          :progressMessage="task.message.value"
        />
        <ProgressBar
          :progress="task.progress.value"
          :status="task.status.value"
        />
        <ConsoleLog
          :logs="logs"
          :status="task.status.value"
        />
        <DownloadBar
          :show="task.status.value === 'completed'"
          :info="downloadInfo"
          @download="handleDownload"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import Particles from './components/Particles.vue'
import AppHeader from './components/AppHeader.vue'
import FileUpload from './components/FileUpload.vue'
import ProcessorGrid from './components/ProcessorGrid.vue'
import ParamForm from './components/ParamForm.vue'
import PreviewArea from './components/PreviewArea.vue'
import ProgressBar from './components/ProgressBar.vue'
import ConsoleLog from './components/ConsoleLog.vue'
import DownloadBar from './components/DownloadBar.vue'
import { useProcessors } from './composables/useProcessors.js'
import { useUpload } from './composables/useUpload.js'
import { useTask } from './composables/useTask.js'
import { downloadResult } from './api/index.js'

const currentCategory = ref('image')
const selectedProcessorName = ref('')
const params = ref({})

const { allProcessors, fetchAll, getByCategory } = useProcessors()
const upload = useUpload()
const task = useTask()

const resultUrl = ref('')
const logs = ref([])

// 初始化加载处理器列表
fetchAll()

// 当前分类的处理器列表
const currentProcessors = computed(() => getByCategory(currentCategory.value))

// 当前选中处理器的 params_schema
const currentSchema = computed(() => {
  const proc = currentProcessors.value.find(p => p.name === selectedProcessorName.value)
  return proc?.params_schema ?? {}
})

// 切换分类时，重置选中处理器
const handleCategoryChange = (category) => {
  currentCategory.value = category
  const procs = getByCategory(category)
  selectedProcessorName.value = procs.length > 0 ? procs[0].name : ''
  params.value = {}
}

// 切换处理器时，重置参数
const handleProcessorChange = (name) => {
  selectedProcessorName.value = name
  params.value = {}
}

// 分类下的处理器列表变化时，自动选中第一个
watch(currentProcessors, (procs) => {
  if (procs.length > 0 && !procs.find(p => p.name === selectedProcessorName.value)) {
    selectedProcessorName.value = procs[0].name
    params.value = {}
  }
}, { immediate: true })

// 是否可以提交
const canSubmit = computed(() => {
  return upload.file.value && selectedProcessorName.value && task.status.value !== 'processing'
})

// 下载信息
const downloadInfo = computed(() => {
  const files = task.outputFiles.value
  if (!files || files.length === 0) return ''
  if (files.length === 1) {
    const name = files[0].split('/').pop()
    return name
  }
  return `${files.length} 个文件`
})

// 添加日志
const addLog = (text, type = '') => {
  const now = new Date()
  const time = [now.getHours(), now.getMinutes(), now.getSeconds()]
    .map(n => String(n).padStart(2, '0')).join(':')
  logs.value.push({ time, text, type })
}

// 监听任务状态变化，自动记录日志
watch(() => task.status.value, (status) => {
  if (status === 'processing') {
    addLog(`▸ 处理器: ${selectedProcessorName.value}`, 'info')
  }
  if (status === 'completed') {
    addLog('✓ 任务完成', 'success')
  }
  if (status === 'failed') {
    addLog(`✗ 任务失败: ${task.message.value}`, 'error')
  }
})

watch(() => task.message.value, (msg) => {
  if (msg && task.status.value === 'processing') {
    addLog(`  ${msg}`)
  }
})

// 提交任务
const handleSubmit = async () => {
  if (!canSubmit.value) return

  logs.value = []
  addLog(`▸ 任务已创建`, 'info')
  resultUrl.value = ''

  try {
    await task.create({
      inputFile: upload.file.value,
      processor: selectedProcessorName.value,
      params: params.value,
    })
  } catch (err) {
    addLog(`✗ 创建任务失败: ${err.message}`, 'error')
    ElMessage.error('创建任务失败')
  }
}

// 监听任务完成，设置结果预览 URL
watch(() => task.status.value, async (status) => {
  if (status === 'completed' && task.outputFiles.value.length > 0) {
    // 用第一个输出文件作为预览
    const firstFile = task.outputFiles.value[0]
    // 通过 download API 获取结果
    try {
      const blob = await downloadResult(task.taskId.value)
      resultUrl.value = URL.createObjectURL(blob)
    } catch {
      // 预览失败不影响主流程
    }
  }
})

// 下载
const handleDownload = async () => {
  try {
    const blob = await downloadResult(task.taskId.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'result'
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    ElMessage.error('下载失败')
  }
}
</script>
```

- [ ] **Step 2: 启动验证**

```bash
# 确保 Redis + FastAPI + Celery 已启动
cd /home/huangnianzhi/tools/frontend && npm run dev
```

验证：
- 打开 http://localhost:5173
- 左面板显示：上传区 + 图片处理器卡片（5 个）+ 参数表单 + 开始处理按钮
- 右面板显示：空状态预览 + 4px 进度条 + 控制台日志
- 点击 Tab 切换到"视频处理"，处理器列表变为只有"视频截帧"，参数表单切换为视频参数
- 切换到"音频处理"，显示音频处理器（MVP 阶段无后端处理器，列表为空）
- 上传一张图片 → 文件卡片显示 → 点击"开始处理" → 进度条 + 控制台实时更新 → 完成后显示结果预览 + 下载按钮

- [ ] **Step 3: 提交**

```bash
cd /home/huangnianzhi/tools
git add frontend/src/App.vue
git commit -m "feat: 组装 App.vue，连接全部组件和数据流"
```

---

## Task 27: 端到端联调

**Files:**
- 可能修改任意前端文件以修复联调问题

- [ ] **Step 1: 启动全部服务**

四个终端，全部 `conda activate gameasset`：

```bash
# 终端 1: Redis
redis-server

# 终端 2: FastAPI
cd /home/huangnianzhi/tools/backend && uvicorn app.main:app --reload --port 8000

# 终端 3: Celery Worker
cd /home/huangnianzhi/tools/backend && celery -A app.tasks.worker worker --loglevel=info

# 终端 4: Vite
cd /home/huangnianzhi/tools/frontend && npm run dev
```

- [ ] **Step 2: 验证后端健康**

```bash
curl http://localhost:8000/api/health
# 期望: {"status":"ok"}

curl http://localhost:8000/api/processors
# 期望: 返回 6 个处理器（4 image + 1 video + 1 image.convert）
```

- [ ] **Step 3: 验证前端加载**

打开 http://localhost:5173：
- 暗色主题 + 粒子动画
- Header 显示 Logo + 三个 Tab
- 左面板：图片分类下显示 5 个处理器卡片
- 点击不同卡片，参数表单切换

- [ ] **Step 4: 测试图片处理完整流程**

1. 上传一张 PNG 图片
2. 选择"裁剪/缩放"处理器
3. 参数保持默认
4. 点击"开始处理"
5. 观察：进度条从 0 到 100%，控制台实时输出日志
6. 完成：预览区显示原图和结果对比，下载栏出现
7. 点击下载，验证文件可以下载

- [ ] **Step 5: 测试其他处理器**

重复 Step 4 测试：
- 抠图（image.cutout）
- 像素风（image.pixelate）
- 格式转换（image.convert）
- 视频截帧（切换到视频 Tab，上传视频）

- [ ] **Step 6: 测试主题切换**

- 点击月亮图标 → 亮色主题
- 所有组件颜色切换
- 刷新页面 → 主题保持
- 亮色主题下执行一次完整处理流程

- [ ] **Step 7: 测试错误场景**

- 不上传文件直接点"开始处理" → 按钮应 disabled
- 上传文件后不选处理器 → 不应出现（默认选中第一个）
- 处理中再次点击"开始处理" → 按钮 disabled

- [ ] **Step 8: 修复联调问题**

记录并修复发现的任何问题，每个修复单独提交。

- [ ] **Step 9: 提交**

```bash
cd /home/huangnianzhi/tools
git add frontend/
git commit -m "fix: 端到端联调修复"
```

---

## 自检

### 规格覆盖

| 规格要求 | 对应 Task |
|---------|-----------|
| 单页 Tab 切换 | Task 21 (AppHeader) + Task 26 (handleCategoryChange) |
| Composables 状态管理 | Task 22 (4 个 composables) |
| 自定义 CSS 控件 | Task 20 (global.css) + Task 24 (ParamForm) |
| Element Plus 仅功能性 | Task 20 (main.js) + Task 26 (ElMessage) |
| 装饰效果全部还原 | Task 20 (global.css) + Task 21 (Particles) |
| API 对接 | Task 22 (api/index.js) |
| WebSocket 进度 | Task 22 (useTask.js connectWs) |
| FileUpload 拖拽上传 | Task 23 (FileUpload.vue) |
| ProcessorGrid 分类过滤 | Task 23 (ProcessorGrid.vue) + Task 26 (computed) |
| ParamForm 动态渲染 | Task 24 (ParamForm.vue) |
| 原图/结果对比预览 | Task 25 (PreviewArea.vue) |
| 处理中遮罩 + Spinner | Task 25 (ProcessingOverlay.vue) |
| 流光进度条 | Task 25 (ProgressBar.vue) |
| 控制台日志 | Task 25 (ConsoleLog.vue) |
| 下载功能 | Task 25 (DownloadBar.vue) + Task 26 (handleDownload) |
| 主题切换 + 持久化 | Task 21 (useTheme.js) |

### Placeholder 扫描

无 TBD/TODO/等占位符。所有步骤包含完整代码。

### 类型一致性

- API 函数签名与 composables 调用一致
- Props 名称跨组件保持一致（如 `currentCategory`、`selectedName`、`schema`、`params`）
- Composable 返回值在 App.vue 中解构使用方式一致
