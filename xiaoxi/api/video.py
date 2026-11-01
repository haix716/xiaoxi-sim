"""MJPEG 双流：multipart/x-mixed-replace。yield 即 flush（uvicorn chunked 直出），
首帧前先 yield b"" 立刻提交响应头——对应旧手写版「首帧前 flush 头」的语义。
注意：不得给这些响应套压缩中间件（会缓冲破坏流）。"""
import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter()


async def _mjpeg(core, stream: str, hz: int):
    core.audience.viewer_enter()  # 持久观众：流开着就不睡（省电三招①）
    try:
        yield b""
        last = -1
        period = 1.0 / hz
        while True:
            got = core.frames.get(stream, after_seq=last)
            if got:
                seq, jpg = got
                last = seq
                yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                       + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")
            await asyncio.sleep(period)  # 客户端断开 → CancelledError → finally
    finally:
        core.audience.viewer_exit()


def _video(request: Request, stream: str) -> StreamingResponse:
    c = request.app.state.core
    hz = c.settings.sim_hz if stream == "main" else c.settings.wrist_hz
    return StreamingResponse(
        _mjpeg(c, stream, hz),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/video")  # 旧路径别名，兼容书签
def video_legacy(request: Request):
    return _video(request, "main")


@router.get("/video/main")
def video_main(request: Request):
    return _video(request, "main")


@router.get("/video/wrist")
def video_wrist(request: Request):
    return _video(request, "wrist")
