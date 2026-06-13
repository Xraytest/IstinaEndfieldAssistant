#!/usr/bin/env python3
"""
自适应每日标准流运行器
- VLM 检测画面，等待"点击进入游戏"按钮出现
- 等待游戏世界加载完成
- 然后执行 daily_quest 标准流
- 无硬编码超时，每一步都靠 VLM 确认
"""

import sys, os, time, json, re, base64, subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(PROJECT_ROOT / "3rd-party" / "python-packages"))

ADB = [str(PROJECT_ROOT / "3rd-party" / "adb" / "adb.exe"), "-s", "localhost:16512"]

# ── MaaFramework 触控初始化 ──
_maafw = None
try:
    from device.touch.maafw_touch_adapter import MaaFwTouchExecutor, MaaFwTouchConfig, MAAFW_AVAILABLE
    if MAAFW_AVAILABLE:
        _maafw_config = MaaFwTouchConfig(
            adb_path=str(PROJECT_ROOT / "3rd-party" / "adb" / "adb.exe"),
            address="localhost:16512",
            screencap_methods=MaaFwTouchConfig.SCREENCAP_ADB_SHELL,
            input_methods=MaaFwTouchConfig.INPUT_ADB_SHELL,
        )
        _maafw = MaaFwTouchExecutor(_maafw_config)
        if _maafw.connect():
            print(f"[MaaFw] 触控初始化成功，分辨率: {_maafw.get_resolution()}")
        else:
            print("[MaaFw] 连接失败，使用 ADB 回退")
            _maafw = None
    else:
        print("[MaaFw] MaaFramework 未安装，使用 ADB 直接触控")
except Exception as e:
    print(f"[MaaFw] 初始化异常: {e}，使用 ADB 回退")
    _maafw = None

# ── 触控工具（优先 MaaFw，回退 ADB）──

def _tap(x, y):
    """触控点击：优先 MaaFw，回退 ADB"""
    if _maafw and _maafw.connected:
        return _maafw.click(x, y)
    subprocess.run(ADB + ["shell", "input", "tap", str(x), str(y)], capture_output=True)
    return True

def adb_screencap() -> bytes:
    r = subprocess.run(ADB + ["exec-out", "screencap", "-p"], capture_output=True, timeout=15)
    return r.stdout if r.returncode == 0 else b""

def _back():
    """返回键：ADB keyevent（MaaFw 无独立 back 方法）"""
    subprocess.run(ADB + ["shell", "input", "keyevent", "4"], capture_output=True)

# ── VLM 分析 ──

def vlm_analyze(instruction: str, system_prompt: str = "") -> dict | None:
    """截图 → VLM 分析 → 返回 JSON"""
    raw = adb_screencap()
    if not raw or len(raw) < 1000:
        return None
    
    from core.communication.communicator import ClientCommunicator
    comm = ClientCommunicator(host="127.0.0.1", port=9999, password="default_password", timeout=180)
    r = comm.send_request("login", {"user_id": "explorer", "key": "aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763"})
    if not r:
        return None
    sid = r.get("session_id", "")
    comm.set_logged_in(True)
    
    b64 = base64.b64encode(raw).decode("utf-8")
    resp = comm.send_request("agent_chat", {
        "instruction": instruction,
        "screenshot": b64,
        "history": [],
        "session_id": sid,
        "user_id": "explorer",
        "model_tag": "exploration_deep",
        "system_prompt": system_prompt,
    })
    if not resp or resp.get("status") != "success":
        return None
    
    reply = resp.get("reply", "")
    m = re.search(r"\{[\s\S]*\}", reply)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return {"_raw": reply[:200]}


def detect_screen() -> str:
    """检测当前画面类型"""
    r = vlm_analyze(
        "识别当前游戏画面。输出JSON：{\"screen_type\":\"\",\"buttons\":[{\"label\":\"\",\"bbox\":[]}],\"description\":\"\"}",
        "你是终末地UI分析器。screen_type取值: loading(加载中), tap_to_enter(点击进入游戏), exploration(探索主界面), event_center(活动中心), sign_in(签到页), quest_panel(任务面板), unknown(未知)。"
    )
    if not r:
        return "unknown"
    return r.get("screen_type", "unknown").lower()


def find_button(r: dict, keywords: list[str]) -> tuple[int, int, str] | None:
    """在 VLM 结果中找匹配关键词的按钮"""
    for b in r.get("buttons", []):
        lbl = str(b.get("label", ""))
        for kw in keywords:
            if kw in lbl:
                bb = b.get("bbox", [0, 0, 0, 0])
                if len(bb) >= 4 and bb[2] > bb[0]:
                    return ((bb[0] + bb[2]) // 2, (bb[1] + bb[3]) // 2, lbl)
    return None


# ── 自适应等待循环 ──

def wait_for_screen(target_type: str, keywords: list[str] = None, max_loops: int = 60) -> dict | None:
    """
    自适应等待目标画面出现。
    每轮：截图 → VLM 分析 → 判断画面类型
    如果找到匹配关键词的按钮，自动点击。
    """
    for i in range(max_loops):
        print(f"  [等待 {i+1}/{max_loops}] 检测画面...", end=" ", flush=True)
        r = vlm_analyze(
            "识别当前游戏画面。逐一列出每个按钮的标签和精确像素坐标。"
            '输出JSON：{"screen_type":"","buttons":[{"label":"","bbox":[]}],"description":""}',
            "你是终末地UI分析器。screen_type取值: loading, tap_to_enter, exploration, event_center, sign_in, quest_panel, unknown。"
        )
        if not r:
            print("VLM 失败，重试")
            time.sleep(3)
            continue
        
        st = r.get("screen_type", "").lower()
        desc = r.get("description", "")
        print(f"→ {st}")
        
        # 如果匹配目标类型，返回
        if st == target_type:
            print(f"  ✅ 目标画面 '{target_type}' 已到达")
            return r

        # 特殊：等待 tap_to_enter 但已进入探索界面 → 跳过
        if target_type == "tap_to_enter" and st == "exploration":
            print(f"  ⏭ 已在探索界面，跳过等待进入游戏")
            return r

        # 特殊：等待 exploration 但还在 tap_to_enter → 点击进入
        if target_type == "exploration" and st == "tap_to_enter":
            btn = find_button(r, ["点击进入游戏", "进入游戏", "点击进入", "进入", "tap to enter", "enter"])
            if btn:
                print(f"  👆 点击进入游戏: ({btn[0]}, {btn[1]}) [{btn[2]}]")
                _tap(btn[0], btn[1])
            else:
                print(f"  👆 点击屏幕中央 (540, 960) [备用]")
                _tap(540, 960)
            time.sleep(5)
            continue
        
        # 如果检测到 tap_to_enter，自动点击进入
        if st == "tap_to_enter":
            btn = find_button(r, ["点击进入游戏", "进入游戏", "点击进入", "进入", "tap to enter", "enter"])
            if btn:
                print(f"  👆 点击进入游戏: ({btn[0]}, {btn[1]}) [{btn[2]}]")
                _tap(btn[0], btn[1])
            else:
                # 备用：点击屏幕中央
                print(f"  👆 点击屏幕中央 (540, 960) [备用]")
                _tap(540, 960)
            time.sleep(5)
            continue

        # 如果检测到签到界面，点击关闭或一键领取
        if st == "sign_in":
            btn = find_button(r, ["关闭", "close", "X", "一键领取", "领取", "签到"])
            if btn:
                print(f"  👆 点击签到按钮: ({btn[0]}, {btn[1]}) [{btn[2]}]")
                _tap(btn[0], btn[1])
            else:
                # 备用：点击右上角关闭位置
                print(f"  👆 点击右上角关闭 (1800, 100) [备用]")
                _tap(1800, 100)
            time.sleep(3)
            continue
        
        # 如果还在加载，继续等
        if st == "loading":
            print("  仍在加载...")
            time.sleep(5)
            continue
        
        # 如果 keywords 指定了，检查是否有匹配按钮
        if keywords:
            btn = find_button(r, keywords)
            if btn:
                print(f"  👆 点击: ({btn[0]}, {btn[1]}) [{btn[2]}]")
                _tap(btn[0], btn[1])
                time.sleep(3)
                continue
        
        # 未知画面，等一会再试
        print(f"  当前: {st} | {desc[:60]}")
        time.sleep(3)
    
    print(f"  ❌ 超时：未到达 '{target_type}'")
    return None


# ── 主流程 ──

def main():
    print("=" * 60)
    print("自适应每日标准流运行器")
    print("=" * 60)
    
    # 1. 检查/启动游戏
    print("\n[1/5] 检查游戏状态...")
    r = subprocess.run(ADB + ["shell", "ps", "-A"], capture_output=True, timeout=10)
    game_running = b"com.hypergryph.endfield" in r.stdout and b"U8UnityContext" in r.stdout
    
    if not game_running:
        print("  游戏未运行，正在启动...")
        subprocess.run(ADB + ["shell", "input", "keyevent", "3"], capture_output=True)  # HOME
        time.sleep(2)
        subprocess.run(ADB + ["shell", "am", "start", "-n",
                              "com.hypergryph.endfield/com.u8.sdk.U8UnityContext"],
                       capture_output=True, timeout=15)
        print("  启动指令已发送，等待加载...")
    else:
        print("  游戏已在运行")
    
    # 2. 自适应等待：加载 → 点击进入游戏
    print("\n[2/5] 等待游戏加载完成...")
    r = wait_for_screen("tap_to_enter", max_loops=40)  # 最多等 40 轮 × ~8s = ~320s
    if not r:
        print("❌ 无法进入游戏")
        return 1
    
    # 3. 点击进入后，等待探索主界面
    print("\n[3/5] 等待进入探索主界面...")
    r = wait_for_screen("exploration", max_loops=30)
    if not r:
        print("⚠️ 未检测到探索界面，尝试继续...")
    
    # 4. 执行 daily_quest 标准流
    print("\n[4/5] 执行每日任务标准流...")
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    
    # 直接调用 standard_flow_engine 的 main
    from standard_flow_engine import main as flow_main
    # 备份 argv，注入 --flow daily_quest --skip-analysis --no-record
    old_argv = sys.argv
    sys.argv = ["standard_flow_engine.py", "--flow", "daily_quest", "--skip-analysis", "--no-record"]
    try:
        ret = flow_main()
    finally:
        sys.argv = old_argv
    
    # 5. 完成
    print("\n[5/5] 每日流程执行完毕")
    if ret == 0:
        print("✅ 全部完成")
    else:
        print(f"⚠️ 流程返回码: {ret}")
    return ret


if __name__ == "__main__":
    sys.exit(main())
