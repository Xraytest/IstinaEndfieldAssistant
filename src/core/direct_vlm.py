"""Cherryin.ai API 直连 — 绕过本地网关直接调用大模型"""

import requests, base64, json, time, os
from typing import Optional, Dict, Any
from pathlib import Path

BASE_URL = "https://open.cherryin.ai"


def _load_api_key() -> str:
    """从 client_config.json 加载 API 密钥"""
    config_path = Path(__file__).resolve().parent.parent.parent / "config" / "client_config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            key = cfg.get("vendors", {}).get("newapi_channel", {}).get("key", "")
            if key and key != "YOUR_API_KEY_HERE":
                return key
        except (json.JSONDecodeError, OSError):
            pass
    return os.environ.get("CHERRYIN_API_KEY", "")

# 已知模型ID映射
MODEL_IDS = {
    "qwen3.6-plus": "qwen/qwen3.6-plus",
    "exploration_deep": "qwen/qwen3.5-35b-a3b",
    "vision": "qwen/qwen3.5-35b-a3b",  # fallback to same model
    "qwen3-vl-plus": "qwen/qwen3-vl-plus",
    "qwen3.5-397b": "qwen/qwen3.5-397b-a17b",
    "qwen3-vl-235b": "qwen/qwen3-vl-235b-a22b-instruct",
}

# 系统提示词
SYSTEM_PROMPT = """你是《明日方舟：终末地》精确UI分析器。
分析游戏截图中的所有UI元素，逐一列出每个可见的按钮和交互元素。
输出严格JSON格式，不要额外文字。"""


def call_vlm_direct(
    image_base64: str,
    instruction: str,
    model_id: str = "qwen/qwen3.6-plus",
    system_prompt: str = SYSTEM_PROMPT,
    timeout: int = 120,
) -> Optional[Dict[str, Any]]:
    """直接调用 cherryin.ai 的 chat/completions API（多模态）"""

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    # 多模态消息：text + image
    user_content = [
        {"type": "text", "text": instruction},
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{image_base64}",
                "detail": "high",
            },
        },
    ]
    messages.append({"role": "user", "content": user_content})

    headers = {
        "Authorization": f"Bearer {_load_api_key()}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_id,
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.1,
    }

    try:
        resp = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}", "detail": resp.text[:300]}

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        import re
        m = re.search(r"\{[\s\S]*\}", content)
        if m:
            return json.loads(m.group())
        return {"_raw": content[:500]}

    except requests.Timeout:
        return {"error": f"timeout after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # 测试：用截图分析当前画面
    import subprocess, sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

    ADB = [os.path.join(os.path.dirname(__file__), "..", "3rd-party", "adb", "adb.exe"),
           "-s", "localhost:16512"]

    r = subprocess.run(ADB + ["exec-out", "screencap", "-p"], capture_output=True, timeout=15)
    if r.returncode != 0:
        print("截图失败")
        sys.exit(1)

    b64 = base64.b64encode(r.stdout).decode("utf-8")
    print(f"截图大小: {len(r.stdout)} bytes")

    for mid in ["qwen/qwen3.6-plus", "qwen/qwen3.5-35b-a3b"]:
        print(f"\n--- {mid} ---")
        t0 = time.time()
        result = call_vlm_direct(b64, "描述这个游戏画面。JSON:{\"page\":\"\",\"buttons\":[]}", mid)
        dt = time.time() - t0
        if "error" in result:
            print(f"  ERROR({dt:.1f}s): {result['error']}")
        else:
            print(f"  ({dt:.1f}s): {json.dumps(result, ensure_ascii=False)[:300]}")
