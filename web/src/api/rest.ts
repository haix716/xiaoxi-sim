// REST 封装：命令全走相对路径（dev 由 vite proxy 转发 /api，prod 同源）。
// 命令语义是「最新值」，幂等可重试。

async function post(path: string, body?: unknown): Promise<Response> {
  return fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export const api = {
  setCtrl: (angles: number[]) => post('/api/ctrl', angles),
  setMode: (mode: 'manual' | 'replay') => post(`/api/mode?mode=${mode}`),
  /** 选集并播放（进回放模式 + 不暂停） */
  playEpisode: (ep: number) => post('/api/replay', { ep, paused: false }),
  seek: (frame: number) => post('/api/replay', { frame }),
  setSpeed: (speed: number) => post('/api/replay', { speed }),
  setPaused: (paused: boolean) => post('/api/replay', { paused }),
  togglePause: () => post('/api/pause'),
  reset: () => post('/api/reset'),
}

export async function fetchJson<T>(path: string): Promise<T> {
  const r = await fetch(path)
  if (!r.ok) throw new Error(`${path} -> ${r.status}`)
  return r.json() as Promise<T>
}
