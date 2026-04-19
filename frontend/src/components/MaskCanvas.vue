<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  src: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['mask-ready', 'mask-clear'])

const canvasRef = ref(null)
const brushSize = ref(20)
const tool = ref('brush')
const isDrawing = ref(false)
const hasMask = ref(false)
const canvasWidth = ref(0)
const canvasHeight = ref(0)

let imageObj = null
let displayCtx = null
let maskCanvas = null
let maskCtx = null
let overlayCanvas = null
let overlayCtx = null
let lastPoint = null

function setupBuffers(width, height) {
  maskCanvas = document.createElement('canvas')
  maskCanvas.width = width
  maskCanvas.height = height
  maskCtx = maskCanvas.getContext('2d')
  maskCtx.fillStyle = '#000000'
  maskCtx.fillRect(0, 0, width, height)

  overlayCanvas = document.createElement('canvas')
  overlayCanvas.width = width
  overlayCanvas.height = height
  overlayCtx = overlayCanvas.getContext('2d')
}

function redraw() {
  if (!displayCtx || !imageObj) return
  displayCtx.clearRect(0, 0, canvasWidth.value, canvasHeight.value)
  displayCtx.drawImage(imageObj, 0, 0, canvasWidth.value, canvasHeight.value)
  displayCtx.drawImage(overlayCanvas, 0, 0, canvasWidth.value, canvasHeight.value)
}

function initCanvas() {
  if (!canvasRef.value || !props.src) return
  imageObj = new Image()
  imageObj.crossOrigin = 'anonymous'
  imageObj.onload = async () => {
    canvasWidth.value = imageObj.naturalWidth
    canvasHeight.value = imageObj.naturalHeight
    await nextTick()
    displayCtx = canvasRef.value.getContext('2d')
    setupBuffers(canvasWidth.value, canvasHeight.value)
    hasMask.value = false
    redraw()
  }
  imageObj.src = props.src
}

function getPos(event) {
  const rect = canvasRef.value.getBoundingClientRect()
  const scaleX = canvasWidth.value / rect.width
  const scaleY = canvasHeight.value / rect.height
  const clientX = event.touches ? event.touches[0].clientX : event.clientX
  const clientY = event.touches ? event.touches[0].clientY : event.clientY
  return {
    x: (clientX - rect.left) * scaleX,
    y: (clientY - rect.top) * scaleY,
  }
}

function drawLine(ctx, from, to, color, width) {
  ctx.globalCompositeOperation = color === 'erase' ? 'destination-out' : 'source-over'
  ctx.strokeStyle = color === 'erase' ? 'rgba(0,0,0,1)' : color
  ctx.lineWidth = width
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.beginPath()
  ctx.moveTo(from.x, from.y)
  ctx.lineTo(to.x, to.y)
  ctx.stroke()
}

function startDraw(event) {
  if (props.disabled || !displayCtx || !maskCtx || !overlayCtx) return
  event.preventDefault()
  isDrawing.value = true
  lastPoint = getPos(event)
}

function draw(event) {
  if (!isDrawing.value || !lastPoint) return
  event.preventDefault()
  const point = getPos(event)

  if (tool.value === 'eraser') {
    drawLine(maskCtx, lastPoint, point, 'erase', brushSize.value)
    drawLine(overlayCtx, lastPoint, point, 'erase', brushSize.value)
  } else {
    drawLine(maskCtx, lastPoint, point, '#ffffff', brushSize.value)
    drawLine(overlayCtx, lastPoint, point, 'rgba(255, 50, 50, 0.62)', brushSize.value)
    hasMask.value = true
  }
  lastPoint = point
  redraw()
}

function endDraw() {
  isDrawing.value = false
  lastPoint = null
}

function clearMask() {
  if (!maskCtx || !overlayCtx) return
  maskCtx.globalCompositeOperation = 'source-over'
  maskCtx.fillStyle = '#000000'
  maskCtx.fillRect(0, 0, canvasWidth.value, canvasHeight.value)
  overlayCtx.clearRect(0, 0, canvasWidth.value, canvasHeight.value)
  hasMask.value = false
  redraw()
  emit('mask-clear')
}

function confirmMask() {
  if (!maskCanvas || !hasMask.value) return
  maskCanvas.toBlob((blob) => {
    if (!blob) return
    emit('mask-ready', new File([blob], 'mask.png', { type: 'image/png' }))
  }, 'image/png')
}

function onWheel(event) {
  event.preventDefault()
  const delta = event.deltaY > 0 ? -2 : 2
  brushSize.value = Math.max(5, Math.min(50, brushSize.value + delta))
}

watch(
  () => props.src,
  () => {
    hasMask.value = false
    initCanvas()
  },
)

onMounted(() => {
  initCanvas()
})

onBeforeUnmount(() => {
  if (imageObj) {
    imageObj.onload = null
    imageObj = null
  }
})
</script>

<template>
  <div class="mask-canvas-wrapper" :class="{ disabled }">
    <div v-if="src" class="toolbar">
      <label class="toolbar-item">
        <span class="toolbar-label">画笔大小</span>
        <input
          class="brush-slider"
          type="range"
          min="5"
          max="50"
          :value="brushSize"
          @input="brushSize = Number($event.target.value)"
        />
        <span class="toolbar-value">{{ brushSize }}px</span>
      </label>

      <div class="toolbar-group">
        <button type="button" class="tool-btn" :class="{ active: tool === 'brush' }" @click="tool = 'brush'">画笔</button>
        <button type="button" class="tool-btn" :class="{ active: tool === 'eraser' }" @click="tool = 'eraser'">橡皮擦</button>
      </div>

      <button type="button" class="tool-btn" :disabled="disabled" @click="clearMask">清除全部</button>
      <button type="button" class="tool-btn primary" :disabled="disabled || !hasMask" @click="confirmMask">确认遮罩</button>
    </div>

    <div class="canvas-container">
      <canvas
        ref="canvasRef"
        :width="canvasWidth"
        :height="canvasHeight"
        @mousedown="startDraw"
        @mousemove="draw"
        @mouseup="endDraw"
        @mouseleave="endDraw"
        @touchstart="startDraw"
        @touchmove="draw"
        @touchend="endDraw"
        @wheel="onWheel"
        :class="{ 'cursor-brush': tool === 'brush', 'cursor-eraser': tool === 'eraser' }"
      ></canvas>
    </div>
  </div>
</template>

<style scoped>
.mask-canvas-wrapper { width: 100%; }
.mask-canvas-wrapper.disabled { opacity: 0.5; pointer-events: none; }

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  margin-bottom: 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--bg-card) 90%, transparent);
  flex-wrap: wrap;
}

.toolbar-item { display: flex; align-items: center; gap: 6px; cursor: default; }
.toolbar-label, .toolbar-value { font-size: 12px; color: var(--text-dim); white-space: nowrap; }
.brush-slider { width: 90px; }
.toolbar-group { display: flex; gap: 3px; }

.tool-btn {
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text);
  cursor: pointer;
  transition: all 0.15s ease;
}
.tool-btn:hover:not(:disabled) { border-color: var(--border-active); }
.tool-btn.active,
.tool-btn.primary {
  border-color: transparent;
  color: #fff;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
}
.tool-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.canvas-container {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  background: color-mix(in srgb, var(--bg-input) 80%, transparent);
}

canvas {
  width: 100%;
  max-height: 420px;
  display: block;
  object-fit: contain;
}

.cursor-brush { cursor: crosshair; }
.cursor-eraser { cursor: cell; }
</style>
