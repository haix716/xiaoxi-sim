// 键盘快捷键：Space 暂停 / R 复位 / M 手动 / P 回放 / ←→ 逐帧 / Shift+←→ ±1s / W 开关 PiP
import { onMounted, onUnmounted } from 'vue'
import { api } from '@/api/rest'
import { useTelemetry } from '@/composables/useTelemetry'
import { useUi } from '@/composables/useUi'

export function useShortcuts() {
  const { state } = useTelemetry()
  const { togglePip } = useUi()

  async function step(frames: number) {
    const t = state.latest
    if (!t || t.mode !== 'replay') return
    await api.seek(Math.round(t.frame) + frames)
  }

  function onKey(e: KeyboardEvent) {
    const tag = (e.target as HTMLElement)?.tagName
    if (tag === 'INPUT' || tag === 'BUTTON' || tag === 'SELECT' || tag === 'TEXTAREA') return
    switch (e.key) {
      case ' ': e.preventDefault(); api.togglePause(); break
      case 'r': case 'R': api.reset(); break
      case 'm': case 'M': api.setMode('manual'); break
      case 'p': case 'P': api.setMode('replay'); break
      case 'ArrowLeft': e.preventDefault(); step(e.shiftKey ? -30 : -1); break
      case 'ArrowRight': e.preventDefault(); step(e.shiftKey ? 30 : 1); break
      case 'w': case 'W': togglePip(); break
    }
  }

  onMounted(() => window.addEventListener('keydown', onKey))
  onUnmounted(() => window.removeEventListener('keydown', onKey))
}
