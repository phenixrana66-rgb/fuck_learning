import axios from 'axios'
import { buildSignedPayload } from '@/utils/sign'
import { showErrorMessage } from '@/utils/message'
import { getTeacherPlatformToken } from '@/utils/platform'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json; charset=UTF-8'
  }
})

service.interceptors.request.use(
  (config) => {
    const token = getTeacherPlatformToken()
    const data = config.data || {}
    const signedData = buildSignedPayload(data)

    // config.method = 'post'
    config.data = signedData

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
      config.headers['X-Platform-Token'] = token
    }

    return config
  },
  (error) => Promise.reject(error)
)

service.interceptors.response.use(
  (response) => {
    const res = response.data || {}

    if (typeof res.code === 'undefined') {
      showErrorMessage('接口响应格式错误')
      return Promise.reject(res)
    }

    if (res.code === 0 || res.code === 200) {
      return res
    }

    const msg = res.msg || '请求失败'
    showErrorMessage(`${msg}${res.requestId ? `（requestId: ${res.requestId}）` : ''}`)
    return Promise.reject(res)
  },
  (error) => {
    const status = error?.response?.status
    const rawMessage = error?.message || ''
    const isLocalMockUnavailable = !status && (
      rawMessage.includes('Network Error') ||
      rawMessage.includes('ECONNREFUSED') ||
      rawMessage.includes('Failed to fetch')
    )

    let msg = '网络异常，请稍后重试'

    if (isLocalMockUnavailable) {
      msg = '统一后端未启动，请先运行 backend FastAPI（127.0.0.1:3001），再执行 npm run dev:web'
      showErrorMessage(msg)
      return Promise.reject({
        code: 503,
        msg,
        data: null,
        requestId: ''
      })
    }

    switch (status) {
      case 400:
        msg = error?.response?.data?.msg || '请求参数错误'
        break
      case 401:
        msg = '登录状态失效或鉴权失败'
        break
      case 403:
        msg = '无权限访问'
        break
      case 404:
        msg = '接口地址不存在'
        break
      case 500:
        msg = '服务端异常'
        break
      default:
        msg = rawMessage || msg
        break
    }

    showErrorMessage(msg)
    return Promise.reject({
      code: status || -1,
      msg,
      data: null,
      requestId: ''
    })
  }
)

export default service
