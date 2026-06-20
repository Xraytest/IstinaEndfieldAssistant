#!/usr/bin/env python3
"""修复 standard_flow_engine.py 中的 gold_count 变量未定义问题"""

path = r"C:\Users\cheng\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\scripts\standard_flow_engine.py"

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 _classify_by_keywords 方法 - 移除金色元素依赖，直接使用 OCR+YOLO 分类
old_classify = '''    def _classify_by_keywords(self, ocr_text: str, yolo_objects: list) -> str:
        """基于 OCR 关键词 + YOLO + 金色元素快速分类（不依赖 VLM）"""
        text = ocr_text.lower()
        yolo_classes = [o["class"] for o in yolo_objects]

        # === 异常状态检测（新增） ===

        # OCR 失效时的视觉特征判断（VLM OCR 超时返回"无文字"）
        # 退出对话框：10-18 个金色元素（扩展范围）+ 无 person + OCR 为空/无文字
        if 10 <= gold_count <= 18 and "person" not in yolo_classes and (not text.strip() or text == "无文字"):
            return "exit_dialog"
        # 世界页面：16-24 个金色元素（扩展范围）+ 无 person + OCR 为空/无文字
        if 16 <= gold_count <= 24 and "person" not in yolo_classes and (not text.strip() or text == "无文字"):
            return "world"
        # 任务面板：大量金色元素（UI 按钮/边框）+ 无 person（非 3D 场景）
        if gold_count > 20 and "person" not in yolo_classes:
            return "quest_panel"
        # 任务面板：中等金色元素 + 无 person + 有 UI 类物体
        if gold_count > 10 and "person" not in yolo_classes:
            ui_classes = ["laptop", "cell phone", "remote", "keyboard", "mouse"]
            if any(c in yolo_classes for c in ui_classes):
                return "quest_panel"'''

new_classify = '''    def _classify_by_keywords(self, ocr_text: str, yolo_objects: list) -> str:
        """基于 OCR 关键词 + YOLO 快速分类（不依赖 VLM 和金色元素）"""
        text = ocr_text.lower()
        yolo_classes = [o["class"] for o in yolo_objects]

        # === 异常状态检测 ===

        # OCR 失效时的降级判断（VLM OCR 超时返回"无文字"）
        # 退出对话框：OCR 为空 + 有 button 元素
        if (not text.strip() or text == "无文字") and "button" in yolo_classes:
            return "exit_dialog"
        # 世界页面：OCR 为空 + 无 person
        if (not text.strip() or text == "无文字") and "person" not in yolo_classes:
            return "world"'''

if old_classify in content:
    content = content.replace(old_classify, new_classify)
    print("✓ 修复了 _classify_by_keywords 方法")
else:
    print("✗ 未找到 _classify_by_keywords 方法")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ 修复完成")
