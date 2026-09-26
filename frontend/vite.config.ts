import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 后端地址默认取本文件里写的端口，起服务时可以用 VITE_PROXY_TARGET 覆盖，
// 这样换端口调试或做启动探针时前端不用改代码。
const proxyTarget = process.env.VITE_PROXY_TARGET ?? 'http://127.0.0.1:8000'
// 前端端口可用 FRONTEND_PORT 覆盖（scripts/dev.sh 会从根目录 .env 注入）。
const frontendPort = Number(process.env.FRONTEND_PORT ?? 5173)

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '127.0.0.1',
    port: frontendPort,
    // 关掉自动打开页面：起服务时只打印地址，不拉起浏览器
    open: false,
    // 端口被占用时直接报错退出，而不是悄悄换端口让人找不到页面
    strictPort: true,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
