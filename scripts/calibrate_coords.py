#!/usr/bin/env python3
"""
坐标校准脚本

通过像素扫描找出任务图标的准确坐标
参考：之前坐标扫描验证结果 (860,80) 59.9%
"""

import subprocess, time, cv2, numpy as np, sys, os, json, argparse
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

# 命令行参数
parser = argparse.ArgumentParser()
parser.add_argument("--device", help="设备地址, 如 localhost:16512")
parser.add_argument("--adb", help="ADB 路径")
args = parser.parse_args()

# 从配置读取默认值
config = {}
try:
    with open(str(PROJECT / "config" / "client_config.json")) as f:
        config = json.load(f)
except Exception:
    pass
device_config = config.get("device", {})

ADB = args.adb or device_config.get("adb_path", str(PROJECT / '3rd-party' / 'adb' / 'adb.exe'))
SERIAL = args.device or device_config.get("address", 'localhost:16512')

def tap(x, y):
    subprocess.run([ADB, '-s', SERIAL, 'shell', 'input', 'tap', str(int(x)), str(int(y))],
                   capture_output=True, timeout=10)

def back():
    subprocess.run([ADB, '-s', SERIAL, 'shell', 'input', 'keyevent', '4'], 
                   capture_output=True, timeout=5)

def screencap():
    r = subprocess.run([ADB, '-s', SERIAL, 'exec-out', 'screencap', '-p'],
                       capture_output=True, timeout=15)
    if len(r.stdout) < 1000:
        return None
    return cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR)

def screen_diff(img1, img2):
    if img1 is None or img2 is None:
        return 0
    d = cv2.absdiff(img1, img2)
    g = cv2.cvtColor(d, cv2.COLOR_BGR2GRAY)
    _, t = cv2.threshold(g, 30, 255, cv2.THRESH_BINARY)
    return cv2.countNonZero(t)

def find_icon_by_scanning():
    """
    通过扫描右上角区域找出任务图标坐标
    
    参考之前的扫描结果：
    - 棋盘格扫描发现 y=40/60/80 有效，y=50/70 无效
    - 最佳坐标 (860, 80) 产生 59.9% 匹配度
    """
    print("\n" + "="*70)
    print("坐标扫描：任务图标")
    print("="*70)
    
    # 确保在世界页面
    print("\n[准备] 确保在世界页面...")
    for i in range(10):
        back()
        time.sleep(0.5)
    time.sleep(1)

    # 基准截图
    baseline = screencap()

    # 扫描区域：右上角 (x: 700-1000, y: 20-120)
    x_range = range(750, 950, 50)
    y_range = [40, 60, 80, 100]

    best_coord = None
    best_diff = 0

    print("\n[扫描] 右上角区域...")
    results = []

    for x in x_range:
        for y in y_range:
            before = screencap()

            tap(x, y)
            time.sleep(1.5)

            after = screencap()
            diff = screen_diff(before, after)

            results.append((x, y, diff))

            # 记录最佳
            if diff > best_diff:
                best_diff = diff
                best_coord = (x, y)

            # 恢复
            back()
            time.sleep(0.3)

    # 排序显示前 10 个结果
    results.sort(key=lambda r: r[2], reverse=True)

    print("\n[结果] 前 10 个最佳坐标:")
    for i, (x, y, diff) in enumerate(results[:10]):
        marker = "★" if (x, y) == best_coord else " "
        print(f"  {marker} ({x:4}, {y:3}) diff={diff:>8,}")

    if best_coord:
        print(f"\n[最佳] {best_coord} diff={best_diff:,}")

    return best_coord

def verify_coordinate(coord):
    """验证给定坐标是否有效"""
    print("\n" + "="*70)
    print(f"坐标验证：{coord}")
    print("="*70)
    
    x, y = coord
    
    # 确保在世界页面
    print("\n[准备] 确保在世界页面...")
    for i in range(10):
        back()
        time.sleep(0.5)
    time.sleep(1)
    
    # 多次点击测试
    success_count = 0
    for attempt in range(5):
        print(f"\n[尝试 {attempt+1}/5] 点击 {coord}...")

        before = screencap()

        tap(x, y)
        time.sleep(2)

        after = screencap()
        diff = screen_diff(before, after)

        print(f"  [结果] diff={diff:,}")

        # 判断是否成功打开面板（差异 > 500000）
        if diff > 500000:
            print(f"  [成功] 面板已打开")
            success_count += 1

            # 保存截图
            cv2.imwrite(str(PROJECT / 'cache' / f'verify_{x}_{y}.png'), after)

            # 恢复
            back()
            time.sleep(1)
        else:
            print(f"  [失败] 面板未打开")
            back()
            time.sleep(0.5)
    
    print(f"\n[统计] 成功 {success_count}/5 次 ({success_count*20}%)")
    
    return success_count >= 3

def main():
    print("\n" + "="*70)
    print("坐标校准")
    print("="*70)
    
    # 扫描找出最佳坐标
    best_coord = find_icon_by_scanning()
    
    if best_coord:
        # 验证最佳坐标
        success = verify_coordinate(best_coord)
        
        if success:
            print(f"\n[✓] 坐标 {best_coord} 验证通过")
            return 0
        else:
            print(f"\n[✗] 坐标 {best_coord} 验证失败")
            return 1
    else:
        print("\n[✗] 未找到有效坐标")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
