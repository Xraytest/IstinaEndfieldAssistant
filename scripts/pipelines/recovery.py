# Robust game recovery + task analysis
import subprocess, time, sys, io, os, base64, json, re
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

adb = [os.path.join(PROJECT_ROOT, '3rd-party/adb/adb.exe'), '-s', 'localhost:16512']

def tap(x, y):
    subprocess.run(adb + ['shell', 'input', 'tap', str(x), str(y)], capture_output=True)

def screenshot():
    subprocess.run(adb + ['shell', 'screencap', '-p', '/sdcard/s.png'], capture_output=True)
    subprocess.run(adb + ['pull', '/sdcard/s.png', 'cache/screenshot_current.png'], capture_output=True)

def vlm_check(instruction, system_prompt=''):
    with open('cache/screenshot_current.png', 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')
    from core.communication import ClientCommunicator
    comm = ClientCommunicator(host='127.0.0.1', port=9999, password='default_password', timeout=120)
    login = comm.send_request('login', {'user_id': 'explorer', 'key': 'aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763'})
    session_id = login.get('session_id', '')
    comm.set_logged_in(True)
    payload = {'instruction': instruction, 'screenshot': b64, 'history': [], 'session_id': session_id, 'user_id': 'explorer', 'model_tag': 'vision', 'system_prompt': system_prompt}
    r = comm.send_request('agent_chat', payload)
    if r and r.get('status') == 'success':
        reply = r.get('reply', '')
        m = re.search(r'\{[\s\S]*\}', reply)
        if m:
            return json.loads(m.group())
        return {'_raw': reply[:200]}
    return None

MAX_RETRIES = 3

def robust_tap(x, y, expected_page_keyword, tap_desc=''):
    for attempt in range(MAX_RETRIES):
        print(f'  Tap {tap_desc} ({x},{y}) attempt {attempt+1}')
        tap(x, y)
        time.sleep(5)
        screenshot()
        result = vlm_check(f'当前页面是{expected_page_keyword}吗？输出JSON:{{"is_match":false,"page":""}}', '')
        if result and result.get('is_match'):
            print(f'  OK - reached {result.get("page","?")}')
            return True
        # Recovery: force-stop + restart
        print(f'  Touch failed, force-stopping game...')
        subprocess.run(adb + ['shell', 'am', 'force-stop', 'com.hypergryph.endfield'], capture_output=True)
        time.sleep(2)
        subprocess.run(adb + ['shell', 'am', 'start', '-n', 'com.hypergryph.endfield/com.u8.sdk.U8UnityContext'], capture_output=True)
        print('  Waiting 50s for restart...')
        time.sleep(50)
        # Skip start screen
        tap(1360, 530)
        print('  Waiting 40s for load...')
        time.sleep(40)
    return False

def navigate_to_game():
    print('\n=== Navigate to game world ===')
    # Assume already logged in, just skip start screen
    tap(1360, 530)
    time.sleep(40)
    screenshot()
    result = vlm_check('当前页面类型？输出JSON:{"page_type":""}', '')
    page_type = result.get('page_type', '') if result else ''
    print(f'After start screen: {page_type}')
    return 'world' in page_type or '探索' in str(result) or '地图' in str(result)

def navigate_to_event():
    print('\n=== Navigate to event center ===')
    # Tap EVENT button at (739, 48)
    if robust_tap(739, 48, '活动|event|EVENT', 'EVENT'):
        return True
    return False

def navigate_to_signin():
    print('\n=== Navigate to sign-in ===')
    if robust_tap(107, 291, '签到|sign|DAY', 'sign-in tab'):
        return True
    return False

def claim_daily():
    print('\n=== Claim daily reward ===')
    # Get claim button position from VLM
    result = vlm_check('签到页DAY2领取按钮坐标？输出JSON:{"claim_bbox":[0,0,0,0],"status":""}', '')
    if result:
        bbox = result.get('claim_bbox', [])
        status = result.get('status', '')
        if len(bbox) >= 4 and bbox[2] > 0:
            cx, cy = (bbox[0]+bbox[2])//2, (bbox[1]+bbox[3])//2
            print(f'Claim button at ({cx},{cy}), status={status}')
            if '未' in str(status) or 'available' in str(status).lower():
                return robust_tap(cx, cy, '已领取|claimed', 'claim')
    return False

# === MAIN ===
print('='*60)
print('FULL ROUTINE: restart → navigate → analyze → claim')
print('='*60)

# 1. Force stop + restart
print('\n--- Step 0: Fresh restart ---')
subprocess.run(adb + ['shell', 'am', 'force-stop', 'com.hypergryph.endfield'], capture_output=True)
time.sleep(2)
subprocess.run(adb + ['shell', 'am', 'start', '-n', 'com.hypergryph.endfield/com.u8.sdk.U8UnityContext'], capture_output=True)
print('Waiting 80s for game boot...')
time.sleep(80)

# 2. Navigate to game world
if not navigate_to_game():
    print('ERROR: Cannot reach game world')
    sys.exit(1)

# 3. Navigate to event center
if not navigate_to_event():
    print('WARN: Event nav failed, trying again after recovery...')
    # recovery already happened in robust_tap
    if not navigate_to_game():
        sys.exit(1)
    navigate_to_event()

# 4. Navigate to sign-in page
if not navigate_to_signin():
    print('WARN: Sign-in nav failed')

# 5. Claim daily reward
claim_daily()

# 6. Analyze weekly tasks
print('\n--- Weekly Task Analysis ---')
screenshot()
result = vlm_check('分析当前页面中的每周任务。输出JSON:{"tasks":[{"name":"","progress":"","status":""}]}', '你是任务分析器，提取所有可见的每周任务及其进度。')
if result and result.get('tasks'):
    for t in result['tasks']:
        print(f'  Task: {t.get("name","?")} | {t.get("progress","")} | {t.get("status","")}')

print('\n=== DONE ===')
