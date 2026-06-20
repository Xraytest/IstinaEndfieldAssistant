#!/usr/bin/env python3
"""
每日任务执行脚本 - 增强版
记录每张图的 OCR 与模板匹配结果，判断执行是否顺利
"""

import sys, os, json, time, base64, hashlib, cv2, numpy as np, argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from core.adb_utils import ADB, adb_screencap
from core.recognition.recognition_engine import RecognitionEngine, PREDEFINED_STATES

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

def adb_tap(x: int, y: int) -> bool:
    """ADB tap 点击"""
    import subprocess
    try:
        r = subprocess.run(
            [ADB_PATH, "-s", DEVICE_ADDR, "shell", "input", "tap", str(x), str(y)],
            capture_output=True, timeout=5
        )
        return r.returncode == 0
    except Exception as e:
        print(f"  [TAP 错误] {e}")
        return False

def adb_swipe(x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
    """ADB swipe 滑动"""
    import subprocess
    try:
        cmd = f"input swipe {x1} {y1} {x2} {y2} {duration}"
        r = subprocess.run(
            [ADB_PATH, "-s", DEVICE_ADDR, "shell", cmd],
            capture_output=True, timeout=10
        )
        return r.returncode == 0
    except Exception as e:
        print(f"  [SWIPE 错误] {e}")
        return False

def adb_back() -> bool:
    """ADB 返回键"""
    import subprocess
    try:
        r = subprocess.run(
            [ADB_PATH, "-s", DEVICE_ADDR, "shell", "input", "keyevent", "4"],
            capture_output=True, timeout=5
        )
        return r.returncode == 0
    except Exception as e:
        print(f"  [BACK 错误] {e}")
        return False

def capture_and_analyze(step_name: str, recognition_engine: RecognitionEngine) -> Dict[str, Any]:
    """截图并进行 OCR+ 模板匹配分析"""
    print(f"\n{'='*60}")
    print(f"[{step_name}]")
    print(f"{'='*60}")
    
    # 截图
    img_bytes = adb_screencap(serial=DEVICE_ADDR)
    if not img_bytes:
        print("  [错误] 截图失败")
        return {"error": "screenshot_failed"}
    
    # 转换为 numpy 数组
    np_img = np.frombuffer(img_bytes, dtype=np.uint8)
    cv_img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
    if cv_img is None:
        print("  [错误] 图片解码失败")
        return {"error": "decode_failed"}
    
    # 旋转为横屏 (1280x720)
    rotated = cv2.rotate(cv_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    resized = cv2.resize(rotated, (1280, 720))
    
    result = {
        "step": step_name,
        "timestamp": time.time(),
        "resolution": [resized.shape[1], resized.shape[0]],
        "template_match": [],
        "color_match": [],
        "page_analysis": {}
    }
    
    # 1. 模板匹配检测
    print("\n[模板匹配]")
    template_checks = [
        ("TaskIcon", "SceneManager/TaskIcon.png", [700, 30, 300, 150], 15),
        ("WorldMenu", "SceneManager/WorldMenu.png", [0, 0, 200, 200], 5),
        ("CancelButton", "Common/Button/CancelButtonType1.png", [200, 500, 700, 500], 5),
    ]
    
    for name, template, roi, threshold in template_checks:
        config = {
            "type": "TemplateMatch",
            "template": template,
            "roi": roi,
            "threshold": threshold
        }
        success, detail = recognition_engine.recognize(resized, config)
        
        if success:
            print(f"  ✓ {name}: bbox={detail.get('bbox')}, center={detail.get('center')}, confidence={detail.get('confidence', 0):.2f}")
            result["template_match"].append({
                "name": name,
                "success": True,
                "bbox": detail.get("bbox"),
                "center": detail.get("center"),
                "confidence": detail.get("confidence", 0)
            })
        else:
            print(f"  ✗ {name}: matches={detail.get('matches', 0)}/{threshold}")
            result["template_match"].append({
                "name": name,
                "success": False,
                "matches": detail.get("matches", 0)
            })
    
    # 2. 颜色匹配检测
    print("\n[颜色匹配]")
    color_checks = [
        ("YellowButton", [200, 500, 700, 500], [28, 100, 100], [29, 255, 255], 100, 1),
        ("GreenResource", [900, 0, 380, 150], [35, 80, 80], [85, 255, 200], 50, 1),
    ]
    
    for name, roi, lower, upper, min_area, min_contours in color_checks:
        config = {
            "type": "ColorMatch",
            "roi": roi,
            "lower": lower,
            "upper": upper,
            "min_area": min_area,
            "min_contours": min_contours
        }
        success, detail = recognition_engine.recognize(resized, config)
        
        if success:
            print(f"  ✓ {name}: contours={detail.get('contours')}, centers={detail.get('centers', [])[:3]}")
            result["color_match"].append({
                "name": name,
                "success": True,
                "contours": detail.get("contours"),
                "centers": detail.get("centers", [])
            })
        else:
            print(f"  ✗ {name}: contours={detail.get('contours', 0)}/{min_contours}")
            result["color_match"].append({
                "name": name,
                "success": False,
                "contours": detail.get("contours", 0)
            })
    
    # 3. 页面类型分析
    print("\n[页面分析]")
    from core.page_analyzer import HighPrecisionPageAnalyzer
    analyzer = HighPrecisionPageAnalyzer()
    page_result = analyzer.analyze(resized)
    
    result["page_analysis"] = {
        "page_type": page_result["page_type"],
        "confidence": page_result["confidence"],
        "detail": page_result["detail"],
        "features": page_result["features"]
    }
    
    print(f"  页面类型：{page_result['page_type']} (置信度 {page_result['confidence']:.2f})")
    print(f"  特征：left_bar={page_result['features'].get('left_bar_brightness', 0):.0f}, "
          f"green={page_result['features'].get('green_pixels_top_right', 0)}")
    
    return result

def main():
    """主流程"""
    print("="*60)
    print("每日任务执行 - OCR 与模板匹配记录")
    print("="*60)
    
    # 初始化识别引擎
    recognition_engine = RecognitionEngine()
    
    # 记录目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    record_dir = PROJECT_ROOT / "cache" / f"daily_quest_record_{timestamp}"
    record_dir.mkdir(parents=True, exist_ok=True)
    
    all_records = []
    
    # 步骤 1: 当前画面分析
    record = capture_and_analyze("Step1_当前画面", recognition_engine)
    all_records.append(record)
    
    # 判断当前页面
    page_type = record.get("page_analysis", {}).get("page_type", "unknown")
    print(f"\n[判断] 当前页面：{page_type}")
    
    # 步骤 2: 如果不是世界页面，尝试导航
    if page_type not in ("world", "world_transition"):
        print("\n[导航] 尝试点击任务图标 (860, 80)")
        adb_tap(860, 80)
        time.sleep(3)
        
        record = capture_and_analyze("Step2_点击任务图标后", recognition_engine)
        all_records.append(record)
        
        page_type = record.get("page_analysis", {}).get("page_type", "unknown")
        print(f"\n[判断] 点击后页面：{page_type}")
    
    # 步骤 3: 检查是否在任务面板
    if page_type == "quest_panel":
        print("\n[成功] 已进入任务面板")
        
        # 滑动查找每日任务
        print("\n[滑动] 查找每日任务列表")
        adb_swipe(540, 800, 540, 400, 500)
        time.sleep(1)
        
        record = capture_and_analyze("Step3_滑动后", recognition_engine)
        all_records.append(record)
        
        # 领取奖励
        print("\n[领取] 点击领取按钮 (810, 900)")
        adb_tap(810, 900)
        time.sleep(2)
        
        record = capture_and_analyze("Step4_领取后", recognition_engine)
        all_records.append(record)
        
        # 返回
        print("\n[返回] 按返回键")
        adb_back()
        time.sleep(2)
        
        record = capture_and_analyze("Step5_返回后", recognition_engine)
        all_records.append(record)
    else:
        print(f"\n[警告] 未在任务面板 (当前：{page_type})")
        record = capture_and_analyze("Step3_非任务面板", recognition_engine)
        all_records.append(record)
    
    # 保存记录
    report_path = record_dir / "recognition_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"[完成] 记录已保存到：{report_path}")
    print(f"{'='*60}")
    
    # 执行总结
    print("\n[执行总结]")
    total_steps = len(all_records)
    successful_taps = sum(1 for r in all_records if any(t.get("success") for t in r.get("template_match", [])))
    print(f"  总步骤：{total_steps}")
    print(f"  成功识别：{successful_taps}/{total_steps}")
    
    # 判断执行是否顺利
    print("\n[执行判断]")
    if any(r.get("page_analysis", {}).get("page_type") == "quest_panel" for r in all_records):
        print("  ✓ 成功进入任务面板")
    else:
        print("  ✗ 未进入任务面板")
    
    if any(r.get("page_analysis", {}).get("page_type") == "world" for r in all_records):
        print("  ✓ 成功返回世界页面")
    else:
        print("  ✗ 未返回世界页面")

if __name__ == "__main__":
    main()
