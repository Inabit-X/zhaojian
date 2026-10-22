import type { AuthResponse, LoginPayload, RegisterPayload, User } from '../types/auth'
import { api } from './client'

/** 注册并直接登录，后端返回令牌与用户信息。 */
export async function register(payload: RegisterPayload): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/auth/register', payload)
  return data
}

/** 邮箱 + 密码登录。 */
export async function login(payload: LoginPayload): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/auth/login', payload)
  return data
}

/** 校验当前令牌并返回最新用户信息。 */
export async function me(): Promise<User> {
  const { data } = await api.get<User>('/auth/me')
  return data
}

/** 无状态登出：服务端返回 204，客户端负责删除本地令牌。 */
export async function logout(): Promise<void> {
  await api.post('/auth/logout')
}
