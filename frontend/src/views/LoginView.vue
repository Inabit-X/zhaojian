<script setup lang="ts">
import { computed, nextTick, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import AuthLayout from '../components/AuthLayout.vue'
import PasswordInput from '../components/PasswordInput.vue'
import { useAuthStore } from '../stores/auth'
import { toApiError } from '../utils/errors'
import { validateLogin, type FormErrors, type LoginForm } from '../utils/validation'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const form = reactive<LoginForm>({ email: '', password: '' })
const errors = ref<FormErrors>({})
const formError = ref('')
const submitting = ref(false)

const redirectTarget = computed(() => {
  const value = route.query.redirect
  if (typeof value === 'string' && value.startsWith('/') && !value.startsWith('//')) {
    return value
  }
  return '/'
})

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
  errors.value = validateLogin(form)
  if (Object.keys(errors.value).length > 0) {
    await focusFirstError()
    return
  }

  submitting.value = true
  try {
    await auth.login({ email: form.email.trim(), password: form.password })
    await router.replace(redirectTarget.value)
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
  <AuthLayout title="欢迎回来" subtitle="登录后继续整理你的记忆与陪伴方式。">
    <form class="form" novalidate @submit.prevent="onSubmit">
      <p v-if="formError" class="form-alert" role="alert">{{ formError }}</p>

      <div class="field">
        <label class="field-label" for="login-email">邮箱</label>
        <input
          id="login-email"
          v-model="form.email"
          class="input"
          type="email"
          inputmode="email"
          autocomplete="email"
          placeholder="you@example.com"
          :aria-invalid="errors.email ? 'true' : undefined"
          :aria-describedby="errors.email ? 'login-email-error' : undefined"
        />
        <p v-if="errors.email" id="login-email-error" class="field-error">
          {{ errors.email }}
        </p>
      </div>

      <div class="field">
        <label class="field-label" for="login-password">密码</label>
        <PasswordInput
          id="login-password"
          v-model="form.password"
          autocomplete="current-password"
          placeholder="输入密码"
          :invalid="Boolean(errors.password)"
          :described-by="errors.password ? 'login-password-error' : undefined"
        />
        <p v-if="errors.password" id="login-password-error" class="field-error">
          {{ errors.password }}
        </p>
      </div>

      <button class="btn btn-primary" type="submit" :disabled="submitting">
        <span v-if="submitting" class="spinner" aria-hidden="true"></span>
        {{ submitting ? '登录中…' : '登录' }}
      </button>
    </form>

    <template #switch>
      还没有账号？
      <RouterLink :to="{ name: 'register' }">创建一个</RouterLink>
    </template>
  </AuthLayout>
</template>
