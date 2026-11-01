// 跨组件 UI 状态（PiP 开关等），无持久化需求，不值得上 pinia。
import { reactive, readonly } from 'vue'

const ui = reactive({
  pip: true,
  focusJoint: 0, // 曲线图高亮的关节（显示其目标虚线）
})

export function useUi() {
  return {
    ui: readonly(ui),
    togglePip: () => { ui.pip = !ui.pip },
    setFocusJoint: (j: number) => { ui.focusJoint = j },
  }
}
