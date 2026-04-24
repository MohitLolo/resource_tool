import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

function buildTaskFormData(inputFile, processor, params = {}, extraFiles = [], options = {}) {
  const formData = new FormData()
  formData.append('input_file', inputFile)
  formData.append('processor', processor)
  formData.append('params', JSON.stringify(params))
  if (options.idempotencyKey) {
    formData.append('idempotency_key', options.idempotencyKey)
  }

  for (const file of extraFiles) {
    formData.append('extra_files', file)
  }

  return formData
}

export async function getProcessors(category = '') {
  const path = category ? `/processors/${category}` : '/processors'
  const { data } = await api.get(path)
  return data
}

export async function createTask(inputFile, processor, params = {}, extraFiles = [], options = {}) {
  const formData = buildTaskFormData(inputFile, processor, params, extraFiles, options)
  const { data } = await api.post('/tasks', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return data
}

export async function getTask(taskId) {
  const { data } = await api.get(`/tasks/${taskId}`)
  return data
}

export async function deleteTask(taskId) {
  const { data } = await api.delete(`/tasks/${taskId}`)
  return data
}

function parseFilenameFromDisposition(disposition = '') {
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1])
  }

  const asciiMatch = disposition.match(/filename="?([^";]+)"?/i)
  if (asciiMatch?.[1]) {
    return asciiMatch[1]
  }

  return ''
}

export async function downloadResult(taskId) {
  const response = await api.get(`/tasks/${taskId}/download`, {
    responseType: 'blob',
  })

  const disposition = response.headers['content-disposition'] || ''
  const filename = parseFilenameFromDisposition(disposition) || `task_${taskId}_result`

  return {
    blob: response.data,
    filename,
  }
}

export async function downloadTaskOutput(taskId, index) {
  const response = await api.get(`/tasks/${taskId}/outputs/${index}`, {
    responseType: 'blob',
  })
  const disposition = response.headers['content-disposition'] || ''
  const filename = parseFilenameFromDisposition(disposition) || `task_${taskId}_output_${index}`
  return {
    blob: response.data,
    filename,
  }
}

export default api
