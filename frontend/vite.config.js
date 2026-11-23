import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    // En dev, /api/* est redirigé vers l'API FastAPI (port 8000) : pas de souci de CORS.
    proxy: {
      '/api': {
        // 127.0.0.1 plutôt que localhost : sous Windows, ::1:8000 peut être pris par WSL (wslrelay).
        target: process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
