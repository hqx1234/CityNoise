import axios from 'axios'

const API_BASE_URL = import.meta.env.DEV ? '/api' : 'http://localhost:5000/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API 请求错误:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    })
    
    if (error.response?.status === 401) {
      // 只有在非登录页面时才清除 token 和跳转
      if (window.location.pathname !== '/login') {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = '/login'
      }
    }
    
    // 确保错误对象包含完整的响应信息
    return Promise.reject(error)
  }
)

// 认证API
export const authAPI = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }),
  register: (data: any) => api.post('/auth/register', data)
}

// 噪音数据API
export const noiseDataAPI = {
  get: (params?: any) => api.get('/noise-data', { params }),
  post: (data: any) => api.post('/noise-data', data),
  getStatistics: (params?: any) => api.get('/noise-data/statistics', { params })
}

// 告警API
export const alertAPI = {
  get: (params?: any) => api.get('/alerts', { params }),
  update: (alertId: number, data: any) => api.put(`/alerts/${alertId}`, data)
}

// 区域API
export const regionAPI = {
  get: (params?: any) => api.get('/regions', { params }),
  getDevices: (regionId: number) => api.get(`/regions/${regionId}/devices`)
}

// 设备API
export const deviceAPI = {
  get: (params?: any) => api.get('/devices', { params }),
  getStatuses: () => api.get('/devices/statuses')
}

// 报告API
export const reportAPI = {
  get: (params?: any) => api.get('/reports', { params }),
  post: (data: any) => api.post('/reports', data),
  delete: (reportId: number) => api.delete(`/reports/${reportId}`)
}

// 仪表板API
export const dashboardAPI = {
  getStats: () => api.get('/dashboard/stats')
}

// 地图API
export const mapAPI = {
  getData: () => api.get('/map/data')
}

// 数据导入API
export const importAPI = {
  importData: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/data-import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }
}

export default api

