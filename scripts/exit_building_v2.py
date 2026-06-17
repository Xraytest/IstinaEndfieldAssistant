"""VLM 定位建造模式中的取消按钮"""
import subprocess, time, os, sys, cv2, numpy as np

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(PROJECT, 'cache')
ADB = os.path.join(PROJECT, '3rd-party', 'adb', 'adb.exe')
SERIAL = 'localhost:16512'
os.makedirs(CACHE, exist_ok=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from standard_flow_engine import ScreenAnalyzer
analyzer = ScreenAnalyzer()

def screencap(path):
    r = subprocess.run([ADB, '-s', SERIAL, 'exec-out', 'screencap', '-p'], timeout=15, capture_output=True)
    if len(r.stdout) < 1000:
        for g in r.get('golden_elements', []):
    for g in golden:
    x, y, w, h = g.get('bbox', [0,0,0,0])
    cx, cy = x + w//2, y + h//2
    
print("\nDone - 请根据上述信息定位取消按钮")
