#!/usr/bin/env python3
"""在 daily_quest 流程中添加 clear_dialog 步骤"""
import json

file_path = r'C:\Users\xray\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\config\standard_flows\flows_config.json'

with open(file_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 在 daily_quest 的第一步前添加 clear_dialog
daily_steps = config['flows']['daily_quest']['steps']
clear_dialog_step = {
    "id": "clear_dialog",
    "action": "back",
    "wait": 2,
    "desc": "清除可能的退出对话框"
}
daily_steps.insert(0, clear_dialog_step)

# 更新状态注释
config['flows']['daily_quest']['_status'] = "quest_icon(860,80) 已验证; daily_claim 面板内待确认; 添加 clear_dialog 清除退出对话框"

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print("SUCCESS: clear_dialog step added to daily_quest")
print(f"Steps: {[s['id'] for s in daily_steps]}")
