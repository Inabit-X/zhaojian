/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 可选：覆盖 API 前缀，默认同源 /api/v1（开发期由 Vite 代理） */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
