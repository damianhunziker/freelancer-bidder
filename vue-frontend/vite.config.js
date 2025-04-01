import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [
    vue(),
  ],
  server: {
    port: 8080,
    host: 'localhost',
    strictPort: true,
    hmr: {
      host: 'localhost',
      protocol: 'ws',
      clientPort: 8080
    },
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  }
}) 