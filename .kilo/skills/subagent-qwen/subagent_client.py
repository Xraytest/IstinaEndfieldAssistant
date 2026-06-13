"""
SubAgent Qwen Client — 通过 Cherryin.ai 调用 qwen/qwen3.5-27b(free) 进行复杂任务分析委托。

遵循 kilo code 子智能体模式：
1. 注入丰富上下文 (代码、截图、日志、配置)
2. Qwen 模型逐步分析推理
3. Qwen 可请求更多信息
4. 返回结构化分析结果

用法:
    from subagent_client import SubAgentQwen

    agent = SubAgentQwen()
    result = agent.analyze(task="...", code=..., logs=...)
    result = agent.analyze(task="...", screenshot_base64=b64)
"""

import json
import time
import base64
import requests
from typing import Optional, Dict, List, Any


# === 配置 ===
CHERRYIN_API_URL = "https://open.cherryin.cc/v1"
CHERRYIN_API_KEY = "sk-SHYG0HNKhAEPXbEHOdlLcggKXYlyEGJyolvGjh0T2r5FQOst"

REQUEST_TIMEOUT = 180

MODEL = "qwen/qwen3.5-27b(free)"

DEFAULT_SYSTEM_PROMPT = """你是 SubAgent Qwen — 一个深度分析子智能体。你的任务是对提供的上下文进行彻底分析。

## 分析流程
1. 首先理解任务目标
2. 分析提供的所有上下文信息（代码、截图、日志、配置）
3. 逐步推理问题根因
4. 给出具体的解决方案或下一步行动建议
5. 如果信息不足，明确说明还需要什么信息

## 输出格式
请以结构化方式输出：
### 问题理解
[你对该问题的理解]

### 上下文分析
[对提供的代码/截图/日志的分析]

### 根因诊断
[问题根因]

### 解决方案
[具体的解决步骤]

### 信息需求
[如果需要更多信息才能确定，列出还需要什么]
"""


class SubAgentQwen:
    """通过 Cherryin.ai 调用 qwen/qwen3.5-27b(free) 的 subagent 客户端"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self._last_error = None
        self.conversation_history: List[Dict] = []

    def _request(self, method: str, path: str, json_data: dict = None, timeout: int = 30) -> requests.Response:
        url = f"{CHERRYIN_API_URL}{path}"
        headers = {"Authorization": f"Bearer {CHERRYIN_API_KEY}"}
        headers["Content-Type"] = "application/json"
        if method == "GET":
            return self.session.get(url, headers=headers, timeout=timeout)
        return self.session.post(url, headers=headers, json=json_data, timeout=timeout)

    def discover_models(self) -> List[str]:
        """获取 Cherryin.ai 可用模型列表"""
        try:
            resp = self._request("GET", "/models", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                models = [m["id"] for m in data.get("data", []) if isinstance(m, dict) and "id" in m]
                if models:
                    self._last_error = None
                    return models
        except Exception as e:
            self._last_error = f"cherryin: {e}"
        return []

    def analyze(
        self,
        task: str,
        code: Optional[str] = None,
        logs: Optional[str] = None,
        screenshot_base64: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> Dict[str, Any]:
        """
        向 Cherryin.ai 发送分析请求。

        Args:
            task: 任务描述
            code: 相关代码段（可选）
            logs: 执行日志（可选）
            screenshot_base64: base64 编码的截图（可选）
            context: 额外上下文字典（可选）
            system_prompt: 自定义系统提示词
            temperature: 采样温度
            max_tokens: 最大输出 token 数

        Returns:
            {
                "success": bool,
                "model": str,
                "analysis": str,
                "info_requests": [],
                "error": str | None,
                "usage": {} | None,
                "elapsed": float,
                "endpoint": str,
            }
        """
        messages = []

        sp = system_prompt or DEFAULT_SYSTEM_PROMPT
        if sp:
            messages.append({"role": "system", "content": sp})

        user_content = []
        context_parts = [f"## 任务\n{task}\n"]

        if code:
            context_parts.append(f"## 相关代码\n```python\n{code}\n```\n")
        if logs:
            context_parts.append(f"## 执行日志\n```\n{logs}\n```\n")
        if context:
            ctx_lines = ["## 上下文信息\n"]
            for k, v in context.items():
                ctx_lines.append(f"- **{k}**: {v}")
            context_parts.append("\n".join(ctx_lines))

        user_content.append({"type": "text", "text": "\n".join(context_parts)})

        if screenshot_base64:
            img_data = screenshot_base64
            if img_data.startswith("data:"):
                img_data = img_data.split(",", 1)[-1]
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_data}"}
            })

        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        result = self._try_chat_completion(payload, REQUEST_TIMEOUT)

        if result["success"]:
            reply = result["reply"]
            self.conversation_history = messages
            self.conversation_history.append({"role": "assistant", "content": reply})

        return {
            "success": result["success"],
            "model": MODEL,
            "analysis": result.get("reply", ""),
            "info_requests": self._extract_info_requests(result.get("reply", "")),
            "error": result.get("error"),
            "usage": result.get("usage"),
            "elapsed": result.get("elapsed", 0),
            "endpoint": result.get("endpoint", "cherryin"),
        }

    def _try_chat_completion(self, payload: dict, timeout: int) -> Dict[str, Any]:
        start_time = time.time()
        try:
            resp = self._request("POST", "/chat/completions", json_data=payload, timeout=timeout)
            elapsed = time.time() - start_time

            if resp.status_code != 200:
                return {
                    "success": False, "model": MODEL, "reply": "",
                    "error": f"API error ({resp.status_code}): {resp.text[:200]}",
                    "usage": None, "elapsed": round(elapsed, 1), "endpoint": "cherryin",
                }

            data = resp.json()
            msg = data["choices"][0]["message"]
            reply = msg.get("content") or msg.get("reasoning_content") or ""
            usage = data.get("usage")
            return {
                "success": True, "model": MODEL, "reply": reply,
                "error": None, "usage": usage,
                "elapsed": round(elapsed, 1), "endpoint": "cherryin",
            }

        except requests.Timeout:
            return {
                "success": False, "model": MODEL, "reply": "",
                "error": f"Timeout ({timeout}s)",
                "usage": None, "elapsed": round(time.time() - start_time, 1), "endpoint": "cherryin",
            }
        except requests.ConnectionError as e:
            return {
                "success": False, "model": MODEL, "reply": "",
                "error": f"Connection failed: {e}",
                "usage": None, "elapsed": round(time.time() - start_time, 1), "endpoint": "cherryin",
            }
        except Exception as e:
            return {
                "success": False, "model": MODEL, "reply": "",
                "error": f"Exception: {type(e).__name__}: {e}",
                "usage": None, "elapsed": round(time.time() - start_time, 1), "endpoint": "cherryin",
            }

    def follow_up(
        self,
        additional_info: str,
        screenshot_base64: Optional[str] = None,
    ) -> Dict[str, Any]:
        """在之前的分析基础上提供额外信息继续分析。"""
        if not self.conversation_history:
            return self.analyze(task=additional_info, screenshot_base64=screenshot_base64)

        new_messages = [m for m in self.conversation_history if m["role"] == "system"]

        user_content = [{"type": "text", "text": additional_info}]
        if screenshot_base64:
            img_data = screenshot_base64
            if img_data.startswith("data:"):
                img_data = img_data.split(",", 1)[-1]
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_data}"}
            })

        new_messages.append({"role": "user", "content": user_content})

        payload = {
            "model": MODEL,
            "messages": new_messages,
            "temperature": 0.3,
            "max_tokens": 8192,
        }

        result = self._try_chat_completion(payload, REQUEST_TIMEOUT)

        if result["success"]:
            reply = result["reply"]
            self.conversation_history = new_messages
            self.conversation_history.append({"role": "assistant", "content": reply})

        return {
            "success": result["success"],
            "model": MODEL,
            "analysis": result.get("reply", ""),
            "info_requests": self._extract_info_requests(result.get("reply", "")),
            "error": result.get("error"),
            "usage": result.get("usage"),
        }

    def reset_conversation(self):
        """清空对话历史"""
        self.conversation_history = []

    @staticmethod
    def _extract_info_requests(reply: str) -> List[str]:
        """从回复中提取信息请求"""
        requests_found = []
        import re
        for section_header in ["### 信息需求", "### 信息请求",
                               "### 需要的信息", "### 还需要",
                               "### 额外信息", "## 信息需求"]:
            pattern = re.compile(
                rf"{re.escape(section_header)}\s*\n(.*?)(?:\n###|\n##|$)",
                re.DOTALL
            )
            match = pattern.search(reply)
            if match:
                section_content = match.group(1).strip()
                items = re.findall(r'[-*\d]+\.?\s*(.*?)(?:\n|$)', section_content)
                requests_found.extend([item.strip() for item in items if item.strip()])

        if not requests_found:
            question_patterns = re.findall(
                r'(?:需要|能否|请提供|建议|请给我|我需要|请截)[^。\n]*[？?]',
                reply
            )
            requests_found = [q.strip() for q in question_patterns[:5]]

        return requests_found


def quick_analyze(
    task: str,
    code: Optional[str] = None,
    logs: Optional[str] = None,
    screenshot_path: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """一键分析。"""
    agent = SubAgentQwen()

    b64 = None
    if screenshot_path:
        try:
            with open(screenshot_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            print(f"[WARN] 读取截图失败: {e}")

    return agent.analyze(
        task=task,
        code=code,
        logs=logs,
        screenshot_base64=b64,
        **kwargs
    )


if __name__ == "__main__":
    import sys

    agent = SubAgentQwen()
    models = agent.discover_models()
    if models:
        print(f"Cherryin.ai 可用模型 ({len(models)}):")
        for m in models:
            print(f"  - {m}")
        print(f"\n固定使用模型: {MODEL}")
    else:
        print("WARNING: 无法获取模型列表，Cherryin.ai 可能未运行。")

    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        print(f"\n分析任务: {task}")
        result = agent.analyze(task=task)

        if result["success"]:
            print(f"\n{'='*60}")
            print(f"模型: {result['model']}")
            if result.get("elapsed"):
                print(f"耗时: {result['elapsed']}s")
            print(f"{'='*60}")
            print(result["analysis"])

            if result["info_requests"]:
                print(f"\n{'='*60}")
                print("模型请求额外信息:")
                for req in result["info_requests"]:
                    print(f"  - {req}")
        else:
            print(f"分析失败: {result['error']}")
