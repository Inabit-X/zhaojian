<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const loggingOut = ref(false)

const joinedAt = computed(() => {
  const raw = auth.user?.created_at
  if (!raw) {
    return '—'
  }
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) {
    return '—'
  }
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(date)
})

const modules = [
  {
    name: '账号与登录',
    description: '注册、登录、刷新后保持会话、角色鉴权',
    status: '已开放',
    tone: 'ready',
  },
  {
    name: '个案管理',
    description: '管理员建档分配，咨询师接案，学生查看本人个案',
    status: '已开放',
    tone: 'ready',
  },
  {
    name: '咨询记录起草',
    description: '会谈要点生成四段草稿，咨询师修改确认后归档',
    status: '阶段 2',
    tone: 'wip',
  },
  {
    name: '档案摘要与检索',
    description: '三层档案、个案内向量检索与接案简报',
    status: '阶段 3',
    tone: 'later',
  },
  {
    name: '随访问卷',
    description: '学生端量表、定时推送与告警待办',
    status: '阶段 4',
    tone: 'later',
  },
] as const

async function onLogout(): Promise<void> {
  if (loggingOut.value) {
    return
  }
  loggingOut.value = true
  try {
    await auth.logout()
    await router.replace({ name: 'login' })
  } finally {
    loggingOut.value = false
  }
}
</script>

<template>
  <div class="home-page">
    <header class="topbar">
      <div class="topbar-brand">
        <span class="topbar-mark" aria-hidden="true">照</span>
        <span class="topbar-name">照见</span>
      </div>
      <div class="topbar-actions">
        <span class="user-chip" :title="auth.user?.email">{{ auth.displayName }}</span>
        <button class="btn btn-ghost btn-small" type="button" :disabled="loggingOut" @click="onLogout">
          {{ loggingOut ? '登出中…' : '登出' }}
        </button>
      </div>
    </header>

    <main class="home-main">
      <section class="panel hero">
        <p class="hero-eyebrow">心理中心工作台</p>
        <h1 class="hero-title">你好，{{ auth.displayName }}</h1>
        <p class="hero-text">
          账号、角色与个案权限已经可用。接下来这里会接入咨询记录起草、档案摘要与随访；
          系统只辅助整理文书，不提供诊断或治疗决策。
        </p>
      </section>

      <section class="panel">
        <h2 class="panel-title">账号信息</h2>
        <dl class="account-grid">
          <div class="account-item">
            <dt>邮箱</dt>
            <dd>{{ auth.user?.email ?? '—' }}</dd>
          </div>
          <div class="account-item">
            <dt>用户名</dt>
            <dd>{{ auth.user?.username ?? '未设置' }}</dd>
          </div>
          <div class="account-item">
            <dt>注册时间</dt>
            <dd>{{ joinedAt }}</dd>
          </div>
        </dl>
        <p class="panel-note">
          本期不提供修改邮箱/密码、邮箱验证与密码找回，相关入口会在后续批次补齐。
        </p>
      </section>

      <section class="panel">
        <h2 class="panel-title">功能进度</h2>
        <ul class="module-list">
          <li v-for="item in modules" :key="item.name" class="module-item">
            <div class="module-text">
              <p class="module-name">{{ item.name }}</p>
              <p class="module-desc">{{ item.description }}</p>
            </div>
            <span class="badge" :class="`badge--${item.tone}`">{{ item.status }}</span>
          </li>
        </ul>
      </section>
    </main>
  </div>
</template>
