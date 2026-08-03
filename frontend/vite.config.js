import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Keeps the browser same-origin in dev, so CORS never enters the
      // picture. Backend routes already live under /api (see main.py), so
      // no path rewrite is needed here. dev.bat passes the target through so
      // the proxy follows API_PORT from .env instead of assuming 8000.
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
