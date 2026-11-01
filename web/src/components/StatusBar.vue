<script setup lang="ts">
import { computed } from 'vue'
import { useTelemetry } from '@/composables/useTelemetry'

const { state } = useTelemetry()
const t = computed(() => state.latest)
const modeLabel = computed(() =>
  t.value?.mode === 'replay' ? `回放 · 第 ${t.value.ep} 集` : '手动')
</script>

<template>
  <div class="statusbar">
    <span class="chip" :class="t?.mode">{{ modeLabel }}</span>
    <span v-if="t?.mode === 'replay'" class="kv">帧 {{ Math.round(t.frame) }}/{{ t.frame_count }}</span>
    <span v-if="t?.mode === 'replay'" class="kv">{{ t.speed }}x</span>
    <span v-if="t?.paused" class="chip paused">已暂停</span>
    <span class="kv">{{ t ? `${t.img_seq.main}帧` : '…' }}</span>
    <span class="dot" :class="{ on: state.connected }" :title="state.connected ? '遥测在线' : '重连中'" />
  </div>
</template>

<style scoped>
.statusbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.kv { color: var(--dim); font-size: 12px; font-variant-numeric: tabular-nums; }
.chip { font-size: 11px; padding: 1px 8px; border-radius: 10px; border: 1px solid var(--line); color: var(--dim); }
.chip.replay { border-color: var(--acc); color: var(--acc); }
.chip.paused { border-color: #e5484d; color: #e5484d; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: #e5484d; }
.dot.on { background: #46a758; }
</style>
