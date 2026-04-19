<script setup>
import { computed } from 'vue'

const props = defineProps({
  progress: {
    type: Number,
    default: 0,
  },
  status: {
    type: String,
    default: 'idle',
  },
  message: {
    type: String,
    default: '',
  },
  logs: {
    type: Array,
    default: () => [],
  },
})

const statusText = computed(() => {
  const map = {
    idle: '空闲',
    connected: '已连接',
    pending: '等待中',
    processing: '处理中',
    completed: '已完成',
    failed: '失败',
    canceled: '已取消',
  }
  return map[props.status] || props.status || '未知'
})

const boundedProgress = computed(() => {
  const value = Number(props.progress || 0)
  if (Number.isNaN(value)) return 0
  return Math.max(0, Math.min(100, value))
})
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <strong>处理进度</strong>
      <span class="status">{{ statusText }}</span>
    </header>

    <div class="progress-track" role="progressbar" :aria-valuenow="boundedProgress" aria-valuemin="0" aria-valuemax="100">
      <div class="progress-fill" :style="{ width: `${boundedProgress}%` }"></div>
    </div>
    <p class="message">{{ message || '等待任务开始...' }}</p>

    <div class="logs" role="log" aria-label="处理日志">
      <p v-if="logs.length === 0" class="empty">暂无日志</p>
      <p v-for="(item, idx) in logs" :key="idx" class="line">{{ item }}</p>
    </div>
  </section>
</template>

<style scoped>
.panel {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px;
  background: color-mix(in srgb, var(--bg-card) 70%, transparent);
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.status {
  font-size: 12px;
  color: var(--text-dim);
}

.progress-track {
  width: 100%;
  height: 4px;
  border-radius: 999px;
  overflow: hidden;
  background: color-mix(in srgb, var(--bg-input) 90%, transparent);
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background:
    linear-gradient(90deg, var(--accent), var(--accent2)),
    linear-gradient(120deg, transparent 30%, rgba(255, 255, 255, 0.5) 50%, transparent 70%);
  background-size: 100% 100%, 28px 100%;
  animation: flow 1s linear infinite;
  transition: width 0.25s ease;
}

.message {
  margin: 10px 0 12px;
  color: var(--text-dim);
}

.logs {
  border: 1px solid var(--border);
  border-radius: 10px;
  min-height: 160px;
  max-height: 160px;
  overflow: auto;
  padding: 10px;
  background: color-mix(in srgb, var(--bg-input) 88%, transparent);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.empty,
.line {
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
}

.empty {
  color: var(--text-dim);
}

.line + .line {
  margin-top: 6px;
}

@keyframes flow {
  to {
    background-position: 0 0, 28px 0;
  }
}
</style>
