#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
截图分析脚本 - 使用Kimi K2.5分析界面布局
从providers.json加载正确的API配置
"""

import os
import sys
import base64
import json
import requests

def load_provider_config(provider_name: str = "Kimi_K2_5") -> dict:
    """从providers.json加载API配置"""
    # 查找providers.json文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    providers_file = os.path.join(project_root, "server", "config", "providers.json")
    
    if os.path.exists(providers_file):
        with open(providers_file, 'r', encoding='utf-8') as f:
            providers = json.load(f)
        
        # 查找指定的provider
        for key, config in providers.items():
            if key.lower() == provider_name.lower() and config.get('enabled', True):
                return {
                    'api_key': config.get('api_key'),
                    'api_base_url': config.get('api_base_url'),
                    'model': config.get('model')
                }
    
    # 如果找不到，返回空配置
    print(f"[警告] 未找到provider配置: {provider_name}")
    return {'api_key': None, 'api_base_url': None, 'model': None}

def analyze_screenshot(image_path: str, config: dict) -> str:
    """分析单张截图"""
    if not config.get('api_key'):
        return "错误：未配置API密钥"
    
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
    
    api_base_url = config.get('api_base_url', 'https://coding.dashscope.aliyuncs.com/v1')
    model = config.get('model', 'kimi-k2.5')
    
    # 调用API
    response = requests.post(
        f"{api_base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        },
        json={
            "model": model,
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
    # 从providers.json加载API配置
    config = load_provider_config("Kimi_K2_5")
    print(f"[配置] API Base URL: {config.get('api_base_url')}")
    print(f"[配置] Model: {config.get('model')}")
    
    if not config.get('api_key'):
        print("[错误] 未找到有效的API密钥")
        return
    
    # 截图目录（支持命令行参数）
    if len(sys.argv) > 1:
        screenshot_dir = sys.argv[1]
    else:
        screenshot_dir = "client/debug_friends_test3"
    
    # 确保目录存在
    if not os.path.exists(screenshot_dir):
        print(f"[错误] 截图目录不存在: {screenshot_dir}")
        return
    
    # 获取截图列表
    screenshots = [f for f in os.listdir(screenshot_dir) if f.endswith('.png')]
    screenshots.sort()
    
    print(f"找到 {len(screenshots)} 张截图")
    
    if not screenshots:
        print("[警告] 没有找到截图文件")
        return
    
    # 分析前5张和最后3张截图（更全面的分析）
    analyze_list = screenshots[:5] + screenshots[-3:] if len(screenshots) > 8 else screenshots
    
    for i, screenshot in enumerate(analyze_list):
        print(f"\n{'='*60}")
        print(f"分析截图 {i+1}/{len(analyze_list)}: {screenshot}")
        print('='*60)
        
        image_path = os.path.join(screenshot_dir, screenshot)
        result = analyze_screenshot(image_path, config)
        print(result)

if __name__ == "__main__":
    main()