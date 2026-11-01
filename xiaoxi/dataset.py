"""LeRobot v3.0 parquet 数据集加载：动作/状态（度）+ 分集索引 O(1) 切片。

被 xiaoxi.sim（网页示教台回放）和 回放示教.py（mjpython viewer）共用。
关节顺序与真臂一字不差，见 JOINTS。
"""
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyarrow
import pyarrow.parquet as pq


@dataclass(frozen=True)
class EpisodeMeta:
    index: int
    length: int
    seconds: float
    tasks: tuple[str, ...]


def _read_sorted(root: Path, pattern: str) -> pyarrow.Table:
    files = sorted(root.glob(pattern))
    if not files:
        raise FileNotFoundError(f"{root}/{pattern} 下没有 parquet")
    return pq.read_table(files[0]) if len(files) == 1 else sum(
        (pq.read_table(f) for f in files[1:]), pq.read_table(files[0]))


class EpisodeDataset:
    JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex",
              "wrist_flex", "wrist_roll", "gripper")

    def __init__(self, root: Path):
        self.root = Path(root)
        info_path = self.root / "meta/info.json"
        if not info_path.exists():
            raise FileNotFoundError(f"缺少 {info_path}（不是 LeRobot 数据集目录？）")
        self._info = json.loads(info_path.read_text(encoding="utf-8"))

        data = _read_sorted(self.root, "data/chunk-*/file-*.parquet").to_pydict()
        order = np.lexsort((np.asarray(data["index"]), np.asarray(data["episode_index"])))
        self._ep = np.asarray(data["episode_index"])[order]
        self._actions = np.asarray(data["action"], dtype=np.float32)[order]
        self._states = np.asarray(data["observation.state"], dtype=np.float32)[order]

        meta = _read_sorted(self.root, "meta/episodes/chunk-*/file-*.parquet").to_pydict()
        self._meta_tasks = {int(i): tuple(t) for i, t in
                            zip(meta["episode_index"], meta.get("tasks", []))}

    @property
    def fps(self) -> int:
        return int(self._info.get("fps", 30))

    def episode_list(self) -> list[EpisodeMeta]:
        return [EpisodeMeta(int(ep), int(n), n / self.fps, self._meta_tasks.get(int(ep), ()))
                for ep, n in self._lengths()]

    def _lengths(self):
        """[(episode_index, 行数)]，以数据行数为准（meta 的 length 只作参考）。"""
        if len(self._ep) == 0:
            return []
        heads = np.flatnonzero(np.diff(self._ep)) + 1
        starts = np.concatenate(([0], heads))
        ends = np.concatenate((heads, [len(self._ep)]))
        return zip(self._ep[starts].tolist(), (ends - starts).tolist())

    def episode_length(self, ep: int) -> int:
        rows = self._slice(ep)
        return rows.stop - rows.start

    def _slice(self, ep: int) -> slice:
        start, stop = np.searchsorted(self._ep, [int(ep), int(ep) + 1])
        if start == stop:
            raise KeyError(f"episode {ep} 不在数据集里")
        return slice(int(start), int(stop))

    def actions(self, ep: int) -> np.ndarray:
        """(N,6) float32，单位=度。返回大数组的视图，勿原地改写。"""
        return self._actions[self._slice(ep)]

    def states(self, ep: int) -> np.ndarray:
        """observation.state，(N,6) float32，单位=度。"""
        return self._states[self._slice(ep)]
