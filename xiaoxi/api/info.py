"""只读信息端点：status / config / episodes。"""
from fastapi import APIRouter, Request

from xiaoxi.schemas import EpisodeDTO, Joints, StatusResponse

router = APIRouter()


def status_payload(core) -> StatusResponse:
    """status 的唯一构造处，control.py 的 /api/replay 也复用。"""
    st = core.store.snapshot()
    got = core.telemetry.get()
    tele = got[1] if got else {"target_deg": [0.0] * 6, "actual_deg": [0.0] * 6}
    return StatusResponse(
        mode=st.mode, ep=st.ep, frame=int(st.frame),
        frame_count=core.dataset.episode_length(st.ep),
        speed=st.speed, paused=st.paused, sim_hz=core.runtime.measured_hz,
        joints=Joints(target_deg=tele["target_deg"], actual_deg=tele["actual_deg"]),
    )


@router.get("/api/status", response_model=StatusResponse)
def status(request: Request):
    return status_payload(request.app.state.core)


@router.get("/api/config")
def config(request: Request):
    c = request.app.state.core
    return {
        "joints": list(c.joints),
        "limits_deg": c.limits_deg,
        "fps": c.dataset.fps,
        "sim_hz": c.settings.sim_hz,
        "telemetry_hz": c.settings.telemetry_hz,
        "streams": {"main": "/video/main", "wrist": "/video/wrist"},
    }


@router.get("/api/episodes", response_model=list[EpisodeDTO])
def episodes(request: Request):
    ds = request.app.state.core.dataset
    return [EpisodeDTO(index=e.index, length=e.length, seconds=round(e.seconds, 1),
                       tasks=list(e.tasks)) for e in ds.episode_list()]
