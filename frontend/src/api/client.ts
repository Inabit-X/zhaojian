import axios from 'axios'

import { clearSession, readToken } from '../utils/storage'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

/** 全局 axios 实例：自动带 Bearer，401 时交给外部处理器清理会话。 */
export const api = axios.create({
  baseURL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

let unauthorizedHandler: (() => void) | null = null

/** 注册 401 处理器，由 main.ts 注入，避免 client 反向依赖 store/router。 */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler
}

api.interceptors.request.use((config) => {
  const token = readToken()
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`)
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      const url = error.config?.url ?? ''
      // 登录/注册的 401 是业务错误，由页面展示，不触发全局登出
      const isCredentialAttempt = url.includes('/auth/login') || url.includes('/auth/register')
      if (!isCredentialAttempt) {
        clearSession()
        unauthorizedHandler?.()
      }
    }
    return Promise.reject(error)
  },
)
