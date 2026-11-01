# 小犀仿真练习场

SO-101 单臂的本地 MuJoCo 仿真 + 网页示教台。Mac 无 NVIDIA，Isaac 跑不了也不需要——单臂单场景正是 MuJoCo 主场。

**技术栈**：Python 3.12 + FastAPI/uvicorn + MuJoCo 3.x（后端）｜ Vue 3 + TypeScript + Vite + uPlot（前端，零运行时 node 依赖）

---

## 快速开始

### 网页示教台（主入口）

双击 `启动.command`（自动起服务并开浏览器），或：

```bash
uv sync                                    # 首次：装齐依赖
uv run python -m xiaoxi --open             # 默认 127.0.0.1:8777
```

VSCode 侧边栏用法：⌘⇧P → `Simple Browser: Show` → `http://localhost:8777`，标签页可拖进侧边栏当驾驶舱。

页面能力：视频流（含腕部相机画中画）· 六关节滑条（目标 vs 实际 vs 误差）· 50 集示教回放（选集/变速/进度条拖动/暂停态预览）· 20Hz 关节遥测曲线 · 快捷键。

### MuJoCo 原生 viewer（交互式）

双击 `启动viewer.command`，或：

```bash
.venv/bin/python -m mujoco.viewer --mjcf=menagerie-so101/scene_box.xml
```

- 视角：左键拖=环绕，右键拖=平移，滚轮=缩放；左侧 Control 区六滑条=舵机命令
- **Ctrl+拖拽** perturbation：双击选中部件后按住 Ctrl 拖 = 弹簧力拽它（感受 kp=998 的伺服刚度）
- 空格=暂停，Backspace=复位，F1=全部快捷键；Keyframes 里的 `pickup` 是官方存的抓取瞬间

### 回放示教（mjpython 独立窗口版）

```bash
.venv/bin/mjpython 回放示教.py 0 1.0    # 集数 + 慢放倍率
```

开环回放跳的是「动作」不是「成果」——方块位置对不上真示教、抓取瞬间抓空，均正常。

### 键盘快捷键（网页）

| 键 | 动作 | | 键 | 动作 |
|---|---|---|---|---|
| `Space` | 暂停/继续 | | `←` `→` | 逐帧 seek |
| `R` | 复位 | | `Shift+←→` | ±1s seek |
| `M` / `P` | 手动 / 回放 | | `W` | 腕部相机 PiP 开关 |

---

## 架构

```
┌─ uvicorn 事件循环（主线程）─────────────┐   ┌─ sim 线程（daemon，唯一 GL 持有者）──┐
│  REST /api/*  ──命令──▶ StateStore ◀──快照─┐│   MjModel（共享只读）                │
│  WS /ws/telemetry ◀── TelemetryHub ◀─────┼──│ MjData + Renderer(main) + Renderer   │
│  MJPEG /video/* ◀──── FrameHub ◀─────────┘  │   (wrist)  ← 只在本线程创建/销毁     │
│  StaticFiles 托管 web/dist                   │ 30Hz：物理步进 + 按需渲染 + 省电三招 │
└──────────────────────────────────────────┘   └─────────────────────────────────────┘
```

```
├── xiaoxi/                  后端包（pip 可安装，uv 管理）
│   ├── config.py            pydantic-settings，环境变量前缀 XIAOXI_
│   ├── units.py             度↔弧度、限位裁剪（纯函数）
│   ├── dataset.py           LeRobot v3 parquet 加载，分集索引 O(1)
│   ├── state.py             线程安全状态机（RLock + 原子转移）
│   ├── frames.py            FrameHub/TelemetryHub/Audience（线程间单槽通道）
│   ├── sim.py               SimRuntime 仿真线程（GL 三铁律 + 省电三招）
│   ├── schemas.py / app.py  pydantic 模型 / create_app + lifespan
│   ├── __main__.py          python -m xiaoxi 入口
│   └── api/                 info(只读) / control(命令) / video(MJPEG) / ws(遥测)
├── web/                     Vue3+TS+Vite 前端
│   ├── src/api/rest.ts      REST 封装
│   ├── src/composables/     useTelemetry(WS+重连) useShortcuts useUi useVideoSrc
│   ├── src/components/      VideoPanel(PiP) JointSliders EpisodeBrowser
│   │                        TransportBar TelemetryChart(uPlot) StatusBar
│   └── dist/                构建产物，**入库**（双击启动不依赖 node）
├── tests/                   pytest：units / dataset / state / api（FakeRuntime 注入）
├── menagerie-so101/         机器人 MJCF（scene_box.xml 主场景）
├── data-maxt90/             LeRobot v3.0 数据集：50 集 22771 帧 30fps
├── 启动.command             网页示教台（双击）
├── 启动viewer.command       MuJoCo 原生 viewer（双击）
└── 回放示教.py              mjpython 回放工具（复用 xiaoxi.dataset）
```

### GL 三铁律（macOS 坑账，违反即静默挂死）

1. `mujoco.Renderer` 的创建与 `close()` 只能发生在 sim 线程内（CGL 上下文跨线程静默挂死，不报错无帧）
2. 事件循环线程永远不碰 MjData/Renderer——命令经 StateStore 下行、快照经 Hub 上行；MjModel 加载后不可变，跨线程只读限位元数据安全
3. sim 线程不调用任何 asyncio API

### 省电三招（2026-10-15 引入，重构后语义保留）

1. **观众检测**：无 MJPEG 流/WS 连接且 60s 无 REST 请求 → 整循环 1s 粒度睡觉
2. **静止检测**：qpos 连续 3 tick 没动 → 跳过渲染复用上一帧（静止期 ~1fps 存照防慢漂移画面陈旧）
3. **门铃**：任何命令 wake() 立刻进入下一 tick（滑条零延迟）

---

## API

FastAPI 自带交互文档：`http://localhost:8777/docs`。

### REST

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/status` | `{mode, ep, frame, paused}`（旧版四字段兼容）+ `frame_count/speed/sim_hz/joints{target_deg, actual_deg}` |
| GET | `/api/config` | 关节名/限位(度，来自 MJCF)/fps/流地址——前端自举不硬编码 |
| GET | `/api/episodes` | `[{index, length, seconds, tasks}]`，来自数据集 meta |
| POST | `/api/ctrl` | body `[6]` 度（裸数组，旧版兼容）或 `{"angles": [6]}`，自动裁剪到限位 |
| POST | `/api/mode?mode=&ep=&speed=` | 旧版 query 风格，语义保留 |
| POST | `/api/replay` | 统一入口 `{ep, frame, speed, paused}` 全可选；**调用即进回放模式**；frame 越界自动 clamp |
| POST | `/api/reset` / `/api/pause` | 复位 / 暂停切换 |

```bash
# 例：直接命令行选第 3 集 2 倍速回放
curl -X POST 'localhost:8777/api/replay' -H 'Content-Type: application/json' -d '{"ep":3,"speed":2}'
```

### 视频流

`GET /video/main`（640×420 30fps）· `GET /video/wrist`（320×210 15fps，腕部相机）· `GET /video`（旧路径别名）——MJPEG `multipart/x-mixed-replace`，`<img>` 标签直接吃。

### WS 遥测

`/ws/telemetry`：连接即 hello（关节名/限位/集数），之后 20Hz 推最新快照（`target_deg/actual_deg/frame/speed/paused/img_seq`）。单槽 latest 语义：慢客户端天然丢旧留新，不拖垮别人。前端断线自动指数退避重连，并回退 1s 轮询 `/api/status` 兜底。

---

## 开发工作流

```bash
# 后端（依赖、测试）
uv sync
uv run pytest                              # 47 项：纯逻辑 + API（FakeRuntime，不起 GL）

# 后端热重载（--reload-dir 很重要，防止 dist/parquet 触发重启）
uv run uvicorn xiaoxi.app:app --reload --reload-dir xiaoxi --port 8777

# 前端 dev（5173，/api 与 /ws 走 proxy；视频流自动直连 8777，见 vite.config.ts 注释）
cd web && npm install && npm run dev

# 前端构建 + 交付纪律：改了前端必须 rebuild，dist 与源码同一 commit（双击启动只认 dist）
cd web && npm run build
```

dev 遇 GL 挂死（reload 后渲染线程没起来）→ 手动重启即愈；生产模式（`python -m xiaoxi`）无 reload，无此问题。

### 配置（环境变量前缀 `XIAOXI_`）

| 变量 | 默认 | 说明 |
|---|---|---|
| `XIAOXI_PORT` | `8777` | 端口（`python -m xiaoxi 8778` 亦可） |
| `XIAOXI_HOST` | `127.0.0.1` | 只绑本机；勿改 0.0.0.0，服务无鉴权 |
| `XIAOXI_JPEG_QUALITY` | `78` | MJPEG 压缩质量 |
| `XIAOXI_WRIST_HZ` | `15` | 腕部相机帧率（省 CPU） |
| `XIAOXI_IDLE_SLEEP_SECONDS` | `60` | 省电①的睡岗阈值 |

---

## 坑账（踩过的坑，别再踩）

- **Renderer 必须在渲染线程里创建**——主线程建、子线程用，CGL 上下文跨线程会**静默挂死**（不报错、无帧）。见「GL 三铁律」。
- MJPEG 边界流要 `multipart/x-mixed-replace` 且首帧前先提交响应头（FastAPI `StreamingResponse` 的 yield-per-chunk 天然满足；**别加压缩中间件**，会缓冲破坏流）。
- `launch_passive` 在 macOS 必须 `mjpython` 跑；mjpython 需要软链 `.venv/lib/libpython3.12.dylib` → uv 的 python 发行版里那份（已链好）。
- **项目路径含中文**：Vite alias 的 `URL.pathname` 会百分号编码，必须 `decodeURIComponent`（见 `vite.config.ts`）。
- 网络代理 127.0.0.1:4780 常死：git/curl/npm 一律 `--noproxy` 或卸 env。
- `@types/uplot` 已从 npm 消失；uplot 自带 `dist/uPlot.d.ts`。

## 账目

- 模型来源：MuJoCo Menagerie `robotstudio_so101`（gh-proxy 逐文件抓取）
- 数据集：MaxT90/so101-pick-place（LeRobot v3.0，50 集 22771 帧，action/observation.state 均为度）
- **关节名与真臂一字不差**：shoulder_pan / shoulder_lift / elbow_flex / wrist_flex / wrist_roll / gripper——lerobot 0.6.2 观测键同款，仿真训的策略接真臂不用改字典
- 物理参数官方调好：timestep 5ms、implicitfast 积分器、STS3215 舵机位置执行器 kp=998
- 服务无鉴权，只绑 127.0.0.1——不要暴露到公网

## 五件套进度（仿真环境解剖，面试可讲）

1. 引擎 ✅ MuJoCo
2. 机器人模型 ✅ Menagerie MJCF（含执行器）
3. 场景 ✅ 桌面+方块（scene_box.xml）
4. 接口层 ✅ 网页示教台（REST+WS+MJPEG，2026-11 全栈框架化）
5. 并行与随机化 ⬜ domain randomization——下一步

## 下一步

gym 接口 → 随机化 → 把 ACT/π0 策略放进仿真 rollout（对接 `~/Documents/项目/pi0-部署`）
