"""create_app：装配 Core + lifespan + 路由 + 静态托管。

模块级 `app` 仅供 uvicorn 命令行（xiaoxi.app:app）用；测试用
create_app(runtime=FakeRuntime()) 注入假 runtime，不碰 GL。
"""
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Protocol

import mujoco
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from xiaoxi.api import control, info, video, ws
from xiaoxi.config import Settings
from xiaoxi.dataset import EpisodeDataset
from xiaoxi.frames import Audience, FrameHub, TelemetryHub
from xiaoxi.sim import SimRuntime
from xiaoxi.state import StateStore
from xiaoxi.units import rad_to_deg

log = logging.getLogger("xiaoxi")


class RuntimeLike(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def wake(self) -> None: ...

    @property
    def measured_hz(self) -> float: ...


@dataclass
class Core:
    """API 层看得见的全部家当；MjData/Renderer 永远不在其中（铁律 2）。"""
    settings: Settings
    dataset: EpisodeDataset
    store: StateStore
    frames: FrameHub
    telemetry: TelemetryHub
    audience: Audience
    runtime: RuntimeLike
    joints: tuple[str, ...]
    limits_deg: list[list[float]]


def create_app(settings: Settings | None = None,
               runtime: RuntimeLike | None = None) -> FastAPI:
    s = settings or Settings()
    dataset = EpisodeDataset(s.dataset_root)
    model = mujoco.MjModel.from_xml_path(str(s.model_xml))  # 纯 CPU，无 GL；传给 sim 线程
    limits = model.actuator_ctrlrange[:6].copy()
    store = StateStore(limits_rad=limits)
    frames, telemetry, audience = FrameHub(), TelemetryHub(), Audience()
    rt = runtime or SimRuntime(s, model, dataset, store, frames, telemetry, audience)
    core = Core(settings=s, dataset=dataset, store=store, frames=frames,
                telemetry=telemetry, audience=audience, runtime=rt,
                joints=EpisodeDataset.JOINTS,
                limits_deg=rad_to_deg(limits).round(2).tolist())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        rt.start()
        log.info("小犀示教台就绪: http://%s:%s", s.host, s.port)
        yield
        rt.stop()  # join sim 线程，Renderer 在线程内 close（dev reload 安全退出）
        log.info("已关停")

    app = FastAPI(title="小犀示教台", version=s.version if hasattr(s, "version") else "0.1.0",
                  lifespan=lifespan)
    app.state.core = core

    # Vite dev（5173）直连后端端口时免 CORS 拦截
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"], allow_headers=["*"],
    )

    @app.middleware("http")
    async def doorbell(request: Request, call_next):
        core.audience.note_activity()  # 门铃：有请求=有观众（省电三招③）
        return await call_next(request)

    for r in (info.router, control.router, video.router, ws.router):
        app.include_router(r)

    if s.web_dist.exists():
        app.mount("/", StaticFiles(directory=s.web_dist, html=True), name="web")
    else:
        log.warning("前端 dist 不存在（%s）——只提供 API。开发期用 vite dev，"
                    "或 cd web && npm run build。", s.web_dist)
    return app


app = create_app()
