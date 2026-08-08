import axios from 'axios'

const TOKEN_KEY = 'valve_kb_token'
const USER_KEY = 'valve_kb_user'

const http = axios.create({
  baseURL: '/api',
  timeout: 60000
})

http.interceptors.request.use(config => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  response => response,
  error => {
    const status = error?.response?.status
    const requestUrl = error?.config?.url || ''
    if (status === 401 && !requestUrl.includes('/auth/login')) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      if (window.location.pathname !== '/login') {
        const redirect = encodeURIComponent(window.location.pathname + window.location.search)
        window.location.replace(`/login?redirect=${redirect}`)
      }
    }
    const message = error?.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(message))
  }
)

export default http
