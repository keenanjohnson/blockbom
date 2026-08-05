import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Build straight into the Python package so the wheel ships the editor.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../src/blockbom/_static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8352',
    },
  },
})
