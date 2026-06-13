#!/usr/bin/env python3
"""添加 world 页面的视觉特征判断"""

file_path = r'C:\Users\xray\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\scripts\standard_flow_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在 exit_dialog 判断后添加 world 判断
old_code = '''        # OCR 失效时的视觉特征判断（VLM OCR 超时返回"无文字"）
        # 退出对话框：12-16 个金色元素 + 无 person + OCR 为空/无文字
        if 12 <= len(golden_elements) <= 16 and "person" not in yolo_classes and (not text.strip() or text == "无文字"):
            return "exit_dialog"
        # 任务面板：大量金色元素（UI 按钮/边框）+ 无 person（非 3D 场景）
        if len(golden_elements) > 20 and "person" not in yolo_classes:
            return "quest_panel"'''

new_code = '''        # OCR 失效时的视觉特征判断（VLM OCR 超时返回"无文字"）
        # 退出对话框：12-16 个金色元素 + 无 person + OCR 为空/无文字
        if 12 <= len(golden_elements) <= 16 and "person" not in yolo_classes and (not text.strip() or text == "无文字"):
            return "exit_dialog"
        # 世界页面：约 20 个金色元素 + 无 person + OCR 为空/无文字
        if 18 <= len(golden_elements) <= 22 and "person" not in yolo_classes and (not text.strip() or text == "无文字"):
            return "world"
        # 任务面板：大量金色元素（UI 按钮/边框）+ 无 person（非 3D 场景）
        if len(golden_elements) > 20 and "person" not in yolo_classes:
            return "quest_panel"'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: world visual detection added")
else:
    print("ERROR: pattern not found")
