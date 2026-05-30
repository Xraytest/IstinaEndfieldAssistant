import sys, os, time, json, subprocess, base64

project_root = os.path.dirname(os.path.dirname(__file__))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from core.communication import ClientCommunicator
from screenshot import ScreenCapture
from device.adb_manager import ADBDeviceManager

adb_path = os.path.join(project_root, "3rd-party", "adb", "adb.exe")
adb = lambda cmd: subprocess.run(f"{adb_path} -s emulator-5562 {cmd}", shell=True, capture_output=True, timeout=15)

print("=== 步骤1: 等待游戏加载完成 ===")
time.sleep(20)

print("=== 步骤2: 截图分析当前页面 ===")
communicator = ClientCommunicator(host="127.0.0.1", port=9999, password="default_password", timeout=120)
login_r = communicator.send_request("login", {"user_id": "explorer", "key": "aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763"})
session_id = login_r.get("session_id", "") if login_r else ""
communicator.set_logged_in(True)

adb_mgr = ADBDeviceManager(adb_path=adb_path)
adb_mgr.connect_device("emulator-5562")
capture = ScreenCapture(adb_mgr)

for attempt in range(30):
    print(f"\n--- 尝试 {attempt+1} ---")
    raw = capture.capture_screen("emulator-5562")
    if not raw:
        print("截图失败")
        time.sleep(5)
        continue

    b64 = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    payload = {
        "instruction": "识别当前游戏页面类型。是公告弹窗、登录页、加载中还是主游戏界面？输出JSON格式。",
        "screenshot": b64,
        "history": [],
        "session_id": session_id,
        "user_id": "explorer",
        "model_tag": "exploration_deep",
        "system_prompt": "你是《明日方舟：终末地》游戏界面分析器。输出JSON: {page_name, page_type: 'announcement/login/loading/main_menu/battle/world_map/dialog', elements: [{label, bbox, action}], description}。page_type必须准确。",
    }
    result = communicator.send_request("agent_chat", payload)
    if not result or result.get("status") != "success":
        print(f"VLM失败: {result}")
        time.sleep(5)
        continue

    reply = result.get("reply", "")
    import re
    json_match = re.search(r'\{[\s\S]*\}', reply)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
        except:
            parsed = {}
    else:
        parsed = {}

    page_name = parsed.get("page_name", "")
    page_type = parsed.get("page_type", "")
    elements = parsed.get("elements", [])
    print(f"  页面: {page_name} ({page_type})")

    if page_type == "main_menu" or "主界面" in page_name or "世界地图" in page_name:
        print(f"\n⭐ 到达游戏主界面!")
        with open(os.path.join(project_root, "cache", "reached_main.json"), "w", encoding="utf-8") as f:
            json.dump({"page_name": page_name, "attempt": attempt, "reply": reply[:1000]}, f, ensure_ascii=False, indent=2)
        break

    # Find close/confirm buttons
    close_buttons = []
    for e in elements:
        label = e.get("label", "")
        if any(k in label for k in ["关闭", "X", "×", "确认", "确定", "进入游戏", "点击", "跳过", "接受", "同意"]):
            close_buttons.append(e)
        if e.get("action") == "tap" and ("关闭" in e.get("id","") or e.get("type") == "button"):
            close_buttons.append(e)

    if close_buttons:
        target = close_buttons[0]
        bbox = target.get("bbox", [0,0,0,0])
        if len(bbox) >= 4 and bbox[2] > 0:
            cx, cy = int((bbox[0]+bbox[2])/2), int((bbox[1]+bbox[3])/2)
            label = target.get("label", "")
            print(f"  点击: {label} at ({cx},{cy})")
            subprocess.run([adb_path, "-s", "emulator-5562", "shell", "input", "tap", str(cx), str(cy)],
                          capture_output=True, timeout=10)
            time.sleep(8)
            continue

    # No close button found - try common positions for X button
    for x, y in [(940, 110), (950, 90), (1800, 110), (920, 100), (500, 693)]:
        print(f"  尝试固定位置点击: ({x},{y})")
        subprocess.run([adb_path, "-s", "emulator-5562", "shell", "input", "tap", str(x), str(y)],
                      capture_output=True, timeout=10)
        time.sleep(2)

    time.sleep(5)

print("\n完成")
