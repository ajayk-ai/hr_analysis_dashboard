import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Keeps the browser same-origin in dev, so CORS never enters the
      // picture. Backend routes already live under /api (see main.py), so
      // no path rewrite is needed here.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
