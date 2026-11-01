export type Mode = 'manual' | 'replay'

export interface Config {
  joints: string[]
  limits_deg: number[][]
  fps: number
  sim_hz: number
  telemetry_hz: number
  streams: { main: string; wrist: string }
}

export interface Hello {
  type: 'hello'
  push_hz: number
  fps: number
  joints: string[]
  limits_deg: number[][]
  episode_count: number
}

export interface Telemetry {
  type: 'telemetry'
  t: number
  mode: Mode
  ep: number
  frame: number
  frame_count: number
  speed: number
  paused: boolean
  target_deg: number[]
  actual_deg: number[]
  img_seq: { main: number; wrist: number }
}

export interface Status {
  ok: boolean
  mode: Mode
  ep: number
  frame: number
  frame_count: number
  speed: number
  paused: boolean
  sim_hz: number
  joints: { target_deg: number[]; actual_deg: number[] }
}

export interface Episode {
  index: number
  length: number
  seconds: number
  tasks: string[]
}
