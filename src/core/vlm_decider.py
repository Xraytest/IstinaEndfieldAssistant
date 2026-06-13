#!/usr/bin/env python3
"""
VLM 动作决策器 — 当 OpenCV 无法确定下一步时介入

职责：
1. 页面类型再次确认（OpenCV 不确定时）
2. 动作建议（点击哪里、滑动方向、按键等）
3. 异常恢复决策（页面不匹配时的纠正策略）

调用前提：
- Layer 1 (HighPrecisionPageAnalyzer) 已运行完毕
- 仅当 confidence < 0.5 或 page_type == "unknown" 时调用 VLM
- 或当标准动作执行失败后，请求 VLM 给出替代方案

与 Layer 1 的关系：
- OpenCV 负责快速判页（10ms），覆盖 90%+ 场景
- VLM 负责语义理解和复杂决策（15s），覆盖 10% 边缘场景
"""

import cv2
import base64
import json
import urllib.request
import numpy as np
from typing import Dict, Any, Tuple, Optional
from pathlib import Path


class VlmActionDecider:
    """VLM 动作决策器"""

    def __init__(self, llama_url: str = "http://127.0.0.1:8080", timeout: int = 15):
        self._llama_url = llama_url
        self._timeout = timeout

    def decide_action(self, img: np.ndarray,
                      page_result: Dict[str, Any],
                      context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        请求 VLM 决策下一步动作

        Args:
            img: 当前截图
            page_result: HighPrecisionPageAnalyzer 的分析结果
            context: 上下文信息 {expected_page, last_action, step_desc, ...}

        Returns:
            {
                "page_type": str,           # VLM 确认的页面类型
                "suggested_action": str,    # tap / swipe / back / wait / claim / navigate
                "target": str,              # 目标元素描述（如 "领取按钮"）
                "coordinates": [x, y],      # 点击坐标（可选）
                "reason": str,              # 决策理由
                "confidence": float,        # 0-1
            }
        """
        if context is None:
            context = {}

        prompt = self._build_prompt(page_result, context)

        try:
            _, buf = cv2.imencode('.png', img)
            img_b64 = base64.b64encode(buf).decode()
            resp = self._call_vlm(prompt, img_b64)
            return self._parse_response(resp)
        except Exception as e:
            return {
                "page_type": page_result.get("page_type", "unknown"),
                "suggested_action": "back",
                "reason": f"VLM 不可用，降级返回: {e}",
                "confidence": 0.0
            }

    def _build_prompt(self, page_result: Dict[str, Any],
                      context: Dict[str, Any]) -> str:
        """构建 VLM 提示词"""
        page_type = page_result.get("page_type", "unknown")
        confidence = page_result.get("confidence", 0)
        features = page_result.get("features", {})
        expected = context.get("expected_page", "world")
        step_desc = context.get("step_desc", "")
        last_action = context.get("last_action", "")

        prompt = f"""你正在操控《明日方舟：终末地》，需要根据当前画面决定下一步操作。

当前信息：
- OpenCV 判页：{page_type}（置信度 {confidence:.2f}）
- 期望页面：{expected}
- 当前步骤：{step_desc}
- 上次动作：{last_action}

画面特征：
- 左侧边栏亮度：{features.get('left_bar_brightness', 0):.1f}
- 右上角绿色像素：{features.get('green_pixels_top_right', 0):.0f}
- 全屏亮度：{features.get('full_brightness', 0):.1f}

请分析画面并返回 JSON 决策结果，格式如下：
{{
  "page_type": "world|quest_panel|exit_dialog|loading|title|menu|other",
  "suggested_action": "tap|swipe|back|wait|claim|navigate|skip",
  "target": "目标元素的中文描述",
  "coordinates": [x, y],
  "reason": "决策理由，一句话"
}}

动作说明：
- tap: 点击坐标
- swipe: 滑动（给出方向和距离）
- back: 按返回键
- wait: 等待加载
- claim: 领取奖励（找出领取按钮坐标）
- navigate: 需要导航到某个页面
- skip: 跳过当前画面（如标题页点继续）
"""
        return prompt

    def _call_vlm(self, prompt: str, img_b64: str) -> Dict[str, Any]:
        """调用 llama-server VLM API"""
        req = urllib.request.Request(
            f"{self._llama_url}/v1/chat/completions",
            data=json.dumps({
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                ]}],
                "max_tokens": 300,
                "temperature": 0,
                "chat_template_kwargs": {"enable_thinking": False}
            }).encode(),
            headers={"Content-Type": "application/json"}
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=self._timeout).read())
        content = resp["choices"][0]["message"].get("content", "").strip()
        if not content:
            content = resp["choices"][0]["message"].get("reasoning_content", "").strip()
        return {"raw": content}

    def _parse_response(self, resp: Dict[str, Any]) -> Dict[str, Any]:
        """解析 VLM 响应为结构化决策"""
        raw = resp.get("raw", "")
        try:
            # 尝试提取 JSON
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except json.JSONDecodeError:
            pass

        # JSON 解析失败，基于文本关键词推断
        return {
            "page_type": "unknown",
            "suggested_action": "back",
            "reason": raw[:200] if raw else "VLM 无响应",
            "confidence": 0.0
        }


# ═══════════════════════════════════════════════════════════════
# 集成点：标准流引擎中的 VLM 决策流程
# ═══════════════════════════════════════════════════════════════

def should_invoke_vlm(page_result: Dict[str, Any],
                      expected_page: str = None) -> bool:
    """
    判断是否需要调用 VLM

    条件：
    1. OpenCV 置信度 < 0.5
    2. 页面类型为 unknown
    3. 页面与预期不符
    """
    page_type = page_result.get("page_type", "unknown")
    confidence = page_result.get("confidence", 0)

    if confidence < 0.5:
        return True
    if page_type == "unknown":
        return True
    if expected_page and page_type != expected_page:
        return True
    return False


# ═══════════════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import subprocess, time
    from pathlib import Path

    PROJECT = Path(__file__).resolve().parent.parent.parent
    ADB = PROJECT / '3rd-party' / 'adb' / 'adb.exe'

    # 截图
    r = subprocess.run([str(ADB), "-s", "localhost:16512", "exec-out", "screencap", "-p"],
                      capture_output=True, timeout=10)
    if r.returncode != 0 or len(r.stdout) < 1000:
        print("截图失败")
        exit(1)

    img = cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR)

    # 模拟 OpenCV 分析结果（模拟一个不确定的情况）
    page_result = {
        "page_type": "unknown",
        "confidence": 0.3,
        "features": {
            "left_bar_brightness": 100,
            "green_pixels_top_right": 50,
            "full_brightness": 80,
        }
    }

    # 检查是否应该调 VLM
    print(f"\n[决策] 是否调用 VLM: {should_invoke_vlm(page_result, 'world')}")

    # 实际调用 VLM（如果可用）
    decider = VlmActionDecider()
    context = {
        "expected_page": "world",
        "step_desc": "前置验证：确保进入游戏世界",
        "last_action": "按返回键"
    }

    print("\n[VLM] 请求决策...")
    result = decider.decide_action(img, page_result, context)

    print(f"\n[VLM 决策结果]")
    for k, v in result.items():
        print(f"  {k}: {v}")
