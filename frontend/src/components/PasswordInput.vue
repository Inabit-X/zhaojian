<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  modelValue: string
  id: string
  autocomplete?: string
  invalid?: boolean
  describedBy?: string
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const visible = ref(false)

function onInput(event: Event): void {
  emit('update:modelValue', (event.target as HTMLInputElement).value)
}
</script>

<template>
  <div class="password-wrap">
    <input
      :id="props.id"
      class="input"
      :type="visible ? 'text' : 'password'"
      :value="props.modelValue"
      :autocomplete="props.autocomplete"
      :placeholder="props.placeholder"
      :aria-invalid="props.invalid ? 'true' : undefined"
      :aria-describedby="props.describedBy"
      @input="onInput"
    />
    <button
      type="button"
      class="password-toggle"
      :aria-label="visible ? '隐藏密码' : '显示密码'"
      :aria-pressed="visible"
      @click="visible = !visible"
    >
      <svg v-if="visible" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M3 3l18 18" />
        <path d="M10.6 10.6a2 2 0 002.8 2.8" />
        <path d="M9.9 5.2A9.8 9.8 0 0112 5c5.5 0 9 5.2 9 7 0 .8-.5 1.9-1.4 3" />
        <path d="M6.6 6.6C4.6 8 3 10.2 3 12c0 1.8 3.5 7 9 7 1.2 0 2.3-.3 3.3-.7" />
      </svg>
      <svg v-else viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M3 12c0-1.8 3.5-7 9-7s9 5.2 9 7-3.5 7-9 7-9-5.2-9-7z" />
        <circle cx="12" cy="12" r="2.5" />
      </svg>
    </button>
  </div>
</template>
