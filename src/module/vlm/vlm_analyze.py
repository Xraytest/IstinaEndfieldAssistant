"""VLM 分析函数 - 从 adb_utils 迁移而来

提供统一的 VLM 画面分析接口，通过 VLMClient 中间体执行。
"""
import base64
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class VLMOptions:
    """VLM 调用参数"""
    model_tag: str = "exploration_deep"
    timeout: int = 120
    temperature: float = 0.01
    max_tokens: int = 2048
    system_prompt: str = ""


DEFAULT_VLM_OPTS = VLMOptions()


def vlm_analyze(image_bytes: bytes,
                instruction: str = "识别当前画面",
                opts: Optional[VLMOptions] = None,
                vlm_client=None) -> Optional[Dict[str, Any]]:
    """通过 VLMClient 统一中间体分析画面

    Args:
        image_bytes: PNG 截图字节
        instruction: 分析指令
        opts: VLM 参数
        vlm_client: VLMClient 实例（可选，不传则创建默认本地模式实例）

    Returns:
        VLM 分析结果或 None
    """
    if opts is None:
        opts = DEFAULT_VLM_OPTS

    if vlm_client is None:
        from module.vlm import VLMClient
        vlm_client = VLMClient({
            "vlm_mode": "local",
            "vlm_timeout": opts.timeout,
            "temperature": opts.temperature,
            "max_tokens": opts.max_tokens,
        })

    b64 = base64.b64encode(image_bytes).decode("utf-8")

    result = vlm_client.analyze_image(
        b64, instruction,
        system_prompt=opts.system_prompt or "你是终末地界面分析器。输出JSON格式。",
        max_tokens=opts.max_tokens,
        temperature=opts.temperature,
    )

    if result.get("status") == "success":
        return result
    return None
