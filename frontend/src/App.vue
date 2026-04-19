<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()
const isLight = ref(false)

const particles = Array.from({ length: 20 }, (_, index) => ({
  id: index,
  left: `${(index * 73) % 100}%`,
  delay: `${(index % 10) * 0.7}s`,
  duration: `${10 + (index % 6) * 3}s`,
  size: `${2 + (index % 4)}px`,
}))

const tabs = [
  {
    to: '/image',
    label: '图片处理',
    iconPath:
      'M3 5.5A2.5 2.5 0 0 1 5.5 3h13A2.5 2.5 0 0 1 21 5.5v13a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 18.5z M7.4 15.5l2.8-3.2 2.2 2.3 2.6-3.4 3 4.3',
  },
  {
    to: '/video',
    label: '视频处理',
    iconPath: 'M4 6.5A2.5 2.5 0 0 1 6.5 4h8A2.5 2.5 0 0 1 17 6.5v11a2.5 2.5 0 0 1-2.5 2.5h-8A2.5 2.5 0 0 1 4 17.5z M17 10.5l3.8-2.1v7.2L17 13.5',
  },
  {
    to: '/audio',
    label: '音频处理',
    iconPath: 'M12 5v10.2a3.3 3.3 0 1 1-1.6-2.8V7.2l7.2-1.6v7.3a3.3 3.3 0 1 1-1.6-2.8V4.1z',
  },
]

const currentTab = computed(() => tabs.find((item) => route.path.startsWith(item.to))?.to || '/image')

function applyTheme(light) {
  const root = document.documentElement
  if (light) {
    root.classList.add('light')
  } else {
    root.classList.remove('light')
  }
}

function toggleTheme() {
  isLight.value = !isLight.value
  applyTheme(isLight.value)
  localStorage.setItem('ga_theme', isLight.value ? 'light' : 'dark')
}

onMounted(() => {
  const saved = localStorage.getItem('ga_theme')
  isLight.value = saved === 'light'
  applyTheme(isLight.value)
})
</script>

<template>
  <div class="app-shell">
    <header class="top-nav">
      <div class="brand">
        <svg class="brand-logo" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M7 3.5h10L22 12l-5 8.5H7L2 12z" stroke="url(#brandGradient)" stroke-width="1.8" />
          <path d="M8.8 13.2l2.2 2.1 4.5-5" stroke="url(#brandGradient)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          <defs>
            <linearGradient id="brandGradient" x1="4" y1="4" x2="20" y2="20" gradientUnits="userSpaceOnUse">
              <stop stop-color="var(--accent)" />
              <stop offset="1" stop-color="var(--accent2)" />
            </linearGradient>
          </defs>
        </svg>
        <span class="brand-text">GameAsset 素材工具箱</span>
      </div>

      <nav class="tabs" aria-label="主导航">
        <RouterLink
          v-for="item in tabs"
          :key="item.to"
          :to="item.to"
          class="tab"
          :class="{ active: currentTab === item.to }"
        >
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path :d="item.iconPath" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          {{ item.label }}
        </RouterLink>
      </nav>

      <div class="header-actions">
        <button type="button" class="icon-btn" @click="toggleTheme">
          {{ isLight ? '☀' : '☾' }}
        </button>
      </div>
    </header>

    <main class="content">
      <div class="particles" aria-hidden="true">
        <span
          v-for="item in particles"
          :key="item.id"
          class="particle"
          :style="{
            left: item.left,
            animationDelay: item.delay,
            animationDuration: item.duration,
            width: item.size,
            height: item.size,
          }"
        ></span>
      </div>
      <router-view />
    </main>
  </div>
</template>
