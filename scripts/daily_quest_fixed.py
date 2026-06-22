#!/usr/bin/env python3
"""
每日任务执行 - 修正版
修复模板匹配和页面类型判断问题
"""

import sys, os, json, time, cv2, numpy as np, argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from _path_setup import PROJECT_ROOT, SRC_DIR, MODULE_DIR, ensure_path
ensure_path()

from core.adb_utils import adb_screencap
from core.recognition.recognition_engine import RecognitionEngine
from core.page_analyzer import HighPrecisionPageAnalyzer

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

def adb_restart_game() -> bool:
    """重启游戏（明日方舟：终末地）"""
    import subprocess
    GAME_PACKAGE = "com.hypergryph.endfield"  # 正确的包名
    try:
        # 先关闭游戏进程
        print("  [重启] 关闭游戏进程...")
        r1 = subprocess.run(
            [ADB_PATH, "-s", DEVICE_ADDR, "shell", "am", "force-stop", GAME_PACKAGE],
            capture_output=True, timeout=10
        )

        # 等待 2 秒
        time.sleep(2)

        # 重新启动游戏
        print("  [重启] 启动游戏...")
        r2 = subprocess.run(
            [ADB_PATH, "-s", DEVICE_ADDR, "shell", "monkey", "-p", GAME_PACKAGE, "1"],
            capture_output=True, timeout=10
        )

        # 等待游戏启动（约 15 秒）
        print("  [重启] 等待游戏启动...")
        time.sleep(15)

        return r1.returncode == 0 and r2.returncode == 0
    except Exception as e:
        print(f"  [重启错误] {e}")
        return False

def adb_tap(x: int, y: int) -> bool:
    import subprocess
    try:
        r = subprocess.run([ADB_PATH, "-s", DEVICE_ADDR, "shell", "input", "tap", str(x), str(y)],
                          capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception as e:
        print(f"  [TAP 错误] {e}")
        return False

def adb_back() -> bool:
    import subprocess
    try:
        r = subprocess.run([ADB_PATH, "-s", DEVICE_ADDR, "shell", "input", "keyevent", "4"],
                          capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception as e:
        print(f"  [BACK 错误] {e}")
        return False

def adb_swipe(x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
    import subprocess
    try:
        cmd = f"input swipe {x1} {y1} {x2} {y2} {duration}"
        r = subprocess.run([ADB_PATH, "-s", DEVICE_ADDR, "shell", cmd],
                          capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception as e:
        print(f"  [SWIPE 错误] {e}")
        return False

def detect_page_type(features: dict) -> str:
    """根据特征判断页面类型（改进版）"""
    left_bar = features.get("left_bar_brightness", 0)
    green = features.get("green_pixels_top_right", 0)
    brightness = features.get("full_brightness", 0)
    
    # 任务面板：left_bar 高 + 亮度低
    if left_bar > 40 and brightness < 90:
        return "quest_panel"
    
    # 世界页面：left_bar 中等 + 有绿色元素
    if left_bar > 30 and green > 100:
        return "world"
    
    # 退出对话框：left_bar 低 + 亮度高
    if left_bar < 30 and brightness > 100:
        return "exit_dialog"
    
    # 标题/加载画面
    if left_bar < 25 and brightness > 100:
        return "title_loading"
    
    return "unknown"

def capture_and_analyze(step_name: str, recognition_engine: RecognitionEngine,
                       page_analyzer: HighPrecisionPageAnalyzer, record_dir: Path) -> Dict[str, Any]:
    """截图并分析"""
    print(f"\n{'='*60}")
    print(f"[{step_name}]")
    print(f"{'='*60}")
    
    # 截图
    img_bytes = adb_screencap(serial=DEVICE_ADDR)
    if not img_bytes:
        return {"error": "screenshot_failed"}
    
    np_img = np.frombuffer(img_bytes, dtype=np.uint8)
    cv_img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
    if cv_img is None:
        return {"error": "decode_failed"}
    
    # 保存原始截图
    screenshot_path = record_dir / f"screenshot_{step_name.replace(' ', '_')}.png"
    cv2.imwrite(str(screenshot_path), cv_img)
    
    # 旋转为横屏
    rotated = cv2.rotate(cv_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    resized = cv2.resize(rotated, (1280, 720))
    
    result = {
        "step": step_name,
        "timestamp": time.time(),
        "screenshot": str(screenshot_path),
        "template_match": [],
        "color_match": [],
        "page_analysis": {}
    }
    
    # 1. 模板匹配（降低阈值）
    print("\n[模板匹配]")
    template_checks = [
        ("TaskIcon", "SceneManager/TaskIcon.png", [700, 30, 300, 150], 5),  # 从 15 降到 5
        ("WorldMenu", "SceneManager/WorldMenu.png", [0, 0, 200, 200], 3),    # 从 5 降到 3
        ("CancelButton", "Common/Button/CancelButtonType1.png", [200, 500, 700, 500], 3),  # 从 5 降到 3
    ]
    
    for name, template, roi, threshold in template_checks:
        config = {"type": "TemplateMatch", "template": template, "roi": roi, "threshold": threshold}
        success, detail = recognition_engine.recognize(resized, config)
        
        if success:
            print(f"  ✓ {name}: bbox={detail.get('bbox')}, center={detail.get('center')}, "
                  f"confidence={detail.get('confidence', 0):.2f}, matches={detail.get('matches', 0)}")
        else:
            print(f"  ✗ {name}: matches={detail.get('matches', 0)}/{threshold}")
        
        result["template_match"].append({
            "name": name, "success": success,
            "bbox": detail.get("bbox"), "center": detail.get("center"),
            "confidence": detail.get("confidence", 0), "matches": detail.get("matches", 0)
        })
    
    # 2. 颜色匹配（移除金色元素匹配）
    print("\n[颜色匹配]")
    color_checks = [
        ("YellowButton", [200, 500, 700, 500], [28, 100, 100], [29, 255, 255], 50, 1),
        ("GreenResource", [900, 0, 380, 150], [35, 80, 80], [85, 255, 200], 30, 1),
    ]
    
    for name, roi, lower, upper, min_area, min_contours in color_checks:
        config = {"type": "ColorMatch", "roi": roi, "lower": lower, "upper": upper,
                 "min_area": min_area, "min_contours": min_contours}
        success, detail = recognition_engine.recognize(resized, config)
        
        centers = detail.get('centers', [])[:3]
        print(f"  {'✓' if success else '✗'} {name}: contours={detail.get('contours', 0)}/{min_contours}, "
              f"centers={centers}")
        
        result["color_match"].append({
            "name": name, "success": success,
            "contours": detail.get("contours", 0), "centers": detail.get("centers", [])
        })
    
    # 3. 页面分析
    print("\n[页面分析]")
    page_result = page_analyzer.analyze(resized)
    
    # 使用改进的页面类型判断
    detected_type = detect_page_type(page_result["features"])
    
    result["page_analysis"] = {
        "page_type": detected_type,
        "vlm_page_type": page_result["page_type"],
        "confidence": page_result["confidence"],
        "features": page_result["features"]
    }
    
    print(f"  页面类型：{detected_type} (VLM: {page_result['page_type']})")
    print(f"  特征：left_bar={page_result['features'].get('left_bar_brightness', 0):.1f}, "
          f"green={page_result['features'].get('green_pixels_top_right', 0)}, "
          f"brightness={page_result['features'].get('full_brightness', 0):.1f}")
    
    return result

def main():
    print("="*60)
    print("每日任务执行 - 修正版")
    print("="*60)
    
    recognition_engine = RecognitionEngine()
    page_analyzer = HighPrecisionPageAnalyzer()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    record_dir = PROJECT_ROOT / "cache" / f"daily_quest_fixed_{timestamp}"
    record_dir.mkdir(parents=True, exist_ok=True)
    
    all_records = []
    
    # Step1: 当前画面
    record = capture_and_analyze("Step1_当前画面", recognition_engine, page_analyzer, record_dir)
    all_records.append(record)
    
    page_type = record.get("page_analysis", {}).get("page_type", "unknown")
    print(f"\n[判断] 当前页面：{page_type}")
    
    # 根据页面类型导航
    max_retries = 3
    for retry in range(max_retries):
        print(f"\n[判断] 当前页面：{page_type} (尝试 {retry+1}/{max_retries})")

        if page_type == "exit_dialog":
            print(f"\n[导航] 检测到退出对话框，尝试关闭...")
            # 尝试点击黄色按钮（取消按钮）
            yellow_centers = None
            for cm in record.get("color_match", []):
                if cm.get("name") == "YellowButton" and cm.get("centers"):
                    yellow_centers = cm["centers"]
                    break

            if yellow_centers:
                # 点击第一个黄色按钮中心
                target_center = yellow_centers[0]
                print(f"  点击取消按钮：{target_center}")
                adb_tap(int(target_center[0]), int(target_center[1]))
            else:
                # 点击底部中央
                print("  点击底部中央")
                adb_tap(960, 600)

            time.sleep(2)

            record = capture_and_analyze(f"Step{retry+2}_关闭对话框后", recognition_engine, page_analyzer, record_dir)
            all_records.append(record)

            page_type = record.get("page_analysis", {}).get("page_type", "unknown")

            if page_type != "exit_dialog":
                print(f"\n[成功] 对话框已关闭，当前页面：{page_type}")
                break
            else:
                print(f"\n[警告] 对话框仍未关闭，重试...")
        else:
            break
    
    # 如果仍然是退出对话框，尝试重启游戏
    if page_type == "exit_dialog":
        print(f"\n[警告] 多次尝试失败，检测到无响应状态，尝试重启游戏...")
        if adb_restart_game():
            print(f"\n[成功] 游戏已重启")
            # 等待游戏加载
            time.sleep(10)
            
            record = capture_and_analyze("Step_重启后", recognition_engine, page_analyzer, record_dir)
            all_records.append(record)
            
            page_type = record.get("page_analysis", {}).get("page_type", "unknown")
            print(f"\n[判断] 重启后页面：{page_type}")
        else:
            print(f"\n[错误] 重启游戏失败")

    # 检查是否在任务面板
    if page_type == "quest_panel":
        print("\n[成功] 已在任务面板")
        
        # 领取奖励
        print("\n[领取] 点击领取按钮 (810, 900)")
        adb_tap(810, 900)
        time.sleep(2)
        
        record = capture_and_analyze("Step3_领取后", recognition_engine, page_analyzer, record_dir)
        all_records.append(record)
        
        # 返回
        print("\n[返回] 按返回键")
        adb_back()
        time.sleep(2)
        
        record = capture_and_analyze("Step4_返回后", recognition_engine, page_analyzer, record_dir)
        all_records.append(record)
        
    elif page_type == "world":
        print("\n[导航] 在世界页面，点击任务图标 (860, 80)")
        adb_tap(860, 80)
        time.sleep(3)
        
        record = capture_and_analyze("Step2_点击任务图标后", recognition_engine, page_analyzer, record_dir)
        all_records.append(record)
        
        # 检查是否进入任务面板
        if record.get("page_analysis", {}).get("page_type") == "quest_panel":
            print("\n[成功] 已进入任务面板")
            
            # 领取
            adb_tap(810, 900)
            time.sleep(2)
            
            record = capture_and_analyze("Step3_领取后", recognition_engine, page_analyzer, record_dir)
            all_records.append(record)
            
            adb_back()
            time.sleep(2)
            
            record = capture_and_analyze("Step4_返回后", recognition_engine, page_analyzer, record_dir)
            all_records.append(record)
        else:
            print("\n[尝试] 按返回键")
            adb_back()
            time.sleep(2)
            
            record = capture_and_analyze("Step3_按返回后", recognition_engine, page_analyzer, record_dir)
            all_records.append(record)
            
    else:
        print(f"\n[尝试] 按返回键")
        adb_back()
        time.sleep(2)
        
        record = capture_and_analyze("Step2_按返回后", recognition_engine, page_analyzer, record_dir)
        all_records.append(record)
    
    # 保存记录
    report_path = record_dir / "recognition_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    
    # 执行判断
    print(f"\n{'='*60}")
    print(f"[完成] 记录已保存到：{report_path}")
    print(f"{'='*60}")
    
    print("\n[执行判断]")
    success_flags = []
    
    if any(r.get("page_analysis", {}).get("page_type") == "quest_panel" for r in all_records):
        print("  ✓ 成功进入任务面板")
        success_flags.append(True)
    else:
        print("  ✗ 未进入任务面板")
        success_flags.append(False)
    
    if any(r.get("page_analysis", {}).get("page_type") == "world" for r in all_records):
        print("  ✓ 检测到世界页面")
        success_flags.append(True)
    else:
        print("  ✗ 未检测到世界页面")
        success_flags.append(False)
    
    if any(any(t.get("success") for t in r.get("template_match", [])) for r in all_records):
        print("  ✓ 模板匹配有成功项")
        success_flags.append(True)
    else:
        print("  ✗ 模板匹配全部失败")
        success_flags.append(False)
    
    if any(any(c.get("success") for c in r.get("color_match", [])) for r in all_records):
        print("  ✓ 颜色匹配有成功项")
        success_flags.append(True)
    else:
        print("  ✗ 颜色匹配全部失败")
        success_flags.append(False)
    
    success_rate = sum(success_flags) / len(success_flags) if success_flags else 0
    print(f"\n[总体判断] 成功率：{success_rate*100:.0f}%")
    
    if success_rate >= 0.75:
        print("  ✅ 执行顺利")
    elif success_rate >= 0.5:
        print("  ⚠️ 执行部分成功")
    else:
        print("  ❌ 执行失败")

if __name__ == "__main__":
    main()
