#!/usr/bin/env python3
"""
分析截图并将结果保存到文件（避免GBK编码问题）
"""

import os
import sys
import base64
import json
import requests
import re
from typing import List, Dict, Optional

def load_provider_config(provider_name: str = 'Kimi_K2_5') -> dict:
    """加载指定provider的配置"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    providers_file = os.path.join(project_root, 'server', 'config', 'providers.json')
    
    if os.path.exists(providers_file):
        with open(providers_file, 'r', encoding='utf-8') as f:
            providers = json.load(f)
        
        for key, config in providers.items():
            if key.lower() == provider_name.lower() and config.get('enabled', True):
                return {
                    'name': config.get('name', key),
                    'api_key': config.get('api_key'),
                    'api_base_url': config.get('api_base_url'),
                    'model': config.get('model'),
                    'description': config.get('description', '')
                }
    
    return {'api_key': None, 'api_base_url': None, 'model': None}

def load_image(image_path: str) -> Optional[str]:
    """加载图像并编码为base64"""
    if not os.path.exists(image_path):
        return None
    
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    return base64.b64encode(image_data).decode('utf-8')

def analyze_screenshot(image_path: str, provider_name: str = 'Kimi_K2_5') -> str:
    """分析截图"""
    config = load_provider_config(provider_name)
    
    if not config.get('api_key'):
        return f"错误: 未找到provider配置: {provider_name}"
    
    image_base64 = load_image(image_path)
    if not image_base64:
        return f"错误: 图像文件不存在: {image_path}"
    
    # 构建请求
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    
    system_prompt = """你是一个游戏界面分析专家。分析截图并回答：
1. 当前是什么界面
2. 界面上有哪些关键元素
3. 游戏状态

用简洁的中文回答。"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "请分析这张截图，描述当前界面状态。"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                }
            ]
        }
    ]
    
    payload = {
        "model": config.get('model', 'kimi-k2.5'),
        "messages": messages,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(
            f"{config['api_base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            # 移除emoji
            emoji_pattern = re.compile("["
                u"\U0001F600-\U0001F64F"
                u"\U0001F300-\U0001F5FF"
                u"\U0001F680-\U0001F6FF"
                u"\U0001F1E0-\U0001F1FF"
                u"\U00002702-\U000027B0"
                u"\U000024C2-\U0001F251"
                u"\u2b50"
                u"\u2605"
                "]+", flags=re.UNICODE)
            return emoji_pattern.sub('', content)
        else:
            return f"API错误: {response.status_code} - {response.text}"
    except Exception as e:
        return f"请求异常: {str(e)}"

def main():
    if len(sys.argv) < 2:
        print("用法: python analyze_screenshots_to_file.py <截图目录或文件> [provider]")
        return
    
    target = sys.argv[1]
    provider = sys.argv[2] if len(sys.argv) > 2 else 'Kimi_K2_5'
    
    # 输出文件
    output_file = "screenshot_analysis_result.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write(f"截图分析结果\n")
        f.write(f"Provider: {provider}\n")
        f.write("=" * 60 + "\n\n")
        
        if os.path.isfile(target):
            # 单个文件
            f.write(f"文件: {target}\n\n")
            result = analyze_screenshot(target, provider)
            f.write(result + "\n")
        elif os.path.isdir(target):
            # 目录
            png_files = sorted([x for x in os.listdir(target) if x.endswith('.png')])
            for png_file in png_files:
                image_path = os.path.join(target, png_file)
                f.write(f"\n{'=' * 60}\n")
                f.write(f"文件: {png_file}\n")
                f.write("=" * 60 + "\n\n")
                result = analyze_screenshot(image_path, provider)
                f.write(result + "\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("分析完成\n")
    
    print(f"分析结果已保存到: {output_file}")

if __name__ == '__main__':
    main()