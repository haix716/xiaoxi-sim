"""测试公共 fixture：真实数据集 + 项目根路径。"""
from pathlib import Path

import pytest

from xiaoxi.dataset import EpisodeDataset

PROJECT_ROOT = Path(__file__).parents[1]


@pytest.fixture(scope="session")
def dataset() -> EpisodeDataset:
    return EpisodeDataset(PROJECT_ROOT / "data-maxt90")
