"""EpisodeDataset：真实数据集契约 + 合成数据边界。"""
import json

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from xiaoxi.dataset import EpisodeDataset


class TestRealDataset:
    def test_joint_names_exact(self, dataset):
        # 与真臂一字不差（lerobot 观测键同款），顺序不许动
        assert dataset.JOINTS == ("shoulder_pan", "shoulder_lift", "elbow_flex",
                                  "wrist_flex", "wrist_roll", "gripper")

    def test_50_episodes(self, dataset):
        eps = dataset.episode_list()
        assert len(eps) == 50
        assert [e.index for e in eps] == list(range(50))

    def test_ep0_meta(self, dataset):
        ep0 = dataset.episode_list()[0]
        assert ep0.length == 948
        assert ep0.seconds == pytest.approx(948 / 30)
        assert any("Pick" in t for t in ep0.tasks)

    def test_fps(self, dataset):
        assert dataset.fps == 30

    def test_actions_shape_and_units(self, dataset):
        a = dataset.actions(0)
        assert a.shape == (948, 6)
        assert a.dtype == np.float32
        assert np.all(np.abs(a) < 200.0)  # 数据单位是度

    def test_actions_first_frame_matches_raw(self, dataset):
        # 对照旧实现：整表读出来按 episode_index 过滤的第 0 行
        t = pq.read_table(dataset.root / "data/chunk-000/file-000.parquet").to_pydict()
        rows = [i for i, e in enumerate(t["episode_index"]) if e == 0]
        raw = np.asarray(t["action"][rows[0]], dtype=np.float32)
        assert np.allclose(dataset.actions(0)[0], raw)

    def test_states_shape(self, dataset):
        assert dataset.states(0).shape == (948, 6)

    def test_lengths_consistent_with_actions(self, dataset):
        for ep in (0, 17, 49):
            assert dataset.episode_length(ep) == len(dataset.actions(ep))


class TestSynthetic:
    @pytest.fixture
    def tiny_root(self, tmp_path):
        """两集合成数据：ep0 三帧、ep1 两帧，验证分集索引切片边界。"""
        cols = {
            "action": [[0.0] * 6, [1.0] * 6, [2.0] * 6, [3.0] * 6, [4.0] * 6],
            "observation.state": [[10.0] * 6] * 5,
            "episode_index": [0, 0, 0, 1, 1],
            "index": list(range(5)),
        }
        (tmp_path / "data/chunk-000").mkdir(parents=True)
        pq.write_table(pa.table(cols), tmp_path / "data/chunk-000/file-000.parquet")
        meta = pa.table({
            "episode_index": [0, 1],
            "length": [3, 2],
            "tasks": [["pick"], ["place"]],
        })
        (tmp_path / "meta/episodes/chunk-000").mkdir(parents=True)
        pq.write_table(meta, tmp_path / "meta/episodes/chunk-000/file-000.parquet")
        info = {"fps": 30, "features": {}}
        (tmp_path / "meta/info.json").write_text(
            json.dumps(info), encoding="utf-8")
        return tmp_path

    def test_episode_split(self, tiny_root):
        ds = EpisodeDataset(tiny_root)
        assert ds.episode_length(0) == 3
        assert ds.episode_length(1) == 2
        assert np.allclose(ds.actions(0)[:, 0], [0.0, 1.0, 2.0])
        assert np.allclose(ds.actions(1)[:, 0], [3.0, 4.0])
        assert ds.episode_list()[1].tasks == ("place",)

    def test_unknown_episode_raises(self, tiny_root):
        ds = EpisodeDataset(tiny_root)
        with pytest.raises(KeyError, match="episode 2"):
            ds.actions(2)

    def test_meta_length_mismatch_falls_back_to_data(self, tiny_root):
        # meta 里的 length 与数据行数不一致时，以数据为准
        pq.write_table(pa.table({
            "episode_index": [0, 1], "length": [99, 2], "tasks": [["a"], ["b"]],
        }), tiny_root / "meta/episodes/chunk-000/file-000.parquet")
        ds = EpisodeDataset(tiny_root)
        assert ds.episode_length(0) == 3
