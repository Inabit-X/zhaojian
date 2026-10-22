<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <main class="notfound-page">
    <p class="notfound-code">404</p>
    <h1 class="notfound-title">这里什么也没有</h1>
    <p class="notfound-text">链接可能已失效，或者页面还没做出来。</p>
    <RouterLink class="btn btn-primary notfound-action" :to="{ name: 'home' }">
      回到我的空间
    </RouterLink>
  </main>
</template>
