"""
任务周期分析脚本
将任务结束前35张截图与描述json发至Kimi-K2.5供应商，要求其分析任务是否被正确完成
若无法判断则让其选择截图（可选任意时段，单次最多50张）
可多次请求，上下文仅保留文本分析，图像仅当拍选中图像
"""
import os
import sys
import json
import base64
import argparse
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
cli_method_dir = os.path.dirname(current_dir)
client_dir = os.path.dirname(cli_method_dir)
project_root = os.path.dirname(client_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import requests
from urllib3.exceptions import InsecureRequestWarning
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(InsecureRequestWarning)


class TaskCycleAnalyzer:
    """任务周期分析器 - 使用Kimi-K2.5分析任务执行情况"""
    
    # Kimi-K2.5供应商配置
    DEFAULT_API_BASE = "https://dashscope.aliyuncs.com/api/v1"
    DEFAULT_MODEL = "kimi-k2.5"
    
    # 分析系统提示
    ANALYSIS_SYSTEM_PROMPT = """你是一个游戏任务执行分析专家。你的任务是分析截图序列，判断自动化任务是否被正确完成。

要求：
1. 仔细观察每张截图的内容和变化
2. 结合任务目标分析执行情况
3. 判断任务是否成功完成，或指出问题所在

分析结果格式：
- 任务完成状态：[成功/失败/无法判断]
- 详细说明：描述你的判断依据
- 如果无法判断，说明需要查看哪些时间段的截图

注意：
- 截图按时间顺序排列，每张都有时间戳
- 任务变量描述了任务的具体目标
- 请关注关键操作步骤是否正确执行

**重要判断规则**：
对于奖励领取类任务（如"每日奖励领取"、"邮件领取"等）：
- 如果看到"暂无附件可收取"、"暂无更多奖励可领取"、"没有可领取的邮件"、"无奖励可领取"等提示文字，这表示所有奖励已被领取完毕或当前没有新奖励，这是**正常完成状态**，应判断为**成功**，而不是失败。
- 只有当任务完全没有执行（如卡在某个界面不动、没有尝试进入奖励界面）时才判断为失败。
- 奖励领取任务的目标是"检查并领取所有可用奖励"，如果没有可用奖励，任务目标已达成。

对于访问好友类任务：
- 如果看到"暂无可助力设施"、"暂无可交换情报"等提示，这表示当前好友基地没有可操作项，这也是正常状态。
- 只有当完全没有进入好友基地或没有尝试执行操作时才判断为失败。"""

    def __init__(self, 
                 api_key: str,
                 api_base: str = None,
                 model: str = None,
                 max_screenshots_per_request: int = 50,
                 initial_screenshot_count: int = 35,
                 provider_name: str = None):
        """
        初始化分析器
        
        Args:
            api_key: Kimi API密钥
            api_base: API基础URL
            model: 模型名称
            max_screenshots_per_request: 每次请求最大截图数
            initial_screenshot_count: 初始发送的截图数量
        """
        self.api_key = api_key
        self.api_base = api_base or self.DEFAULT_API_BASE
        self.model = model or self.DEFAULT_MODEL
        self.max_screenshots_per_request = max_screenshots_per_request
        # 根据供应商调整初始截图数量
        if provider_name == "local":
            # local供应商上下文限制较小，减少初始截图数量
            self.initial_screenshot_count = min(initial_screenshot_count, 10)
        elif provider_name == "Kimi_K2_5":
            # Kimi K2.5 API有缓冲区限制（50MB），减少初始截图数量避免超限
            self.initial_screenshot_count = min(initial_screenshot_count, 8)
        else:
            self.initial_screenshot_count = initial_screenshot_count
        
        # 对话历史（仅保留文本）
        self.conversation_history: List[Dict[str, str]] = []
        
    def load_run_output(self, output_dir: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        加载运行输出
        
        Args:
            output_dir: 输出目录
            
        Returns:
            (截图信息列表, 截图base64列表)
        """
        description_file = os.path.join(output_dir, "task_description.json")
        
        if not os.path.exists(description_file):
            raise FileNotFoundError(f"描述文件不存在: {description_file}")
        
        with open(description_file, 'r', encoding='utf-8') as f:
            description = json.load(f)
        
        screenshots_info = description.get('screenshots', [])
        
        # 加载截图文件
        screenshots_b64 = []
        for info in screenshots_info:
            screenshot_path = os.path.join(output_dir, info.get('screenshot_file', ''))
            if os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as f:
                    image_data = f.read()
                screenshots_b64.append(base64.b64encode(image_data).decode('utf-8'))
            else:
                print(f"警告: 截图文件不存在: {screenshot_path}")
                screenshots_b64.append(None)  # 占位
        
        return screenshots_info, screenshots_b64, description
    
    def _build_messages(self, 
                        screenshots_info: List[Dict[str, Any]], 
                        screenshots_b64: List[str],
                        task_context: Dict[str, Any],
                        selected_indices: List[int] = None) -> List[Dict]:
        """
        构建消息
        
        Args:
            screenshots_info: 截图信息列表
            screenshots_b64: 截图base64列表
            task_context: 任务上下文
            selected_indices: 选中的截图索引（None表示使用最后N张）
            
        Returns:
            消息列表
        """
        messages = []
        
        # 系统消息
        messages.append({
            'role': 'system',
            'content': self.ANALYSIS_SYSTEM_PROMPT
        })
        
        # 添加历史对话（仅文本）
        messages.extend(self.conversation_history)
        
        # 确定要发送的截图
        if selected_indices is None:
            # 使用最后N张
            count = min(self.initial_screenshot_count, len(screenshots_info))
            selected_indices = list(range(len(screenshots_info) - count, len(screenshots_info)))
        
        # 构建用户消息内容
        content = []
        
        # 文本描述
        text_content = f"""请分析以下任务执行情况：

任务执行信息:
- 运行开始时间: {task_context.get('run_start_time', '未知')}
- 触控方案: {task_context.get('control_scheme', '未知')}
- 窗口标题: {task_context.get('window_title', '未知')}
- 截图间隔: {task_context.get('screenshot_interval', '未知')}秒

截图序列（共{len(selected_indices)}张，按时间顺序）：
"""
        for i, idx in enumerate(selected_indices):
            if idx < len(screenshots_info):
                info = screenshots_info[idx]
                text_content += f"\n[截图{i+1}] 时间={info.get('timestamp', '未知')}, 任务={info.get('task_name', '未知')}"
                if info.get('task_variables'):
                    text_content += f", 变量={json.dumps(info['task_variables'], ensure_ascii=False)}"
        
        text_content += "\n\n请分析以上截图，判断任务是否被正确完成。"
        
        content.append({
            'type': 'text',
            'text': text_content
        })
        
        # 添加截图
        for i, idx in enumerate(selected_indices):
            if idx < len(screenshots_b64) and screenshots_b64[idx]:
                content.append({
                    'type': 'text',
                    'text': f"\n[截图{i+1}]"
                })
                content.append({
                    'type': 'image_url',
                    'image_url': {
                        'url': f"data:image/png;base64,{screenshots_b64[idx]}"
                    }
                })
        
        messages.append({
            'role': 'user',
            'content': content
        })
        
        return messages
    
    def _call_api(self, messages: List[Dict]) -> Optional[str]:
        """
        调用API
        
        Args:
            messages: 消息列表
            
        Returns:
            模型响应文本
        """
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': 0.1
        }
        
        try:
            print(f"[API] 正在调用 {self.model}...")
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                verify=False,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    message = result['choices'][0]['message']
                    # 优先使用content，如果没有则尝试reasoning_content（某些模型如qwen使用此字段）
                    content = message.get('content', '')
                    if not content and 'reasoning_content' in message:
                        content = message.get('reasoning_content', '')
                    if content:
                        return content
                    else:
                        print(f"[API] 响应无内容: {message}")
                        return None
                else:
                    print(f"[API] 响应格式错误: {result}")
                    return None
            else:
                print(f"[API] 请求失败: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print("[API] 请求超时")
            return None
        except Exception as e:
            print(f"[API] 请求异常: {e}")
            return None
    
    def _parse_analysis_result(self, response: str) -> Dict[str, Any]:
        """
        解析分析结果
        
        Args:
            response: 模型响应
            
        Returns:
            解析后的结果字典
        """
        result = {
            'status': 'unknown',
            'explanation': response,
            'need_more_screenshots': False,
            'requested_time_range': None
        }
        
        # 解析完成状态（支持多种格式）
        # 先移除可能的markdown标记进行匹配
        clean_response = response.replace('**', '')
        
        # 更灵活的成功判断：检查最后几行是否包含"成功"
        last_lines = '\n'.join(clean_response.split('\n')[-10:])
        
        # 优先匹配明确的格式
        if '任务完成状态：成功' in clean_response or '任务完成状态: 成功' in clean_response:
            result['status'] = 'success'
        # 检查最后几行是否有单独的"成功"标题（如"### 任务完成状态\n\n成功"）
        elif '任务完成状态' in clean_response and '成功' in last_lines:
            # 如果包含"任务完成状态"且最后几行包含"成功"
            if '失败' not in last_lines:
                result['status'] = 'success'
        # 检查最后几行是否有"成功"关键词
        elif last_lines.strip().endswith('成功'):
            result['status'] = 'success'
        elif '任务完成状态：失败' in clean_response or '任务完成状态: 失败' in clean_response:
            result['status'] = 'failed'
        elif '任务完成状态' in clean_response and '失败' in last_lines:
            if '成功' not in last_lines:
                result['status'] = 'failed'
        elif '任务完成状态：无法判断' in clean_response or '任务完成状态: 无法判断' in clean_response:
            result['status'] = 'unknown'
            result['need_more_screenshots'] = True
        
        # 检查是否需要更多截图
        if '需要查看' in response or '需要更多' in response:
            result['need_more_screenshots'] = True
        
        return result
    
    def _extract_requested_indices(self, response: str, screenshots_info: List[Dict]) -> List[int]:
        """
        从响应中提取需要的时间范围对应的截图索引
        
        Args:
            response: 模型响应
            screenshots_info: 截图信息列表
            
        Returns:
            截图索引列表
        """
        import re
        
        # 尝试解析时间范围
        # 格式可能是: "需要查看 14:30:00 到 14:31:00 的截图"
        time_pattern = r'(\d{2}:\d{2}:\d{2})'
        times = re.findall(time_pattern, response)
        
        if len(times) >= 2:
            # 有时间范围
            start_time = times[0]
            end_time = times[1]
            
            indices = []
            for i, info in enumerate(screenshots_info):
                timestamp = info.get('timestamp', '')
                # 简单匹配时间
                if start_time <= timestamp.split('_')[-1].replace('_', ':')[:8] <= end_time:
                    indices.append(i)
            
            if indices:
                return indices
        
        # 如果无法解析时间，返回均匀分布的截图
        total = len(screenshots_info)
        step = max(1, total // self.max_screenshots_per_request)
        return list(range(0, total, step))[:self.max_screenshots_per_request]
    
    def analyze(self, output_dir: str, max_rounds: int = 3) -> Dict[str, Any]:
        """
        分析任务执行情况
        
        Args:
            output_dir: 输出目录
            max_rounds: 最大分析轮数
            
        Returns:
            分析结果
        """
        # 加载输出
        screenshots_info, screenshots_b64, task_context = self.load_run_output(output_dir)
        
        if not screenshots_info:
            return {
                'status': 'error',
                'message': '未找到截图'
            }
        
        print(f"[分析] 加载了 {len(screenshots_info)} 张截图")
        
        # 清空对话历史
        self.conversation_history = []
        
        # 分析循环
        selected_indices = None  # 首次使用最后N张
        analysis_result = None
        
        for round_num in range(max_rounds):
            print(f"\n[分析] 第 {round_num + 1} 轮分析...")
            
            # 构建消息
            messages = self._build_messages(
                screenshots_info, 
                screenshots_b64, 
                task_context, 
                selected_indices
            )
            
            # 调用API
            response = self._call_api(messages)
            
            if not response:
                print("[分析] API调用失败")
                continue
            
            # 安全打印，避免GBK编码错误
            try:
                safe_response = response.encode('gbk', errors='replace').decode('gbk')
                print(f"\n[模型响应]\n{safe_response}\n")
            except Exception:
                print(f"\n[模型响应] (响应内容已保存到文件)\n")
            
            # 解析结果
            analysis_result = self._parse_analysis_result(response)
            
            # 保存对话历史（仅文本）
            # 提取用户消息的文本部分
            user_text = ""
            for msg in messages:
                if msg['role'] == 'user':
                    content = msg['content']
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get('type') == 'text':
                                user_text += item.get('text', '')
                    else:
                        user_text += str(content)
            
            self.conversation_history.append({
                'role': 'user',
                'content': user_text[:2000]  # 限制长度
            })
            self.conversation_history.append({
                'role': 'assistant',
                'content': response
            })
            
            # 如果已有明确结论，返回
            if analysis_result['status'] in ['success', 'failed']:
                break
            
            # 如果需要更多截图，选择截图
            if analysis_result['need_more_screenshots']:
                selected_indices = self._extract_requested_indices(response, screenshots_info)
                if not selected_indices:
                    break
                print(f"[分析] 需要更多截图，选择了 {len(selected_indices)} 张")
            else:
                break
        
        # 保存分析结果
        result_file = os.path.join(output_dir, "analysis_result.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'analysis_time': datetime.now().isoformat(),
                'rounds': round_num + 1 if round_num is not None else 0,
                'result': analysis_result
            }, f, ensure_ascii=False, indent=2)
        
        print(f"[分析] 结果已保存到: {result_file}")
        
        return analysis_result or {
            'status': 'unknown',
            'message': '分析未能完成'
        }


def load_provider_config(provider_name: str = None) -> Dict[str, str]:
    """从服务器配置加载供应商配置
    
    Args:
        provider_name: 供应商名称（如 'local', 'kimi_k2_5' 等），不指定则按优先级查找可用的
    
    Returns:
        包含 api_key, api_base_url, model 的字典
    """
    providers_file = os.path.join(project_root, "server", "config", "providers.json")
    
    result = {'api_key': None, 'api_base_url': None, 'model': None}
    
    if os.path.exists(providers_file):
        with open(providers_file, 'r', encoding='utf-8') as f:
            providers = json.load(f)
        
        # 如果指定了供应商名称，直接查找
        if provider_name:
            provider_key = provider_name
            # 尝试多种匹配方式
            for key in providers:
                if key.lower() == provider_name.lower():
                    provider_key = key
                    break
            
            if provider_key in providers:
                config = providers[provider_key]
                if config.get('enabled', True):
                    result['api_key'] = config.get('api_key')
                    result['api_base_url'] = config.get('api_base_url')
                    result['model'] = config.get('model')
                    print(f"[配置] 使用供应商: {provider_key}")
                    return result
        else:
            # 按优先级查找可用的供应商
            # 优先级: local > kimi > 其他
            priority_order = ['Kimi_K2_5', 'local', 'GLM_4.6vflash_Free']
            
            for preferred_name in priority_order:
                for key, config in providers.items():
                    if preferred_name.lower() in key.lower() and config.get('enabled', True):
                        result['api_key'] = config.get('api_key')
                        result['api_base_url'] = config.get('api_base_url')
                        result['model'] = config.get('model')
                        print(f"[配置] 自动选择供应商: {key}")
                        return result
            
            # 如果没有找到优先供应商，使用第一个启用的
            for key, config in providers.items():
                if config.get('enabled', True):
                    result['api_key'] = config.get('api_key')
                    result['api_base_url'] = config.get('api_base_url')
                    result['model'] = config.get('model')
                    print(f"[配置] 使用供应商: {key}")
                    return result
    
    return result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='任务周期分析脚本 - 分析任务执行情况')
    parser.add_argument('--output-dir', '-o', required=True, help='debug_running.py的输出目录')
    parser.add_argument('--api-key', '-k', default=None, help='模型API密钥（不指定则从服务器配置加载）')
    parser.add_argument('--api-base', '-b', default=None, help='API基础URL')
    parser.add_argument('--model', '-m', default=None, help='模型名称')
    parser.add_argument('--provider', '-p', default=None, help='供应商名称（如 local, kimi_k2_5）')
    parser.add_argument('--max-rounds', '-r', type=int, default=3, help='最大分析轮数')
    parser.add_argument('--initial-screenshots', '-n', type=int, default=35, help='初始发送的截图数量')
    parser.add_argument('--max-screenshots', '-s', type=int, default=50, help='每次请求最大截图数')
    
    args = parser.parse_args()
    
    # 获取API配置
    api_key = args.api_key
    api_base = args.api_base
    model = args.model
    
    # 如果未提供完整的API配置，从服务器配置加载
    if not api_key or not api_base or not model:
        provider_config = load_provider_config(args.provider)
        if not api_key:
            api_key = provider_config['api_key']
        if not api_base:
            api_base = provider_config['api_base_url']
        if not model:
            model = provider_config['model']
    
    if not api_key:
        print("错误: 未提供API密钥，且无法从服务器配置加载")
        return 1
    
    print(f"[配置] API Base: {api_base}")
    print(f"[配置] Model: {model}")
    
    # 创建分析器
    analyzer = TaskCycleAnalyzer(
        api_key=api_key,
        api_base=api_base,
        model=model,
        max_screenshots_per_request=args.max_screenshots,
        initial_screenshot_count=args.initial_screenshots,
        provider_name=args.provider
    )
    
    # 执行分析
    print(f"[分析] 开始分析输出目录: {args.output_dir}")
    result = analyzer.analyze(args.output_dir, max_rounds=args.max_rounds)
    
    print(f"\n[分析] 最终结果: {result.get('status', 'unknown')}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())