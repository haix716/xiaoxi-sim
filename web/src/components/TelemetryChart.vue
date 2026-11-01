<script setup lang="ts">
// uPlot 关节曲线：6 条实际值实线 + 焦点关节的目标值虚线，20Hz 滚动 60s。
import { onMounted, onUnmounted, ref, watch } from 'vue'
import uPlot from 'uplot'
import { useTelemetry } from '@/composables/useTelemetry'
import { useUi } from '@/composables/useUi'

const { state } = useTelemetry()
const { ui, setFocusJoint } = useUi()
const el = ref<HTMLElement>()
const CHART_H = 200
const PALETTE = ['#e8b33d', '#4cc9f0', '#f72585', '#7ae582', '#ff9f1c', '#b28dff']

let plot: uPlot | null = null
let ro: ResizeObserver | null = null

function jointNames(): string[] {
  return [...(state.hello?.joints ?? ['shoulder_pan', 'shoulder_lift', 'elbow_flex',
    'wrist_flex', 'wrist_roll', 'gripper'])]
}

function build(): uPlot | null {
  if (!el.value) return null
  const names = jointNames()
  const focus = Math.min(ui.focusJoint, names.length - 1)
  const series: uPlot.Series[] = [{}]
  names.forEach((n, j) => {
    series.push({ label: n, stroke: PALETTE[j], width: 1.2 })
  })
  series.push({ label: `${names[focus]} 目标`, stroke: PALETTE[focus], dash: [6, 4], width: 1 })
  return new uPlot({
    width: el.value.clientWidth,
    height: CHART_H,
    legend: { show: true, live: true },
    cursor: { drag: { x: false, y: false } },
    scales: { x: { time: false } },
    axes: [
      { stroke: '#8b8f98', grid: { stroke: '#2c3038' }, size: 42, label: '秒' },
      { stroke: '#8b8f98', grid: { stroke: '#2c3038' }, size: 38, label: '°' },
    ],
    series,
  }, [], el.value)
}

function alignedData(): (number | null)[][] {
  const h = state.history
  const focus = Math.min(ui.focusJoint, Math.max(h.target.length - 1, 0))
  return [[...h.t], ...h.actual.map(a => [...a]), [...(h.target[focus] ?? [])]]
}

onMounted(() => {
  plot = build()
  ro = new ResizeObserver(() => {
    if (el.value && plot) plot.setSize({ width: el.value.clientWidth, height: CHART_H })
  })
  if (el.value) ro.observe(el.value)
})

watch(() => state.version, () => { if (plot) plot.setData(alignedData() as never) })

watch(() => ui.focusJoint, () => {
  plot?.destroy()
  plot = build()
  plot?.setData(alignedData() as never)
})

onUnmounted(() => { ro?.disconnect(); plot?.destroy() })
</script>

<template>
  <div class="chart">
    <div ref="el" class="plot"></div>
    <div class="chips">
      <span class="chips-label">目标线:</span>
      <button v-for="(n, i) in jointNames()" :key="n" class="chip"
        :class="{ focus: ui.focusJoint === i }" @click="setFocusJoint(i)">{{ n }}</button>
    </div>
  </div>
</template>

<style scoped>
.chart { margin-top: 10px; }
.plot :deep(.u-legend) { color: #c8ccd4; font-size: 10px; }
.chips { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; margin-top: 6px; }
.chips-label { color: var(--dim); font-size: 11px; }
.chip { background: var(--panel); color: var(--dim); border: 1px solid var(--line);
  border-radius: 10px; padding: 1px 8px; font-size: 11px; cursor: pointer; }
.chip.focus { border-color: var(--acc); color: var(--acc); }
</style>
