// dev 下视频流直连后端端口（MJPEG 不走 vite proxy，见 vite.config.ts 注释）
export function videoSrc(path: string): string {
  return import.meta.env.DEV ? `http://127.0.0.1:8777${path}` : path
}
