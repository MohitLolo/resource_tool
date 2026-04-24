<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import FileUpload from '../components/FileUpload.vue'
import MaskCanvas from '../components/MaskCanvas.vue'
import ParamForm from '../components/ParamForm.vue'
import PreviewPane from '../components/PreviewPane.vue'
import ProgressPanel from '../components/ProgressPanel.vue'
import {
  createTask,
  deleteTask,
  downloadResult,
  downloadTaskOutput,
  getProcessors,
  getTask,
} from '../api'
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
const resultSummary = ref('')
const sampledResultThumbs = ref([])
const maskFile = ref(null)
const maskConfirmed = ref(false)

const pollTimer = ref(null)
const fallbackEnabled = ref(false)
const fallbackErrorCount = ref(0)
const switchingLocked = ref(false)
const lastStableCategory = ref('image')

const ws = useWebSocket('')
const terminalStatuses = new Set(['completed', 'failed', 'canceled'])
const ACTIVE_TASK_STORAGE_KEY = 'ga_active_task_v1'
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
const isManualWatermark = computed(
  () => selectedProcessorName.value === 'image.watermark' && params.value.mode === 'manual',
)

function hashString(input) {
  let hash = 2166136261
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i)
    hash +=
      (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24)
  }
  return (hash >>> 0).toString(36)
}

function buildIdempotencyKey(file, processorName, payloadParams) {
  if (!file || !processorName) return ''
  const signature = JSON.stringify({
    p: processorName,
    n: file.name || '',
    s: file.size || 0,
    m: file.lastModified || 0,
    t: file.type || '',
    params: payloadParams || {},
  })
  return `ga:${currentCategory.value}:${hashString(signature)}`
}

function persistActiveTask() {
  if (!taskId.value || !running.value) return
  const payload = {
    taskId: taskId.value,
    category: currentCategory.value,
    processorName: selectedProcessorName.value,
    savedAt: Date.now(),
  }
  sessionStorage.setItem(ACTIVE_TASK_STORAGE_KEY, JSON.stringify(payload))
}

function clearPersistedActiveTask() {
  sessionStorage.removeItem(ACTIVE_TASK_STORAGE_KEY)
}

async function restoreActiveTaskIfNeeded() {
  const raw = sessionStorage.getItem(ACTIVE_TASK_STORAGE_KEY)
  if (!raw || taskId.value || running.value) return
  let parsed = null
  try {
    parsed = JSON.parse(raw)
  } catch {
    clearPersistedActiveTask()
    return
  }
  if (!parsed?.taskId || parsed?.category !== currentCategory.value) return
  if (parsed?.processorName && processors.value.some((item) => item.name === parsed.processorName)) {
    selectedProcessorName.value = parsed.processorName
  }

  taskId.value = parsed.taskId
  const ok = await refreshTask()
  if (!ok || !taskInfo.value) {
    clearPersistedActiveTask()
    taskId.value = ''
    return
  }

  if (terminalStatuses.has(taskInfo.value.status)) {
    running.value = false
    clearPersistedActiveTask()
    buildResultSummary()
    await previewAndCacheResult()
    await loadSampledResultThumbs()
    appendLog(`已恢复历史任务: ${taskId.value} (${taskInfo.value.status})`)
    return
  }

  running.value = true
  ws.progress.value = taskInfo.value.progress || 0
  ws.message.value = taskInfo.value.message || '任务处理中'
  ws.status.value = taskInfo.value.status || 'processing'
  ws.connect(taskId.value)
  appendLog(`已恢复未完成任务: ${taskId.value}`)
}

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

function resetSampledThumbs() {
  for (const item of sampledResultThumbs.value) {
    if (item.src?.startsWith('blob:')) {
      URL.revokeObjectURL(item.src)
    }
  }
  sampledResultThumbs.value = []
}

function filenameOf(path) {
  return String(path || '')
    .split('/')
    .pop()
}

function buildResultSummary() {
  const info = taskInfo.value
  if (!info) {
    resultSummary.value = ''
    return
  }
  const outputs = Array.isArray(info.output_files) ? info.output_files : []
  if (info.status !== 'completed') {
    resultSummary.value = info.message || '任务处理中'
    return
  }
  if (outputs.length === 0) {
    resultSummary.value = '任务完成，但无输出文件'
    return
  }
  const firstNames = outputs.slice(0, 3).map(filenameOf).join('、')
  const suffix = outputs.length > 3 ? ' ...' : ''
  const sampledHint =
    currentCategory.value === 'video' && selectedProcessorName.value === 'video.extract_frames'
      ? `；共 ${outputs.length} 帧，已按时间均匀抽样展示 ${Math.min(outputs.length, 6)} 帧缩略图`
      : ''
  resultSummary.value = `已生成 ${outputs.length} 个文件：${firstNames}${suffix}${sampledHint}`
}

function buildSampleIndexes(total, maxCount = 6) {
  if (total <= 0) return []
  if (total <= maxCount) {
    return Array.from({ length: total }, (_, idx) => idx)
  }
  const step = (total - 1) / (maxCount - 1)
  const indexes = []
  for (let i = 0; i < maxCount; i += 1) {
    indexes.push(Math.round(i * step))
  }
  return [...new Set(indexes)]
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
  resetSampledThumbs()
  resultSummary.value = ''
  maskFile.value = null
  maskConfirmed.value = false
  if (sourcePreview.value.src?.startsWith('blob:')) {
    URL.revokeObjectURL(sourcePreview.value.src)
  }
  sourcePreview.value = { src: '', mimeType: '' }
  clearPersistedActiveTask()
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
  maskFile.value = null
  maskConfirmed.value = false
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

function buildTaskPayload() {
  const payloadParams = { ...params.value }
  for (const [key, config] of Object.entries(paramsSchema.value)) {
    if (payloadParams[key] === undefined && config.default !== undefined) {
      payloadParams[key] = config.default
    }
  }
  const extraFiles = []

  for (const [key, file] of Object.entries(extraFileMap.value)) {
    if (!file) continue
    extraFiles.push(file)
    payloadParams[`${key}_key`] = file.name
  }

  if (maskFile.value && isManualWatermark.value) {
    payloadParams.mask_file_key = 'mask_file'
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
  if (!taskId.value || taskInfo.value?.status !== 'completed') {
    return
  }
  if (!isImageMode.value) {
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

async function loadSampledResultThumbs() {
  resetSampledThumbs()
  if (currentCategory.value !== 'video') return
  if (!taskInfo.value || taskInfo.value.status !== 'completed') return
  if (selectedProcessorName.value !== 'video.extract_frames') return

  const outputs = Array.isArray(taskInfo.value.output_files) ? taskInfo.value.output_files : []
  const sampleIndexes = buildSampleIndexes(outputs.length, 6)
  const thumbs = []
  for (const index of sampleIndexes) {
    try {
      const { blob, filename } = await downloadTaskOutput(taskId.value, index)
      const mimeType = blob.type || ''
      if (!mimeType.startsWith('image/')) {
        continue
      }
      thumbs.push({
        src: URL.createObjectURL(blob),
        name: filename || filenameOf(outputs[index]),
      })
    } catch (error) {
      appendLog(`缩略图加载失败(index=${index}): ${error}`)
    }
  }
  sampledResultThumbs.value = thumbs
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
  resetSampledThumbs()
  resultSummary.value = ''
  if (isManualWatermark.value && !maskConfirmed.value) {
    pushNotice('请先在右侧画布确认遮罩')
    return
  }
  const { payloadParams, extraFiles } = buildTaskPayload()
  const idempotencyKey = buildIdempotencyKey(
    selectedFile.value,
    selectedProcessorName.value,
    payloadParams,
  )

  try {
    running.value = true
    const result = await createTask(
      selectedFile.value,
      selectedProcessorName.value,
      payloadParams,
      extraFiles,
      { idempotencyKey },
    )
    taskId.value = result.task_id
    appendLog(`任务已创建: ${taskId.value}`)
    if (result.reused) {
      appendLog('检测到重复提交，已复用已有任务')
    }
    persistActiveTask()

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
    clearPersistedActiveTask()
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
  () => isManualWatermark.value,
  (manual) => {
    if (manual) return
    onMaskClear()
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
      clearPersistedActiveTask()
      fallbackEnabled.value = false
      clearPoll()
      await refreshTask()
      buildResultSummary()
      await previewAndCacheResult()
      await loadSampledResultThumbs()
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
    await restoreActiveTaskIfNeeded()
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
  resetSampledThumbs()
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
      <div v-if="isManualWatermark && sourcePreview.src" class="panel-section mask-section">
        <p class="section-title">涂抹水印区域</p>
        <MaskCanvas :src="sourcePreview.src" :disabled="running" @mask-ready="onMaskReady" @mask-clear="onMaskClear" />
        <div v-if="maskConfirmed" class="mask-hint">遮罩已确认，可以开始处理</div>
      </div>

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

      <section v-if="!isImageMode" class="result-note">
        <header class="result-note-head">结果说明</header>
        <p class="result-note-text">
          {{ resultSummary || '任务完成后将显示输出文件数量与样例信息。' }}
        </p>
        <div v-if="sampledResultThumbs.length > 0" class="thumb-grid">
          <figure v-for="item in sampledResultThumbs" :key="item.src" class="thumb-item">
            <img :src="item.src" :alt="item.name" class="thumb-image" />
            <figcaption class="thumb-name">{{ item.name }}</figcaption>
          </figure>
        </div>
      </section>

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

<style scoped>
.result-note {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 14px;
  background: color-mix(in srgb, var(--bg-card) 68%, transparent);
}

.result-note-head {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 8px;
}

.result-note-text {
  margin: 0;
  color: var(--text-dim);
  font-size: 13px;
  line-height: 1.5;
}

.thumb-grid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.thumb-item {
  margin: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: color-mix(in srgb, var(--bg-input) 86%, transparent);
}

.thumb-image {
  width: 100%;
  display: block;
  aspect-ratio: 16 / 9;
  object-fit: cover;
}

.thumb-name {
  margin: 0;
  padding: 6px 8px;
  font-size: 11px;
  color: var(--text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

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

@media (max-width: 1024px) {
  .thumb-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
