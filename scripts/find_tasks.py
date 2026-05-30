import sys, os, time, json, subprocess, re, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

project_root = os.path.dirname(os.path.dirname(__file__))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from core.communication import ClientCommunicator
from screenshot import ScreenCapture
from device.adb_manager import ADBDeviceManager

adb_path = os.path.join(project_root, "3rd-party", "adb", "adb.exe")

communicator = ClientCommunicator(host="127.0.0.1", port=9999, password="default_password", timeout=120)
login_r = communicator.send_request("login", {"user_id": "explorer", "key": "aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763"})
session_id = login_r.get("session_id", "") if login_r else ""
communicator.set_logged_in(True)

adb_mgr = ADBDeviceManager(adb_path=adb_path)
adb_mgr.connect_device("emulator-5562")
capture = ScreenCapture(adb_mgr)

TASK_PROMPT = """你是《明日方舟：终末地》游戏界面分析器。识别当前画面并输出JSON：
{
  "page_name": "中文页面名称",
  "page_type": "world_map/menu/dialog/task_ui/battle/shop/gacha/base/other",
  "has_daily_tasks": false,
  "has_weekly_tasks": false,
  "elements": [
    {"id":"e1","type":"button/text/icon/tab","label":"精确可见文本","bbox":[x1,y1,x2,y2],"action":"tap/none","function":"该元素功能"}
  ],
  "menu_buttons": ["列出可见的顶部/侧边菜单按钮"],
  "description": "一句中文描述"
}
特别注意：每日任务、每周任务、作战汇报、签到、奖励领取等任务相关按钮。如果看到任务相关按钮，has_daily_tasks/has_weekly_tasks设为true。"""

def analyze():
    raw = capture.capture_screen("emulator-5562")
    if not raw:
        return None
    b64 = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    payload = {
        "instruction": "这是什么游戏界面？列出所有可交互元素，特别注意任务相关按钮。",
        "screenshot": b64, "history": [], "session_id": session_id,
        "user_id": "explorer", "model_tag": "exploration_deep", "system_prompt": TASK_PROMPT,
    }
    result = communicator.send_request("agent_chat", payload)
    if not result or result.get("status") != "success":
        return None
    reply = result.get("reply", "")
    json_match = re.search(r'\{[\s\S]*\}', reply)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    return {"page_name": "unknown", "page_type": "other", "elements": [], "has_daily_tasks": False, "has_weekly_tasks": False}

def tap_elem(elem):
    bbox = elem.get("bbox", [0,0,0,0])
    if len(bbox) >= 4 and bbox[2] > 0:
        cx, cy = int((bbox[0]+bbox[2])/2), int((bbox[1]+bbox[3])/2)
        subprocess.run([adb_path, "-s", "emulator-5562", "shell", "input", "tap", str(cx), str(cy)],
                      capture_output=True, timeout=10)
        return cx, cy
    return None, None

print("=== 探索游戏UI - 寻找每日/每周任务 ===")

found_tasks = False
task_pages = []

for cycle in range(40):
    result = analyze()
    if not result:
        print(f"[{cycle+1}] VLM失败")
        time.sleep(5)
        continue

    page_name = result.get("page_name", "")
    page_type = result.get("page_type", "")
    elements = result.get("elements", [])
    has_daily = result.get("has_daily_tasks", False)
    has_weekly = result.get("has_weekly_tasks", False)
    menu_btns = result.get("menu_buttons", [])

    print(f"[{cycle+1}] {page_name} ({page_type}) - {len(elements)}元素" +
          ("  [每日任务!]" if has_daily else "") +
          ("  [每周任务!]" if has_weekly else ""))

    # Save if task page
    is_task_page = has_daily or has_weekly or any(k in page_name for k in ["每日", "每周", "任务", "计划", "工业", "使命", "奖励"])
    if is_task_page:
        task_pages.append({"cycle": cycle, "page_name": page_name, "reply": result})
        print(f"  *** 发现任务页面: {page_name} ***")
        with open(os.path.join(project_root, "cache", "task_page.json"), "w", encoding="utf-8") as f:
            json.dump(task_pages, f, ensure_ascii=False, indent=2)
        found_tasks = True

    # Look for task-related buttons
    task_related = [e for e in elements if any(k in e.get("label","").lower() or k in e.get("function","").lower()
                   for k in ["任务", "每日", "每周", "签到", "奖励", "作战汇报", "使命", "日常", "周常"])]

    # Look for claim/collect buttons (for completing tasks)
    claim_buttons = [e for e in elements if any(k in e.get("label","") for k in ["领取", "收取", "一键领取", "完成", "提交", "领奖"])]
    if claim_buttons:
        print(f"  发现领取按钮: {[e.get('label') for e in claim_buttons]}")
        for e in claim_buttons[:3]:
            cx, cy = tap_elem(e)
            if cx:
                print(f"  点击领取: {e.get('label')} at ({cx},{cy})")
                time.sleep(5)

    if task_related:
        print(f"  发现任务按钮: {[e.get('label') for e in task_related]}")
        for e in task_related[:3]:
            cx, cy = tap_elem(e)
            if cx:
                print(f"  点击: {e.get('label')} at ({cx},{cy})")
                time.sleep(8)
                result2 = analyze()
                if result2:
                    pn = result2.get("page_name","")
                    pt = result2.get("page_type","")
                    print(f"  跳转后: {pn} ({pt})")
                    task_pages.append({"cycle": f"{cycle}_post_tap", "page_name": pn, "reply": result2})
                continue

    # No task buttons found - try common navigation
    # Try menu buttons
    menu_elems = [e for e in elements if any(k in e.get("label","") for k in ["菜单", "MENU", "menu", "☰", "≡", "功能"])]
    if not menu_elems:
        menu_elems = [e for e in elements if "菜单" in e.get("label","") or e.get("function","") == "菜单"]

    if menu_elems:
        cx, cy = tap_elem(menu_elems[0])
        if cx:
            print(f"  打开菜单: {menu_elems[0].get('label')} at ({cx},{cy})")
            time.sleep(5)
            continue

    # Try top-right buttons (usually menu/settings)
    # Try visible buttons in order
    buttons = [e for e in elements if e.get("action") == "tap" and e.get("type") in ("button", "icon", "tab")]
    if buttons:
        # Prefer buttons in the top/right area (menu area)
        top_buttons = [e for e in buttons if len(e.get("bbox",[])) >= 4 and e["bbox"][1] < 200]
        if top_buttons:
            target = top_buttons[0]
        else:
            target = buttons[0]
        cx, cy = tap_elem(target)
        if cx:
            print(f"  点击: {target.get('label')} at ({cx},{cy})")
            time.sleep(5)
            continue

    # Fallback: back
    print("  无合适元素，返回")
    subprocess.run([adb_path, "-s", "emulator-5562", "shell", "input", "keyevent", "4"],
                  capture_output=True, timeout=10)
    time.sleep(3)

print(f"\n=== 探索结束 ===")
print(f"发现任务页面: {len(task_pages)}")
if task_pages:
    for tp in task_pages:
        print(f"  - {tp.get('page_name', '?')}")
