"""Test different model tags with an actual screenshot"""
import sys, os, json, base64, subprocess, re

import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _path_setup import PROJECT_ROOT, SRC_DIR, MODULE_DIR, ensure_path
ensure_path()

project_root = str(PROJECT_ROOT)
src_dir = str(SRC_DIR)
from core.logger import init_logger
init_logger()
from core.communication.communicator import ClientCommunicator

ADB = os.path.join(project_root, "3rd-party", "adb", "adb.exe")
SERIAL = "localhost:16512"

# Take screenshot
result = subprocess.run([ADB, "-s", SERIAL, "exec-out", "screencap", "-p"], capture_output=True, timeout=15)
if result.returncode != 0 or len(result.stdout) <= 1000:
    print(json.dumps({"error": "screenshot failed"}))
    sys.exit(1)

b64 = base64.b64encode(result.stdout).decode("utf-8")

comm = ClientCommunicator(host="127.0.0.1", port=9999, password="default_password", timeout=300)
r = comm.send_request("login", {"user_id": "explorer", "key": "aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763"})
session_id = r.get("session_id", "") if r else ""
comm.set_logged_in(True)

# Try different model tags
model_tags = ["exploration_deep", "vision", "standard", "prts_full_intelligence", "large_vision"]

for tag in model_tags:
    print(f"\n=== Testing model_tag: {tag} ===")
    try:
        payload = {
            "instruction": "用中文描述这个游戏画面：当前在哪个页面？有什么主要按钮？",
            "screenshot": b64,
            "history": [],
            "session_id": session_id,
            "user_id": "explorer",
            "model_tag": tag,
            "system_prompt": "简短的JSON输出：{page_name, page_type, buttons:[]}",
        }
        resp = comm.send_request("agent_chat", payload)
        if resp:
            status = resp.get("status", "unknown")
            reply = resp.get("reply", "")[:500]
            print(f"  status={status}")
            print(f"  reply={reply[:300]}")
        else:
            print(f"  No response")
    except Exception as e:
        print(f"  Error: {e}")
