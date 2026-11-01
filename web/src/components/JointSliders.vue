<script setup lang="ts">
// 六关节滑条：手动模式下发目标（60ms 防抖整组 POST，旧版节奏）；
// 回放模式只读展示遥测的目标/实际/误差。
import { reactive, watch } from 'vue'
import { api } from '@/api/rest'
import { useTelemetry } from '@/composables/useTelemetry'
import type { Config } from '@/types'

defineProps<{ config: Config }>()
const { state } = useTelemetry()

const targets = reactive([0, 0, 0, 0, 0, 0])
let timer: ReturnType<typeof setTimeout> | null = null

function push() {
  if (state.latest?.mode !== 'manual') return
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => api.setCtrl([...targets]), 60)
}

// 切回手动时把滑条对齐当前实际角度，避免突跳
watch(() => state.latest?.mode, (mode, old) => {
  if (mode === 'manual' && old === 'replay' && state.latest) {
    state.latest.actual_deg.forEach((v, i) => { targets[i] = Math.round(v * 10) / 10 })
  }
})

function err(i: number): number {
  const t = state.latest
  if (!t) return 0
  return Math.abs((t.target_deg[i] ?? 0) - (t.actual_deg[i] ?? 0))
}
</script>

<template>
  <div class="joints">
    <div v-for="(name, i) in config.joints" :key="name" class="j">
      <label>
        <span class="jname">{{ name }}</span>
        <span class="nums">
          <span class="actual" :class="{ warn: err(i) > 5 }">{{ (state.latest?.actual_deg[i] ?? 0).toFixed(1) }}°</span>
          <span v-if="state.latest?.mode === 'replay'" class="tgt">← {{ (state.latest?.target_deg[i] ?? 0).toFixed(1) }}°</span>
        </span>
      </label>
      <input v-if="state.latest?.mode === 'manual'" v-model.number="targets[i]" type="range"
        :min="config.limits_deg[i][0]" :max="config.limits_deg[i][1]" step="0.5" @input="push" />
      <div v-else class="fake-track">
        <div class="fake-fill" :style="{ left: `${((state.latest?.target_deg[i] ?? 0) - config.limits_deg[i][0]) / (config.limits_deg[i][1] - config.limits_deg[i][0]) * 100}%` }" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.j { margin: 8px 0; }
label { display: flex; justify-content: space-between; align-items: baseline; }
.jname { color: var(--dim); font-size: 12px; }
.nums { font-size: 12px; font-variant-numeric: tabular-nums; }
.actual { color: var(--fg); }
.actual.warn { color: #e5484d; }
.tgt { color: var(--dim); margin-left: 6px; }
input[type=range] { width: 100%; accent-color: var(--acc); }
.fake-track { position: relative; height: 4px; background: var(--line); border-radius: 2px; margin: 6px 0 2px; }
.fake-fill { position: absolute; top: -3px; width: 10px; height: 10px; border-radius: 50%;
  background: var(--acc); transform: translateX(-50%); }
</style>
