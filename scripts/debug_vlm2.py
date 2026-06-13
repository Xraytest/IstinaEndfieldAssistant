#!/usr/bin/env python3
"""调试：直接调用 VLM 看原始回复（静默模式）"""
import sys, os, json, re, base64, subprocess, time, io
from pathlib import Path

# 重定向日志输出
os.environ["LOG_QUIET"] = "1"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

# 禁用所有日志
import logging
logging.disable(logging.CRITICAL)

ADB = [str(PROJECT_ROOT / "3rd-party" / "adb" / "adb.exe"), "-s", "localhost:16512"]

def adb_screencap() -> bytes:
    r = subprocess.run(ADB + ["exec-out", "screencap", "-p"], capture_output=True, timeout=15)
    return r.stdout if r.returncode == 0 else b""

# 截图
raw = adb_screencap()
print(f"截图大小: {len(raw)} bytes")

# VLM 调用 - 直接使用 socket 通信，避免 logger 干扰
from core.communication.communicator import ClientCommunicator
comm = ClientCommunicator(host="127.0.0.1", port=9999, password="default_password", timeout=180)
r = comm.send_request("login", {"user_id": "explorer", "key": "aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763"})
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

print(f"\n=== VLM 原始回复 ===")
print(f"状态: {resp.get('status') if resp else 'None'}")
reply = resp.get('reply', 'N/A') if resp else 'N/A'
print(f"回复长度: {len(reply)}")
print(f"回复内容:\n{reply}")