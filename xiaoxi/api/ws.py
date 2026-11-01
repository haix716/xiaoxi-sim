"""WS 遥测：连接即 hello，之后按 telemetry_hz 推最新快照。

背压：每连接独立协程直接拉 TelemetryHub 单槽（latest 语义）——慢客户端
只拖慢自己，永远拿到的是最新值，天然丢旧留新，不需要广播队列。
"""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/telemetry")
async def telemetry_ws(ws: WebSocket):
    await ws.accept()
    c = ws.app.state.core
    c.audience.viewer_enter()
    try:
        await ws.send_json({
            "type": "hello",
            "push_hz": c.settings.telemetry_hz,
            "fps": c.dataset.fps,
            "joints": list(c.joints),
            "limits_deg": c.limits_deg,
            "episode_count": len(c.dataset.episode_list()),
        })
        last = -1
        period = 1.0 / c.settings.telemetry_hz
        while True:
            got = c.telemetry.get(after_seq=last)
            if got:
                last, msg = got
                await ws.send_json(msg)
            await asyncio.sleep(period)
    except WebSocketDisconnect:
        pass
    finally:
        c.audience.viewer_exit()
