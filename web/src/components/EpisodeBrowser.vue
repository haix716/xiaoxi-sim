<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/rest'
import { useTelemetry } from '@/composables/useTelemetry'
import type { Episode } from '@/types'

const props = defineProps<{ episodes: Episode[] }>()
const { state } = useTelemetry()
const query = ref('')

function filtered(): Episode[] {
  const q = query.value.trim()
  return q === '' ? props.episodes
    : props.episodes.filter(e => String(e.index).includes(q) || e.tasks.some(t => t.toLowerCase().includes(q.toLowerCase())))
}
</script>

<template>
  <div class="episodes">
    <div class="head">
      <span class="title">示教分集</span>
      <input v-model="query" placeholder="筛选 #" class="filter" />
    </div>
    <div class="list">
      <button v-for="e in filtered()" :key="e.index" class="ep"
        :class="{ active: state.latest?.mode === 'replay' && state.latest?.ep === e.index }"
        @click="api.playEpisode(e.index)">
        <span class="idx">#{{ e.index }}</span>
        <span class="meta">{{ e.length }} 帧 · {{ e.seconds.toFixed(0) }}s</span>
        <span class="task">{{ e.tasks[0] ?? '' }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.episodes { display: flex; flex-direction: column; min-height: 0; }
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.title { color: var(--dim); font-size: 12px; }
.filter { width: 110px; background: var(--panel); border: 1px solid var(--line); border-radius: 6px;
  color: var(--fg); font-size: 12px; padding: 3px 8px; }
.list { overflow-y: auto; display: flex; flex-direction: column; gap: 4px; min-height: 0; }
.ep { display: grid; grid-template-columns: auto 1fr; grid-template-rows: auto auto; column-gap: 8px;
  text-align: left; background: var(--panel); border: 1px solid var(--line); border-radius: 6px;
  padding: 5px 10px; cursor: pointer; color: var(--fg); }
.ep:hover { border-color: var(--dim); }
.ep.active { border-color: var(--acc); }
.idx { color: var(--acc); font-size: 12px; font-weight: 600; }
.meta { color: var(--dim); font-size: 11px; text-align: right; font-variant-numeric: tabular-nums; }
.task { grid-column: 1 / -1; color: var(--dim); font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
