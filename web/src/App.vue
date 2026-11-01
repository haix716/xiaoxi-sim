<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api, fetchJson } from '@/api/rest'
import { useTelemetry } from '@/composables/useTelemetry'
import { useShortcuts } from '@/composables/useShortcuts'
import { useUi } from '@/composables/useUi'
import StatusBar from '@/components/StatusBar.vue'
import VideoPanel from '@/components/VideoPanel.vue'
import JointSliders from '@/components/JointSliders.vue'
import TransportBar from '@/components/TransportBar.vue'
import EpisodeBrowser from '@/components/EpisodeBrowser.vue'
import TelemetryChart from '@/components/TelemetryChart.vue'
import type { Config, Episode, Status } from '@/types'

const { state, connect, disconnect } = useTelemetry()
const { ui, togglePip } = useUi()
useShortcuts()

const config = ref<Config | null>(null)
const episodes = ref<Episode[]>([])
const fallbackMode = ref<'manual' | 'replay'>('manual')

const mode = computed(() => state.latest?.mode ?? fallbackMode.value)

// WS 断线兜底：退回 1s 轮询（旧习惯天然兜底）
let pollTimer: number | undefined

onMounted(async () => {
  config.value = await fetchJson<Config>('/api/config')
  episodes.value = await fetchJson<Episode[]>('/api/episodes')
  connect()
  pollTimer = window.setInterval(async () => {
    if (!state.connected) {
      try {
        const s = await fetchJson<Status>('/api/status')
        fallbackMode.value = s.mode
      } catch { /* 服务重启中，下一轮再试 */ }
    }
  }, 1000)
})

onUnmounted(() => {
  disconnect()
  window.clearInterval(pollTimer)
})
</script>

<template>
  <div class="app">
    <header>
      <h1>小犀 · 示教台</h1>
      <StatusBar />
    </header>
    <main>
      <section class="col video-col">
        <VideoPanel />
      </section>
      <section class="col ctrl-col">
        <div class="mode-row">
          <button :class="{ on: mode === 'manual' }" @click="api.setMode('manual')">手动</button>
          <button :class="{ on: mode === 'replay' }" @click="api.setMode('replay')">回放</button>
          <span class="spacer" />
          <button @click="api.reset()">复位</button>
          <button :class="{ on: ui.pip }" @click="togglePip()" title="快捷键 W">PiP</button>
        </div>
        <JointSliders v-if="config" :config="config" />
        <TransportBar v-if="mode === 'replay'" />
      </section>
      <section class="col data-col">
        <EpisodeBrowser :episodes="episodes" />
        <TelemetryChart />
      </section>
    </main>
  </div>
</template>
