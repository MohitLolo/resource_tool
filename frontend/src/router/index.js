import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/image',
  },
  {
    path: '/image',
    name: 'image',
    component: () => import('../views/ToolWorkbench.vue'),
  },
  {
    path: '/video',
    name: 'video',
    component: () => import('../views/ToolWorkbench.vue'),
  },
  {
    path: '/audio',
    name: 'audio',
    component: () => import('../views/ToolWorkbench.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
