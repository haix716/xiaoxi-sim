// WS 遥测单例：连接 + 指数退避重连 + 环形历史缓冲（曲线图数据源）。
// 断线时 App 层可回退轮询 /api/status（fetchStatusAndApply 由调用方注入，避免环依赖）。
import { reactive, readonly } from 'vue'
import type { Hello, Telemetry } from '@/types'

const HISTORY_MAX = 1200 // 20Hz × 60s

interface History {
  t: number[] // 相对秒
  target: number[][] // [joint][sample]
  actual: number[][]
}

const state = reactive({
  connected: false,
  hello: null as Hello | null,
  latest: null as Telemetry | null,
  history: { t: [], target: [], actual: [] } as History,
  version: 0, // 曲线图 watch 触发器
})

let ws: WebSocket | null = null
let backoff = 500
let closed = false
let t0 = 0

function pushHistory(msg: Telemetry) {
  const h = state.history
  if (!h.t.length) t0 = msg.t
  h.t.push((msg.t - t0) / 1000)
  for (let j = 0; j < 6; j++) {
    if (!h.target[j]) { h.target[j] = []; h.actual[j] = [] }
    h.target[j].push(msg.target_deg[j] ?? 0)
    h.actual[j].push(msg.actual_deg[j] ?? 0)
  }
  if (h.t.length > HISTORY_MAX) {
    h.t.shift()
    for (let j = 0; j < 6; j++) { h.target[j].shift(); h.actual[j].shift() }
  }
}

function connect() {
  if (closed) return
  const url = import.meta.env.DEV ? 'ws://127.0.0.1:8777/ws/telemetry' : '/ws/telemetry'
  const sock = new WebSocket(url)
  ws = sock
  sock.onopen = () => {
    state.connected = true
    backoff = 500
  }
  sock.onmessage = (ev) => {
    const msg = JSON.parse(ev.data)
    if (msg.type === 'hello') state.hello = msg
    else if (msg.type === 'telemetry') {
      state.latest = msg
      pushHistory(msg)
      state.version++
    }
  }
  sock.onclose = () => {
    state.connected = false
    ws = null
    if (!closed) {
      setTimeout(connect, backoff)
      backoff = Math.min(backoff * 2, 8000)
    }
  }
  sock.onerror = () => sock.close()
}

export function useTelemetry() {
  return {
    state: readonly(state),
    connect,
    disconnect() {
      closed = true
      ws?.close()
    },
  }
}
