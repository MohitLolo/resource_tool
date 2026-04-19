<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({}),
  },
  paramsSchema: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['update:modelValue', 'file-change'])

const entries = computed(() =>
  Object.entries(props.paramsSchema || {}).filter(([, config]) => shouldShowField(config)),
)
const selectedFiles = ref({})

function updateValue(key, value) {
  emit('update:modelValue', {
    ...props.modelValue,
    [key]: value,
  })
}

function onFileChange(key, event) {
  const file = event.target.files?.[0] || null
  selectedFiles.value = {
    ...selectedFiles.value,
    [key]: file?.name || '',
  }
  emit('file-change', { key, file })
  event.target.value = ''
}

function currentValue(key, config) {
  if (props.modelValue[key] !== undefined) {
    return props.modelValue[key]
  }
  return config.default
}

function shouldShowField(config) {
  const visibleWhen = config?.visible_when
  if (!visibleWhen || typeof visibleWhen !== 'object') {
    return true
  }

  return Object.entries(visibleWhen).every(([depKey, expected]) => {
    const depConfig = props.paramsSchema?.[depKey] || {}
    const actual = currentValue(depKey, depConfig)
    if (Array.isArray(expected)) {
      return expected.includes(actual)
    }
    return actual === expected
  })
}

function displayValue(value, fallback = '') {
  return value === undefined || value === null ? fallback : value
}
</script>

<template>
  <div class="param-form">
    <div v-for="[key, config] in entries" :key="key" class="form-group">
      <label class="form-label" :for="`param-${key}`">{{ config.label || key }}</label>

      <select
        v-if="config.type === 'select'"
        :id="`param-${key}`"
        class="form-control"
        :value="displayValue(currentValue(key, config), '')"
        @change="(event) => updateValue(key, event.target.value)"
      >
        <option v-if="currentValue(key, config) === undefined" value="" disabled>请选择</option>
        <option v-for="option in config.options || []" :key="String(option)" :value="option">
          {{ option }}
        </option>
      </select>

      <div v-else-if="config.type === 'slider'" class="slider-wrap">
        <input
          :id="`param-${key}`"
          class="slider"
          type="range"
          :min="config.min ?? 0"
          :max="config.max ?? 100"
          :step="config.step ?? 1"
          :value="displayValue(currentValue(key, config), config.min ?? 0)"
          @input="(event) => updateValue(key, Number(event.target.value))"
        />
        <span class="slider-value">{{ displayValue(currentValue(key, config), config.min ?? 0) }}</span>
      </div>

      <input
        v-else-if="config.type === 'number'"
        :id="`param-${key}`"
        class="form-control"
        type="number"
        :min="config.min"
        :max="config.max"
        :step="config.step ?? 1"
        :value="displayValue(currentValue(key, config), '')"
        @input="(event) => updateValue(key, Number(event.target.value))"
      />

      <label v-else-if="config.type === 'checkbox'" class="switch-wrap">
        <input
          :id="`param-${key}`"
          class="switch-input"
          type="checkbox"
          :checked="Boolean(currentValue(key, config))"
          @change="(event) => updateValue(key, Boolean(event.target.checked))"
        />
        <span class="switch-indicator"></span>
        <span class="switch-text">{{ Boolean(currentValue(key, config)) ? '开启' : '关闭' }}</span>
      </label>

      <div v-else-if="config.type === 'file'" class="file-picker">
        <input
          :id="`param-${key}`"
          class="file-input-hidden"
          type="file"
          @change="(event) => onFileChange(key, event)"
        />
        <label :for="`param-${key}`" class="file-picker-btn">选择文件</label>
        <span class="file-picker-name">
          {{ selectedFiles[key] || '未选择文件' }}
        </span>
      </div>

      <input
        v-else
        :id="`param-${key}`"
        class="form-control"
        type="text"
        :value="displayValue(currentValue(key, config), '')"
        @input="(event) => updateValue(key, event.target.value)"
      />
    </div>
  </div>
</template>

<style scoped>
.param-form {
  width: 100%;
}

.form-group + .form-group {
  margin-top: 14px;
}

.form-label {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-dim);
}

.form-control {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  color: var(--text);
  background: var(--bg-input);
  outline: none;
}

.form-control:focus {
  border-color: var(--border-active);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
}

.file-picker {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
}

.file-input-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.file-picker-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 96px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--bg-card) 78%, var(--accent) 22%),
    color-mix(in srgb, var(--bg-card) 70%, var(--accent2) 30%)
  );
  color: var(--text);
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: 0.2px;
  cursor: pointer;
  box-shadow: 0 2px 10px color-mix(in srgb, var(--accent-glow) 55%, transparent);
  transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.file-picker-btn:hover {
  border-color: var(--border-active);
  transform: translateY(-1px);
  box-shadow: 0 6px 16px color-mix(in srgb, var(--accent-glow) 78%, transparent);
}

.file-picker-name {
  flex: 1;
  min-width: 0;
  color: var(--text-dim);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.slider-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.slider {
  width: 100%;
}

.slider-value {
  min-width: 36px;
  text-align: right;
  font-size: 12px;
  color: var(--text-dim);
}

.switch-wrap {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.switch-input {
  display: none;
}

.switch-indicator {
  width: 42px;
  height: 24px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: var(--bg-input);
  position: relative;
}

.switch-indicator::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.2s ease;
}

.switch-input:checked + .switch-indicator {
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  border-color: transparent;
}

.switch-input:checked + .switch-indicator::after {
  transform: translateX(18px);
}

.switch-text {
  font-size: 12px;
  color: var(--text-dim);
}
</style>
