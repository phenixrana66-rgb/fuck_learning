import axios from 'axios'
import { buildSignedPayload } from '@/utils/sign'
import { showErrorMessage } from '@/utils/message'
import { getStudentPlatformToken } from '@/utils/platform'

const studentService = axios.create({
  baseURL: import.meta.env.VITE_STUDENT_API_BASE || '/student-api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json; charset=UTF-8'
  }
})

let missingEndpointToastShown = false

studentService.interceptors.request.use(
  (config) => {
    const token = getStudentPlatformToken()
    const data = config.data || {}

    config.method = 'post'
    config.data = buildSignedPayload(data)

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
      config.headers['X-Platform-Token'] = token
    }

    return config
  },
  (error) => Promise.reject(error)
)

studentService.interceptors.response.use(
  (response) => {
    const res = response.data || {}

    if (res.code === 200 || res.code === 0) {
      return res
    }

    const message = res.msg || '学生端接口请求失败'
    showErrorMessage(message)
    return Promise.reject({
      ...res,
      handled: true
    })
  },
  (error) => {
    const status = error?.response?.status
    const rawMessage = error?.message || ''
    const isLocalBackendUnavailable = !status && (
      rawMessage.includes('Network Error') ||
      rawMessage.includes('ECONNREFUSED') ||
      rawMessage.includes('Failed to fetch')
    )

    if (isLocalBackendUnavailable) {
      const message = '统一后端未启动，请先运行 backend FastAPI（127.0.0.1:3001），再执行 npm run dev:web'
      showErrorMessage(message)
      return Promise.reject({
        code: 503,
        msg: message,
        data: null,
        requestId: '',
        handled: true
      })
    }

    const fallback = error?.response?.data?.msg || error.message || '学生端接口请求失败'
    let message = fallback

    if (status === 401) message = '免登鉴权失败，请重新从学习通入口进入'
    if (status === 403) message = '当前账号无权访问该学生端能力'
    if (status === 404) message = '学生端接口不存在'
    if (status === 500) message = '学生端服务异常'

    if (status === 404) {
      if (!missingEndpointToastShown) {
        showErrorMessage(message)
        missingEndpointToastShown = true
      }
    } else {
      showErrorMessage(message)
    }

    return Promise.reject({
      code: status || -1,
      msg: message,
      data: null,
      requestId: '',
      handled: true
    })
  }
)

export default studentService
