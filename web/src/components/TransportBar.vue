<script setup lang="ts">
// 回放传输控制：播放/暂停、变速、进度条拖动 seek（100ms 节流）。
import { ref, watch } from 'vue'
import { api } from '@/api/rest'
import { useTelemetry } from '@/composables/useTelemetry'

const { state } = useTelemetry()
const dragging = ref(false)
const dragValue = ref(0)
let lastSent = 0

const frame = ref(0)
watch(() => state.version, () => {
  if (!dragging.value && state.latest) frame.value = state.latest.frame
})

function onInput(e: Event) {
  dragValue.value = Number((e.target as HTMLInputElement).value)
  dragging.value = true
  const now = Date.now()
  if (now - lastSent > 100) { // 10 req/s，中间值可丢（最新值语义）
    lastSent = now
    api.seek(dragValue.value)
  }
}

function onCommit() {
  dragging.value = false
  api.seek(dragValue.value)
}

function seconds(f: number): string {
  return (f / (state.hello?.fps ?? 30)).toFixed(1) + 's'
}
</script>

<template>
  <div class="transport">
    <div class="row">
      <button class="primary" @click="api.togglePause()">
        {{ state.latest?.paused ? '▶ 继续' : '⏸ 暂停' }}
      </button>
      <select :value="state.latest?.speed ?? 1" @change="api.setSpeed(Number(($event.target as HTMLSelectElement).value))">
        <option v-for="s in [0.25, 0.5, 1, 2, 4]" :key="s" :value="s">{{ s }}x</option>
      </select>
      <span class="hint">←→ 逐帧 · Shift+←→ ±1s</span>
    </div>
    <div class="progress-row">
      <span class="time">{{ seconds(frame) }}</span>
      <input type="range" min="0" :max="state.latest?.frame_count ?? 1000" step="1"
        :value="dragging ? dragValue : Math.round(frame)" @input="onInput" @change="onCommit" />
      <span class="time">{{ seconds(state.latest?.frame_count ?? 0) }}</span>
    </div>
  </div>
</template>

<style scoped>
.transport { border-top: 1px solid var(--line); padding-top: 10px; margin-top: 4px; }
.row { display: flex; gap: 8px; align-items: center; }
button { background: var(--panel); color: var(--fg); border: 1px solid var(--line);
  border-radius: 6px; padding: 5px 12px; font-size: 13px; cursor: pointer; }
button.primary { border-color: var(--acc); color: var(--acc); }
select { background: var(--panel); color: var(--fg); border: 1px solid var(--line);
  border-radius: 6px; padding: 4px 8px; font-size: 13px; }
.hint { color: var(--dim); font-size: 11px; margin-left: auto; }
.progress-row { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.progress-row input { flex: 1; accent-color: var(--acc); }
.time { color: var(--dim); font-size: 11px; font-variant-numeric: tabular-nums; min-width: 42px; text-align: center; }
</style>
