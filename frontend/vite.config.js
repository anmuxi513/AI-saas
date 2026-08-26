import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 前端开发服务器 + 代理配置
// 所有 API 统一走门户服务（projects/portal/app.py，端口 6666）
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://localhost:6660', changeOrigin: true },
    },
  },
})
