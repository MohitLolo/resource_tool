import { onBeforeUnmount, ref } from 'vue'

function buildWsUrl(taskId) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/tasks/${taskId}`
}

export function useWebSocket(taskId) {
  const activeTaskId = ref(taskId || '')
  const progress = ref(0)
  const message = ref('')
  const status = ref('idle')
  const connected = ref(false)
  const error = ref('')

  let socket = null

  const connect = (nextTaskId = '') => {
    if (nextTaskId) {
      activeTaskId.value = nextTaskId
    }

    if (!activeTaskId.value || socket) {
      return
    }

    error.value = ''
    socket = new WebSocket(buildWsUrl(activeTaskId.value))

    socket.onopen = () => {
      connected.value = true
      status.value = 'connected'
    }

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        progress.value = typeof payload.progress === 'number' ? payload.progress : progress.value
        message.value = payload.message ?? message.value
        status.value = payload.status ?? status.value

        if (['completed', 'failed', 'canceled'].includes(status.value)) {
          disconnect()
        }
      } catch (err) {
        error.value = `WebSocket 消息解析失败: ${err}`
      }
    }

    socket.onerror = () => {
      error.value = 'WebSocket 连接异常'
    }

    socket.onclose = () => {
      connected.value = false
      socket = null
    }
  }

  const disconnect = () => {
    if (!socket) {
      return
    }
    socket.close()
    socket = null
    connected.value = false
  }

  onBeforeUnmount(() => {
    disconnect()
  })

  return {
    taskId: activeTaskId,
    progress,
    message,
    status,
    connected,
    error,
    connect,
    disconnect,
  }
}
