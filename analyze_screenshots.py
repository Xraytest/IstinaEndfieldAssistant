#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
截图分析脚本 - 使用Kimi K2.5分析界面布局
"""

import os
import sys
import base64
import json
import requests

def analyze_screenshot(image_path: str, api_key: str) -> str:
    """分析单张截图"""
    # 读取图片
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    # 构建请求
    messages = [
        {
            "role": "system",
            "content": "你是一个游戏界面分析专家。请分析截图中的界面元素，特别关注：\n1. 当前是什么界面（主界面/邮箱/暂停菜单/好友列表等）\n2. 界面上有哪些按钮和图标\n3. 按钮的位置（用自然语言描述，如'右上角'、'屏幕底部中间'等）\n4. 特别注意是否有菜单按钮、好友按钮、邮箱按钮\n\n请用简洁的中文回答。"
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_data}"
                    }
                },
                {
                    "type": "text",
                    "text": "请分析这张游戏截图，描述界面布局和按钮位置。"
                }
            ]
        }
    ]
    
    # 调用API
    response = requests.post(
        "https://coding.dashscope.aliyuncs.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "kimi-k2.5",
            "messages": messages,
            "max_tokens": 1000
        },
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        return result.get('choices', [{}])[0].get('message', {}).get('content', '')
    else:
        return f"API调用失败: {response.status_code} - {response.text}"

def main():
    # API密钥
    api_key = "b5c26b8c2d21e9587310b5f148530436"
    
    # 截图目录
    screenshot_dir = "client/debug_friends_fixed2"
    
    # 获取截图列表
    screenshots = [f for f in os.listdir(screenshot_dir) if f.endswith('.png')]
    screenshots.sort()
    
    print(f"找到 {len(screenshots)} 张截图")
    
    # 分析前3张和最后1张截图
    analyze_list = screenshots[:3] + [screenshots[-1]] if len(screenshots) > 3 else screenshots
    
    for i, screenshot in enumerate(analyze_list):
        print(f"\n{'='*60}")
        print(f"分析截图 {i+1}/{len(analyze_list)}: {screenshot}")
        print('='*60)
        
        image_path = os.path.join(screenshot_dir, screenshot)
        result = analyze_screenshot(image_path, api_key)
        print(result)

if __name__ == "__main__":
    main()