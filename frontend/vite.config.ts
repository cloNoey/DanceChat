import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react({
    jsxImportSource: '@emotion/react',
    babel: {
      plugins: ['@emotion/babel-plugin']
    }
  })],
  server: {
    proxy: {
      '/chat': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/chat/stream': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/stats': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/feedback': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/export': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/reset': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})