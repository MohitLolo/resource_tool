<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: '预览',
  },
  src: {
    type: String,
    default: '',
  },
  mimeType: {
    type: String,
    default: '',
  },
  processing: {
    type: Boolean,
    default: false,
  },
  progress: {
    type: Number,
    default: 0,
  },
})

const viewType = computed(() => {
  const type = props.mimeType.toLowerCase()
  if (type.startsWith('image/')) return 'image'
  if (type.startsWith('video/')) return 'video'
  if (type.startsWith('audio/')) return 'audio'
  return 'unknown'
})
</script>

<template>
  <section class="pane">
    <header class="pane-head">{{ title }}</header>

    <div v-if="!src" class="placeholder">暂无可预览内容</div>

    <img v-else-if="viewType === 'image'" :src="src" alt="预览图片" class="media" />

    <video v-else-if="viewType === 'video'" :src="src" controls class="media"></video>

    <audio v-else-if="viewType === 'audio'" :src="src" controls class="audio"></audio>

    <div v-else class="placeholder">暂不支持该文件类型预览</div>

    <div v-if="processing" class="overlay">
      <div class="spinner"></div>
      <p>处理中 {{ Math.max(0, Math.min(100, Number(progress || 0))) }}%</p>
    </div>
  </section>
</template>

<style scoped>
.pane {
  position: relative;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--bg-card) 72%, transparent);
  overflow: hidden;
}

.pane-head {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  color: var(--text-dim);
  font-size: 13px;
}

.placeholder {
  min-height: 180px;
  display: grid;
  place-items: center;
  color: var(--text-dim);
  padding: 16px;
}

.media {
  display: block;
  width: 100%;
  max-height: 420px;
  object-fit: contain;
  background: color-mix(in srgb, var(--bg-input) 80%, transparent);
}

.audio {
  width: calc(100% - 20px);
  margin: 10px;
}

.overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  background: color-mix(in srgb, var(--bg-deep) 70%, transparent);
  backdrop-filter: blur(2px);
}

.overlay p {
  margin: 0;
  color: var(--text);
  font-size: 13px;
}

.spinner {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 3px solid color-mix(in srgb, var(--accent) 30%, transparent);
  border-top-color: var(--accent);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
