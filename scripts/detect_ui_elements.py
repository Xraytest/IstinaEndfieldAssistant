"""检测当前画面的金色元素和YOLO对象 - 无VLM依赖"""
import subprocess, time, os, cv2, numpy as np, sys

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADB = os.path.join(PROJECT, '3rd-party', 'adb', 'adb.exe')
SERIAL = 'localhost:16512'
CACHE = os.path.join(PROJECT, 'cache')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from standard_flow_engine import ScreenAnalyzer
analyzer = ScreenAnalyzer()

# 截图
r = subprocess.run([ADB, '-s', SERIAL, 'exec-out', 'screencap', '-p'], timeout=15, capture_output=True)
img = cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR)
for g in golden:
    y_label = ""
    if g['cy'] < 150:
        y_label = " [顶部]"
    elif g['cy'] > 850:
        y_label = " [底部]"
    elif g['cy'] > 700:
        y_label = " [中下]"
    bottom_golden = [g for g in golden if g['cy'] > 800]
if bottom_golden:
    for g in sorted(bottom_golden, key=lambda g: g['area'], reverse=True):
        
# 顶部区域分析
top_golden = [g for g in golden if g['cy'] < 150]
for g in sorted(top_golden, key=lambda g: g['area'], reverse=True):
    right_golden = [g for g in golden if g['cx'] > 1200]
for g in sorted(right_golden, key=lambda g: g['area'], reverse=True):
    print(f"  ({g['cx']},{g['cy']}) w={g['w']} h={g['h']} area={g['area']:.0f} {g['range']}")

print("\nDone")
