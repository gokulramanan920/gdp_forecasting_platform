import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  optimizeDeps: {
    include: ['react-plotly.js', 'plotly.js-dist-min'],
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
