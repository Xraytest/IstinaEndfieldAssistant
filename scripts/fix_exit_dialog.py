#!/usr/bin/env python3
"""在前置验证阶段添加 exit_dialog 处理"""
import sys

file_path = r'C:\Users\xray\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\scripts\standard_flow_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 在第 1735 行后插入 exit_dialog 处理（time.sleep(3) 之后，else 之前）
insert_lines = [
    "                elif page == \"exit_dialog\":\n",
    "                    print(\"[前置] 检测到退出对话框，按返回关闭...\")\n",
    "                    subprocess.run([adb_path, \"-s\", \"localhost:16512\", \"shell\", \"input\", \"keyevent\", \"4\"],\n",
    "                                  capture_output=True, timeout=5)\n",
    "                    time.sleep(3)\n",
]

# 找到第 1735 行（索引 1734）
insert_pos = 1734  # 0-based index for line 1735
print("Before insertion:")
for i in range(1730, 1740):
    print(f"Line {i+1}: {lines[i].rstrip()}")

print("\n--- Inserting after line 1735 ---\n")

# 插入
lines[insert_pos:insert_pos] = insert_lines

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("SUCCESS: exit_dialog handler inserted")

# 验证
print("\n--- Verification ---")
for i in range(1730, 1750):
    print(f"Line {i+1}: {lines[i].rstrip()}")
