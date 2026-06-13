#!/usr/bin/env python3
"""修改 daily_quest 流程：用返回键代替点击中央清除对话框"""
import json

file_path = r'C:\Users\xray\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\config\standard_flows\flows_config.json'

with open(file_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 修改 daily_quest 流程：用返回键清除对话框
config['flows']['daily_quest']['steps'] = [
    {
        "id": "clear_dialog",
        "action": "back",
        "wait": 2,
        "desc": "按返回键关闭退出对话框"
    },
    {
        "id": "verify_not_title",
        "action": "check",
        "desc": "验证不在标题画面"
    },
    {
        "id": "open_quest",
        "action": "tap",
        "coords": "{{nav_coords.quest_icon}}",
        "wait": 5,
        "expect": "quest_panel",
        "desc": "点击任务图标 (860,80)"
    },
    {
        "id": "check_daily",
        "action": "check",
        "desc": "检查每日任务状态"
    },
    {
        "id": "claim_daily",
        "action": "tap",
        "coords": "{{nav_coords.daily_claim}}",
        "wait": 3,
        "desc": "点击领取按钮 (975,288)"
    },
    {
        "id": "return_world",
        "action": "back",
        "wait": 3,
        "desc": "返回探索界面"
    }
]

config['flows']['daily_quest']['_status'] = "用返回键清除对话框 + 点击任务图标"

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print("SUCCESS: daily_quest flow updated to use back key")
print(f"Steps: {[s['id'] for s in config['flows']['daily_quest']['steps']]}")
