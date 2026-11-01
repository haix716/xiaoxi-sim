<script setup lang="ts">
import { ref } from 'vue'
import { videoSrc } from '@/composables/useVideoSrc'
import { useUi } from '@/composables/useUi'

const { ui } = useUi()
const stalled = ref(false)
const lastLoad = ref(Date.now())

// MJPEG 断流检测：帧不再到达（onload 不触发）超 6s 视为断流，闪一下 src 重连
setInterval(() => {
  const img = document.getElementById('mainVideo') as HTMLImageElement | null
  if (img && img.src && Date.now() - lastLoad.value > 6000 && !stalled.value) {
    stalled.value = true
    img.src = img.src // 触发重连
  }
}, 3000)

function onLoad() {
  lastLoad.value = Date.now()
  stalled.value = false
}
</script>

<template>
  <div class="video-wrap">
    <img id="mainVideo" :src="videoSrc('/video/main')" alt="仿真画面" @load="onLoad" @error="stalled = true" />
    <div v-if="stalled" class="overlay">重连中…</div>
    <div v-if="ui.pip" class="pip">
      <img :src="videoSrc('/video/wrist')" alt="腕部相机" @error="($event.target as HTMLImageElement).style.opacity = '0.2'" />
      <span class="pip-tag">wrist</span>
    </div>
  </div>
</template>

<style scoped>
.video-wrap { position: relative; border-radius: 8px; overflow: hidden; background: #000; }
.video-wrap img { display: block; width: 100%; }
.overlay { position: absolute; inset: 0; display: grid; place-items: center;
  background: rgba(0,0,0,.6); color: var(--acc); font-size: 13px; }
.pip { position: absolute; right: 10px; bottom: 10px; width: 32%; max-width: 240px;
  border: 1px solid var(--line); border-radius: 6px; overflow: hidden; background: #000; }
.pip img { display: block; width: 100%; }
.pip-tag { position: absolute; left: 6px; bottom: 4px; font-size: 10px; color: #fff;
  text-shadow: 0 1px 2px #000; }
</style>
