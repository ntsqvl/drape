import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5321,
    strictPort: true,
    proxy: {
      '/api': 'http://localhost:8321',
      '/assets': 'http://localhost:8321',
    },
  },
})
