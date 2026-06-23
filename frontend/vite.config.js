import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/tests': { target: 'http://api:8000', changeOrigin: true },
      '/questions': { target: 'http://api:8000', changeOrigin: true },
      '/attempts': { target: 'http://api:8000', changeOrigin: true },
      '/users': { target: 'http://api:8000', changeOrigin: true },
    },
  },
})
