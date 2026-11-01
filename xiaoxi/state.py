"""线程安全控制状态机：REST 写命令、sim 线程读快照，唯一交汇点。

一把 RLock 包住所有转移；每个方法=一个原子转移。帧号 frame 为 float——
speed>1 时每 tick 前进 speed（沿用旧版语义）。单位约定：manual_ctrl 存弧度
（sim 原生），API 层进出的角度转换用 units。
"""
import copy
import threading
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from xiaoxi.units import deg_to_rad

Mode = Literal["manual", "replay"]
MAX_SPEED = 4.0


@dataclass
class SimState:
    mode: Mode = "manual"
    ep: int = 0
    frame: float = 0.0
    speed: float = 1.0
    paused: bool = False
    manual_ctrl: np.ndarray = field(default_factory=lambda: np.zeros(6, dtype=np.float64))
    reset_req: bool = False
    seek_gen: int = 0  # 暂停中被 seek 的代数号，sim 线程据此补一帧预览


class StateStore:
    def __init__(self, limits_rad: np.ndarray):
        self._limits = np.asarray(limits_rad, dtype=np.float64)  # (6,2) ctrlrange 弧度
        self._state = SimState()
        self._lock = threading.RLock()

    def snapshot(self) -> SimState:
        with self._lock:
            s = copy.copy(self._state)
            s.manual_ctrl = self._state.manual_ctrl.copy()
            return s

    # ---- 命令侧（事件循环调用） ----

    def set_manual_ctrl(self, deg) -> None:
        with self._lock:
            rad = deg_to_rad(deg)
            self._state.manual_ctrl = np.clip(rad, self._limits[:, 0], self._limits[:, 1])

    def set_mode(self, mode: Mode) -> None:
        with self._lock:
            self._state.mode = mode
            if mode == "replay":
                self._state.frame = 0.0  # 兼容旧行为：进回放从头放

    def select_episode(self, ep: int) -> None:
        with self._lock:
            self._state.ep = int(ep)
            self._state.frame = 0.0

    def set_speed(self, speed: float) -> None:
        with self._lock:
            self._state.speed = min(max(float(speed), 1e-3), MAX_SPEED)

    def seek(self, frame: int, length: int) -> None:
        with self._lock:
            self._state.frame = float(np.clip(int(frame), 0, max(length - 1, 0)))
            self._state.seek_gen += 1

    def toggle_pause(self) -> bool:
        with self._lock:
            self._state.paused = not self._state.paused
            return self._state.paused

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            self._state.paused = bool(paused)

    def request_reset(self) -> None:
        with self._lock:
            self._state.reset_req = True

    # ---- sim 线程侧 ----

    def advance_frame(self, length: int) -> None:
        with self._lock:
            if self._state.mode == "replay" and length > 0:
                self._state.frame = (self._state.frame + self._state.speed) % length

    def complete_reset(self) -> None:
        """sim 线程执行完复位后调用：清标记、帧号归零、手动目标归零（旧版同款）。"""
        with self._lock:
            self._state.reset_req = False
            self._state.frame = 0.0
            self._state.manual_ctrl[:] = 0.0
