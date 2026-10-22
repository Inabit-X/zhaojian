<script setup lang="ts">
import { nextTick, reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import AuthLayout from '../components/AuthLayout.vue'
import PasswordInput from '../components/PasswordInput.vue'
import { useAuthStore } from '../stores/auth'
import { toApiError } from '../utils/errors'
import { validateRegister, type FormErrors, type RegisterForm } from '../utils/validation'

const auth = useAuthStore()
const router = useRouter()

const form = reactive<RegisterForm>({
  email: '',
  username: '',
  password: '',
  confirmPassword: '',
  privacyAccepted: false,
})
const errors = ref<FormErrors>({})
const formError = ref('')
const submitting = ref(false)

async function focusFirstError(): Promise<void> {
  await nextTick()
  const element = document.querySelector<HTMLElement>('[aria-invalid="true"]')
  element?.focus()
}

async function onSubmit(): Promise<void> {
  if (submitting.value) {
    return
  }
  formError.value = ''
  errors.value = validateRegister(form)
  if (Object.keys(errors.value).length > 0) {
    await focusFirstError()
    return
  }

  submitting.value = true
  try {
    await auth.register({
      email: form.email.trim(),
      password: form.password,
      username: form.username.trim() || null,
      privacy_accepted: form.privacyAccepted,
    })
    // 后端注册成功即签发令牌，直接进入已登录状态
    await router.replace({ name: 'home' })
  } catch (error) {
    const info = toApiError(error)
    errors.value = info.fields
    if (Object.keys(info.fields).length > 0) {
      await focusFirstError()
    } else {
      formError.value = info.message
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthLayout title="创建你的空间" subtitle="只需要一个邮箱。用户名可选，之后也能改。">
    <form class="form" novalidate @submit.prevent="onSubmit">
      <p v-if="formError" class="form-alert" role="alert">{{ formError }}</p>

      <div class="field">
        <label class="field-label" for="register-email">邮箱</label>
        <input
          id="register-email"
          v-model="form.email"
          class="input"
          type="email"
          inputmode="email"
          autocomplete="email"
          placeholder="you@example.com"
          :aria-invalid="errors.email ? 'true' : undefined"
          :aria-describedby="errors.email ? 'register-email-error' : undefined"
        />
        <p v-if="errors.email" id="register-email-error" class="field-error">
          {{ errors.email }}
        </p>
      </div>

      <div class="field">
        <label class="field-label" for="register-username">
          用户名 <span class="field-optional">可选</span>
        </label>
        <input
          id="register-username"
          v-model="form.username"
          class="input"
          type="text"
          autocomplete="nickname"
          placeholder="2–50 位中文、字母、数字、_ 或 -"
          :aria-invalid="errors.username ? 'true' : undefined"
          :aria-describedby="errors.username ? 'register-username-error' : 'register-username-hint'"
        />
        <p v-if="errors.username" id="register-username-error" class="field-error">
          {{ errors.username }}
        </p>
        <p v-else id="register-username-hint" class="field-hint">
          留空也可以，登录始终使用邮箱。
        </p>
      </div>

      <div class="field">
        <label class="field-label" for="register-password">密码</label>
        <PasswordInput
          id="register-password"
          v-model="form.password"
          autocomplete="new-password"
          placeholder="至少 8 位"
          :invalid="Boolean(errors.password)"
          :described-by="errors.password ? 'register-password-error' : undefined"
        />
        <p v-if="errors.password" id="register-password-error" class="field-error">
          {{ errors.password }}
        </p>
      </div>

      <div class="field">
        <label class="field-label" for="register-confirm">确认密码</label>
        <PasswordInput
          id="register-confirm"
          v-model="form.confirmPassword"
          autocomplete="new-password"
          placeholder="再输入一次"
          :invalid="Boolean(errors.confirmPassword)"
          :described-by="errors.confirmPassword ? 'register-confirm-error' : undefined"
        />
        <p v-if="errors.confirmPassword" id="register-confirm-error" class="field-error">
          {{ errors.confirmPassword }}
        </p>
      </div>

      <div class="consent">
        <label class="checkbox-row">
          <input
            v-model="form.privacyAccepted"
            type="checkbox"
            :aria-invalid="errors.privacyAccepted ? 'true' : undefined"
            :aria-describedby="errors.privacyAccepted ? 'register-privacy-error' : undefined"
          />
          <span>我已阅读并同意隐私说明与非医疗免责声明</span>
        </label>
        <p v-if="errors.privacyAccepted" id="register-privacy-error" class="field-error">
          {{ errors.privacyAccepted }}
        </p>

        <details class="consent-details">
          <summary>查看隐私说明与非医疗免责声明</summary>
          <div class="consent-body">
            <p>
              「照见」是非医疗产品，不提供心理诊断、治疗或危机干预，不能替代专业帮助。如有紧急危险，请立即联系当地急救或可信赖的专业机构。
            </p>
            <p>
              本期为本地开发 MVP：密码以 Argon2 哈希存储，访问令牌保存在浏览器 localStorage；暂不提供邮箱验证、密码找回与第三方登录。你可以随时登出以清除本地令牌。
            </p>
          </div>
        </details>
      </div>

      <button class="btn btn-primary" type="submit" :disabled="submitting">
        <span v-if="submitting" class="spinner" aria-hidden="true"></span>
        {{ submitting ? '创建中…' : '创建账号' }}
      </button>
    </form>

    <template #switch>
      已经有账号？
      <RouterLink :to="{ name: 'login' }">去登录</RouterLink>
    </template>
  </AuthLayout>
</template>
