#!/usr/bin/env python3
"""修复 standard_flow_engine.py 中的 golden_summary 未定义错误"""

import re

file_path = r"C:\Users\cheng\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\scripts\standard_flow_engine.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找 yolo_summary 定义后、prompt 定义前的位置
# 需要添加 golden_summary 定义
old_text = '''            if yolo_objects else "无检测")

            prompt = (
                f"OCR 文字：{ocr_text[:300]}\\n"
                f"{yolo_summary}\\n"
                f"{golden_summary}\\n\\n"'''

new_text = '''            if yolo_objects else "无检测")

            golden_summary = "金色元素：待检测"  # 定义变量避免 NameError

            prompt = (
                f"OCR 文字：{ocr_text[:300]}\\n"
                f"{yolo_summary}\\n"
                f"{golden_summary}\\n\\n"'''

if old_text in content:
    content = content.replace(old_text, new_text)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("修复成功！")
else:
    print("未找到匹配文本，尝试另一种模式...")
    # 尝试查找包含 golden_summary 但未定义的位置
    if 'golden_summary' in content and 'golden_summary = ' not in content:
        print("找到 golden_summary 使用但未定义")
        # 在 yolo_summary 后添加
        pattern = r'(yolo_summary = "YOLO 检测："[^)]+\))'
        replacement = r'\1\n\n            golden_summary = "金色元素：待检测"'
        content = re.sub(pattern, replacement, content)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("修复成功！")
    else:
        print("无法自动修复")
