import axios from 'axios'

/** 字段级错误：键为后端字段名，值为中文提示。 */
export type FieldErrors = Record<string, string>

export interface ApiErrorInfo {
  message: string
  code?: string
  fields: FieldErrors
  status?: number
}

const FALLBACK_MESSAGE = '操作失败，请稍后重试。'
const NETWORK_MESSAGE = '无法连接服务，请确认后端已启动（默认 http://localhost:18080）。'

const FIELD_MESSAGES: Record<string, string> = {
  email: '请输入有效的邮箱地址。',
  password: '密码至少 8 位，最多 128 位。',
  username: '用户名需为 2–50 位中文、字母、数字、下划线或连字符。',
  privacy_accepted: '请先阅读并同意隐私说明与非医疗免责声明。',
}

interface ValidationDetail {
  loc?: unknown[]
  msg?: string
  type?: string
}

function fieldFromLocation(loc: unknown[] | undefined): string | null {
  if (!loc) {
    return null
  }
  for (let index = loc.length - 1; index >= 0; index -= 1) {
    const item = loc[index]
    if (typeof item === 'string' && item !== 'body') {
      return item
    }
  }
  return null
}

function friendlyFieldMessage(field: string, detail: ValidationDetail): string {
  return FIELD_MESSAGES[field] ?? detail.msg ?? '该字段填写有误。'
}

/** 把 axios / 未知异常归一化成可直接展示的错误信息。 */
export function toApiError(error: unknown): ApiErrorInfo {
  if (!axios.isAxiosError(error)) {
    return { message: FALLBACK_MESSAGE, fields: {} }
  }
  if (!error.response) {
    return {
      message: error.code === 'ECONNABORTED' ? '请求超时，请稍后重试。' : NETWORK_MESSAGE,
      fields: {},
    }
  }

  const status = error.response.status
  const data = error.response.data as
    | { code?: string; message?: string; details?: ValidationDetail[] }
    | undefined
  const fields: FieldErrors = {}

  if (status === 422 && Array.isArray(data?.details)) {
    for (const detail of data.details) {
      const field = fieldFromLocation(detail.loc)
      if (field) {
        fields[field] = friendlyFieldMessage(field, detail)
      }
    }
  }
  if (status === 409) {
    if (data?.code === 'email_taken') {
      fields.email = data.message ?? '该邮箱已注册。'
    }
    if (data?.code === 'username_taken') {
      fields.username = data.message ?? '该用户名已被占用。'
    }
  }

  return {
    message: data?.message ?? FALLBACK_MESSAGE,
    code: data?.code,
    fields,
    status,
  }
}
