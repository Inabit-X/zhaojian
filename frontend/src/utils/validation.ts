/** 登录/注册的前端校验，规则与后端保持一致，先在前端给出即时提示。 */

export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
export const USERNAME_PATTERN = /^[A-Za-z0-9_\-\u4e00-\u9fa5]{2,50}$/
export const PASSWORD_MIN_LENGTH = 8
export const PASSWORD_MAX_LENGTH = 128

export interface LoginForm {
  email: string
  password: string
}

export interface RegisterForm {
  email: string
  username: string
  password: string
  confirmPassword: string
  privacyAccepted: boolean
}

export type FormErrors = Record<string, string>

function checkEmail(email: string): string | null {
  const value = email.trim()
  if (!value) {
    return '请输入邮箱。'
  }
  return EMAIL_PATTERN.test(value) ? null : '请输入有效的邮箱地址。'
}

function checkPassword(password: string): string | null {
  if (!password) {
    return '请输入密码。'
  }
  if (password.length < PASSWORD_MIN_LENGTH) {
    return `密码至少 ${PASSWORD_MIN_LENGTH} 位。`
  }
  if (password.length > PASSWORD_MAX_LENGTH) {
    return `密码最多 ${PASSWORD_MAX_LENGTH} 位。`
  }
  return null
}

/** 校验登录表单，返回字段错误；空对象表示通过。 */
export function validateLogin(form: LoginForm): FormErrors {
  const errors: FormErrors = {}
  const emailError = checkEmail(form.email)
  if (emailError) {
    errors.email = emailError
  }
  if (!form.password) {
    errors.password = '请输入密码。'
  }
  return errors
}

/** 校验注册表单，返回字段错误；空对象表示通过。 */
export function validateRegister(form: RegisterForm): FormErrors {
  const errors: FormErrors = {}
  const emailError = checkEmail(form.email)
  if (emailError) {
    errors.email = emailError
  }

  const username = form.username.trim()
  if (username && !USERNAME_PATTERN.test(username)) {
    errors.username = '用户名需为 2–50 位中文、字母、数字、下划线或连字符。'
  }

  const passwordError = checkPassword(form.password)
  if (passwordError) {
    errors.password = passwordError
  }

  if (!form.confirmPassword) {
    errors.confirmPassword = '请再次输入密码。'
  } else if (form.confirmPassword !== form.password) {
    errors.confirmPassword = '两次输入的密码不一致。'
  }

  if (!form.privacyAccepted) {
    errors.privacyAccepted = '请先阅读并同意隐私说明与非医疗免责声明。'
  }

  return errors
}
