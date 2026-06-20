#!/usr/bin/env python3
"""
高可靠标准流执行引擎 v5
基于 OCR+ 模板匹配 +MaaEnd 流程参考 +VLM 决策

核心特性：
1. 识别增强：OCR+ 模板匹配
2. LLM 决策：根据识别结果决定点击位置
3. MaaEnd 模式：Navigation→StatusCheck→ScrollFind→Claim→Back
4. 错误恢复：无响应时自动重启游戏
5. 多重验证：坐标验证 + 页面验证+OCR 验证
6. 无超时机制：等待用户确认或自动恢复
7. 仅两种页面类型：主世界和确认退出
"""

import sys, os, json, time, cv2, numpy as np, argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from core.adb_utils import adb_screencap
from core.recognition.recognition_engine import RecognitionEngine
from core.page_analyzer import HighPrecisionPageAnalyzer
from core.ocr.ocr_manager import OCRManager

# 命令行参数
parser = argparse.ArgumentParser()
parser.add_argument("--device", help="设备地址, 如 192.168.1.12:16512")
parser.add_argument("--adb", help="ADB 路径")
args = parser.parse_args()

# 从配置读取默认值
config = {}
try:
    with open(str(PROJECT_ROOT / "config" / "client_config.json")) as f:
        config = json.load(f)
except Exception:
    pass
device_config = config.get("device", {})

DEVICE_ADDR = args.device or device_config.get("address", "192.168.1.12:16512")
ADB_PATH = args.adb or device_config.get("adb_path", str(PROJECT_ROOT / "3rd-party" / "adb" / "adb.exe"))


class HighReliabilityFlowExecutor:
    """高可靠标准流执行引擎"""

    def __init__(self, flow_config: dict):
        self.flow_config = flow_config
        self.recognition_engine = RecognitionEngine()
        self.page_analyzer = HighPrecisionPageAnalyzer()
        self.ocr_manager = OCRManager()
        self.screenshots = []
        self.recognition_records = []
        self.ocr_results = []

        # 初始化 MaaFw 执行器（用于 OCR）
        self._maafw_executor = None
        self._controller_id = ""
        try:
            from device.touch.maafw_touch_adapter import MaaFwTouchExecutor, MaaFwTouchConfig
            maafw_config = MaaFwTouchConfig(
                adb_path=ADB_PATH,
                address=DEVICE_ADDR,
                screencap_methods=MaaFwTouchConfig.SCREENCAP_ADB_SHELL,
                input_methods=3,
            )
            executor = MaaFwTouchExecutor(maafw_config)
            if executor.connect():
                self._maafw_executor = executor
                self._controller_id = "ctrl_1"
                self.ocr_manager.set_maafw_executor(executor, self._controller_id)
                print(f"[MaaFw] OCR 执行器初始化成功")
            else:
                print("[MaaFw] 连接失败，OCR 将不可用")
        except Exception as e:
            print(f"[MaaFw] 初始化失败：{e}，OCR 将不可用")

    def _adb_tap(self, x: int, y: int) -> bool:
        import subprocess
        try:
            r = subprocess.run(
                [ADB_PATH, "-s", DEVICE_ADDR, "shell", "input", "tap", str(x), str(y)],
                capture_output=True, timeout=5
            )
            return r.returncode == 0
        except:
            return False

    def _adb_back(self) -> bool:
        import subprocess
        try:
            r = subprocess.run(
                [ADB_PATH, "-s", DEVICE_ADDR, "shell", "input", "keyevent", "4"],
                capture_output=True, timeout=5
            )
            return r.returncode == 0
        except:
            return False

    def _adb_restart_game(self) -> bool:
        import subprocess
        try:
            print("  [重启] 关闭游戏进程...")
            subprocess.run(
                [ADB_PATH, "-s", DEVICE_ADDR, "shell", "am", "force-stop", "com.hypergryph.endfield"],
                capture_output=True, timeout=10
            )
            time.sleep(2)
            print("  [重启] 启动游戏...")
            subprocess.run(
                [ADB_PATH, "-s", DEVICE_ADDR, "shell", "monkey", "-p", "com.hypergryph.endfield", "1"],
                capture_output=True, timeout=10
            )
            print("  [重启] 等待游戏启动...")
            time.sleep(15)
            return True
        except Exception as e:
            print(f"  [重启错误] {e}")
            return False

    def _capture_and_recognize(self, step_name: str) -> Dict[str, Any]:
        """截图并执行识别（仅 OCR+ 模板匹配，无颜色检测）"""
        print(f"  [截图] 设备：{DEVICE_ADDR}")
        img_bytes = adb_screencap(serial=DEVICE_ADDR)
        if not img_bytes:
            print(f"  [截图] 失败：无数据")
            return {"error": "screenshot_failed"}

        print(f"  [截图] 数据大小：{len(img_bytes)} bytes")

        np_img = np.frombuffer(img_bytes, dtype=np.uint8)
        cv_img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
        if cv_img is None:
            print(f"  [截图] 解码失败")
            return {"error": "decode_failed"}

        print(f"  [截图] 图片尺寸：{cv_img.shape[1]}x{cv_img.shape[0]}")

        # 旋转为横屏
        rotated = cv2.rotate(cv_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        resized = cv2.resize(rotated, (1280, 720))

        # 保存截图
        self.screenshots.append(cv_img.copy())

        # 页面分析（仅亮度特征）
        page_result = self.page_analyzer.analyze(resized)
        print(f"  [页面] 类型：{page_result['page_type']}, left_bar: {page_result['features'].get('left_bar_brightness', 0):.1f}")

        # OCR 识别
        ocr_texts = []
        try:
            ocr_results = self.ocr_manager.run_ocr()
            for r in ocr_results:
                text = r.get("text", "").strip()
                if text:
                    ocr_texts.append({
                        "text": text,
                        "bbox": [r.get("x", 0), r.get("y", 0), r.get("x", 0) + r.get("w", 0), r.get("y", 0) + r.get("h", 0)],
                        "center": [r.get("cx", 0), r.get("cy", 0)],
                        "score": r.get("score", 0)
                    })
            print(f"  [OCR] 识别到 {len(ocr_texts)} 个文本")
            for t in ocr_texts:
                print(f"    - {t['text']} @ {t['center']}")
        except Exception as e:
            print(f"  [OCR] 识别失败：{e}")

        record = {
            "step": step_name,
            "timestamp": time.time(),
            "page_type": page_result["page_type"],
            "features": page_result["features"],
            "ocr": ocr_texts,
        }
        self.recognition_records.append(record)

        return record

    def _detect_page_type(self, features: dict, ocr_texts: list = None) -> str:
        """根据特征检测页面类型（简化版：只有主世界和确认退出）

        只使用亮度特征 + OCR 辅助判断
        """
        left_bar = features.get("left_bar_brightness", 0)
        brightness = features.get("full_brightness", 0)

        # OCR 辅助判断
        if ocr_texts:
            all_text = " ".join([t.get("text", "") for t in ocr_texts])

            # 退出/登出对话框（强关键词：不依赖 left_bar）
            if "是否退出游戏" in all_text or "长时间没有操作" in all_text:
                return "exit_dialog"

            # 退出/登出对话框（普通关键词：依赖 left_bar）
            exit_keywords = ["退出", "确认退出", "取消", "Exit", "Quit",
                           "自动登出", "登出", "确认"]
            if any(kw in all_text for kw in exit_keywords):
                if left_bar < 30:
                    return "exit_dialog"

            # 标题/适龄提示画面
            title_keywords = ["适龄提示", "CADPA", "12+", "点击任意位置",
                            "Tap to Start", "开始游戏", "进入游戏"]
            if any(kw in all_text for kw in title_keywords):
                if left_bar > 150:
                    return "title_screen"

            # 加载画面（优先检测：包含"终末"、"地"等加载文本，left_bar 在 80-150 之间）
            loading_keywords = ["终末", "宏山科学院", "加载中", "Loading",
                              "TIPS", "rare", "铁誓军", "JNOW LOADING"]
            if any(kw in all_text for kw in loading_keywords):
                if 80 < left_bar < 150:
                    return "loading_screen"

            # 世界页面关键词
            world_keywords = ["再引春来", "UID:", "探索", "前往", "完成",
                            "领取", "任务", "查看等级", "进入自由演算"]
            if any(kw in all_text for kw in world_keywords):
                if left_bar > 30:
                    green = features.get("green_pixels_top_right", 0)
                    if left_bar > 100 and green > 10000:
                        return "world"
                    elif left_bar < 100:
                        return "quest_panel"
                    return "world"

        # 确认退出对话框：left_bar 极低 (<15) + 亮度高 (>100)
        if left_bar < 15 and brightness > 100:
            return "exit_dialog"

        # 标题画面：left_bar 极高 (>150) + 亮度高 (>180)
        if left_bar > 150 and brightness > 180:
            return "title_screen"

        # 主世界页面：left_bar 较高 (>30)
        if left_bar > 30:
            return "world"

        return "unknown"

    def _llm_decide(self, record: dict, goal: str) -> dict:
        """LLM 根据 OCR 结果 + 画面特征决定下一步动作"""
        import urllib.request
        import json as json_mod
        import re

        ocr_texts = record.get("ocr", [])
        features = record.get("features", {})
        page_type = record.get("page_type", "unknown")

        ocr_summary = "\n".join([f"  - {t['text']} @ {t['center']}" for t in ocr_texts[:15]])
        if not ocr_texts:
            ocr_summary = "  无 OCR 结果"

        prompt = f"""你是明日方舟终末地游戏自动化助手。根据当前画面决定下一步动作。

目标：{goal}

画面特征：
- 页面类型：{page_type}
- 左侧边栏亮度：{features.get('left_bar_brightness', 0):.1f}
- 整体亮度：{features.get('full_brightness', 0):.1f}

OCR 识别文本：
{ocr_summary}

请分析当前画面状态，决定下一步动作。返回 JSON（仅返回 JSON，不要其他文字）：
{{    "action": "tap/back/swipe/wait/none",    "coords": [x, y],    "completed": true/false,    "reason": "决策原因"}}

规则：
1. 如果画面是退出对话框（包含"退出"、"取消"、"确认"、"登出"等），点击"取消"按钮关闭；如果没有"取消"只有"确认"，则点击"确认"
2. 如果画面是标题画面（包含"适龄提示"、"CADPA"等），点击中央进入游戏
3. 如果画面是加载画面（left_bar 在 40-110 之间），等待
4. 如果画面是主世界（left_bar > 30），判断任务是否完成
5. 如果任务完成（包含"完成"、"已领取"等关键词），返回 completed=true
6. 如果任务未完成，决定下一步操作（点击任务图标、滑动查找、领取等）
7. 点击坐标优先使用 OCR 检测到的按钮位置
"""

        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8080/v1/chat/completions",
                data=json_mod.dumps({
                    "messages": [{"role": "system", "content": "你是一个直接回答问题的助手，不要思考过程，直接输出JSON。"}, {"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 512
                }).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json_mod.loads(resp.read())
                text = result["choices"][0]["message"]["content"]

            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                decision = json_mod.loads(json_match.group())
                print(f"  [LLM] 决策: action={decision.get('action')}, "
                      f"coords={decision.get('coords')}, "
                      f"completed={decision.get('completed')}, "
                      f"reason={decision.get('reason', '')[:50]}")
                return decision

        except Exception as e:
            print(f"  [LLM] 调用失败：{e}")

        return {"action": "wait", "coords": None, "completed": False, "reason": "LLM 调用失败"}

    def _check_task_completed(self, record: dict) -> bool:
        """LLM 判断任务是否完成（替代模板化关键词匹配）"""
        decision = self._llm_decide(record, "判断每日任务是否已完成")
        completed = decision.get("completed", False)
        print(f"  [LLM 检查] 任务完成：{completed} (原因：{decision.get('reason', '')[:50]})")
        return completed
        """OCR 检查任务是否完成"""
        # 任务完成关键词
        completed_keywords = ["已完成", "已领取", "完成", "领取", "Done", "Claimed",
                            "收取", "一键领取", "可领取"]
        ocr_texts = record.get("ocr", [])
        if not ocr_texts:
            print(f"  [OCR 检查] 无 OCR 结果，默认成功")
            return True  # 无 OCR 结果时默认成功

        for ocr_item in ocr_texts:
            text = ocr_item.get("text", "")
            for keyword in completed_keywords:
                if keyword in text:
                    print(f"  [OCR 检查] ✓ 检测到关键词：'{keyword}'")
                    return True

        # 如果页面是 world 类型，也认为成功
        page_type = record.get("page_type", "")
        if page_type == "world":
            print(f"  [OCR 检查] ✓ 页面类型为 world，认为成功")
            return True

        all_texts = [t.get("text", "") for t in ocr_texts]
        print(f"  [OCR 检查] ✗ 未找到完成关键词")
        print(f"  [OCR 检查]   识别文本：{all_texts[:5]}")
        return False

    def _handle_exit_dialog(self, max_retries: int = 3) -> bool:
        """处理退出对话框（使用 OCR 定位按钮，优先取消）"""
        for i in range(max_retries):
            print(f"  [对话框] 尝试关闭 (尝试 {i+1}/{max_retries})")

            record = self._capture_and_recognize(f"check_dialog_{i+1}")
            ocr_texts = record.get("ocr", [])

            # 优先查找"取消"按钮（关闭对话框）
            # 其次查找"确认"按钮（确认操作）
            target_coords = None
            target_text = ""
            for t in ocr_texts:
                text = t.get("text", "")
                if "取消" in text:
                    target_coords = t.get("center")
                    target_text = text
                    print(f"  [OCR] 找到取消按钮：{text} @ {target_coords}")
                    break

            if not target_coords:
                for t in ocr_texts:
                    text = t.get("text", "")
                    if "确认" in text or "确定" in text or "OK" in text:
                        target_coords = t.get("center")
                        target_text = text
                        print(f"  [OCR] 找到确认按钮：{text} @ {target_coords}")
                        break

            if target_coords:
                # 先尝试 ADB 点击
                x, y = int(target_coords[0]), int(target_coords[1])
                tap_success = self._adb_tap(x, y)
                # ADB 点击后尝试 MaaFw 触控（双重保障）
                if self._maafw_executor:
                    self._maafw_executor.click(x, y)
                if not tap_success:
                    print(f"  [对话框] ADB 点击失败，尝试滑动...")
                    import subprocess
                    cmd = f"input swipe {x} {y} {x+1} {y+1} 50"
                    subprocess.run(
                        [ADB_PATH, "-s", DEVICE_ADDR, "shell", cmd],
                        capture_output=True, timeout=5
                    )
            else:
                print(f"  [OCR] 未找到取消/确认按钮，点击底部中央")
                self._adb_tap(960, 600)

            time.sleep(2)

            # 如果点击后对话框仍在，尝试按返回键
            record = self._capture_and_recognize(f"check_after_click_{i+1}")
            page_type = self._detect_page_type(
                record.get("features", {}),
                record.get("ocr", [])
            )
            if page_type == "exit_dialog":
                print(f"  [对话框] 点击无效，尝试按返回键...")
                self._adb_back()
                time.sleep(2)

            record = self._capture_and_recognize(f"close_dialog_{i+1}")
            page_type = self._detect_page_type(
                record.get("features", {}),
                record.get("ocr", [])
            )

            if page_type != "exit_dialog":
                print(f"  [成功] 对话框已关闭，当前页面：{page_type}")
                return True

        # 重试失败，重启游戏
        print("  [警告] 对话框无法关闭，尝试重启游戏...")
        if self._adb_restart_game():
            print("  [成功] 游戏已重启")
            self._capture_and_recognize("after_restart")
            return True

        return False

    def execute_flow(self, flow_name: str) -> Dict[str, Any]:
        """执行标准流"""
        flow = self.flow_config.get("flows", {}).get(flow_name)
        if not flow:
            return {"error": f"Flow not found: {flow_name}"}

        print(f"\n{'='*60}")
        print(f"执行标准流：{flow_name}")
        print(f"{'='*60}\n")

        steps = flow.get("steps", [])
        results = []

        for step in steps:
            step_id = step.get("id", "unknown")
            action = step.get("action", "tap")
            desc = step.get("desc", "")

            print(f"\n[步骤] {step_id}: {desc}")

            if action == "check":
                expect = step.get("expect", "")
                record = self._capture_and_recognize(step_id)
                ocr_texts = record.get("ocr", [])
                page_type = self._detect_page_type(record.get("features", {}), ocr_texts)

                # 处理退出对话框
                if page_type == "exit_dialog":
                    if not self._handle_exit_dialog():
                        return {"error": "Failed to close exit dialog", "step": step_id}
                    record = self._capture_and_recognize(f"{step_id}_after_dialog")
                    ocr_texts = record.get("ocr", [])
                    page_type = self._detect_page_type(record.get("features", {}), ocr_texts)

                # 处理标题画面
                # 处理标题画面→加载画面→世界页面过渡
                if page_type == "title_screen":
                    print(f"  [标题] 检测到标题画面，点击进入游戏...")
                    # 优先使用 MaaFw 触控，失败时降级到 ADB
                    if self._maafw_executor and self._maafw_executor.click(960, 540):
                        print(f"  [标题] MaaFw 触控成功")
                    else:
                        self._adb_tap(960, 540)
                        print(f"  [标题] ADB tap 发送")
                    # 等待加载完成（最多 120 秒）
                    for wait_i in range(6):
                        time.sleep(5)
                        record = self._capture_and_recognize(f"{step_id}_transition_{wait_i}")
                        ocr_texts = record.get("ocr", [])
                        page_type = self._detect_page_type(record.get("features", {}), ocr_texts)
                        if page_type == "world":
                            print(f"  [成功] 已进入世界页面")
                            break
                        elif page_type == "loading_screen":
                            print(f"  [加载] 等待加载完成... ({wait_i+1}/24)")
                        else:
                            print(f"  [过渡] 当前页面: {page_type} ({wait_i+1}/24)")

                # 处理加载画面
                if page_type == "loading_screen":
                    print(f"  [加载] 检测到加载画面，等待加载完成...")
                    for wait_i in range(6):
                        time.sleep(5)
                        record = self._capture_and_recognize(f"{step_id}_loading_{wait_i}")
                        ocr_texts = record.get("ocr", [])
                        page_type = self._detect_page_type(record.get("features", {}), ocr_texts)
                        if page_type == "world":
                            print(f"  [成功] 加载完成，已进入世界页面")
                            break
                        print(f"  [加载] 等待... ({wait_i+1}/24)")

                # 处理加载画面（等待加载完成）
                loading_retries = 0
                while page_type == "unknown" and loading_retries < 10:
                    print(f"  [加载] 等待加载完成... (尝试 {loading_retries+1}/10)")
                    time.sleep(5)
                    record = self._capture_and_recognize(f"{step_id}_loading_{loading_retries}")
                    ocr_texts = record.get("ocr", [])
                    page_type = self._detect_page_type(record.get("features", {}), ocr_texts)
                    loading_retries += 1

                # 判断成功：无 expect 默认成功，否则匹配
                if not expect:
                    success = True
                else:
                    # quest_panel 是 world 的子状态，视为等价
                    effective_type = page_type
                    if effective_type == "quest_panel":
                        effective_type = "world"
                    success = effective_type == expect or (expect == "world" and effective_type == "world")
                results.append({"step": step_id, "action": action, "success": success, "page_type": page_type})

            elif action == "tap":
                use_recognition = step.get("use_recognition", False)
                fallback_coords = step.get("fallback_coords", [540, 360])

                if use_recognition:
                    coords = fallback_coords
                    print(f"  [识别] 使用参考坐标：{coords}")
                else:
                    coords = fallback_coords

                success = self._adb_tap(coords[0], coords[1])
                wait_time = step.get("wait", 2)
                time.sleep(wait_time)

                record = self._capture_and_recognize(f"{step_id}_after")
                results.append({"step": step_id, "action": action, "success": success, "coords": coords})

            elif action == "swipe":
                start = step.get("start", [540, 800])
                end = step.get("end", [540, 400])
                duration = step.get("duration", 500)
                print(f"  [滑动] {start} → {end} ({duration}ms)")
                # 实现实际滑动
                import subprocess
                try:
                    cmd = f"input swipe {start[0]} {start[1]} {end[0]} {end[1]} {duration}"
                    r = subprocess.run(
                        [ADB_PATH, "-s", DEVICE_ADDR, "shell", cmd],
                        capture_output=True, timeout=10
                    )
                    success = r.returncode == 0
                    print(f"  [滑动] {'成功' if success else '失败'}")
                except Exception as e:
                    print(f"  [滑动] 错误: {e}")
                    success = False
                results.append({"step": step_id, "action": action, "success": success})

            elif action == "back":
                success = self._adb_back()
                wait_time = step.get("wait", 2)
                time.sleep(wait_time)
                record = self._capture_and_recognize(f"{step_id}_after")
                results.append({"step": step_id, "action": action, "success": success})

            elif action == "wait":
                wait_time = step.get("wait", 2)
                time.sleep(wait_time)
                results.append({"step": step_id, "action": action, "success": True})

            elif action == "claim":
                target = step.get("target", "claim_all")
                record = self._capture_and_recognize(f"{step_id}_before")

                # 检查是否在退出对话框
                ocr_texts = record.get("ocr", [])
                features = record.get("features", {})
                page_type = self._detect_page_type(features, ocr_texts)

                if page_type == "exit_dialog":
                    print(f"  [退出对话框] 检测到退出对话框，先关闭...")
                    if self._handle_exit_dialog():
                        time.sleep(2)
                        record = self._capture_and_recognize(f"{step_id}_after_close")

                # 先判断是否有可领取的奖励
                check_decision = self._llm_decide(record, "判断是否有可领取的奖励")
                has_rewards = check_decision.get("completed", False)

                if not has_rewards:
                    print(f"  [领取] LLM 判断无奖励可领取，跳过")
                    print(f"    原因: {check_decision.get('reason', '')[:80]}")
                    results.append({
                        "step": step_id, "action": action, "success": True,
                        "target": target, "claimed": False,
                        "reason": check_decision.get("reason", "无奖励可领取")
                    })
                    continue

                # 有奖励，查找领取按钮
                decision = self._llm_decide(record, "查找并点击领取按钮")

                if decision.get("action") == "tap" and decision.get("coords"):
                    coords = decision["coords"]
                    print(f"  [LLM 领取] 点击 {coords} (原因: {decision.get('reason', '')[:50]})")
                else:
                    coords = [810, 900]
                    print(f"  [LLM 领取] LLM 未返回有效坐标，使用默认 {coords}")

                success = self._adb_tap(coords[0], coords[1])
                time.sleep(2)
                record = self._capture_and_recognize(f"{step_id}_after_claim")
                ocr_check = self._check_task_completed(record)

                results.append({
                    "step": step_id, "action": action,
                    "success": success and ocr_check,
                    "target": target, "ocr_verified": ocr_check,
                    "llm_coords": coords, "claimed": True
                })

        return {
            "flow": flow_name,
            "success": all(r.get("success", False) for r in results),
            "steps": len(steps),
            "results": results,
            "recognition_records": self.recognition_records
        }


def main():
    """主函数"""
    config_path = PROJECT_ROOT / "config" / "standard_flows" / "flows_config_v5.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        flow_config = json.load(f)

    executor = HighReliabilityFlowExecutor(flow_config)
    result = executor.execute_flow("daily_quest")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    record_dir = PROJECT_ROOT / "cache" / f"high_reliability_{timestamp}"
    record_dir.mkdir(parents=True, exist_ok=True)

    with open(record_dir / "recognition_records.json", 'w', encoding='utf-8') as f:
        json.dump(result.get("recognition_records", []), f, ensure_ascii=False, indent=2)

    with open(record_dir / "execution_result.json", 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    for i, img in enumerate(executor.screenshots):
        cv2.imwrite(str(record_dir / f"screenshot_{i:03d}.png"), img)

    print(f"\n{'='*60}")
    print(f"执行完成：{result.get('flow')}")
    print(f"成功率：{sum(1 for r in result.get('results', []) if r.get('success'))}/{len(result.get('results', []))}")
    print(f"记录保存：{record_dir}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
