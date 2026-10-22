import type { User } from '../types/auth'

const TOKEN_KEY = 'own_partner.token'
const USER_KEY = 'own_partner.user'

/** 读取访问令牌；localStorage 不可用时返回 null。 */
export function readToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

/** 写入或删除访问令牌。 */
export function writeToken(token: string | null): void {
  try {
    if (token) {
      window.localStorage.setItem(TOKEN_KEY, token)
    } else {
      window.localStorage.removeItem(TOKEN_KEY)
    }
  } catch {
    // 隐私模式等场景下写入失败时忽略，会话仅保留在内存
  }
}

function isUser(value: unknown): value is User {
  if (typeof value !== 'object' || value === null) {
    return false
  }
  const candidate = value as Record<string, unknown>
  return (
    typeof candidate.id === 'string' &&
    typeof candidate.email === 'string' &&
    typeof candidate.created_at === 'string' &&
    (candidate.username === null || typeof candidate.username === 'string')
  )
}

/** 读取缓存的用户信息，用于刷新后先渲染再校验。 */
export function readUser(): User | null {
  try {
    const raw = window.localStorage.getItem(USER_KEY)
    if (!raw) {
      return null
    }
    const parsed: unknown = JSON.parse(raw)
    return isUser(parsed) ? parsed : null
  } catch {
    return null
  }
}

/** 缓存用户信息；传 null 时清除。 */
export function writeUser(user: User | null): void {
  try {
    if (user) {
      window.localStorage.setItem(USER_KEY, JSON.stringify(user))
    } else {
      window.localStorage.removeItem(USER_KEY)
    }
  } catch {
    // 同上，缓存失败不影响本次会话
  }
}

/** 清除本地令牌与用户缓存（登出或令牌失效时调用）。 */
export function clearSession(): void {
  try {
    window.localStorage.removeItem(TOKEN_KEY)
    window.localStorage.removeItem(USER_KEY)
  } catch {
    // 忽略存储异常
  }
}
