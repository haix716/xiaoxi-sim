"""API 层测试：TestClient + FakeRuntime 注入（不碰 GL，不起仿真线程）。"""
import pytest
from fastapi.testclient import TestClient

from xiaoxi.app import create_app
from xiaoxi.config import Settings

JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex",
          "wrist_flex", "wrist_roll", "gripper")


class FakeRuntime:
    def __init__(self):
        self.started = False
        self.wake_count = 0

    def start(self):
        self.started = True

    def stop(self):
        pass

    def wake(self):
        self.wake_count += 1

    @property
    def measured_hz(self):
        return 42.0


@pytest.fixture(scope="module")
def engine():
    fake = FakeRuntime()
    app = create_app(Settings(), runtime=fake)
    with TestClient(app) as client:
        yield client, fake, app.state.core


def test_lifespan_starts_runtime(engine):
    _, fake, _ = engine
    assert fake.started


def test_status_legacy_fields(engine):
    client, _, _ = engine
    s = client.get("/api/status").json()
    for k in ("mode", "ep", "frame", "paused"):
        assert k in s
    assert s["frame_count"] == 948
    assert s["sim_hz"] == 42.0
    assert len(s["joints"]["target_deg"]) == 6


def test_ctrl_bare_array_and_wake(engine):
    client, fake, _ = engine
    before = fake.wake_count
    r = client.post("/api/ctrl", json=[0.0, 10.0, -20.0, 30.0, -40.0, 50.0])
    assert r.json() == {"ok": True}
    assert fake.wake_count == before + 1


def test_ctrl_object_form(engine):
    client, _, _ = engine
    assert client.post("/api/ctrl", json={"angles": [0] * 6}).status_code == 200


def test_ctrl_bad_length(engine):
    client, _, _ = engine
    assert client.post("/api/ctrl", json=[1, 2, 3]).status_code == 422


def test_ctrl_non_numeric(engine):
    client, _, _ = engine
    assert client.post("/api/ctrl", json=["a"] * 6).status_code == 422


def test_mode_query_style(engine):
    client, _, _ = engine
    client.post("/api/mode?mode=replay&ep=3&speed=2")
    s = client.get("/api/status").json()
    assert (s["mode"], s["ep"], s["speed"]) == ("replay", 3, 2.0)


def test_mode_rejects_unknown(engine):
    client, _, _ = engine
    assert client.post("/api/mode?mode=warp").status_code == 422


def test_mode_rejects_unknown_episode(engine):
    client, _, _ = engine
    assert client.post("/api/mode?mode=replay&ep=99").status_code == 422


def test_replay_seek_clamped(engine):
    client, _, _ = engine
    r = client.post("/api/replay", json={"ep": 0, "frame": 99999}).json()
    assert r["frame"] == 947


def test_replay_paused_absolute(engine):
    client, _, _ = engine
    client.post("/api/replay", json={"ep": 0, "paused": True})
    assert client.get("/api/status").json()["paused"] is True
    client.post("/api/replay", json={"paused": False})
    assert client.get("/api/status").json()["paused"] is False


def test_pause_toggle(engine):
    client, _, _ = engine
    assert client.post("/api/pause").json()["paused"] is True
    assert client.post("/api/pause").json()["paused"] is False


def test_reset(engine):
    client, _, _ = engine
    assert client.post("/api/reset").json() == {"ok": True}


def test_episodes(engine):
    client, _, _ = engine
    eps = client.get("/api/episodes").json()
    assert len(eps) == 50
    assert eps[0]["length"] == 948
    assert eps[0]["seconds"] == pytest.approx(31.6, abs=0.1)
    assert any("Pick" in t for t in eps[0]["tasks"])


def test_config_joints_and_limits(engine):
    client, _, _ = engine
    cfg = client.get("/api/config").json()
    assert tuple(cfg["joints"]) == JOINTS
    assert len(cfg["limits_deg"]) == 6
    # wrist_roll 是不对称限位 [-157, 163]
    assert cfg["limits_deg"][4] == pytest.approx([-157, 163], abs=1.0)


def test_ws_hello_and_telemetry(engine):
    client, _, core = engine
    with client.websocket_connect("/ws/telemetry") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        assert tuple(hello["joints"]) == JOINTS
        assert hello["episode_count"] == 50
        core.telemetry.put({"type": "telemetry", "frame": 7.0})
        msg = ws.receive_json()
        assert msg["type"] == "telemetry"
        assert msg["frame"] == 7.0


def test_dns_rebinding_blocked(engine):
    """Host 白名单：外部域名打到 127.0.0.1 要被 403。"""
    client, _, _ = engine
    r = client.get("/api/status", headers={"Host": "evil.example.com:8777"})
    assert r.status_code == 403
