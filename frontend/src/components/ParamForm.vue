<script setup>
import { computed } from 'vue'

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

const entries = computed(() => Object.entries(props.paramsSchema || {}))

function updateValue(key, value) {
  emit('update:modelValue', {
    ...props.modelValue,
    [key]: value,
  })
}

function onFileChange(key, event) {
  const file = event.target.files?.[0] || null
  emit('file-change', { key, file })
  event.target.value = ''
}

function currentValue(key, config) {
  if (props.modelValue[key] !== undefined) {
    return props.modelValue[key]
  }
  return config.default
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

      <input
        v-else-if="config.type === 'file'"
        :id="`param-${key}`"
        class="form-control file-input"
        type="file"
        @change="(event) => onFileChange(key, event)"
      />

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

.file-input {
  padding: 8px;
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
