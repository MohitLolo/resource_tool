<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  modelValue: {
    type: [File, Object, null],
    default: null,
  },
  maxSize: {
    type: Number,
    default: 500 * 1024 * 1024,
  },
  accept: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue', 'error'])

const dragOver = ref(false)
const picker = ref(null)

const maxSizeText = computed(() => `${Math.round(props.maxSize / 1024 / 1024)}MB`)

function validateAndEmit(file) {
  if (!file) return
  if (file.size > props.maxSize) {
    emit('error', `文件大小超过限制（${maxSizeText.value}）`)
    return
  }
  emit('update:modelValue', file)
}

function onInputChange(event) {
  const file = event.target.files?.[0]
  validateAndEmit(file)
  event.target.value = ''
}

function onDrop(event) {
  event.preventDefault()
  dragOver.value = false
  const file = event.dataTransfer?.files?.[0]
  validateAndEmit(file)
}

function openPicker() {
  picker.value?.click()
}

function clearFile() {
  emit('update:modelValue', null)
}

function readableSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const size = Number(bytes)
  const idx = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1)
  return `${(size / 1024 ** idx).toFixed(idx === 0 ? 0 : 1)} ${units[idx]}`
}
</script>

<template>
  <div class="file-upload">
    <button
      type="button"
      class="upload-zone"
      :class="{ dragover: dragOver }"
      @click="openPicker"
      @dragover.prevent="dragOver = true"
      @dragleave.prevent="dragOver = false"
      @drop="onDrop"
    >
      <span class="icon">⬆</span>
      <p>拖拽文件到此处，或 <em>点击上传</em></p>
      <p class="hint">单文件上传，最大 {{ maxSizeText }}</p>
    </button>

    <input ref="picker" class="picker" type="file" :accept="accept" @change="onInputChange" />

    <div v-if="modelValue" class="file-card">
      <div class="file-thumb">📄</div>
      <div class="file-info">
        <p class="file-name">{{ modelValue.name || '未命名文件' }}</p>
        <p class="file-meta">{{ readableSize(modelValue.size) }}</p>
      </div>
      <button type="button" class="file-remove" @click="clearFile">移除</button>
    </div>
  </div>
</template>

<style scoped>
.picker {
  display: none;
}

.upload-zone {
  width: 100%;
  border: 2px dashed var(--border);
  border-radius: var(--radius);
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.25s ease;
  color: var(--text-dim);
  background: var(--bg-card);
}

.upload-zone:hover,
.upload-zone.dragover {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, var(--bg-card));
  box-shadow: 0 0 20px var(--accent-glow);
}

.icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  margin-bottom: 8px;
  border-radius: 50%;
  color: #fff;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  box-shadow: 0 0 20px var(--accent-glow);
}

.upload-zone p {
  margin: 0;
}

.upload-zone em {
  color: var(--accent);
  font-style: normal;
}

.hint {
  margin-top: 6px;
  font-size: 12px;
}

.file-card {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-card);
}

.file-thumb {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: var(--bg-input);
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  margin: 0;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--text-dim);
}

.file-remove {
  border: 0;
  border-radius: 8px;
  background: rgba(248, 113, 113, 0.18);
  color: var(--danger);
  padding: 6px 10px;
  cursor: pointer;
}
</style>
