#!/usr/bin/env python3
"""修改 daily_quest 流程：点击中央后验证页面，确保 exit_dialog 已关闭"""
import json

file_path = r'C:\Users\xray\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\config\standard_flows\flows_config.json'

with open(file_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 修改 daily_quest 流程
config['flows']['daily_quest']['steps'] = [
    {
        "id": "clear_dialog_1",
        "action": "tap",
        "coords": [960, 540],
        "wait": 2,
        "desc": "点击中央关闭退出对话框 (1/3)"
    },
    {
        "id": "clear_dialog_2",
        "action": "tap",
        "coords": [960, 540],
        "wait": 2,
        "desc": "点击中央关闭退出对话框 (2/3)"
    },
    {
        "id": "clear_dialog_3",
        "action": "tap",
        "coords": [960, 540],
        "wait": 2,
        "desc": "点击中央关闭退出对话框 (3/3)"
    },
    {
        "id": "verify_world",
        "action": "check",
        "expect": "world",
        "desc": "验证已进入世界"
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

config['flows']['daily_quest']['_status'] = "添加 3 次点击中央清除对话框 + 页面验证"

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print("SUCCESS: daily_quest flow updated")
print(f"Steps: {[s['id'] for s in config['flows']['daily_quest']['steps']]}")
