#!/usr/bin/env python3
"""修改 daily_quest 的 clear_dialog 为点击中央而非返回键"""
import json

file_path = r'C:\Users\xray\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\config\standard_flows\flows_config.json'

with open(file_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 修改 clear_dialog 步骤
clear_step = config['flows']['daily_quest']['steps'][0]
clear_step['action'] = 'tap'
clear_step['coords'] = [960, 540]  # 中央位置
clear_step['desc'] = '点击中央关闭可能的退出对话框'

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print("SUCCESS: clear_dialog modified to tap center")
print(f"Step: {clear_step}")
