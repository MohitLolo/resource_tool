<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import FileUpload from '../components/FileUpload.vue'
import ParamForm from '../components/ParamForm.vue'
import PreviewPane from '../components/PreviewPane.vue'
import ProgressPanel from '../components/ProgressPanel.vue'
import { createTask, deleteTask, downloadResult, getProcessors, getTask } from '../api'
import { useWebSocket } from '../composables/useWebSocket'

const route = useRoute()
const router = useRouter()

const selectedFile = ref(null)
const processors = ref([])
const selectedProcessorName = ref('')
const params = ref({})
const extraFileMap = ref({})

const taskId = ref('')
const taskInfo = ref(null)
const running = ref(false)
const logs = ref([])
const notice = ref('')

const sourcePreview = ref({ src: '', mimeType: '' })
const resultPreview = ref({ src: '', mimeType: '' })

const pollTimer = ref(null)
const fallbackEnabled = ref(false)
const fallbackErrorCount = ref(0)
const switchingLocked = ref(false)
const lastStableCategory = ref('image')

const ws = useWebSocket('')
const terminalStatuses = new Set(['completed', 'failed', 'canceled'])
const processorIcons = {
  'image.watermark': '🩹',
  'image.cutout': '✂️',
  'image.crop': '📐',
  'image.pixelate': '🧩',
  'image.convert': '🔁',
  'video.extract_frames': '🎞️',
}

const currentCategory = computed(() => {
  if (route.path.startsWith('/video')) return 'video'
  if (route.path.startsWith('/audio')) return 'audio'
  return 'image'
})

const categoryMeta = computed(() => {
  const map = {
    image: {
      title: '图片任务',
      accept: 'image/*',
      emptyProcessor: '当前无图片处理器',
      sourceTitle: '原图预览',
      resultTitle: '结果预览',
    },
    video: {
      title: '视频任务',
      accept: 'video/*',
      emptyProcessor: '当前无视频处理器',
      sourceTitle: '输入视频',
      resultTitle: '结果说明',
    },
    audio: {
      title: '音频任务',
      accept: 'audio/*',
      emptyProcessor: '当前无音频处理器',
      sourceTitle: '输入音频',
      resultTitle: '结果说明',
    },
  }
  return map[currentCategory.value]
})

const selectedProcessor = computed(() =>
  processors.value.find((item) => item.name === selectedProcessorName.value) || null,
)
const paramsSchema = computed(() => selectedProcessor.value?.params_schema || {})
const hasProcessors = computed(() => processors.value.length > 0)
const canDownload = computed(() => taskInfo.value?.status === 'completed')
const isImageMode = computed(() => currentCategory.value === 'image')

function appendLog(text) {
  if (!text) return
  logs.value.push(`[${new Date().toLocaleTimeString()}] ${text}`)
}

function pushNotice(text) {
  notice.value = text
  appendLog(`提示: ${text}`)
}

function clearPoll() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
  fallbackErrorCount.value = 0
}

function startFallbackPolling() {
  if (pollTimer.value || fallbackEnabled.value || !running.value || !taskId.value) return
  fallbackEnabled.value = true
  fallbackErrorCount.value = 0
  appendLog('WebSocket 异常，启用轮询兜底')
  pollTimer.value = setInterval(async () => {
    const ok = await refreshTask()
    if (!ok) {
      fallbackErrorCount.value += 1
      if (fallbackErrorCount.value >= 5) {
        appendLog('轮询连续失败，已自动停止兜底轮询')
        fallbackEnabled.value = false
        clearPoll()
      }
      return
    }
    fallbackErrorCount.value = 0
    if (terminalStatuses.has(taskInfo.value?.status)) {
      clearPoll()
      fallbackEnabled.value = false
    }
  }, 1500)
}

function resetResultPreview() {
  if (resultPreview.value.src?.startsWith('blob:')) {
    URL.revokeObjectURL(resultPreview.value.src)
  }
  resultPreview.value = { src: '', mimeType: '' }
}

function updateSourcePreview(file) {
  if (sourcePreview.value.src?.startsWith('blob:')) {
    URL.revokeObjectURL(sourcePreview.value.src)
  }
  if (!file) {
    sourcePreview.value = { src: '', mimeType: '' }
    return
  }

  sourcePreview.value = {
    src: URL.createObjectURL(file),
    mimeType: file.type || (currentCategory.value === 'video' ? 'video/mp4' : 'audio/mpeg'),
  }
}

function resetCategoryState() {
  selectedFile.value = null
  processors.value = []
  selectedProcessorName.value = ''
  params.value = {}
  extraFileMap.value = {}
  taskId.value = ''
  taskInfo.value = null
  running.value = false
  logs.value = []
  notice.value = ''
  ws.disconnect()
  ws.progress.value = 0
  ws.message.value = ''
  ws.status.value = 'idle'
  fallbackEnabled.value = false
  clearPoll()
  resetResultPreview()
  if (sourcePreview.value.src?.startsWith('blob:')) {
    URL.revokeObjectURL(sourcePreview.value.src)
  }
  sourcePreview.value = { src: '', mimeType: '' }
}

async function loadProcessors() {
  processors.value = await getProcessors(currentCategory.value)
  if (processors.value.length > 0) {
    selectedProcessorName.value = processors.value[0].name
  }
}

function onProcessorChange(name) {
  selectedProcessorName.value = name
  params.value = {}
  extraFileMap.value = {}
}

function onParamFileChange({ key, file }) {
  extraFileMap.value = {
    ...extraFileMap.value,
    [key]: file,
  }
  if (!file) {
    delete extraFileMap.value[key]
  }
}

function buildTaskPayload() {
  const payloadParams = { ...params.value }
  const extraFiles = []

  for (const [key, file] of Object.entries(extraFileMap.value)) {
    if (!file) continue
    extraFiles.push(file)
    payloadParams[`${key}_key`] = file.name
  }

  return { payloadParams, extraFiles }
}

async function refreshTask() {
  if (!taskId.value) return
  try {
    taskInfo.value = await getTask(taskId.value)
    return true
  } catch (error) {
    appendLog(`任务查询失败: ${error}`)
    return false
  }
}

async function previewAndCacheResult() {
  if (!taskId.value || taskInfo.value?.status !== 'completed' || !isImageMode.value) {
    return
  }
  try {
    const { blob } = await downloadResult(taskId.value)
    resetResultPreview()
    resultPreview.value = {
      src: URL.createObjectURL(blob),
      mimeType: blob.type || 'application/octet-stream',
    }
  } catch (error) {
    appendLog(`结果预览加载失败: ${error}`)
  }
}

async function submitTask() {
  notice.value = ''
  if (!hasProcessors.value) {
    pushNotice(categoryMeta.value.emptyProcessor)
    return
  }
  if (!selectedFile.value) {
    pushNotice('请先选择输入文件')
    return
  }
  if (!selectedProcessorName.value) {
    pushNotice('请先选择处理器')
    return
  }

  logs.value = []
  taskInfo.value = null
  resetResultPreview()
  const { payloadParams, extraFiles } = buildTaskPayload()

  try {
    running.value = true
    const result = await createTask(
      selectedFile.value,
      selectedProcessorName.value,
      payloadParams,
      extraFiles,
    )
    taskId.value = result.task_id
    appendLog(`任务已创建: ${taskId.value}`)

    ws.progress.value = 0
    ws.message.value = '任务已提交'
    ws.status.value = 'pending'
    ws.connect(taskId.value)

    await refreshTask()
  } catch (error) {
    running.value = false
    appendLog(`任务提交失败: ${error}`)
    pushNotice('任务提交失败')
  }
}

async function cancelTask() {
  if (!taskId.value) return
  try {
    await deleteTask(taskId.value)
    appendLog('任务已取消')
    await refreshTask()
  } catch (error) {
    appendLog(`任务取消失败: ${error}`)
  } finally {
    running.value = false
    ws.disconnect()
    fallbackEnabled.value = false
    clearPoll()
  }
}

async function downloadTaskResult() {
  notice.value = ''
  if (!taskId.value) {
    pushNotice('当前无可下载任务')
    return
  }
  try {
    const { blob, filename } = await downloadResult(taskId.value)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    anchor.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    appendLog(`下载失败: ${error}`)
    pushNotice('下载失败')
  }
}

watch(
  () => selectedFile.value,
  (file) => {
    updateSourcePreview(file)
  },
)

watch(
  () => [ws.progress.value, ws.message.value, ws.status.value],
  async ([progress, message, status], [prevProgress, prevMessage, prevStatus]) => {
    if (message && (message !== prevMessage || status !== prevStatus || progress !== prevProgress)) {
      appendLog(`${status || 'processing'} | ${progress}% | ${message}`)
    }

    if (terminalStatuses.has(status)) {
      running.value = false
      fallbackEnabled.value = false
      clearPoll()
      await refreshTask()
      await previewAndCacheResult()
    }
  },
)

watch(
  () => ws.error.value,
  (error) => {
    if (error) {
      appendLog(error)
      startFallbackPolling()
    }
  },
)

watch(
  () => currentCategory.value,
  async (newCategory, oldCategory) => {
    if (switchingLocked.value) {
      return
    }
    if (oldCategory) {
      lastStableCategory.value = oldCategory
    }
    if (running.value && taskId.value) {
      pushNotice('当前任务处理中，请完成后再切换分类')
      switchingLocked.value = true
      await router.replace(`/${lastStableCategory.value}`)
      switchingLocked.value = false
      return
    }
    resetCategoryState()
    try {
      await loadProcessors()
    } catch (error) {
      pushNotice(`加载处理器失败: ${error}`)
    }
  },
)

onMounted(async () => {
  try {
    await loadProcessors()
  } catch (error) {
    pushNotice(`加载处理器失败: ${error}`)
  }
})

onBeforeUnmount(() => {
  clearPoll()
  ws.disconnect()
  if (sourcePreview.value.src?.startsWith('blob:')) {
    URL.revokeObjectURL(sourcePreview.value.src)
  }
  resetResultPreview()
})
</script>

<template>
  <div class="tool-layout">
    <section class="left-panel">
      <div class="panel-section">
        <h2 class="panel-title">{{ categoryMeta.title }}</h2>
      </div>

      <div class="panel-section">
        <p class="section-title">上传文件</p>
        <FileUpload v-model="selectedFile" :accept="categoryMeta.accept" @error="pushNotice" />
      </div>

      <div class="panel-section">
        <p class="section-title">处理器</p>
        <div v-if="hasProcessors" class="processor-grid">
          <button
            v-for="item in processors"
            :key="item.name"
            type="button"
            class="processor-card"
            :class="{ active: selectedProcessorName === item.name }"
            @click="onProcessorChange(item.name)"
          >
            <div class="proc-icon">{{ processorIcons[item.name] || '⚙️' }}</div>
            <div class="proc-name">{{ item.label }}</div>
          </button>
        </div>
        <div v-else class="notice warning">{{ categoryMeta.emptyProcessor }}</div>
      </div>

      <div class="panel-section">
        <p class="section-title">参数设置</p>
        <ParamForm v-model="params" :params-schema="paramsSchema" @file-change="onParamFileChange" />
      </div>

      <div class="panel-section">
        <div v-if="notice" class="notice warning">{{ notice }}</div>
        <div class="action-row">
          <button type="button" class="btn btn-primary" :disabled="running || !hasProcessors" @click="submitTask">
            {{ running ? '处理中...' : '开始处理' }}
          </button>
          <button type="button" class="btn" :disabled="!taskId || !running" @click="cancelTask">取消任务</button>
        </div>
      </div>
    </section>

    <section class="right-panel">
      <div class="preview-grid">
        <PreviewPane
          :title="categoryMeta.sourceTitle"
          :src="sourcePreview.src"
          :mime-type="sourcePreview.mimeType"
          :processing="running"
          :progress="ws.progress.value"
        />
        <PreviewPane
          :title="categoryMeta.resultTitle"
          :src="isImageMode ? resultPreview.src : ''"
          :mime-type="isImageMode ? resultPreview.mimeType : 'application/octet-stream'"
          :processing="running"
          :progress="ws.progress.value"
        />
      </div>

      <ProgressPanel
        :progress="ws.progress.value"
        :status="ws.status.value"
        :message="ws.message.value"
        :logs="logs"
      />

      <div class="download-bar">
        <div class="download-info">任务 ID: {{ taskId || '未创建' }}</div>
        <button type="button" class="btn" :disabled="!canDownload" @click="downloadTaskResult">下载结果</button>
      </div>
    </section>
  </div>
</template>
