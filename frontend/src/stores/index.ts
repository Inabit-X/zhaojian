import { createPinia } from 'pinia'

/** 单例 Pinia，供 main.ts 与路由守卫共享。 */
export const pinia = createPinia()
