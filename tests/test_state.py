"""StateStore：线程安全状态机的全部转移规则。"""
import threading

import numpy as np
import pytest

from xiaoxi.state import StateStore

LIMITS_DEG = np.array([[-110, 110], [-100, 100], [-97, 97],
                       [-95, 95], [-157, 163], [-10, 100]])
LIMITS_RAD = np.deg2rad(LIMITS_DEG)
N = 948  # ep0 帧数


@pytest.fixture
def store() -> StateStore:
    return StateStore(limits_rad=LIMITS_RAD)


class TestManualCtrl:
    def test_clip_to_limits(self, store):
        store.set_manual_ctrl([-500.0, 0, 0, 0, 0, 500.0])
        deg = np.rad2deg(store.snapshot().manual_ctrl)
        assert deg == pytest.approx([-110.0, 0, 0, 0, 0, 100.0])

    def test_snapshot_is_copy(self, store):
        store.set_manual_ctrl([1.0] * 6)
        snap = store.snapshot()
        snap.manual_ctrl[:] = 9.9
        assert not np.allclose(store.snapshot().manual_ctrl, 9.9)


class TestMode:
    def test_enter_replay_resets_frame(self, store):
        store.set_mode("replay")
        store.advance_frame(N)
        assert store.snapshot().frame > 0
        store.set_mode("manual")
        store.set_mode("replay")  # 手动→回放真切换 → 从头放
        assert store.snapshot().frame == 0.0

    def test_replay_mode_noop_keeps_frame(self, store):
        """replay 内连发 set_mode（变速/seek 会经过）不打断进度。"""
        store.set_mode("replay")
        store.advance_frame(N)
        store.set_mode("replay")
        assert store.snapshot().frame == 1.0

    def test_manual_keeps_frame(self, store):
        store.set_mode("replay")
        store.advance_frame(N)          # frame -> 1.0
        store.set_mode("manual")
        store.advance_frame(N)
        assert store.snapshot().frame == 1.0  # manual 模式 frame 不前进


class TestReplay:
    def test_speed_clamp(self, store):
        store.set_speed(99.0)
        assert store.snapshot().speed == 4.0
        store.set_speed(0.0)
        assert 0.0 < store.snapshot().speed <= 4.0

    def test_seek_clamp_and_gen(self, store):
        store.select_episode(0)
        store.seek(500, N)
        s = store.snapshot()
        assert s.frame == 500.0
        assert s.seek_gen == 1
        store.seek(-50, N)
        store.seek(99999, N)
        s = store.snapshot()
        assert s.frame == N - 1
        assert s.seek_gen == 3

    def test_advance_wraps(self, store):
        store.select_episode(0)
        store.set_speed(2.0)
        for _ in range(N):
            store.advance_frame(N)
        f = store.snapshot().frame
        assert 0.0 <= f < N  # 环回不越界

    def test_select_episode_resets_frame(self, store):
        store.advance_frame(N)
        store.select_episode(5)
        assert store.snapshot().frame == 0.0
        assert store.snapshot().ep == 5


class TestMisc:
    def test_toggle_pause(self, store):
        assert store.toggle_pause() is True
        assert store.snapshot().paused
        assert store.toggle_pause() is False

    def test_reset_request(self, store):
        store.request_reset()
        assert store.snapshot().reset_req
        st = store.snapshot()
        st.reset_req = False  # 快照上改不影响内部
        assert store.snapshot().reset_req


class TestConcurrency:
    def test_hammer(self, store):
        """20 线程混合读写 2000 次：不死锁、不异常、不变量不破。"""
        errors = []

        def worker(k: int):
            try:
                for i in range(200):
                    store.set_manual_ctrl([float((k + i) % 90)] * 6)
                    store.seek(i % N, N)
                    store.set_mode("replay" if i % 2 else "manual")
                    store.advance_frame(N)
                    s = store.snapshot()
                    assert 0.0 <= s.frame < N
                    assert s.speed <= 4.0
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(k,)) for k in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        assert not errors
