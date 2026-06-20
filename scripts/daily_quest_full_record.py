#!/usr/bin/env python3
"""
每日任务执行脚本 - 完整记录版
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

def capture_and_analyze(step_name: str, recognition_engine: RecognitionEngine, 
                       page_analyzer: HighPrecisionPageAnalyzer, save_screenshot: bool = True) -> Dict[str, Any]:
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
    
    # 保存原始截图
    if save_screenshot:
        screenshot_path = record_dir / f"screenshot_{step_name.replace(' ', '_')}.png"
        cv2.imwrite(str(screenshot_path), cv_img)
    
    # 旋转为横屏 (1280x720)
    rotated = cv2.rotate(cv_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    resized = cv2.resize(rotated, (1280, 720))
    
    result = {
        "step": step_name,
        "timestamp": time.time(),
        "resolution": [resized.shape[1], resized.shape[0]],
        "screenshot": str(screenshot_path) if save_screenshot else None,
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
            centers = detail.get('centers', [])[:5]  # 只显示前 5 个
            print(f"  ✓ {name}: contours={detail.get('contours')}, centers={centers}")
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
    page_result = page_analyzer.analyze(resized)
    
    result["page_analysis"] = {
        "page_type": page_result["page_type"],
        "confidence": page_result["confidence"],
        "detail": page_result["detail"],
        "features": page_result["features"]
    }
    
    print(f"  页面类型：{page_result['page_type']} (置信度 {page_result['confidence']:.2f})")
    print(f"  特征：left_bar={page_result['features'].get('left_bar_brightness', 0):.1f}, "
          f"green={page_result['features'].get('green_pixels_top_right', 0)}, "
          f"brightness={page_result['features'].get('full_brightness', 0):.1f}")
    
    return result

def main():
    """主流程"""
    print("="*60)
    print("每日任务执行 - 完整记录版")
    print("="*60)
    
    # 初始化识别引擎
    recognition_engine = RecognitionEngine()
    page_analyzer = HighPrecisionPageAnalyzer()
    
    # 记录目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    global record_dir
    record_dir = PROJECT_ROOT / "cache" / f"daily_quest_full_record_{timestamp}"
    record_dir.mkdir(parents=True, exist_ok=True)
    
    all_records = []
    
    # 步骤 1: 当前画面分析
    record = capture_and_analyze("Step1_当前画面", recognition_engine, page_analyzer)
    all_records.append(record)
    
    # 判断当前页面
    page_type = record.get("page_analysis", {}).get("page_type", "unknown")
    left_bar = record.get("page_analysis", {}).get("features", {}).get("left_bar_brightness", 0)
    
    print(f"\n[判断] 当前页面：{page_type}, left_bar={left_bar:.1f}")
    
    # 如果不是任务面板，尝试导航
    if page_type not in ("quest_panel",):
        print(f"\n[导航] 当前不在任务面板，尝试点击任务图标 (860, 80)")
        adb_tap(860, 80)
        time.sleep(3)
        
        record = capture_and_analyze("Step2_点击任务图标后", recognition_engine, page_analyzer)
        all_records.append(record)
        
        page_type = record.get("page_analysis", {}).get("page_type", "unknown")
        print(f"\n[判断] 点击后页面：{page_type}")
    
    # 检查是否在任务面板
    if page_type == "quest_panel":
        print("\n[成功] 已进入任务面板")
        
        # 领取奖励
        print("\n[领取] 点击领取按钮 (810, 900)")
        adb_tap(810, 900)
        time.sleep(2)
        
        record = capture_and_analyze("Step3_领取后", recognition_engine, page_analyzer)
        all_records.append(record)
        
        # 返回
        print("\n[返回] 按返回键")
        adb_back()
        time.sleep(2)
        
        record = capture_and_analyze("Step4_返回后", recognition_engine, page_analyzer)
        all_records.append(record)
    else:
        print(f"\n[警告] 未在任务面板 (当前：{page_type})")
        
        # 尝试按返回键
        print("\n[尝试] 按返回键")
        adb_back()
        time.sleep(2)
        
        record = capture_and_analyze("Step3_按返回后", recognition_engine, page_analyzer)
        all_records.append(record)
    
    # 保存记录
    report_path = record_dir / "recognition_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    
    # 生成执行判断报告
    print(f"\n{'='*60}")
    print(f"[完成] 记录已保存到：{report_path}")
    print(f"{'='*60}")
    
    # 执行总结
    print("\n[执行总结]")
    total_steps = len(all_records)
    print(f"  总步骤：{total_steps}")
    
    # 判断执行是否顺利
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
    
    # 检查是否有模板匹配成功
    if any(any(t.get("success") for t in r.get("template_match", [])) for r in all_records):
        print("  ✓ 模板匹配有成功项")
        success_flags.append(True)
    else:
        print("  ✗ 模板匹配全部失败")
        success_flags.append(False)
    
    # 检查是否有颜色匹配成功
    if any(any(c.get("success") for c in r.get("color_match", [])) for r in all_records):
        print("  ✓ 颜色匹配有成功项")
        success_flags.append(True)
    else:
        print("  ✗ 颜色匹配全部失败")
        success_flags.append(False)
    
    # 总体判断
    success_rate = sum(success_flags) / len(success_flags) if success_flags else 0
    print(f"\n[总体判断] 成功率：{success_rate*100:.0f}%")
    
    if success_rate >= 0.75:
        print("  ✅ 执行顺利")
    elif success_rate >= 0.5:
        print("  ⚠️ 执行部分成功")
    else:
        print("  ❌ 执行失败")
    
    # 保存判断报告
    judgment_report = {
        "timestamp": datetime.now().isoformat(),
        "total_steps": total_steps,
        "success_flags": success_flags,
        "success_rate": success_rate,
        "judgment": "success" if success_rate >= 0.75 else ("partial" if success_rate >= 0.5 else "failed"),
        "details": {
            "entered_quest_panel": any(r.get("page_analysis", {}).get("page_type") == "quest_panel" for r in all_records),
            "detected_world": any(r.get("page_analysis", {}).get("page_type") == "world" for r in all_records),
            "template_match_success": any(any(t.get("success") for t in r.get("template_match", [])) for r in all_records),
            "color_match_success": any(any(c.get("success") for c in r.get("color_match", [])) for r in all_records),
        }
    }
    
    judgment_path = record_dir / "judgment_report.json"
    with open(judgment_path, 'w', encoding='utf-8') as f:
        json.dump(judgment_report, f, ensure_ascii=False, indent=2)
    
    print(f"\n判断报告已保存到：{judgment_path}")

if __name__ == "__main__":
    main()
