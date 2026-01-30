import base64
import json
import requests
import os
from typing import Generator, Dict, Any, Optional

def llm_requests(prompt: str, img_pth: Optional[str] = None) -> Generator[Dict[str, Any], None, None]:
    """
    严格遵照 OpenAI 库格式的流式请求函数（支持纯文本/多模态）
    
    Args:
        prompt: 文本提示（必填）
        img_pth: 图片路径（Windows 环境，可选）。若为 None 或空字符串，则仅发送文本
    
    Returns:
        生成器，每次 yield 一个符合 OpenAI 流式响应格式的 chunk
    """
    # 构建消息内容：纯文本 或 多模态
    if img_pth and img_pth.strip():
        # 规范化 Windows 路径
        img_pth = os.path.normpath(img_pth.strip())
        
        # 读取图片并转为 base64
        try:
            with open(img_pth, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
            raise FileNotFoundError(f"图片文件不存在: {img_pth}")
        except Exception as e:
            raise IOError(f"读取图片失败 {img_pth}: {str(e)}")
        
        # 多模态消息格式（符合 OpenAI API 规范）
        content = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"image/jpeg;base64,{base64_image}"
                }
            }
        ]
    else:
        # 纯文本消息格式
        content = prompt
    
    # 构造请求数据（严格遵循 OpenAI API 格式）
    payload = {
        "model": "gpt-4-vision-preview",  # 可根据实际模型调整
        "messages": [
            {
                "role": "user",
                "content": content
            }
        ],
        "stream": True
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        # 发送流式请求到本地服务器
        response = requests.post(
            "http://127.0.0.1:8080/v1/chat/completions",
            json=payload,
            headers=headers,
            stream=True,
            timeout=30  # 避免永久阻塞
        )
        response.raise_for_status()
        
        # 处理 SSE (Server-Sent Events) 流式响应
        for line in response.iter_lines():
            if not line:
                continue
                
            decoded_line = line.decode('utf-8').strip()
            
            # 跳过注释行和事件类型行（标准 SSE 格式）
            if decoded_line.startswith(':') or decoded_line.startswith('event:'):
                continue
                
            # 处理 data: 前缀（标准 OpenAI SSE 格式）
            if decoded_line.startswith(''):
                json_str = decoded_line[5:].strip()
                
                # 检查结束标记
                if json_str == '[DONE]':
                    # 发送最终 chunk（finish_reason=stop）
                    yield {
                        "id": "chatcmpl-final",
                        "object": "chat.completion.chunk",
                        "created": 0,
                        "model": "gpt-4-vision-preview",
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }
                    break
                
                # 解析 JSON 并 yield
                try:
                    chunk_data = json.loads(json_str)
                    # 确保最小合规格式（OpenAI 要求）
                    if "choices" not in chunk_data:
                        chunk_data["choices"] = [{
                            "index": 0,
                            "delta": {"content": ""},
                            "finish_reason": None
                        }]
                    yield chunk_data
                except json.JSONDecodeError:
                    # 跳过无法解析的行（保持流式稳定性）
                    continue
                    
    except requests.exceptions.Timeout:
        raise TimeoutError("请求超时：服务器 127.0.0.1:8080 无响应")
    except requests.exceptions.ConnectionError:
        raise ConnectionError("无法连接到服务器 127.0.0.1:8080，请确认服务已启动")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"HTTP 错误 {e.response.status_code}: {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"请求处理异常: {str(e)}")