import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

function buildManualChunk(id) {
  if (!id.includes('node_modules')) {
    return undefined
  }
  return 'vendor'
}

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/student-api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
        rewrite: (currentPath) => currentPath.replace(/^\/student-api/, '')
      },
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: buildManualChunk
      }
    }
  }
})
