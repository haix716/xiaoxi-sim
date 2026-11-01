"""units 纯函数：角度转换与限位裁剪。"""
import numpy as np
import pytest

from xiaoxi.units import D2R, R2D, clip_deg, deg_to_rad, rad_to_deg


class TestConvert:
    def test_deg_to_rad(self):
        assert deg_to_rad(180.0) == pytest.approx(np.pi)
        assert deg_to_rad(0.0) == 0.0

    def test_rad_to_deg(self):
        assert rad_to_deg(np.pi) == pytest.approx(180.0)

    def test_roundtrip_vector(self):
        deg = np.array([-110.5, 0.0, 97.3, 163.0, -42.0])
        assert np.allclose(rad_to_deg(deg_to_rad(deg)), deg)

    def test_constants_consistent(self):
        assert D2R * R2D == pytest.approx(1.0)


class TestClip:
    LIMITS = np.array([[-110, 110], [-100, 100], [-97, 97],
                       [-95, 95], [-157, 163], [-10, 100]])

    def test_inside_unchanged(self):
        v = [0.0, -50.0, 30.0, 90.0, 0.0, 50.0]
        assert np.allclose(clip_deg(v, self.LIMITS), v)

    def test_outside_clipped(self):
        out = clip_deg([-200.0, 150.0, -300.0, 0, 0, 0], self.LIMITS)
        assert out == pytest.approx([-110.0, 100.0, -97.0, 0.0, 0.0, 0.0])

    def test_asymmetric_limit(self):
        # wrist_roll 是 [-157, 163]，wrist/gripper 是 [-10, 100]：上下界不等
        out = clip_deg([999.0, -999.0], np.array([[-157, 163], [-10, 100]]))
        assert out == pytest.approx([163.0, -10.0])

    def test_accepts_list_and_array(self):
        assert np.allclose(clip_deg(np.array([5.0, 5.0]), np.array([[0, 10], [0, 10]])), [5.0, 5.0])
