#!/usr/bin/env python3
"""调试 tap 坐标对比：扫描脚本 vs 标准流引擎"""
import subprocess, time, cv2, numpy as np, sys, os, json, argparse
from pathlib import Path

from _path_setup import PROJECT_ROOT, SRC_DIR, MODULE_DIR, ensure_path
ensure_path()

parser = argparse.ArgumentParser()
parser.add_argument("--device", help="设备地址, 如 localhost:16512")
parser.add_argument("--adb", help="ADB 路径")
args = parser.parse_args()

config = {}
try:
    with open(str(PROJECT_ROOT / "config" / "client_config.json")) as f:
        config = json.load(f)
except Exception:
    pass
device_config = config.get("device", {})

ADB_PATH = args.adb or device_config.get("adb_path", str(PROJECT_ROOT / "3rd-party" / "adb" / "adb.exe"))
DEVICE = args.device or device_config.get("address", "localhost:16512")

# 测试坐标：扫描脚本验证有效的坐标
TEST_X, TEST_Y = 860, 80

def adb_screencap():
    """截图"""
    r = subprocess.run([ADB_PATH, "-s", DEVICE, "exec-out", "screencap", "-p"],
                       capture_output=True, timeout=10)
    if r.returncode == 0 and len(r.stdout) > 1000:
        return cv2.imdecode(np.frombuffer(r.stdout, dtype=np.uint8), cv2.IMREAD_COLOR)
    return None

def adb_back():
    """按返回键"""
    subprocess.run([ADB_PATH, "-s", DEVICE, "shell", "input", "keyevent", "4"], 
                   capture_output=True, timeout=5)

def test_scan_script_tap():
    """测试扫描脚本方式的 tap"""
    print("\n[测试 1] 扫描脚本方式：subprocess.run([... 'input', 'tap', '860', '80'])")
    result = subprocess.run(
        [ADB_PATH, "-s", DEVICE, "shell", "input", "tap", "860", "80"],
        capture_output=True, timeout=5
    )
    return result.returncode == 0

def test_adb_utils_tap():
    """测试 adb_utils 方式的 tap"""
    print("\n[测试 2] adb_utils 方式：ADB().tap(860, 80)")
    from core.adb_utils import ADB
    adb = ADB()
    return adb.tap(860, 80)

def test_adb_utils_tap_direct():
    """测试 adb_utils 底层函数的 tap"""
    print("\n[测试 3] adb_utils 底层：adb_tap(860, 80)")
    from core.adb_utils import adb_tap
    return adb_tap(860, 80)

def main():
    print("="*60)
    print("Tap 坐标调试")
    print("="*60)

    # 基准截图
    img_base = adb_screencap()
    if img_base is None:
        print("[ERROR] 基准截图失败")
        sys.exit(1)
    
    print(f"[基准] 分辨率：{img_base.shape[1]}x{img_base.shape[0]}")

    # 测试三种 tap 方式
    tests = [
        ("扫描脚本方式", test_scan_script_tap),
        ("ADB().tap()", test_adb_utils_tap),
        ("adb_tap()", test_adb_utils_tap_direct),
    ]

    for name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"[测试] {name}")
        print(f"{'='*60}")

        # 确保回到世界
        print("[准备] 回到世界...")
        for _ in range(5):
            adb_back()
            time.sleep(0.3)
        time.sleep(1)

        # 执行 tap
        success = test_func()
        print(f"[点击] input tap 860 80 {'成功' if success else '失败'}")

        # 等待并截图
        time.sleep(3)
        img_after = adb_screencap()

        # 判断结果（通过像素差异）
        if img_after is not None and img_base is not None:
            diff = cv2.absdiff(img_after, img_base)
            gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray_diff, 30, 255, cv2.THRESH_BINARY)
            changed_pixels = cv2.countNonZero(thresh)
            if changed_pixels > 500000:
                print(f"[结果] ✅ 面板已打开 (变化像素: {changed_pixels:,})")
            else:
                print(f"[结果] ⚠️  无明显变化 (变化像素: {changed_pixels:,})")
        else:
            print("[结果] ⚠️  无法判断")

        # 返回
        print("[恢复] 按返回键...")
        for _ in range(3):
            adb_back()
            time.sleep(0.3)
        time.sleep(1)

if __name__ == "__main__":
    main()
