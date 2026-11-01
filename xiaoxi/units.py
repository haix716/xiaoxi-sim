"""角度与限位纯函数。数据集单位=度，MJCF=弧度，所有边界转换集中在这。"""
import numpy as np

D2R = np.pi / 180.0
R2D = 180.0 / np.pi


def deg_to_rad(deg) -> np.ndarray:
    return np.asarray(deg, dtype=np.float64) * D2R


def rad_to_deg(rad) -> np.ndarray:
    return np.asarray(rad, dtype=np.float64) * R2D


def clip_deg(values, limits_deg: np.ndarray) -> np.ndarray:
    """把 (6,) 度值裁剪进 (6,2) [[min,max]] 限位。"""
    lim = np.asarray(limits_deg, dtype=np.float64)
    return np.clip(np.asarray(values, dtype=np.float64), lim[:, 0], lim[:, 1])
