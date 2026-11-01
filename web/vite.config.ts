import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 视频流（/video/*）不走 proxy：dev 下 useVideoSrc 直连 8777，
// 规避 http-proxy 对 MJPEG 长流的缓冲/超时不确定性。
export default defineConfig({
  plugins: [vue()],
  resolve: {
    // 项目路径含中文，URL.pathname 会百分号编码，必须 decode
    alias: { '@': decodeURIComponent(new URL('./src', import.meta.url).pathname) },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8777', changeOrigin: true },
      '/ws': { target: 'ws://127.0.0.1:8777', ws: true },
    },
  },
})
