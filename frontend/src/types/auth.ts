/** 后端认证接口的响应类型。 */
export interface User {
  id: string
  email: string
  username: string | null
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: 'bearer'
  user: User
}

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  email: string
  password: string
  username?: string | null
  privacy_accepted: boolean
}
