"""把 MaxT90/so101-pick-place 的遥操作示教在仿真双胞胎里原样跳一遍。

用法: .venv/bin/python 回放示教.py [集数=0] [慢放倍率=1.0]
- 数据单位是度，MJCF 是弧度，脚本内部转换
- 关节顺序两边一字不差：shoulder_pan/lift, elbow_flex, wrist_flex, wrist_roll, gripper
- 开环回放：跳的是"动作"，不是"成果"——方块位置和真示教对不上，抓取瞬间可能抓空，正常
"""
import sys, time
import numpy as np
import pyarrow.parquet as pq
import mujoco, mujoco.viewer

ROOT = '/Users/hxy/Documents/项目/小犀仿真'
EP = int(sys.argv[1]) if len(sys.argv) > 1 else 0
SLOW = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0

t = pq.read_table(f'{ROOT}/data-maxt90/data/chunk-000/file-000.parquet').to_pydict()
rows = [i for i, e in enumerate(t['episode_index']) if e == EP]
acts = [np.asarray(t['action'][i], dtype=float) for i in rows]
states = [np.asarray(t['observation.state'][i], dtype=float) for i in rows]
n = len(acts)
print(f'第 {EP} 集：{n} 帧，约 {n/30:.0f} 秒（{SLOW}x 速度）')

d2r = np.pi / 180.0
model = mujoco.MjModel.from_xml_path(f'{ROOT}/menagerie-so101/scene_box.xml')
d = mujoco.MjData(model)

# qpos 布局：[0:6]=臂关节（顺序同数据集），[6:13]=方块 freejoint
d.qpos[:6] = states[0] * d2r
d.ctrl[:] = acts[0] * d2r
mujoco.mj_forward(model, d)

with mujoco.viewer.launch_passive(model, d) as v:
    time.sleep(1.0)  # 等窗口起来
    for a in acts:
        d.ctrl[:] = a * d2r
        for _ in range(6):          # 200Hz 物理，6 步 ≈ 30fps
            mujoco.mj_step(model, d)
        v.sync()
        time.sleep((1.0 / 30) * SLOW)
    print('放完了，窗口留着你玩（关窗退出）')
    while v.is_running():
        time.sleep(0.2)
