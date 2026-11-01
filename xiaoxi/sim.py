"""SimRuntime —— 物理+渲染线程，整个后端唯一摸 MuJoCo 对象的地方。

GL 三铁律（macOS 坑账，违反即静默挂死）：
1. mujoco.Renderer 的创建与 close() 只发生在本线程内；
2. 事件循环线程永远不碰 MjData/Renderer——命令经 StateStore 下行，
   快照经 FrameHub/TelemetryHub 上行；MjModel 加载后不可变，跨线程只读
   元数据（限位表）安全，但也仅此而已；
3. 本线程不调用任何 asyncio API。

省电三招（2026-10-15 引入，语义原样迁移）：
① 观众检测：无人看（无 MJPEG 流/WS 连接，且 idle_sleep_seconds 内无 REST 请求）
   → 整循环 1s 粒度睡觉，有人来再醒；
② 静止检测：qpos 连续 still_frames_threshold tick 没动 → 跳过渲染复用上一帧，
   静止期降到 ~1fps 存照防慢漂移时画面陈旧；心跳（mj_step）照常；
③ 门铃：API 层任何命令后 wake()，立刻醒、立刻 tick（滑条零延迟）。
"""
import io
import logging
import threading
import time

import mujoco
import numpy as np
from PIL import Image

from xiaoxi.config import Settings
from xiaoxi.dataset import EpisodeDataset
from xiaoxi.frames import Audience, FrameHub, TelemetryHub
from xiaoxi.state import StateStore
from xiaoxi.units import deg_to_rad, rad_to_deg

log = logging.getLogger(__name__)

STILL_QPOS_EPS = 1e-4  # 关节角变化阈值（弧度），低于视为没动


def encode_jpeg(img: np.ndarray, quality: int) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


class SimRuntime:
    """持有 MjModel/MjData/双 Renderer 的 daemon 线程。start()/stop() 由 lifespan 调。"""

    def __init__(self, settings: Settings, model: "mujoco.MjModel",
                 dataset: EpisodeDataset, store: StateStore, frames: FrameHub,
                 telemetry: TelemetryHub, audience: Audience) -> None:
        self._s = settings
        self._model = model  # 由 app 层加载后传入（不可变，跨线程只读安全）
        self._dataset = dataset
        self._store = store
        self._frames = frames
        self._telemetry = telemetry
        self._audience = audience
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self.measured_hz = 0.0  # 实测循环频率，status 展示用（GIL 下裸读安全）

    # ---- 生命周期 ----

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="xiaoxi-sim", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def wake(self) -> None:
        """门铃：API 命令后调用，立刻进入下一 tick。"""
        self._wake.set()

    # ---- 线程体 ----

    def _run(self) -> None:
        s = self._s
        model = self._model
        data = mujoco.MjData(model)  # MjData 线程私有，在本线程创建
        mujoco.mj_forward(model, data)
        renderer_main = mujoco.Renderer(model, height=s.render_height, width=s.render_width)
        renderer_wrist = mujoco.Renderer(model, height=s.wrist_height, width=s.wrist_width)

        period = 1.0 / s.sim_hz
        wrist_every = max(1, round(s.sim_hz / max(s.wrist_hz, 1)))
        next_t = time.time()
        prev_qpos: np.ndarray | None = None
        still = 0
        tick = 0
        last_seek_gen = -1
        hz_window_start, hz_window_ticks = time.time(), 0

        try:
            while not self._stop.is_set():
                # ① 观众检测：没人看 → 1s 粒度睡，门铃可打断
                if self._audience.idle_for() > s.idle_sleep_seconds:
                    self._wake.wait(1.0)
                    self._wake.clear()
                    next_t = time.time()
                    prev_qpos, still = None, 0
                    continue

                st = self._store.snapshot()

                # 复位（旧版语义：qpos/qvel 清零、帧号归零、手动目标归零）
                if st.reset_req:
                    data.qpos[:] = 0
                    data.qvel[:] = 0
                    mujoco.mj_forward(model, data)
                    self._store.complete_reset()
                    st = self._store.snapshot()
                    prev_qpos, still = None, 0  # 复位后画面必变，重置静止检测

                if not st.paused:
                    if st.mode == "replay":
                        acts = self._dataset.actions(st.ep)
                        n = len(acts)
                        if n:
                            data.ctrl[:] = deg_to_rad(acts[int(st.frame) % n])
                            self._store.advance_frame(n)
                        else:
                            data.ctrl[:] = 0
                    else:
                        data.ctrl[:] = st.manual_ctrl
                    for _ in range(s.physics_substeps):
                        mujoco.mj_step(model, data)
                elif st.mode == "replay" and st.seek_gen != last_seek_gen:
                    # 暂停中拖进度条：mj_forward 不推物理，只摆位补一帧预览
                    acts = self._dataset.actions(st.ep)
                    if len(acts):
                        data.ctrl[:] = deg_to_rad(acts[int(st.frame) % len(acts)])
                        mujoco.mj_forward(model, data)
                last_seek_gen = st.seek_gen

                # 实测循环频率（每秒结算一次，status 展示用）
                hz_window_ticks += 1
                now = time.time()
                if now - hz_window_start >= 1.0:
                    self.measured_hz = round(hz_window_ticks / (now - hz_window_start), 1)
                    hz_window_start, hz_window_ticks = now, 0

                # ② 静止检测：没动就不拍照，浏览器继续看上一帧
                qp = np.asarray(data.qpos).copy()
                moved = prev_qpos is None or np.max(np.abs(qp - prev_qpos)) >= STILL_QPOS_EPS
                still = 0 if moved else still + 1
                prev_qpos = qp
                if still > s.still_frames_threshold and (still % s.sim_hz):
                    next_t = self._tick_pace(next_t, period)
                    continue

                renderer_main.update_scene(data, camera=-1)
                img_main = renderer_main.render()
                seq_main = self._frames.put("main", encode_jpeg(img_main, s.jpeg_quality))
                seq_wrist = self._frames.seq("wrist")
                if tick % wrist_every == 0:
                    renderer_wrist.update_scene(data, camera=s.wrist_camera)
                    seq_wrist = self._frames.put(
                        "wrist", encode_jpeg(renderer_wrist.render(), s.jpeg_quality))
                tick += 1

                self._telemetry.put({
                    "type": "telemetry",
                    "t": int(time.time() * 1000),
                    "mode": st.mode, "ep": st.ep,
                    "frame": round(st.frame, 2), "frame_count": self._dataset.episode_length(st.ep),
                    "speed": st.speed, "paused": st.paused,
                    "target_deg": [round(v, 2) for v in rad_to_deg(data.ctrl)],
                    "actual_deg": [round(v, 2) for v in rad_to_deg(data.qpos[:6])],
                    "img_seq": {"main": seq_main, "wrist": seq_wrist},
                })

                next_t = self._tick_pace(next_t, period)
        finally:
            # 铁律 1：谁创建谁销毁，都在本线程
            renderer_main.close()
            renderer_wrist.close()
            log.info("sim 线程退出")

    # ---- 节拍 ----

    def _tick_pace(self, next_t: float, period: float) -> float:
        next_t += period
        dt = next_t - time.time()
        if dt > 0:
            self._wake.wait(dt)  # 睡到点或被门铃叫醒
            self._wake.clear()
        else:
            next_t = time.time()  # 掉帧就重对表
        return next_t
