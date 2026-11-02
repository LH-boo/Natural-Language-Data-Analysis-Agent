import axios from 'axios'
import { ElMessage } from 'element-plus'

export const API_BASE = '/api'

const DEMO_MODE = import.meta.env.VITE_DEMO === 'true'

const http = axios.create({
  baseURL: API_BASE,
  timeout: 180000
})

function resolveErrorMessage(error) {
  const data = error.response?.data
  const detail = data?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail) && detail.length) {
    return detail.map((item) => item.msg || item.message || '参数校验失败').join('；')
  }
  if (typeof data?.message === 'string' && data.message) return data.message
  if (error.code === 'ECONNABORTED') return '请求超时，请稍后重试'
  if (!error.response) return '无法连接后端服务，请确认服务已启动'
  return '请求失败，请稍后重试'
}

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = resolveErrorMessage(error)
    if (!error.config?.silent && !DEMO_MODE) {
      ElMessage.error(message)
    }
    return Promise.reject(error)
  }
)

export const api = {
  health: (silent = false) => http.get('/health', silent ? { silent: true } : {}),

  dashboard: () => http.get('/analysis/dashboard'),
  monitoring: () => http.get('/analysis/monitoring'),

  listDatasets: () => http.get('/dataset/list'),
  uploadDataset: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return http.post('/dataset/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000
    })
  },
  loadSampleDataset: () => http.post('/dataset/sample'),
  previewDataset: (params) => http.get('/dataset/preview', { params }),
  datasetSchema: (id) => http.get(`/dataset/${id}/schema`),
  deleteDataset: (id) => http.delete(`/dataset/${id}`),

  testConnection: (data) => http.post('/database/test', data),
  saveConnection: (data) => http.post('/database/connect', data),
  listConnections: () => http.get('/database/list'),
  connectionSchema: (id) => http.get('/database/schema', { params: { id } }),
  deleteConnection: (id) => http.delete(`/database/${id}`),

  chat: (data) => http.post('/analysis/chat', data),
  listConversations: () => http.get('/analysis/conversations'),
  getConversation: (id) => http.get(`/analysis/conversations/${id}`),
  deleteConversation: (id) => http.delete(`/analysis/conversations/${id}`),

  runSql: (data) => http.post('/analysis/sql', data),
  buildChart: (data) => http.post('/analysis/chart', data),
  analysisHistory: (limit = 50) => http.get('/analysis/history', { params: { limit } }),
  listReports: (limit = 50) => http.get('/analysis/reports', { params: { limit } }),
  reportDetail: (taskId) => http.get(`/analysis/reports/${taskId}`),
  sqlLogs: (limit = 100) => http.get('/analysis/sql-logs', { params: { limit } })
}

export function exportReportUrl(taskId, format = 'csv') {
  return `${API_BASE}/analysis/export/${taskId}?format=${format}`
}

export default http
