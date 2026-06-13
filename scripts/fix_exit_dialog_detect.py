#!/usr/bin/env python3
"""添加基于金色元素数量的 exit_dialog 判断"""

file_path = r'C:\Users\xray\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\scripts\standard_flow_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到插入位置：在"OCR 失效时的视觉特征判断"注释后
old_code = '''        # OCR 失效时的视觉特征判断（VLM OCR 超时返回"无文字"）
        # 任务面板：大量金色元素（UI 按钮/边框）+ 无 person（非 3D 场景）
        if len(golden_elements) > 20 and "person" not in yolo_classes:
            return "quest_panel"'''

new_code = '''        # OCR 失效时的视觉特征判断（VLM OCR 超时返回"无文字"）
        # 退出对话框：12-16 个金色元素 + 无 person + OCR 为空/无文字
        if 12 <= len(golden_elements) <= 16 and "person" not in yolo_classes and (not text.strip() or text == "无文字"):
            return "exit_dialog"
        # 任务面板：大量金色元素（UI 按钮/边框）+ 无 person（非 3D 场景）
        if len(golden_elements) > 20 and "person" not in yolo_classes:
            return "quest_panel"'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: exit_dialog visual detection added")
else:
    print("ERROR: pattern not found")
    # 尝试查找相似内容
    import re
    if "OCR 失效时的视觉特征判断" in content:
        print("Found comment, but code structure may differ")
        # 打印附近内容
        idx = content.find("OCR 失效时的视觉特征判断")
        print(f"Context: {repr(content[idx:idx+500])}")
