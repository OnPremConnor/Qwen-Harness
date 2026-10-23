import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    // During development, the browser still calls the real FastAPI routes.
    proxy: {
      '/chat': 'http://127.0.0.1:8001',
      '/conversations': 'http://127.0.0.1:8001',
      '/flow': 'http://127.0.0.1:8001',
    },
  },
})
