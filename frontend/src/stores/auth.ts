import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import * as authApi from '../api/auth'
import type { AuthResponse, LoginPayload, RegisterPayload, User } from '../types/auth'
import {
  clearSession,
  readToken,
  readUser,
  writeToken,
  writeUser,
} from '../utils/storage'

/** 认证状态：令牌、当前用户、初始化与提交中标记。 */
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(readToken())
  const user = ref<User | null>(readUser())
  const initialized = ref(false)
  const busy = ref(false)

  const isAuthenticated = computed(() => Boolean(token.value))
  const displayName = computed(() => user.value?.username || user.value?.email || '')

  function applySession(data: AuthResponse): void {
    token.value = data.access_token
    user.value = data.user
    writeToken(data.access_token)
    writeUser(data.user)
  }

  function clear(): void {
    token.value = null
    user.value = null
    clearSession()
  }

  async function login(payload: LoginPayload): Promise<void> {
    busy.value = true
    try {
      applySession(await authApi.login(payload))
    } finally {
      busy.value = false
    }
  }

  async function register(payload: RegisterPayload): Promise<void> {
    busy.value = true
    try {
      applySession(await authApi.register(payload))
    } finally {
      busy.value = false
    }
  }

  /**
   * 应用启动/首次导航时恢复会话。
   * 401 由 axios 拦截器清理；网络错误保留本地缓存，避免后端短暂不可用时误登出。
   */
  async function restore(): Promise<void> {
    if (initialized.value) {
      return
    }
    if (!token.value) {
      initialized.value = true
      return
    }
    try {
      const current = await authApi.me()
      user.value = current
      writeUser(current)
    } catch {
      // 错误提示由具体页面处理；这里只保证初始化流程结束
    } finally {
      initialized.value = true
    }
  }

  /** 登出：即使服务端调用失败也清理本地会话。 */
  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } catch {
      // JWT 无状态，登出失败不影响本地清理
    }
    clear()
  }

  return {
    token,
    user,
    initialized,
    busy,
    isAuthenticated,
    displayName,
    login,
    register,
    restore,
    logout,
    clear,
  }
})
