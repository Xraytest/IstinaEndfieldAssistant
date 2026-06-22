"""Step-by-step game navigation with vision model"""
import subprocess, time, sys, io, os, base64, json, re, argparse
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _path_setup import PROJECT_ROOT, SRC_DIR, MODULE_DIR, ensure_path
ensure_path()

PROJECT_ROOT = str(PROJECT_ROOT)
from core.communication.communicator import ClientCommunicator

# 命令行参数
parser = argparse.ArgumentParser()
parser.add_argument("--device", help="设备地址, 如 localhost:16512")
parser.add_argument("--adb", help="ADB 路径")
args, _ = parser.parse_known_args()

# 从配置读取默认值
config = {}
try:
    with open(os.path.join(PROJECT_ROOT, "config", "client_config.json")) as f:
        config = json.load(f)
except Exception:
    pass
device_config = config.get("device", {})

adb_path = args.adb or device_config.get("adb_path", os.path.join(PROJECT_ROOT, '3rd-party/adb/adb.exe'))
device_addr = args.device or device_config.get("address", 'localhost:16512')

ADB = [adb_path, '-s', device_addr]

def tap(x, y):
    subprocess.run(ADB + ['shell', 'input', 'tap', str(x), str(y)], capture_output=True)

def screenshot():
    subprocess.run(ADB + ['shell', 'screencap', '-p', '/sdcard/s.png'], capture_output=True)
    subprocess.run(ADB + ['pull', '/sdcard/s.png', 'cache/screenshot_current.png'], capture_output=True)

def _load_server_config():
    """从配置加载服务器参数"""
    config = {}
    try:
        with open(os.path.join(PROJECT_ROOT, "config", "client_config.json")) as f:
            config = json.load(f)
    except Exception:
        pass
    return config.get("server", {})

def vlm(instruction, sp=''):
    screenshot()
    with open('cache/screenshot_current.png', 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')
    server_cfg = _load_server_config()
    password = server_cfg.get('password', 'default_password')
    api_key = server_cfg.get('api_key', 'aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763')
    host = server_cfg.get('host', '127.0.0.1')
    port = server_cfg.get('port', 9999)
    user_id = server_cfg.get('user_id', 'explorer')
    comm = ClientCommunicator(host=host, port=port, password=password, timeout=180)
    login = comm.send_request('login', {'user_id': user_id, 'key': api_key})
    sid = login.get('session_id','')
    comm.set_logged_in(True)
    r = comm.send_request('agent_chat', {
        'instruction':instruction,'screenshot':b64,'history':[],
        'session_id':sid,'user_id':'explorer','model_tag':'vision',
        'system_prompt':sp
    })
    if r and r.get('status')=='success':
        reply = r.get('reply','')
        m = re.search(r'\{[\s\S]*\}', reply)
        if m:
            try: return json.loads(m.group())
            except: return {'_raw': reply[:300]}
    return None

# Step 1: See where we are
print('=== Step 1: Current screen ===')
r = vlm('输出JSON:{"page_name":"","buttons":[{"label":"","bbox":[]}]}', '识别每个按钮')
print(f'Page: {r.get("page_name","?")}' if r else 'No response')
if r:
    for b in r.get('buttons',[]):
        print(f'  [{b.get("label","?")}] {b.get("bbox")}')

# Step 2: Tap EVENT if visible
print('\n=== Step 2: Event button ===')
event_btn = None
for b in (r or {}).get('buttons',[]):
    if '活动' in str(b.get('label','')):
        event_btn = b
        break
if event_btn:
    cx = (event_btn['bbox'][0]+event_btn['bbox'][2])//2
    cy = (event_btn['bbox'][1]+event_btn['bbox'][3])//2
    print(f'Tapping EVENT at ({cx},{cy})')
    tap(cx, cy)
    time.sleep(8)
else:
    print('No EVENT found. Trying default position (740,50)')
    tap(740, 50)
    time.sleep(8)

# Step 3: Find sign-in
print('\n=== Step 3: Sign-in tab ===')
r = vlm('寻找签到/寻奇探幽相关按钮。输出JSON:{"page_name":"","sign_btn":[0,0,0,0],"buttons":[]}', '')
print(f'Page: {r.get("page_name","?")}' if r else 'No response')
if r:
    for b in r.get('buttons',[]):
        print(f'  [{b.get("label","?")}] {b.get("bbox")}')

# Step 4: Claim
print('\n=== Step 4: Claim reward ===')
sign_btn = None
for b in (r or {}).get('buttons',[]):
    lbl = str(b.get('label',''))
    if '签到' in lbl or '寻奇' in lbl:
        sign_btn = b
        break
if sign_btn:
    cx = (sign_btn['bbox'][0]+sign_btn['bbox'][2])//2
    cy = (sign_btn['bbox'][1]+sign_btn['bbox'][3])//2
    print(f'Tapping sign-in at ({cx},{cy})')
    tap(cx, cy)
    time.sleep(8)

# Step 5: Find claim button
r = vlm('寻找领取按钮。输出JSON:{"claim_btn":[0,0,0,0],"page_name":"","status":"","buttons":[]}', '精确定位领取按钮')
print(f'\n=== Step 5: Claim ===')
print(f'Result: {json.dumps(r, ensure_ascii=False)[:500]}' if r else 'No response')
claim_btn = None
for b in (r or {}).get('buttons',[]):
    if '领取' in str(b.get('label','')):
        claim_btn = b
        break
if claim_btn:
    cx = (claim_btn['bbox'][0]+claim_btn['bbox'][2])//2
    cy = (claim_btn['bbox'][1]+claim_btn['bbox'][3])//2
    print(f'Tapping claim at ({cx},{cy})')
    tap(cx, cy)
    time.sleep(5)
    # Verify
    r2 = vlm('领取成功了吗? JSON:{"claimed":false,"msg":""}', '')
    print(f'Verify: {json.dumps(r2, ensure_ascii=False)[:300]}' if r2 else 'No response')
else:
    print('No claim button - checking if already claimed')
    for b in (r or {}).get('buttons',[]):
        if '已领' in str(b.get('label','')):
            print(f'Already claimed: [{b.get("label")}]')

# Step 6: Weekly tasks
print('\n=== Step 6: Weekly tasks ===')
r = vlm('分析当前页面中的所有每周任务。JSON:{"tasks":[{"name":"","progress":"","status":""}]}', '')
if r:
    tasks = r.get('tasks',[])
    if tasks:
        for t in tasks:
            print(f'  [{t.get("status","?")}] {t.get("name","?")} - {t.get("progress","?")}')
    else:
        print('No tasks found')

# Save
with open('cache/daily_analysis.json','w') as f:
    json.dump({'timestamp':time.time(),'result':str(r)[:500]}, f, ensure_ascii=False)
print('\n=== DONE ===')
