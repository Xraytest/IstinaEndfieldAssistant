#!/usr/bin/env python3
"""
多轮对话VLM截图分析脚本
支持：
1. 发送截图进行初始分析
2. 多轮追问以详尽确认图像内容
3. 保持对话历史和图像上下文
4. 可切换不同的VLM provider
"""

import os
import sys
import base64
import json
import requests
from typing import List, Dict, Optional

# ============================================================
# 配置部分
# ============================================================

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
    
    print(f'[警告] 未找到provider配置: {provider_name}')
    return {'api_key': None, 'api_base_url': None, 'model': None}

def list_available_providers() -> List[str]:
    """列出所有可用的provider"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    providers_file = os.path.join(project_root, 'server', 'config', 'providers.json')
    
    providers_list = []
    if os.path.exists(providers_file):
        with open(providers_file, 'r', encoding='utf-8') as f:
            providers = json.load(f)
        
        for key, config in providers.items():
            if config.get('enabled', True):
                providers_list.append(key)
    
    return providers_list


# ============================================================
# VLM API调用部分
# ============================================================

class VLMMultiTurnAnalyzer:
    """多轮对话VLM分析器"""
    
    def __init__(self, provider_name: str = 'Kimi_K2_5'):
        self.provider_name = provider_name
        self.config = load_provider_config(provider_name)
        self.message_history: List[Dict] = []
        self.current_image_path: Optional[str] = None
        self.current_image_base64: Optional[str] = None
        
        # 系统提示词
        self.system_prompt = """你是一个游戏界面分析专家。你的任务是帮助用户详尽分析游戏截图。

分析时要特别关注：
1. 当前是什么界面（主界面/邮箱/暂停菜单/好友列表/战斗界面等）
2. 界面上有哪些按钮、图标、文本
3. 按钮和元素的位置（用自然语言描述，如'右上角'、'屏幕底部中间'等）
4. 特别注意：菜单按钮、好友按钮、邮箱按钮、设置按钮、返回按钮
5. 游戏状态（是否在战斗、是否有弹窗、是否需要用户操作等）

回答要求：
- 用简洁的中文回答
- 如果用户追问，详细解释相关元素
- 如果不确定，明确说明并建议可能的解释
- 对于重要的UI元素，给出精确的位置描述（便于后续自动化操作）

记住：你是在协助游戏自动化系统，准确的位置信息非常重要！"""
    
    def load_image(self, image_path: str) -> bool:
        """加载图像并编码为base64"""
        if not os.path.exists(image_path):
            print(f'[错误] 图像文件不存在: {image_path}')
            return False
        
        try:
            with open(image_path, 'rb') as f:
                self.current_image_base64 = base64.b64encode(f.read()).decode('utf-8')
            self.current_image_path = image_path
            print(f'[OK] 已加载图像: {image_path}')
            return True
        except Exception as e:
            print(f'[错误] 加载图像失败: {e}')
            return False
    
    def create_image_message(self, text: str) -> Dict:
        """创建包含图像的消息"""
        return {
            'role': 'user',
            'content': [
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': f'data:image/png;base64,{self.current_image_base64}'
                    }
                },
                {
                    'type': 'text',
                    'text': text
                }
            ]
        }
    
    def create_text_message(self, role: str, text: str) -> Dict:
        """创建纯文本消息"""
        return {
            'role': role,
            'content': text
        }
    
    def call_vlm_api(self) -> Optional[str]:
        """调用VLM API"""
        if not self.config.get('api_key'):
            return '错误：未配置API密钥'
        
        api_base_url = self.config.get('api_base_url', 'https://coding.dashscope.aliyuncs.com/v1')
        model = self.config.get('model', 'kimi-k2.5')
        
        # 构建消息列表（包含系统提示）
        messages = [self.create_text_message('system', self.system_prompt)]
        messages.extend(self.message_history)
        
        try:
            response = requests.post(
                f'{api_base_url}/chat/completions',
                headers={
                    'Authorization': f"Bearer {self.config['api_key']}",
                    'Content-Type': 'application/json'
                },
                json={
                    'model': model,
                    'messages': messages,
                    'max_tokens': 2000
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                return content
            else:
                return f'API调用失败: {response.status_code} - {response.text}'
        
        except requests.exceptions.Timeout:
            return '错误：API请求超时'
        except Exception as e:
            return f'错误：API调用异常 - {e}'
    
    def start_analysis(self, image_path: str, initial_question: str = None) -> str:
        """开始分析图像"""
        if not self.load_image(image_path):
            return '图像加载失败'
        
        # 清空消息历史
        self.message_history = []
        
        # 添加初始分析请求
        if initial_question:
            first_question = initial_question
        else:
            first_question = '请分析这张游戏截图，描述界面布局、按钮位置和当前游戏状态。'
        
        self.message_history.append(self.create_image_message(first_question))
        
        # 调用API
        print('\n[分析中...]')
        response = self.call_vlm_api()
        
        if response and not response.startswith('错误') and not response.startswith('API调用失败'):
            # 添加响应到历史
            self.message_history.append(self.create_text_message('assistant', response))
        
        return response
    
    def ask_follow_up(self, question: str) -> str:
        """追问"""
        if not self.current_image_base64:
            return '错误：尚未加载图像，请先使用 analyze 命令分析图像'
        
        # 添加追问消息
        self.message_history.append(self.create_text_message('user', question))
        
        # 调用API
        print('\n[思考中...]')
        response = self.call_vlm_api()
        
        if response and not response.startswith('错误') and not response.startswith('API调用失败'):
            # 添加响应到历史
            self.message_history.append(self.create_text_message('assistant', response))
        
        return response
    
    def get_history_summary(self) -> str:
        """获取对话历史摘要"""
        if not self.message_history:
            return '对话历史为空'
        
        summary = f'对话轮数: {len(self.message_history) // 2}\n'
        summary += f'当前图像: {self.current_image_path or "无"}\n'
        
        return summary
    
    def save_conversation(self, output_path: str) -> bool:
        """保存对话历史到文件"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# VLM对话记录\n")
                f.write(f"# Provider: {self.provider_name}\n")
                f.write(f"# Model: {self.config.get('model')}\n")
                f.write(f"# Image: {self.current_image_path}\n")
                f.write(f"\n{'=' * 60}\n\n")
                
                for i, msg in enumerate(self.message_history):
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    
                    if isinstance(content, list):
                        # 图像消息，只保存文本部分
                        for item in content:
                            if item.get('type') == 'text':
                                content = item.get('text', '')
                                break
                    
                    f.write(f"## [{role.upper()}]\n")
                    f.write(f"{content}\n")
                    f.write(f"\n{'-' * 40}\n\n")
            
            print(f'[OK] 对话已保存到: {output_path}')
            return True
        except Exception as e:
            print(f'[错误] 保存失败: {e}')
            return False


# ============================================================
# 交互式对话部分
# ============================================================

def interactive_session(analyzer: VLMMultiTurnAnalyzer, image_path: str):
    """交互式多轮对话"""
    print("\n" + "=" * 60)
    print("VLM多轮对话截图分析")
    print("=" * 60)
    print(f"Provider: {analyzer.provider_name}")
    print(f"Model: {analyzer.config.get('model')}")
    print(f"图像: {image_path}")
    print("=" * 60)
    
    # 开始初始分析
    initial_response = analyzer.start_analysis(image_path)
    # 移除emoji字符避免GBK编码错误
    import re
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\u2b50"  # star
        u"\u2605"  # star
        "]+", flags=re.UNICODE)
    safe_response = emoji_pattern.sub('', initial_response)
    print(f"\n[VLM响应]:\n{safe_response}\n")
    
    # 进入交互循环
    print("=" * 60)
    print("进入多轮对话模式")
    print("命令:")
    print("  - 直接输入问题进行追问")
    print("  - 'history' - 查看对话历史摘要")
    print("  - 'save <文件名>' - 保存对话记录")
    print("  - 'new <图像路径>' - 分析新图像")
    print("  - 'provider <名称>' - 切换provider")
    print("  - 'quit' 或 'exit' - 退出")
    print("=" * 60)
    
    while True:
        try:
            user_input = input("\n[用户输入]: ").strip()
            
            if not user_input:
                continue
            
            # 处理命令
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n[退出] 感谢使用!")
                break
            
            elif user_input.lower() == 'history':
                print(f"\n[对话历史]:\n{analyzer.get_history_summary()}")
            
            elif user_input.lower().startswith('save '):
                output_file = user_input[5:].strip()
                if not output_file:
                    output_file = 'vlm_conversation.txt'
                analyzer.save_conversation(output_file)
            
            elif user_input.lower().startswith('new '):
                new_image = user_input[5:].strip()
                if os.path.exists(new_image):
                    print(f"\n[切换图像]: {new_image}")
                    initial_response = analyzer.start_analysis(new_image)
                    print(f"\n[VLM响应]:\n{initial_response}\n")
                else:
                    print(f"[错误] 图像不存在: {new_image}")
            
            elif user_input.lower().startswith('provider '):
                new_provider = user_input[9:].strip()
                available = list_available_providers()
                if new_provider in available:
                    print(f"\n[切换Provider]: {new_provider}")
                    analyzer = VLMMultiTurnAnalyzer(new_provider)
                    # 重新加载当前图像
                    if analyzer.current_image_path:
                        analyzer.start_analysis(analyzer.current_image_path)
                        print(f"\n[VLM响应]:\n{analyzer.message_history[-1].get('content', '')}\n")
                else:
                    print(f"[错误] 未找到provider: {new_provider}")
                    print(f"[可用provider]: {', '.join(available)}")
            
            else:
                # 进行追问
                response = analyzer.ask_follow_up(user_input)
                print(f"\n[VLM响应]:\n{response}\n")
        
        except KeyboardInterrupt:
            print("\n\n[中断] 用户中断对话")
            break
        except EOFError:
            print("\n\n[退出] 输入结束")
            break


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""
    print("=" * 60)
    print("多轮对话VLM截图分析工具")
    print("=" * 60)
    
    # 显示可用provider
    providers = list_available_providers()
    print(f"[可用Provider]: {', '.join(providers)}")
    
    # 解析参数
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # 默认使用最近的截图
        image_path = 'game_docs/screenshot_binary.png'
    
    # 选择provider
    if len(sys.argv) > 2:
        provider_name = sys.argv[2]
    else:
        provider_name = 'Kimi_K2_5'
    
    print(f"[使用Provider]: {provider_name}")
    
    # 检查图像是否存在
    if not os.path.exists(image_path):
        print(f"[错误] 图像不存在: {image_path}")
        print("[提示] 请指定图像路径: python analyze_screenshots_v2.py <图像路径> [provider]")
        return
    
    # 创建分析器
    analyzer = VLMMultiTurnAnalyzer(provider_name)
    
    # 开始交互式对话
    interactive_session(analyzer, image_path)


if __name__ == '__main__':
    main()