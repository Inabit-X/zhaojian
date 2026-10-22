<script setup lang="ts">
import { RouterView } from 'vue-router'

import DisclaimerFooter from './components/DisclaimerFooter.vue'
</script>

<template>
  <div class="app-shell">
    <RouterView />
    <DisclaimerFooter />
  </div>
</template>
