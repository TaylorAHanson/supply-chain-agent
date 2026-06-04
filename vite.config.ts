import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5174,
    strictPort: true,
    proxy: {
      '/chat': 'http://127.0.0.1:8001',
      '/upload': 'http://127.0.0.1:8001',
      '/clear_chat': 'http://127.0.0.1:8001',
      '/feedback': 'http://127.0.0.1:8001',
      '/tools-and-skills': 'http://127.0.0.1:8001'
    }
  }
})
