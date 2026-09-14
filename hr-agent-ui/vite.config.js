import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const agentApiKey = process.env.AGENT_API_KEY || ''

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/v1': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        headers: { 'X-API-Key': agentApiKey },
      },
      '/auth': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/ready': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/workflows': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
    },
  },
})
