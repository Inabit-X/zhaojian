<script setup lang="ts">
defineProps<{
  title: string
  subtitle: string
}>()
</script>

<template>
  <main class="auth-page">
    <section class="auth-brand" aria-label="产品介绍">
      <div class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 48 48" focusable="false">
          <circle cx="24" cy="24" r="20" />
          <path d="M13 26c3.5-5.5 7-8 11-8s7.5 2.5 11 8" />
          <circle cx="24" cy="25" r="3.2" />
        </svg>
      </div>
      <p class="brand-name">照见</p>
      <p class="brand-tagline">让记录更轻，<br />让判断留给人。</p>
      <ul class="brand-points">
        <li>咨询记录起草与咨询师确认</li>
        <li>个案档案与接案简报</li>
        <li>数据留在校园网内</li>
      </ul>
      <p class="brand-note">非医疗产品，不提供心理诊断或治疗决策，不替代咨询师判断。</p>
    </section>

    <section class="auth-panel">
      <div class="auth-card">
        <header class="auth-header">
          <p class="auth-eyebrow">心理中心工作台 · MVP</p>
          <h1 class="auth-title">{{ title }}</h1>
          <p class="auth-subtitle">{{ subtitle }}</p>
        </header>

        <slot />

        <p class="auth-switch">
          <slot name="switch" />
        </p>
      </div>
    </section>
  </main>
</template>
