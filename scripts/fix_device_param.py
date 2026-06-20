#!/usr/bin/env python3
"""修改 standard_flow_engine.py 添加--device 参数"""

path = r"C:\Users\cheng\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\scripts\standard_flow_engine.py"

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找"args = parser.parse_args()"的位置
for i, line in enumerate(lines):
    if 'args = parser.parse_args()' in line and i > 1600:
        # 在这一行前面插入--device 参数
        indent = '    '
        device_lines = [
            indent + 'parser.add_argument("--device", type=str, default="localhost:16512",\n',
            indent + '                    help="ADB 设备地址（默认：localhost:16512）")\n',
        ]
        lines[i:i] = device_lines
        print(f"✓ 在第{i+1}行前插入了--device 参数")
        break
else:
    print("✗ 未找到 parser.parse_args()")

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ 修改完成")
