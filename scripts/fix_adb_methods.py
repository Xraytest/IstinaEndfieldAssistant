#!/usr/bin/env python3
"""修复 standard_flow_engine.py 中的 ADB tap/back 方法调用"""

path = r"C:\Users\cheng\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\scripts\standard_flow_engine.py"

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修复 _tap 方法 - 替换 self.adb.tap(x, y) 为 subprocess 调用
old_tap = '''    def _tap(self, x: int, y: int) -> bool:
        """触控点击：使用 ADB 原生 input tap（避免 MaaFw post_click 的 fortl 崩溃）"""
        return self.adb.tap(x, y)'''

new_tap = '''    def _tap(self, x: int, y: int) -> bool:
        """触控点击：使用 ADB 原生 input tap（避免 MaaFw post_click 的 fortl 崩溃）"""
        import subprocess
        try:
            r = subprocess.run(
                [self.adb_path, "-s", self.device_addr, "shell", "input", "tap", str(x), str(y)],
                capture_output=True, timeout=5
            )
            return r.returncode == 0
        except Exception:
            return False'''

if old_tap in content:
    content = content.replace(old_tap, new_tap)
    print("✓ 修复了 _tap 方法")
else:
    print("✗ 未找到 _tap 方法")

# 2. 修复 _back 方法 - 替换 self.adb.back() 为 subprocess 调用
old_back = '''    def _back(self) -> bool:
        """返回键：ADB keyevent（MaaFw 无独立 back 方法）"""
        return self.adb.back()'''

new_back = '''    def _back(self) -> bool:
        """返回键：ADB keyevent（MaaFw 无独立 back 方法）"""
        import subprocess
        try:
            r = subprocess.run(
                [self.adb_path, "-s", self.device_addr, "shell", "input", "keyevent", "4"],
                capture_output=True, timeout=5
            )
            return r.returncode == 0
        except Exception:
            return False'''

if old_back in content:
    content = content.replace(old_back, new_back)
    print("✓ 修复了 _back 方法")
else:
    print("✗ 未找到 _back 方法")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ 修复完成")
