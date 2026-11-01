"""命令端点：ctrl / mode / replay / reset / pause。写完都 wake()（门铃）。"""
from fastapi import APIRouter, HTTPException, Request

from xiaoxi.api.info import status_payload
from xiaoxi.schemas import ReplayBody, StatusResponse

router = APIRouter()

_VALID_MODES = ("manual", "replay")


def _core(request: Request):
    return request.app.state.core


def _episode_length_or_422(core, ep: int) -> int:
    try:
        return core.dataset.episode_length(ep)
    except KeyError:
        raise HTTPException(422, f"episode {ep} 不在数据集里（共 "
                                 f"{len(core.dataset.episode_list())} 集）") from None


@router.post("/api/ctrl")
async def ctrl(request: Request):
    """六关节角度（度）。兼容两种 body：裸数组 [6]（旧版）或 {"angles": [6]}。"""
    c = _core(request)
    try:
        body = await request.json()
    except Exception:
        body = None
    angles = body if isinstance(body, list) else (body or {}).get("angles") \
        if isinstance(body, dict) else None
    if not isinstance(angles, (list, tuple)) or len(angles) != 6:
        raise HTTPException(422, '需要 6 元素角度数组（度）：[...] 或 {"angles": [...]}')
    try:
        c.store.set_manual_ctrl(angles)
    except (TypeError, ValueError):
        raise HTTPException(422, "角度必须是数字") from None
    c.runtime.wake()
    return {"ok": True}


@router.post("/api/mode")
async def mode(request: Request, mode: str | None = None,
               ep: int | None = None, speed: float | None = None):
    """旧版 query 风格入口，语义保留。"""
    c = _core(request)
    if mode is not None:
        if mode not in _VALID_MODES:
            raise HTTPException(422, f"mode 只能是 {_VALID_MODES}")
        c.store.set_mode(mode)
    if ep is not None:
        _episode_length_or_422(c, ep)
        c.store.select_episode(ep)
    if speed is not None:
        c.store.set_speed(speed)
    c.runtime.wake()
    return {"ok": True}


@router.post("/api/replay", response_model=StatusResponse)
async def replay(body: ReplayBody, request: Request):
    """回放统一入口：调用即进入 replay 模式；选集 / 变速 / seek / 暂停全可选。"""
    c = _core(request)
    c.store.set_mode("replay")
    if body.ep is not None:
        _episode_length_or_422(c, body.ep)
        c.store.select_episode(body.ep)
    if body.speed is not None:
        c.store.set_speed(body.speed)
    if body.frame is not None:
        st = c.store.snapshot()
        n = _episode_length_or_422(c, st.ep)
        c.store.seek(body.frame, n)
    if body.paused is not None:
        c.store.set_paused(body.paused)
    c.runtime.wake()
    return status_payload(c)


@router.post("/api/reset")
async def reset(request: Request):
    c = _core(request)
    c.store.request_reset()
    c.runtime.wake()
    return {"ok": True}


@router.post("/api/pause")
async def pause(request: Request):
    c = _core(request)
    paused = c.store.toggle_pause()
    c.runtime.wake()
    return {"paused": paused}
