"""测试服务器所有可能的模型标签，发现可用的模型映射"""
import sys, os, json, base64, subprocess, time, re

from _path_setup import PROJECT_ROOT, SRC_DIR, MODULE_DIR, ensure_path
ensure_path()

PROJECT_ROOT = str(PROJECT_ROOT)

ADB = [os.path.join(PROJECT_ROOT, "3rd-party", "adb", "adb.exe"), "-s", "localhost:16512"]
r = subprocess.run(ADB + ["exec-out", "screencap", "-p"], capture_output=True, timeout=15)
b64 = base64.b64encode(r.stdout).decode("utf-8")
print(f"Screenshot: {len(r.stdout)} bytes")

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

from core.communication.communicator import ClientCommunicator
from core.logger import init_logger
init_logger()

comm = ClientCommunicator(host="127.0.0.1", port=9999, password=server_password, timeout=60)
login = comm.send_request("login", {"user_id": "explorer", "key": api_key})
sid = login.get("session_id", "")
comm.set_logged_in(True)

# 尝试各种可能的 model_tag
tags_to_try = [
    "exploration_deep",
    "vision",
    "cherryin/qwen3.6-plus",
    "cherryin/qwen3.5-397b",
    "cherryin/qwen3.5-35b-a3b",
    "cherryin/qwen3.5-9b",
    "cherryin/qwen3-vl-plus",
    "local_qwen/qwen3.6-plus",
    "local_qwen/qwen3.5-397b",
    "local_qwen/qwen3.5-35b",
    "qwen3.6-plus",
    "qwen3.5-397b",
    "qwen3.5-35b-a3b",
    "cherryin",
    "cherryin_newapi",
    "local_qwen",
    "standard",
    "prts_full_intelligence",
    "qwen3.5-9b-free",
    "cherryin/qwen3.5-9b-free",
]

results = {}
for tag in tags_to_try:
    print(f"\n--- {tag} ---", end=" ", flush=True)
    t0 = time.time()
    try:
        resp = comm.send_request("agent_chat", {
            "instruction": "识别画面中的UI按钮。JSON:{\"page\":\"\",\"buttons\":[]}",
            "screenshot": b64, "history": [],
            "session_id": sid, "user_id": "explorer",
            "model_tag": tag,
            "system_prompt": "列出所有按钮的标签和坐标。",
        })
        dt = time.time() - t0
        if resp:
            status = resp.get("status", "")
            if status == "success":
                reply = resp.get("reply", "")[:100]
                print(f"[OK] ({dt:.1f}s): {reply[:80]}")
                results[tag] = {"status": "ok", "time": dt}
            else:
                msg = resp.get("message", "")
                print(f"[FAIL] ({dt:.1f}s): {msg[:80]}")
                results[tag] = {"status": "error", "message": msg}
        else:
            print(f"[FAIL] no response")
            results[tag] = {"status": "error", "message": "no response"}
    except Exception as e:
        dt = time.time() - t0
        print(f"[WARN] ({dt:.1f}s): {str(e)[:60]}")
        results[tag] = {"status": "exception", "error": str(e)}

print("\n\n=== 结果汇总 ===")
print(f"{'Model Tag':<35} {'Status':<10} {'Time':<8} {'Note'}")
print("-" * 70)
for tag, info in sorted(results.items(), key=lambda x: (x[1].get("status",""), x[0])):
    status = info.get("status", "?")
    dt = info.get("time", 0)
    note = info.get("message", info.get("error", ""))[:40]
    icon = "[OK]" if status == "ok" else "[FAIL]"
    print(f"{icon} {tag:<33} {status:<10} {dt:<8.1f} {note}")

with open("cache/model_tag_results.json", "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("\n结果已保存: cache/model_tag_results.json")