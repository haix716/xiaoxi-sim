"""sim 线程 → 事件循环 的单向数据通道：最新帧 / 最新遥测，单槽 + seq 去重。

铁律（见 sim.py docstring）：事件循环只从这里拉快照，sim 线程只往这里写，
没有跨线程回调、没有共享 MjData。
"""
import threading
import time
from typing import Literal

StreamName = Literal["main", "wrist"]


class FrameHub:
    """双流单槽：每流只存最新一帧 JPEG + seq。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._slot: dict[str, tuple[int, bytes]] = {"main": (0, b""), "wrist": (0, b"")}

    def put(self, stream: StreamName, jpeg: bytes) -> int:
        with self._lock:
            seq = self._slot[stream][0] + 1
            self._slot[stream] = (seq, jpeg)
            return seq

    def get(self, stream: StreamName, after_seq: int = -1) -> tuple[int, bytes] | None:
        """seq 没变（或还没帧）返回 None；否则 (seq, jpeg)。"""
        with self._lock:
            seq, jpeg = self._slot[stream]
            if seq != after_seq and jpeg:
                return seq, jpeg
            return None

    def seq(self, stream: StreamName) -> int:
        with self._lock:
            return self._slot[stream][0]


class TelemetryHub:
    """单槽最新遥测；seq 用于去重。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seq = 0
        self._msg: dict | None = None

    def put(self, msg: dict) -> int:
        with self._lock:
            self._seq += 1
            self._msg = msg
            return self._seq

    def get(self, after_seq: int = -1) -> tuple[int, dict] | None:
        with self._lock:
            if self._msg is None or self._seq == after_seq:
                return None
            return self._seq, self._msg


class Audience:
    """观众在场证明（省电三招①③的数据源）：
    持久观众（打开的 MJPEG 流 / WS 连接）在场 → 永不睡；
    否则看最近一次 REST 请求距今多久。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._viewers = 0
        self._last_activity = time.time()

    def note_activity(self) -> None:
        with self._lock:
            self._last_activity = time.time()

    def viewer_enter(self) -> None:
        with self._lock:
            self._viewers += 1
            self._last_activity = time.time()

    def viewer_exit(self) -> None:
        with self._lock:
            self._viewers = max(0, self._viewers - 1)
            self._last_activity = time.time()

    def idle_for(self) -> float:
        """距「可以睡」过了多久：有持久观众=0（永不睡）。"""
        with self._lock:
            if self._viewers > 0:
                return 0.0
            return time.time() - self._last_activity
