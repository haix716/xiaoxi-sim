# 小犀仿真练习场（2026-10-14 立）

SO-101 单臂的本地 MuJoCo 仿真。Mac 无 NVIDIA，Isaac 跑不了也不需要——单臂单场景正是 MuJoCo 主场。

## 启动

双击 `启动.command`，或：

```bash
cd ~/Documents/项目/小犀仿真
.venv/bin/python -m mujoco.viewer --mjcf=menagerie-so101/scene_box.xml
```

## 玩法（viewer）

- 视角：左键拖=环绕，右键拖=平移，滚轮=缩放
- 左侧面板 **Control** 区六滑条 = 六个舵机命令（等同往真臂发位置指令）
- **Ctrl+拖拽 perturbation**：双击选中部件后按住 Ctrl 拖 = 弹簧力拽它，执行器跟你对着干（感觉 kp=998 的伺服刚度）；绿方块同款拽法
- 双击任意部件 = 选中；空格 = 暂停；Backspace = 复位；F1 = 全部快捷键
- 左侧 **Keyframes** → 选 `pickup` → Load：官方存的一个抓取瞬间
- 绿色方块是 freejoint 刚体，可以被撞飞/拖动

## 网页示教台（VSCode 侧边栏驾驶舱）

```bash
cd ~/Documents/项目/小犀仿真
.venv/bin/python 网页示教台.py        # 默认 8777 端口，普通 python 即可（离屏渲染不吃 mjpython）
```

VSCode：⌘⇧P → `Simple Browser: Show`（简单浏览器）→ `http://localhost:8777`，标签页可拖到侧边栏。任意浏览器开同地址也行。页面=视频流 + 六关节滑条（手动）+ 50 集回放选集变速 + 复位/暂停。

坑账（macOS MuJoCo 网页流）：①**Renderer 必须在渲染线程里创建**——主线程建、子线程用，CGL 上下文跨线程会**静默挂死**（不报错、无帧）；②MJPEG 边界流要用 `multipart/x-mixed-replace`，首帧前先 flush 头，否则浏览器一直白屏。

## 回放示教（MaxT90/so101-pick-place，50 集）

```bash
cd ~/Documents/项目/小犀仿真
.venv/bin/mjpython 回放示教.py 0 1.0    # 集数 + 慢放倍率
```

坑账：`launch_passive` 在 macOS 必须 `mjpython` 跑（报错原文会提醒）；mjpython 需要软链 `.venv/lib/libpython3.12.dylib` → uv 的 python 发行版里那份（已链好）。开环回放跳的是动作不是成果——方块位置对不上真示教，抓空正常。

## 账目

- 模型来源：MuJoCo Menagerie `robotstudio_so101`（gh-proxy 逐文件抓取，网络坑：本地代理 127.0.0.1:4780 常死，git/curl 一律 `--noproxy` 或卸 env）
- **关节名与真臂一字不差**：shoulder_pan / shoulder_lift / elbow_flex / wrist_flex / wrist_roll / gripper——lerobot 0.6.2 观测键同款，以后仿真训的策略接真臂不用改字典
- venv：`.venv`（uv 建，python 3.12 + mujoco）
- 物理参数已官方调好：timestep 5ms、implicitfast 积分器、STS3215 舵机位置执行器 kp=998

## 五件套进度（仿真环境解剖，面试可讲）

1. 引擎 ✅ MuJoCo
2. 机器人模型 ✅ Menagerie MJCF（含执行器）
3. 场景 ✅ 桌面+方块（scene_box.xml）
4. 接口层 ⬜ gym 规矩（obs/act/reward/reset）——下一步
5. 并行与随机化 ⬜ domain randomization——再下一步

## 下一步

键盘/脚本驱动 → gym 接口 → 随机化 → 把 ACT/π0 策略放进仿真 rollout（对接 `~/Documents/项目/pi0-部署`）
