import sys, os, signal, time, json, base64, subprocess
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

project_root = os.path.dirname(os.path.dirname(__file__))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from core.cloud.exploration_engine import ExplorationEngine, ExplorationConfig
from core.communication import ClientCommunicator
from screenshot import ScreenCapture
from device.touch import TouchManager
from device.adb_manager import ADBDeviceManager
from core.logger import init_logger, LogCategory, get_logger

init_logger()
logger = get_logger()
adb_path = os.path.join(project_root, "3rd-party", "adb", "adb.exe")

def adb(s: str) -> bool:
    try:
        subprocess.run(f"{adb_path} -s emulator-5562 {s}", shell=True, capture_output=True, timeout=10)
        return True
    except:
        return False

def adb_tap(x, y):
    return adb(f"shell input tap {x} {y}")

def vlm_analyze(comm, session_id, screenshot_b64, instruction, system_prompt=""):
    payload = {
        "instruction": instruction,
        "screenshot": screenshot_b64,
        "history": [],
        "session_id": session_id,
        "user_id": "explorer",
        "model_tag": "exploration_deep",
        "system_prompt": system_prompt,
    }
    return comm.send_request("agent_chat", payload)

def capture_b64(screen_capture):
    raw = screen_capture.capture_screen("emulator-5562")
    if raw:
        return raw.decode("utf-8") if isinstance(raw, bytes) else raw
    return None

SYSTEM_PROMPT = """你是《明日方舟：终末地》游戏分析器。识别画面中的所有交互元素并输出JSON：
{
  "page_name": "中文描述",
  "page_type": "login/menu/dialog/battle/world_map/shop/task/gacha/settings/loading/other",
  "elements": [{"id":"elem_1","type":"button/text","label":"精确文本","bbox":[x1,y1,x2,y2],"action":"tap/none"}],
  "has_daily_tasks": false,
  "has_weekly_tasks": false,
  "description": "一句中文摘要"
}
特别注意：每日任务、每周任务、签到、奖励按钮。label用可见中文文本。"""

def main():
    communicator = ClientCommunicator(host="127.0.0.1", port=9999, password="default_password", timeout=300)
    adb_manager = ADBDeviceManager(adb_path=adb_path)
    adb_manager.connect_device("emulator-5562")
    screen_capture = ScreenCapture(adb_manager)

    api_key = "aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763"
    login_r = communicator.send_request("login", {"user_id": "explorer", "key": api_key})
    session_id = login_r.get("session_id", "") if login_r else ""
    communicator.set_logged_in(True)

    print(f"会话ID: {session_id[:16] if session_id else 'N/A'}...")

    for cycle in range(15):
        print(f"\n=== 探索循环 {cycle+1} ===")

        b64 = capture_b64(screen_capture)
        if not b64:
            print("截图失败，等待...")
            time.sleep(5)
            continue

        result = vlm_analyze(communicator, session_id, b64,
            "这是什么游戏画面？列出所有可交互的按钮和元素。", SYSTEM_PROMPT)

        if not result or result.get("status") != "success":
            print(f"VLM失败: {result}")
            if cycle == 0:
                print("尝试确认登出对话框...")
                adb_tap(500, 693)
                time.sleep(3)
            continue

        reply = result.get("reply", "")
        print(f"VLM回复: {reply[:600]}")

        parsed = result.get("parsed", {})
        if isinstance(parsed, dict):
            page_name = parsed.get("page_name", "")
            page_type = parsed.get("page_type", "")
            elements = parsed.get("elements", [])
            desc = parsed.get("description", "")
            has_daily = parsed.get("has_daily_tasks", False)
            has_weekly = parsed.get("has_weekly_tasks", False)

            print(f"  页面: {page_name} ({page_type})")
            print(f"  描述: {desc[:80]}")
            print(f"  元素数: {len(elements)}")

            if has_daily:
                print("  ⭐ 发现每日任务页面!")
            if has_weekly:
                print("  ⭐ 发现每周任务页面!")

            if page_type in ("loading", "login"):
                print(f"  等待游戏加载 ({page_type})...")
                time.sleep(15)
                continue

            # Close announcement/popup screens
            if "公告" in page_name or "通知" in page_name or page_type in ("announcement",):
                close_btn = None
                for e in elements:
                    label = e.get("label", "")
                    if label in ("关闭", "X", "关", "x") or "关闭" in label:
                        close_btn = e
                        break
                if not close_btn:
                    for e in elements:
                        if "关闭" in e.get("label", "") or e.get("id","") in ("close_btn", "close_button"):
                            close_btn = e
                            break
                if close_btn:
                    bbox = close_btn.get("bbox", [0,0,0,0])
                    if len(bbox) >= 4:
                        cx, cy = int((bbox[0]+bbox[2])/2), int((bbox[1]+bbox[3])/2)
                        subprocess.run([adb_path, "-s", "emulator-5562", "shell", "input", "tap", str(cx), str(cy)],
                                      capture_output=True, timeout=10)
                        print(f"  关闭公告: ({cx},{cy})")
                        time.sleep(8)
                        continue

            # Navigate through startup sequence
            if "登录" in page_name or "启动" in page_name:
                print("  发现登录/启动页，尝试点击进入")
                buttons_priority = [e for e in elements if e.get("action") == "tap" and "点击" in e.get("label","")]
                if buttons_priority:
                    bbox = buttons_priority[0].get("bbox", [0,0,0,0])
                    if len(bbox) == 4:
                        cx, cy = int((bbox[0]+bbox[2])/2), int((bbox[1]+bbox[3])/2)
                        subprocess.run([adb_path, "-s", "emulator-5562", "shell", "input", "tap", str(cx), str(cy)],
                                      capture_output=True, timeout=10)
                        print(f"  点击: {buttons_priority[0].get('label','')} at ({cx},{cy})")
                        time.sleep(10)
                        continue

            if "每日任务" in page_name or "每周任务" in page_name or "日常" in page_name or "周常" in page_name or "任务" in page_name:
                print(f"\n  ⭐⭐⭐ 发现任务页面: {page_name}!")
                result_path = os.path.join(project_root, "cache", "task_page_found.json")
                with open(result_path, "w", encoding="utf-8") as f:
                    json.dump({"page_name": page_name, "elements": elements, "reply": reply[:2000],
                              "cycle": cycle, "timestamp": time.time()}, f, ensure_ascii=False, indent=2)
                print(f"  已保存到 {result_path}")

            # Try to find tap targets
            tap_targets = [e for e in elements if e.get("action") in ("tap", None) and e.get("type") in ("button", "icon", "tab")]
            if tap_targets:
                target = tap_targets[0]
                label = target.get("label", "")
                bbox = target.get("bbox", [0,0,0,0])
                if len(bbox) == 4 and bbox[2] > 0 and bbox[3] > 0:
                    cx = int((bbox[0] + bbox[2]) / 2)
                    cy = int((bbox[1] + bbox[3]) / 2)
                    print(f"  点击: {label} at ({cx},{cy})")
                    # Use ADB directly
                    subprocess.run([adb_path, "-s", "emulator-5562", "shell", "input", "tap", str(cx), str(cy)],
                                  capture_output=True, timeout=10)
                    time.sleep(5)
                    continue

            # If no obvious tap target, collect candidate buttons
            candidate_labels = ("确认", "确定", "进入游戏", "点击此位置继续", "关闭", "跳过", "开始", "菜单", "任务", "X", "关")
            buttons = [e for e in elements if "button" in e.get("type","").lower() or e.get("label","") in candidate_labels]
            if buttons:
                bbox = buttons[0].get("bbox", [0,0,0,0])
                if len(bbox) == 4 and bbox[2] > 0:
                    cx = int((bbox[0] + bbox[2]) / 2)
                    cy = int((bbox[1] + bbox[3]) / 2)
                    print(f"  点击按钮: {buttons[0].get('label','')} at ({cx},{cy})")
                    subprocess.run([adb_path, "-s", "emulator-5562", "shell", "input", "tap", str(cx), str(cy)],
                                  capture_output=True, timeout=10)
                    time.sleep(5)
                    continue

        # Fallback: ADB back
        print("  无合适元素，按返回键")
        subprocess.run([adb_path, "-s", "emulator-5562", "shell", "input", "keyevent", "4"],
                      capture_output=True, timeout=10)
        time.sleep(3)

    print("\n探索结束")

if __name__ == "__main__":
    main()
