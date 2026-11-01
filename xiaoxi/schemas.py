"""API 的 pydantic 模型。"""
from pydantic import BaseModel, Field


class Joints(BaseModel):
    target_deg: list[float]
    actual_deg: list[float]


class StatusResponse(BaseModel):
    ok: bool = True
    mode: str
    ep: int
    frame: int
    frame_count: int
    speed: float
    paused: bool
    sim_hz: float
    joints: Joints


class EpisodeDTO(BaseModel):
    index: int
    length: int
    seconds: float
    tasks: list[str]


class ReplayBody(BaseModel):
    """POST /api/replay 的统一入口：全字段可选，给啥改啥。"""
    ep: int | None = None
    frame: int | None = Field(default=None, ge=0)
    speed: float | None = None
    paused: bool | None = None
