#!/usr/bin/env python3
"""添加--device 参数到标准流引擎"""

script_path = r"C:\Users\cheng\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\scripts\standard_flow_engine.py"

with open(script_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加--device 参数
old_args = '''    parser.add_argument("--session-dir", type=str,
                        help="分析已有记录目录（与--analyze-only 配合使用）")

    args = parser.parse_args()'''

new_args = '''    parser.add_argument("--session-dir", type=str,
                        help="分析已有记录目录（与--analyze-only 配合使用）")
    parser.add_argument("--device", type=str, default="localhost:16512",
                        help="ADB 设备地址（默认：localhost:16512）")

    args = parser.parse_args()
    
    # 打印设备地址
    print(f"[配置] ADB 设备地址：{{args.device}}")'''

if old_args in content:
    content = content.replace(old_args, new_args)
    print("✓ 添加了--device 参数")
else:
    print("✗ 未找到参数定义位置")

# 2. 替换所有 localhost:16512 为 args.device 变量
# 首先需要在 main 函数开头定义 device_addr 变量
old_main = '''    args = parser.parse_args()

    # 加载配置'''

new_main = '''    args = parser.parse_args()
    
    # 设备地址
    device_addr = args.device
    print(f"[配置] ADB 设备地址：{device_addr}")

    # 加载配置'''

if old_main in content:
    content = content.replace(old_main, new_main)
    print("✓ 添加了 device_addr 变量")
else:
    print("✗ 未找到 args.parse_args() 位置")

# 3. 替换所有硬编码的 localhost:16512 为 device_addr
content = content.replace('"localhost:16512"', 'f\'{device_addr}\'')
content = content.replace("'localhost:16512'", f'{{device_addr}}')

with open(script_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ 修改完成")
