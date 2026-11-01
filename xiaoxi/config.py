"""配置：pydantic-settings，环境变量前缀 XIAOXI_（如 XIAOXI_PORT=9000）。"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="XIAOXI_")

    host: str = "127.0.0.1"
    port: int = 8777
    open_browser: bool = False

    # 仿真与渲染
    sim_hz: int = 30
    physics_substeps: int = 6            # 5ms timestep × 6 ≈ 30fps
    render_width: int = 640
    render_height: int = 420
    jpeg_quality: int = 78
    wrist_width: int = 320               # 与主流 640:420 同比例
    wrist_height: int = 210
    wrist_hz: int = 15                   # PiP 降频省 CPU
    wrist_camera: str = "wrist_cam"

    # 遥测
    telemetry_hz: int = 20

    # 路径（相对 root）
    root: Path = PROJECT_ROOT
    model_path: Path = Path("menagerie-so101/scene_box.xml")
    dataset_dir: Path = Path("data-maxt90")

    # 省电三招（2026-10-15 引入，语义保留）
    idle_sleep_seconds: float = 60.0     # ① 观众检测：60s 无人看 → 整循环睡
    still_frames_threshold: int = 3      # ② 静止检测：连续 N tick 没动 → 跳渲染

    @property
    def model_xml(self) -> Path:
        return self.root / self.model_path

    @property
    def dataset_root(self) -> Path:
        return self.root / self.dataset_dir

    @property
    def web_dist(self) -> Path:
        return self.root / "web" / "dist"
