#!/usr/bin/env python3
"""直接修复 FlowRecorder 类"""

path = r"C:\Users\cheng\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\scripts\standard_flow_engine.py"

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到并修改 FlowRecorder.__init__
for i, line in enumerate(lines):
    if 'class FlowRecorder:' in line:
        # 找到 __init__ 方法
        for j in range(i, min(i+20, len(lines))):
            if 'def __init__(self, session_name:' in lines[j]:
                # 修改这一行
                lines[j] = lines[j].replace(
                    'def __init__(self, session_name: str = "standard_flow", record_video: bool = True):',
                    'def __init__(self, session_name: str = "standard_flow", record_video: bool = True, device_addr: str = None):'
                )
                print(f"Fixed line {j+1}: __init__ signature")
                
                # 在 self.record_video 后添加 self.device_addr
                for k in range(j+1, min(j+10, len(lines))):
                    if 'self.record_video = record_video' in lines[k]:
                        lines[k] = lines[k].rstrip() + '\n        self.device_addr = device_addr\n'
                        print(f"Fixed line {k+1}: added device_addr attribute")
                        break
                break
        break

# 找到并修改 capture_screenshot 方法
for i, line in enumerate(lines):
    if 'img = adb_screencap()' in line and i > 480:  # 确保在 FlowRecorder 类中
        lines[i] = line.replace(
            'img = adb_screencap()',
            'img = adb_screencap(serial=self.device_addr) if self.device_addr else adb_screencap()'
        )
        print(f"Fixed line {i+1}: capture_screenshot")
        break

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Done")
