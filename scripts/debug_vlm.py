#!/usr/bin/env python3
"""调试：直接调用 VLM 看原始回复"""
import sys, os, json, re, base64, subprocess, time
from pathlib import Path

from _path_setup import PROJECT_ROOT, SRC_DIR, MODULE_DIR, ensure_path
ensure_path()

ADB = [str(PROJECT_ROOT / "3rd-party" / "adb" / "adb.exe"), "-s", "localhost:16512"]

def adb_screencap() -> bytes:
    r = subprocess.run(ADB + ["exec-out", "screencap", "-p"], capture_output=True, timeout=15)
    return r.stdout if r.returncode == 0 else b""

# 截图
raw = adb_screencap()
print(f"截图大小: {len(raw)} bytes")

# 从配置读取密码和密钥
config = {}
try:
    with open(os.path.join(PROJECT_ROOT, "config", "client_config.json")) as f:
        config = json.load(f)
except Exception:
    pass
server_config = config.get("server", {})
server_password = server_config.get("password", "default_password")
api_key = config.get("api_key", "aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763")

# VLM 调用
from core.communication.communicator import ClientCommunicator
comm = ClientCommunicator(host="127.0.0.1", port=9999, password=server_password, timeout=180)
r = comm.send_request("login", {"user_id": "explorer", "key": api_key})
sid = r.get("session_id", "") if r else ""
comm.set_logged_in(True)

b64 = base64.b64encode(raw).decode("utf-8")
resp = comm.send_request("agent_chat", {
    "instruction": "描述这个游戏画面里有什么。输出JSON：{\"screen_type\":\"\",\"buttons\":[{\"label\":\"\",\"bbox\":[]}],\"description\":\"\"}",
    "screenshot": b64,
    "history": [],
    "session_id": sid,
    "user_id": "explorer",
    "model_tag": "exploration_deep",
    "system_prompt": "你是终末地UI分析器。screen_type取值: loading/tap_to_enter/exploration/event_center/sign_in/quest_panel/unknown。"
})

print(f"\nVLM 响应状态: {resp.get('status') if resp else 'None'}")
print(f"VLM 原始回复:\n{resp.get('reply', 'N/A')[:1000] if resp else 'N/A'}")