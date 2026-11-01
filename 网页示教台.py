"""小犀·网页示教台 —— MuJoCo 仿真渲染成网页，VSCode Simple Browser / 任意浏览器当驾驶舱。

用法: .venv/bin/python 网页示教台.py [端口=8777]
VSCode: ⌘⇧P → "Simple Browser: Show" → http://localhost:8777（面板可拖到侧边栏）
页面: 视频流 + 六关节滑条(手动模式) + 回放模式(50 集选集/变速) + 复位
"""
import json, io, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import numpy as np
import pyarrow.parquet as pq
from PIL import Image
import mujoco

ROOT = '/Users/hxy/Documents/项目/小犀仿真'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8777
W, H = 640, 420
D2R = np.pi / 180.0
R2D = 180.0 / np.pi

# ---------- 仿真侧 ----------
model = mujoco.MjModel.from_xml_path(f'{ROOT}/menagerie-so101/scene_box.xml')
data = mujoco.MjData(model)
mujoco.mj_forward(model, data)
# 注意：Renderer 必须在渲染线程里创建（macOS 的 GL 上下文跨线程会静默挂死）

JOINTS = ['shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex', 'wrist_roll', 'gripper']
LIMITS = [model.actuator_ctrlrange[i] for i in range(6)]  # 弧度

# 示教数据
_t = pq.read_table(f'{ROOT}/data-maxt90/data/chunk-000/file-000.parquet').to_pydict()
ACTIONS = np.asarray(_t['action'], dtype=np.float32)      # 度
EP_OF = np.asarray(_t['episode_index'])
EPISODES = sorted(set(EP_OF.tolist()))

state = {
    'mode': 'manual',            # manual | replay
    'ep': 0, 'frame': 0, 'speed': 1.0, 'paused': False,
    'manual_ctrl': np.zeros(6, dtype=np.float32),  # 弧度目标
    'reset_req': False,
    'seq': 0,
}
lock = threading.Lock()
latest_jpeg = b''
last_client = time.time()      # 观众在场证明：任何 HTTP 请求都会刷新（2026-10-15 省电三招）


def _reset_now():
    data.qpos[:] = 0
    data.qvel[:] = 0
    mujoco.mj_forward(model, data)


def sim_loop():
    """物理+渲染线程：30Hz。Renderer 在本线程创建（GL 上下文不跨线程）。
    省电三招（2026-10-15）：①观众检测 60s 无请求→睡觉 ②静止检测 状态没动→不拍照复用上一帧
    ③门铃 滑条输入或状态变化→立刻醒。心跳（mj_step）照常，照片机（render）省着用。"""
    global latest_jpeg
    renderer = mujoco.Renderer(model, height=H, width=W)
    period = 1.0 / 30
    next_t = time.time()
    prev_qpos = None
    still = 0
    while True:
        # ① 观众检测：页面关了（60 秒没人拉数据）→ 整循环睡觉，有人来再醒
        if time.time() - last_client > 60:
            time.sleep(1.0)
            next_t = time.time()
            prev_qpos, still = None, 0
            continue
        with lock:
            if state['reset_req']:
                _reset_now()
                state['reset_req'] = False
                state['frame'] = 0
                state['manual_ctrl'][:] = 0
            mode, ep, fr, spd, paused = state['mode'], state['ep'], state['frame'], state['speed'], state['paused']
            if not paused:
                if mode == 'replay':
                    rows = np.where(EP_OF == ep)[0]
                    if len(rows):
                        a = ACTIONS[int(fr) % len(rows)] * D2R
                        data.ctrl[:] = a
                        state['frame'] = (fr + spd) % len(rows)  # spd>1 加速，<1 慢放
                    else:
                        data.ctrl[:] = 0
                else:
                    data.ctrl[:] = state['manual_ctrl']
                for _ in range(6):
                    mujoco.mj_step(model, data)
        # ② 静止检测：关节角没动（阈值内）就跳过拍照，浏览器继续看上一帧
        qp = np.asarray(data.qpos).copy()
        if prev_qpos is not None and np.max(np.abs(qp - prev_qpos)) < 1e-4:
            still += 1
        else:
            still = 0
        prev_qpos = qp
        if still > 3 and (still % 30):  # 静止期降到 1fps 存照，防慢漂移时画面陈旧
            time.sleep(period)  # 画面没变：心跳照常跳过，照片机歇着
            continue
        renderer.update_scene(data, camera=-1)
        img = renderer.render()
        buf = io.BytesIO()
        Image.fromarray(img).save(buf, format='JPEG', quality=78)
        with lock:
            latest_jpeg = buf.getvalue()
            state['seq'] += 1
        next_t += period
        dt = next_t - time.time()
        if dt > 0:
            time.sleep(dt)
        else:
            next_t = time.time()  # 掉帧就重对表


threading.Thread(target=sim_loop, daemon=True).start()

HTML = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>小犀·示教台</title><style>
:root{--bg:#14161a;--panel:#1d2026;--fg:#e8e6e3;--dim:#8b8f98;--acc:#e8b33d;--line:#2c3038}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.5 -apple-system,"PingFang SC",sans-serif;padding:14px}
h1{font-size:15px;margin:0 0 10px;color:var(--acc)}
img#v{width:100%;border-radius:8px;background:#000;display:block}
.row{display:flex;gap:10px;align-items:center;margin:8px 0;flex-wrap:wrap}
button,select,input[type=range]{accent-color:var(--acc)}
button,select{background:var(--panel);color:var(--fg);border:1px solid var(--line);
border-radius:6px;padding:5px 12px;font-size:13px;cursor:pointer}
button.on{border-color:var(--acc);color:var(--acc)}
.j{margin:6px 0}.j label{display:flex;justify-content:space-between;color:var(--dim);font-size:12px}
.j input{width:100%;margin:2px 0}
#st{color:var(--dim);font-size:12px;margin-top:8px}
</style></head><body>
<h1>小犀 · 示教台</h1>
<img id="v" src="/video" alt="仿真画面">
<div class="row">
  <button id="bm" class="on" onclick="setMode('manual')">手动</button>
  <button id="br" onclick="setMode('replay')">回放</button>
  <button onclick="api('/api/reset')">复位</button>
  <button id="bp" onclick="togglePause()">暂停</button>
</div>
<div class="row" id="replayRow" style="display:none">
  集 <select id="ep"></select>
  速度 <select id="spd">
    <option value="0.25">0.25x</option><option value="0.5">0.5x</option>
    <option value="1" selected>1x</option><option value="2">2x</option></select>
</div>
<div id="sliders"></div>
<div id="st">—</div>
<script>
const J=[['shoulder_pan',-110,110],['shoulder_lift',-100,100],['elbow_flex',-97,97],
['wrist_flex',-95,95],['wrist_roll',-157,163],['gripper',-10,100]];
const sdiv=document.getElementById('sliders');
J.forEach(([n,a,b],i)=>{const d=document.createElement('div');d.className='j';
d.innerHTML=`<label><span>${n}</span><span id="v${i}">0°</span></label>
<input type="range" id="j${i}" min="${a}" max="${b}" value="0" step="0.5"
oninput="push(${i},this.value)">`;sdiv.appendChild(d)});
const eps=document.getElementById('ep');
for(let i=0;i<50;i++){const o=document.createElement('option');o.value=i;o.textContent=i;eps.appendChild(o)}
eps.onchange=()=>api('/api/mode?mode=replay&ep='+eps.value);
document.getElementById('spd').onchange=e=>api('/api/mode?mode=replay&speed='+e.target.value);
let manual=true,tm=null;
function push(i,deg){document.getElementById('v'+i).textContent=deg+'°';
  if(!manual)return; clearTimeout(tm);
  tm=setTimeout(()=>{const a=J.map((_,k)=>+document.getElementById('j'+k).value);
  fetch('/api/ctrl',{method:'POST',body:JSON.stringify(a)})},60)}
async function api(u){await fetch(u,{method:'POST'})}
async function setMode(m){manual=(m==='manual');document.getElementById('bm').classList.toggle('on',manual);
document.getElementById('br').classList.toggle('on',!manual);
document.getElementById('replayRow').style.display=manual?'none':'flex';
await api('/api/mode?mode='+m)}
async function togglePause(){await api('/api/pause');
const b=document.getElementById('bp');b.textContent=b.textContent==='暂停'?'继续':'暂停'}
setInterval(async()=>{try{const r=await fetch('/api/status');const s=await r.json();
document.getElementById('st').textContent=
`模式:${s.mode==='manual'?'手动':'回放·第'+s.ep+'集'} 帧:${s.frame} 暂停:${s.paused?'是':'否'}`}catch(e){}},1000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        global last_client
        last_client = time.time()  # 门铃：有请求=有观众
        u = urlparse(self.path)
        if u.path == '/':
            b = HTML.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        elif u.path == '/video':
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            last = -1
            while True:
                with lock:
                    seq, jpg = state['seq'], latest_jpeg
                if seq != last and jpg:
                    try:
                        self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' +
                                         str(len(jpg)).encode() + b'\r\n\r\n' + jpg + b'\r\n')
                        self.wfile.flush()
                        last = seq
                    except (BrokenPipeError, ConnectionResetError):
                        return
                time.sleep(1 / 30)
        elif u.path == '/api/status':
            with lock:
                st = dict(state)
                st['frame'] = int(st['frame'])
                self._json({k: st[k] for k in ('mode', 'ep', 'frame', 'paused')})
        else:
            self.send_error(404)

    def do_POST(self):
        global last_client
        last_client = time.time()  # 门铃：滑条/按钮一动立刻醒
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == '/api/ctrl':
            n = int(self.headers.get('Content-Length', 0))
            degs = json.loads(self.rfile.read(n) or b'[]')
            with lock:
                state['manual_ctrl'] = np.clip(np.asarray(degs, dtype=np.float32) * D2R,
                                               [l[0] for l in LIMITS], [l[1] for l in LIMITS])
            self._json({'ok': True})
        elif u.path == '/api/mode':
            with lock:
                if 'mode' in q:
                    state['mode'] = q['mode'][0]
                    if q['mode'][0] == 'replay':
                        state['frame'] = 0
                if 'ep' in q:
                    state['ep'] = int(q['ep'][0]); state['frame'] = 0
                if 'speed' in q:
                    state['speed'] = float(q['speed'][0])
            self._json({'ok': True})
        elif u.path == '/api/reset':
            with lock:
                state['reset_req'] = True
            self._json({'ok': True})
        elif u.path == '/api/pause':
            with lock:
                state['paused'] = not state['paused']
                self._json({'paused': state['paused']})
        else:
            self.send_error(404)


print(f'小犀示教台: http://localhost:{PORT}  （Ctrl+C 停）')
ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
