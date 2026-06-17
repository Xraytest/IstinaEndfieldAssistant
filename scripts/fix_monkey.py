#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复 standard_flow_engine.py 中的 monkey 代码"""

import re

file_path = r'C:\Users\xray\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\scripts\standard_flow_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换所有 monkey 启动代码为 am start
old_pattern = r'''    # 先强制停止旧实例，再 monkey 启动新实例.*?
    subprocess\.run\(\[adb_path, "-s", device_serial, "shell", "am", "force-stop", "com\.hypergryph\.endfield"\],
                  capture_output=True, timeout=10\)
    time\.sleep\(3\)
    subprocess\.run\(\[adb_path, "-s", device_serial, "shell", "input", "keyevent", "3"\],
                  capture_output=True, timeout=5\)
    time\.sleep\(1\)
    r = subprocess\.run\(\[adb_path, "-s", device_serial, "shell",
                      "monkey", "-p", "com\.hypergryph\.endfield",
                      "-c", "android\.intent\.category\.LAUNCHER", "1"\],
                      capture_output=True, timeout=15\)
    print\(f"  启动：\{r\.stdout\.decode\(errors='replace'\)\[:120\]"\)'''

new_code = '''    # 先强制停止旧实例，再 am start 启动新实例（避免状态污染）
    subprocess.run([adb_path, "-s", device_serial, "shell", "am", "force-stop", "com.hypergryph.endfield"],
                  capture_output=True, timeout=10)
    time.sleep(3)
    # 使用 am start 启动游戏（比 monkey 更可靠）
    subprocess.run([adb_path, "-s", device_serial, "shell", "am", "start", "-n", "com.hypergryph.endfield/.ui.splash.SplashActivity"],
                  capture_output=True, timeout=10)
    time.sleep(3)
    print(f"  启动：com.hypergryph.endfield")'''

content_new = re.sub(old_pattern, new_code, content, flags=re.DOTALL)

if content == content_new:
    print("No changes made - pattern not found")
    # 尝试简单替换
    if '"monkey"' in content:
        print("Found monkey string, trying simple replacement...")
        # 直接删除包含 monkey 的行
        lines = content.split('\n')
        new_lines = []
        skip_until_print = False
        for i, line in enumerate(lines):
            if '"monkey"' in line:
                # 删除前 7 行和后 3 行
                start = max(0, i-7)
                end = min(len(lines), i+4)
                print(f"Deleting lines {start+1}-{end}")
                new_lines = lines[:start] + [new_code + '\n'] + lines[end:]
                break
        content_new = '\n'.join(new_lines)
else:
    print("Pattern replaced successfully")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content_new)

# 验证
with open(file_path, 'r', encoding='utf-8') as f:
    content_final = f.read()
if '"monkey"' in content_final:
    print("WARNING: monkey still exists in file")
else:
    print("SUCCESS: monkey removed")
