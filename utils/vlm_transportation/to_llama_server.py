# utils/vlm_transportation/to_llama_server.py 
import base64
import json
import requests
import os
from typing import Generator, Dict, Any, Optional

def llm_requests(
    prompt: str, 
    img_pth: Optional[str] = None,
    tools: Optional[list] = None,
    tool_choice: str = "auto"
) -> Generator[Dict[str, Any], None, None]:
    """
    支持Tool Calling的流式LLM请求
    
    Args:
        prompt: 任务描述
        img_pth: 截图路径（可选）
        tools: OpenAI格式的工具定义列表
        tool_choice: 工具选择策略 ("auto", "none", "required")
    """
    # 构建消息内容
    if img_pth and img_pth.strip():
        img_pth = os.path.normpath(img_pth.strip())
        try:
            with open(img_pth, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            raise IOError(f"读取图片失败: {str(e)}")
        
        content = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            }
        ]
    else:
        content = prompt

    # 构建请求负载
    payload = {
        "model": "gpt-4o-mini",  # 或您部署的VLM模型
        "messages": [{"role": "user", "content": content}],
        "stream": True,
        "stream_options": {"include_usage": True}
    }
    
    # 添加工具定义
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(
            "http://127.0.0.1:8080/v1/chat/completions",
            json=payload,
            headers=headers,
            stream=True,
            timeout=45
        )
        response.raise_for_status()
        
        buffer = ""
        for line in response.iter_lines():
            if not line:
                continue
                
            line = line.decode('utf-8').strip()
            if line.startswith('data: '):
                json_str = line[6:]
                
                if json_str == '[DONE]':
                    yield {
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }
                    break
                    
                try:
                    chunk = json.loads(json_str)
                    yield chunk
                except json.JSONDecodeError:
                    # 尝试累积解析（处理分块JSON）
                    buffer += json_str
                    try:
                        chunk = json.loads(buffer)
                        buffer = ""
                        yield chunk
                    except:
                        continue
                        
    except Exception as e:
        raise RuntimeError(f"LLM请求失败: {str(e)}")