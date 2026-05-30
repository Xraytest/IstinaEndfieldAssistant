"""Comprehensive game exploration + daily quest completion script.
Connects to localhost:16512, explores pages via VLM, completes daily tasks,
records page relationships and execution flow into cache/."""
import sys, os, time, json, re, subprocess, base64, io, hashlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

project_root = os.path.dirname(os.path.dirname(__file__))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from core.logger import init_logger, get_logger, LogCategory
from core.communication.communicator import ClientCommunicator
from device.adb_manager import ADBDeviceManager
from screenshot.screen_capture import ScreenCapture
from device.touch.touch_manager import TouchManager

init_logger()
logger = get_logger()

ADB_PATH = os.path.join(project_root, "3rd-party", "adb", "adb.exe")
DEVICE_SERIAL = "emulator-5562"
TOUCH_ADDRESS = "127.0.0.1:5563"
CACHE_DIR = os.path.join(project_root, "cache")
API_KEY = "aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763"

TASK_SYSTEM_PROMPT = """你是《明日方舟：终末地》游戏界面分析器。识别当前画面并输出JSON：
{
  "page_name": "中文页面名称",
  "page_type": "world_map/menu/dialog/task_ui/battle/shop/gacha/base/loading/login/announcement/other",
  "has_daily_tasks": false,
  "has_weekly_tasks": false,
  "has_claimable": false,
  "elements": [
    {"id":"e1","type":"button/text/icon/tab","label":"精确可见文本","bbox":[x1,y1,x2,y2],"action":"tap/none","function":"元素功能描述"}
  ],
  "menu_buttons": ["可见的顶部/侧边菜单按钮名称"],
  "navigation_path": ["从主界面到此页面的路径推测"],
  "description": "一句中文描述"
}
特别注意：每日任务、每周任务、作战汇报、签到、奖励领取等按钮。has_claimable看到"领取/收取/一键领取"按钮时为true。"""

ALL_PAGES = {}
ALL_EDGES = []
EXECUTION_LOG = []
session_id = ""
current_page_hash = None
previous_page_hash = None
os.makedirs(CACHE_DIR, exist_ok=True)


def adb_tap(x, y):
    subprocess.run([ADB_PATH, "-s", DEVICE_SERIAL, "shell", "input", "tap", str(x), str(y)],
                   capture_output=True, timeout=10)

def adb_keyevent(code):
    subprocess.run([ADB_PATH, "-s", DEVICE_SERIAL, "shell", "input", "keyevent", str(code)],
                   capture_output=True, timeout=10)

def adb_screencap():
    result = subprocess.run([ADB_PATH, "-s", DEVICE_SERIAL, "exec-out", "screencap", "-p"],
                            capture_output=True, timeout=15)
    return result.stdout if result.returncode == 0 and len(result.stdout) > 1000 else None


def analyze_page(raw_bytes) -> dict:
    b64 = base64.b64encode(raw_bytes).decode("utf-8") if isinstance(raw_bytes, bytes) else raw_bytes
    payload = {
        "instruction": "分析当前游戏画面，识别所有可交互UI元素。特别注意任务、奖励、签到相关按钮。",
        "screenshot": b64, "history": [], "session_id": session_id,
        "user_id": "explorer", "model_tag": "exploration_deep",
        "system_prompt": TASK_SYSTEM_PROMPT,
    }
    try:
        result = communicator.send_request("agent_chat", payload)
    except Exception as e:
        log(f"[ERROR] VLM call failed: {e}")
        return None
    if not result or result.get("status") != "success":
        return None
    reply = result.get("reply", "")
    json_match = re.search(r'\{[\s\S]*\}', reply)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {"page_name": "unknown", "page_type": "other", "elements": []}


def record_page(raw_bytes, page_info, action_taken=None):
    global current_page_hash, previous_page_hash
    h = hashlib.md5(raw_bytes if isinstance(raw_bytes, bytes) else raw_bytes.encode()).hexdigest()[:16]
    current_page_hash = h
    page_name = page_info.get("page_name", "Unknown")
    page_type = page_info.get("page_type", "other")
    elements_raw = page_info.get("elements", [])
    has_daily = page_info.get("has_daily_tasks", False)
    has_weekly = page_info.get("has_weekly_tasks", False)
    has_claim = page_info.get("has_claimable", False)

    if h not in ALL_PAGES:
        elements = []
        for i, e in enumerate(elements_raw):
            bbox = e.get("bbox", [0, 0, 0, 0])
            ele = {
                "element_id": f"elem_{h}_{i}",
                "type": e.get("type", "unknown"),
                "label": e.get("label", ""),
                "bbox": bbox,
                "confidence": e.get("confidence", 0.7),
                "explored": False,
                "leads_to": None,
                "extra": {"action": e.get("action", "none"), "function": e.get("function", "")}
            }
            if action_taken and e.get("label", "") == action_taken.get("label", ""):
                ele["explored"] = True
            elements.append(ele)

        ALL_PAGES[h] = {
            "page_id": f"page_{h}",
            "name": page_name,
            "screenshot_hash": h,
            "elements": elements,
            "parent_edge": previous_page_hash if previous_page_hash else None,
            "depth": len(EXECUTION_LOG),
            "state": "explored",
            "resolution": [1280, 720],
            "timestamp": time.time(),
            "verification_count": 0,
            "has_daily_tasks": has_daily,
            "has_weekly_tasks": has_weekly,
            "has_claimable": has_claim,
            "page_type": page_type,
        }

    if previous_page_hash and previous_page_hash != h and action_taken:
        from_page = ALL_PAGES.get(previous_page_hash, {})
        from_elements = from_page.get("elements", [])
        matched_elem_id = None
        for ele in from_elements:
            label = ele.get("label", "")
            if action_taken.get("label", "") and label == action_taken.get("label", ""):
                matched_elem_id = ele["element_id"]
                ele["explored"] = True
                ele["leads_to"] = f"page_{h}"
                break
        edge = {
            "edge_id": f"edge_{previous_page_hash}_{matched_elem_id or 'nav'}_{h}",
            "from": f"page_{previous_page_hash}",
            "to": f"page_{h}",
            "element_id": matched_elem_id or "navigation",
            "action_type": action_taken.get("type", "tap"),
            "params": action_taken.get("params", {}),
            "flow_step": len(EXECUTION_LOG),
        }
        if edge not in ALL_EDGES:
            ALL_EDGES.append(edge)

    previous_page_hash = current_page_hash


def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
    EXECUTION_LOG.append({"time": ts, "message": msg})


def tap_element(elem):
    bbox = elem.get("bbox", [0, 0, 0, 0])
    if len(bbox) >= 4 and bbox[2] > 0 and bbox[3] > 0:
        cx = int((bbox[0] + bbox[2]) / 2)
        cy = int((bbox[1] + bbox[3]) / 2)
        adb_tap(cx, cy)
        return cx, cy, elem.get("label", "")
    return None, None, None


def tap_coords(x, y, label="fixed_position"):
    adb_tap(x, y)
    return x, y, label


def take_screenshot():
    raw = adb_screencap()
    if raw:
        return raw
    return None


# ========== MAIN FLOW ==========
log("Initializing components...")
adb_mgr = ADBDeviceManager(adb_path=ADB_PATH)
adb_mgr.connect_device(DEVICE_SERIAL)
capture = ScreenCapture(adb_mgr)

touch_mgr = TouchManager()
touch_mgr.connect_android(adb_path=ADB_PATH, address=TOUCH_ADDRESS)
capture.set_touch_manager(touch_mgr)

communicator = ClientCommunicator(host="127.0.0.1", port=9999, password="default_password", timeout=300)
log("Logging in as explorer...")
login_r = communicator.send_request("login", {"user_id": "explorer", "key": API_KEY})
status = login_r.get("status", "?") if login_r else "NO RESPONSE"
log(f"Login result: {status}")
session_id = login_r.get("session_id", "") if login_r else ""
communicator.set_logged_in(True)

arkpass_data = {"user_id": "explorer", "api_key": API_KEY, "server_host": "127.0.0.1", "server_port": 9999}
with open(os.path.join(CACHE_DIR, "explorer.arkpass"), "w") as f:
    json.dump(arkpass_data, f)

log(f"Session: {session_id[:16] if session_id else 'NONE'}...")
log(f"Device: {DEVICE_SERIAL}")
log("=" * 60)

# PHASE 1: Navigate past any auto-logout/login dialogs into the game
log("PHASE 1: Navigating into game world...")
for nav_attempt in range(15):
    raw = take_screenshot()
    if not raw:
        log("[SKIP] Screenshot failed")
        time.sleep(3)
        continue

    info = analyze_page(raw)
    if not info:
        log("[SKIP] VLM analysis failed")
        time.sleep(3)
        continue

    pn = info.get("page_name", "")
    pt = info.get("page_type", "")
    elems = info.get("elements", [])

    record_page(raw, info)
    log(f"[{nav_attempt+1}] {pn} ({pt}) - {len(elems)} elements")

    is_in_game = (
        pt in ("world_map", "main_menu", "battle") or
        any(k in pn for k in ["世界", "主界面", "地图", "探索", "战斗", "终端", "基建", "指挥"])
    )
    if is_in_game:
        log(f"*** IN GAME WORLD: {pn} ***")
        break

    confirm_btns = [e for e in elems if any(k in e.get("label", "") for k in ["确认", "确定", "OK", "CONFIRM", "confirm"])]
    if confirm_btns and ("登出" in pn or "超时" in pn or "logout" in pn.lower()):
        target = confirm_btns[0]
        cx, cy, lbl = tap_element(target)
        if cx:
            log(f"  Click confirm (auto-logout): '{lbl}' at ({cx},{cy})")
            action_taken = {"type": "tap", "label": lbl, "params": {"x": cx, "y": cy}}
            record_page(raw, info, action_taken)
            time.sleep(5)
            continue

    nav_btns = [e for e in elems if any(k in e.get("label", "") for k in ["关闭", "进入游戏", "开始", "点击进入", "跳过", "X", "close", "CLOSE", "ENTER"])]
    if nav_btns:
        target = nav_btns[0]
        cx, cy, lbl = tap_element(target)
        if cx:
            log(f"  Click nav: '{lbl}' at ({cx},{cy})")
            action_taken = {"type": "tap", "label": lbl, "params": {"x": cx, "y": cy}}
            record_page(raw, info, action_taken)
            time.sleep(5)
            continue

    for x, y in [(940, 110), (950, 90), (1800, 110), (920, 100)]:
        log(f"  Try close at ({x},{y})")
        tap_coords(x, y, "close_x")
        time.sleep(3)
        raw2 = take_screenshot()
        if raw2:
            info2 = analyze_page(raw2)
            if info2:
                pt2 = info2.get("page_type", "")
                if pt2 in ("world_map", "main_menu") or any(k in info2.get("page_name", "") for k in ["世界", "主界面"]):
                    log(f"*** After close: {info2.get('page_name', '')} ***")
                    record_page(raw2, info2, {"type": "tap", "label": "close_x", "params": {"x": x, "y": y}})
                    break
        time.sleep(2)
    else:
        log("  BACK")
        adb_keyevent(4)
        time.sleep(3)

# PHASE 2: Explore and find daily/weekly task pages
log("=" * 60)
log("PHASE 2: Exploring task pages...")
task_pages_found = []
claim_attempts = 0

for cycle in range(40):
    raw = take_screenshot()
    if not raw:
        time.sleep(3)
        continue

    info = analyze_page(raw)
    if not info:
        time.sleep(3)
        continue

    pn = info.get("page_name", "")
    pt = info.get("page_type", "")
    elems = info.get("elements", [])
    has_daily = info.get("has_daily_tasks", False)
    has_weekly = info.get("has_weekly_tasks", False)
    has_claim = info.get("has_claimable", False)

    record_page(raw, info)
    log(f"[{cycle+1}] {pn} ({pt}) - {len(elems)}e" +
        (" [DAILY!]" if has_daily else "") + (" [WEEKLY!]" if has_weekly else "") +
        (" [CLAIM!]" if has_claim else ""))

    is_task_page = has_daily or has_weekly or any(k in pn for k in ["每日", "每周", "任务", "计划", "使命", "奖励", "签到", "作战"])
    if is_task_page and pn not in task_pages_found:
        task_pages_found.append(pn)
        log(f"  *** TASK PAGE: {pn} ***")

    claim_btns = [e for e in elems if any(k in e.get("label", "") for k in ["领取", "收取", "一键领取", "完成", "提交", "领奖", "CLAIM", "collect"])]
    if claim_btns and claim_attempts < 10:
        for e in claim_btns[:3]:
            cx, cy, lbl = tap_element(e)
            if cx:
                claim_attempts += 1
                log(f"  CLAIM: '{lbl}' at ({cx},{cy})")
                action_taken = {"type": "tap", "label": lbl, "params": {"x": cx, "y": cy}}
                record_page(raw, info, action_taken)
                time.sleep(5)
                break
        else:
            continue

    task_btns = [e for e in elems if any(k in (e.get("label", "") + e.get("function", "")).lower()
                 for k in ["任务", "每日", "每周", "签到", "奖励", "作战汇报", "使命", "日常", "周常",
                           "quest", "daily", "weekly", "mission", "reward"])]
    if task_btns:
        target = task_btns[0]
        cx, cy, lbl = tap_element(target)
        if cx:
            log(f"  Navigate task: '{lbl}' at ({cx},{cy})")
            action_taken = {"type": "tap", "label": lbl, "params": {"x": cx, "y": cy}}
            record_page(raw, info, action_taken)
            time.sleep(5)
            continue

    top_btns = [e for e in elems if e.get("action") == "tap" and e.get("type") in ("button", "icon", "tab")
                and len(e.get("bbox", [])) >= 4 and e["bbox"][1] < 150]
    if top_btns:
        target = top_btns[0]
        cx, cy, lbl = tap_element(target)
        if cx:
            log(f"  Top menu: '{lbl}' at ({cx},{cy})")
            action_taken = {"type": "tap", "label": lbl, "params": {"x": cx, "y": cy}}
            record_page(raw, info, action_taken)
            time.sleep(5)
            continue

    btns = [e for e in elems if e.get("action") == "tap"]
    if btns:
        target = btns[0]
        cx, cy, lbl = tap_element(target)
        if cx:
            log(f"  Generic tap: '{lbl}' at ({cx},{cy})")
            action_taken = {"type": "tap", "label": lbl, "params": {"x": cx, "y": cy}}
            record_page(raw, info, action_taken)
            time.sleep(5)
            continue

    log("  BACK")
    adb_keyevent(4)
    time.sleep(3)

# PHASE 3: Save results
log("=" * 60)
log("PHASE 3: Saving results...")

tree = {
    "root_page_id": f"page_{list(ALL_PAGES.keys())[0]}" if ALL_PAGES else "",
    "nodes": ALL_PAGES,
    "edges": ALL_EDGES,
    "stats": {
        "pages_discovered": len(ALL_PAGES),
        "elements_found": sum(len(p.get("elements", [])) for p in ALL_PAGES.values()),
        "edges_created": len(ALL_EDGES),
        "vlm_calls": len(EXECUTION_LOG),
        "taps": sum(1 for s in EXECUTION_LOG if "tap" in s.get("message", "").lower()),
        "daily_tasks_found": len(task_pages_found),
        "claim_attempts": claim_attempts,
    },
    "task_pages": task_pages_found,
    "execution_flow": EXECUTION_LOG,
    "timestamp": time.time(),
}
with open(os.path.join(CACHE_DIR, "page_tree.json"), "w", encoding="utf-8") as f:
    json.dump(tree, f, ensure_ascii=False, indent=2)
log(f"Saved page_tree.json ({len(ALL_PAGES)} pages, {len(ALL_EDGES)} edges)")

md_lines = [
    f"# Arknights Endfield - Game Map",
    f"",
    f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
    f"**Pages Discovered**: {len(ALL_PAGES)}",
    f"**Elements Found**: {sum(len(p.get('elements', [])) for p in ALL_PAGES.values())}",
    f"**Edges Created**: {len(ALL_EDGES)}",
    f"**Task Pages Found**: {len(task_pages_found)}",
    f"**Claim Attempts**: {claim_attempts}",
    f"**VLM Calls**: {len(EXECUTION_LOG)}",
    f"",
    f"---",
    f"## Task Pages",
]
for tp in task_pages_found:
    md_lines.append(f"- {tp}")
md_lines.extend(["", "---", "## Execution Flow"])
for step in EXECUTION_LOG:
    md_lines.append(f"- [{step['time']}] {step['message']}")
md_lines.extend(["", "---", "## Page Tree"])
for h, p in ALL_PAGES.items():
    md_lines.extend([
        f"",
        f"### {p['name']}",
        f"- **ID**: `{p['page_id']}`",
        f"- **Type**: {p.get('page_type', 'other')}",
        f"- **Depth**: {p['depth']}",
        f"- **Elements**: {len(p['elements'])}",
        f"- **Daily**: {p.get('has_daily_tasks', False)}",
        f"- **Weekly**: {p.get('has_weekly_tasks', False)}",
        f"- **Claimable**: {p.get('has_claimable', False)}",
    ])
    if p['elements']:
        md_lines.append(f"| # | Type | Label | Action |")
        md_lines.append(f"|---|------|-------|--------|")
        for i, e in enumerate(p['elements']):
            md_lines.append(f"| {i+1} | {e['type']} | {e['label']} | {e['extra'].get('action','?')} |")
    md_lines.append(f"")
with open(os.path.join(CACHE_DIR, "game_map.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))
log(f"Saved game_map.md")

summary = {
    "stats": tree["stats"],
    "task_pages": task_pages_found,
    "timestamp": time.time(),
    "device": DEVICE_SERIAL,
    "model_tag": "exploration_deep",
}
with open(os.path.join(CACHE_DIR, "exploration_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
log(f"Saved exploration_summary.json")

model_tag_path = os.path.join(CACHE_DIR, "model_tag.json")
model_tags = {"standard_reasoning": "exploration_deep", "prts_full_intelligence": "exploration_deep"}
if os.path.exists(model_tag_path):
    with open(model_tag_path, "r") as f:
        model_tags = json.load(f)
model_tags["standard_reasoning"] = "exploration_deep"
with open(model_tag_path, "w") as f:
    json.dump(model_tags, f, indent=2)

log("=" * 60)
log("SUMMARY:")
log(f"  Pages discovered: {len(ALL_PAGES)}")
log(f"  Edges recorded: {len(ALL_EDGES)}")
log(f"  Task pages found: {len(task_pages_found)}")
if task_pages_found:
    for tp in task_pages_found:
        log(f"    - {tp}")
log(f"  Claim attempts: {claim_attempts}")
log(f"  VLM calls: {len(EXECUTION_LOG)}")
log("=" * 60)
log("Done.")