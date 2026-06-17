"""VLM 验证核心 - ModelEndpointManager + VLMVerifier

基于 cherryin.ai qwen/qwen3.5-27b(free) 的图像理解能力进行游戏状态验证。
"""
import os, sys, time, json, re, base64
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import requests
from core.logger import get_logger, LogCategory
logger = get_logger()

CHERRYIN_API_URL = "https://open.cherryin.cc/v1"


def _load_api_key() -> str:
    """从 client_config.json 加载 API 密钥"""
    config_path = Path(__file__).resolve().parent.parent.parent.parent / "config" / "client_config.json"
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

# --- 验证结果数据模型 ---

@dataclass
class VerificationResult:
    verified: bool
    confidence: float
    reasoning: str = ""
    extracted_data: Optional[Dict] = None
    raw_response: Optional[str] = None
    model_used: Optional[str] = None
    error: Optional[str] = None

# --- 模型端点管理器 ---

class ModelEndpointManager:
    FREE_MODELS = [
        "qwen/qwen3.5-27b(free)",
        "qwen/qwen3-vl-plus",
        "qwen/qwen3.5-9b-free",
    ]
    PAID_MODELS = [
        "qwen/qwen3-vl-235b-a22b-instruct",
        "qwen/qwen3.6-plus",
    ]

    def __init__(self, url: str = CHERRYIN_API_URL, api_key: str = None):
        self.url = url.rstrip("/")
        self.api_key = api_key or _load_api_key()
        self.current_model = None
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
        })

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def health_check(self, model: str, timeout: int = 15) -> bool:
        try:
            r = requests.post(
                f"{self.url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "1+1=?"}],
                    "max_tokens": 10,
                },
                timeout=timeout,
            )
            if r.status_code != 200:
                return False
            content = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            return "2" in content
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"模型健康检查失败：{e}")
            return False

    def discover_available(self) -> List[str]:
        available = []
        for model in self.FREE_MODELS:
            if self.health_check(model):
                available.append(model)
                logger.info(LogCategory.MAIN, f"Model available: {model}")
        if not available:
            for model in self.PAID_MODELS:
                if self.health_check(model):
                    available.append(model)
        return available

    def select_best(self, task_type: str = "general") -> Optional[str]:
        if self.current_model and self.health_check(self.current_model):
            return self.current_model
        available = self.discover_available()
        self.current_model = available[0] if available else None
        return self.current_model

    def get_fallback_chain(self, primary: str) -> List[str]:
        if primary in self.FREE_MODELS:
            remaining = [m for m in self.FREE_MODELS if m != primary]
            return remaining + self.PAID_MODELS[:2]
        return self.FREE_MODELS

# --- VLM 验证器 ---

class VLMVerifier:
    def __init__(self, endpoint_mgr: Optional[ModelEndpointManager] = None):
        self.endpoint_mgr = endpoint_mgr or ModelEndpointManager()
        self.current_model = self.endpoint_mgr.select_best()
        logger.info(LogCategory.MAIN, f"VLMVerifier initialized with model: {self.current_model}")

    def _call_vlm(self, screenshot_b64: str, prompt: str,
                  model: str, timeout: int = 60) -> Dict:
        url = f"{self.endpoint_mgr.url}/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}},
                {"type": "text", "text": prompt},
            ]}],
            "max_tokens": 2048,
            "temperature": 0.1,
        }
        r = requests.post(url, headers=self.endpoint_mgr._headers(), json=payload, timeout=timeout)
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
        data = r.json()
        msg = data.get("choices", [{}])[0].get("message", {})
        content = msg.get("content", "")
        reasoning = msg.get("reasoning_content", "")
        return {"content": content, "reasoning": reasoning, "model": data.get("model", model), "raw": data}

    def _call_with_retry(self, screenshot_b64: str, prompt: str, max_retries: int = 3) -> Dict:
        models = [self.current_model] + self.endpoint_mgr.get_fallback_chain(self.current_model)
        last_error = "all models failed"
        for i, model in enumerate(models[:max_retries]):
            try:
                result = self._call_vlm(screenshot_b64, prompt, model)
                if "error" in result:
                    last_error = result["error"]
                    logger.warning(LogCategory.MAIN, f"Model {model} failed: {last_error}")
                    continue
                content = result.get("content", "")
                if not content:
                    reasoning = result.get("reasoning", "")
                    if reasoning:
                        result["content"] = reasoning
                self.current_model = model
                return result
            except Exception as e:
                last_error = str(e)
                logger.warning(LogCategory.MAIN, f"Model {model} exception: {last_error}")
                continue
        return {"error": last_error, "content": ""}

    def _parse_json(self, text: str) -> Optional[Dict]:
        m = re.search(r'\{[\s\S]*?\}', text)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        m = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        return None

    # === 核心验证方法 ===

    def verify_task_progress(self, screenshot_b64: str, expected: str = "10/10") -> VerificationResult:
        prompt = (
            f'You are a game verification assistant. Analyze this screenshot of Arknights Endfield.\n'
            f'Task: Verify daily task progress shows "{expected}".\n'
            f'Return strict JSON:\n'
            f'{{"matches_expected": bool, "current_progress": "x/y", "numeric": [x, y], '
            f'"state": "not_started/in_progress/completed/claimed", '
            f'"vlm_confidence": 0.0-1.0, "explanation": ""}}'
        )
        resp = self._call_with_retry(screenshot_b64, prompt)
        if "error" in resp:
            return VerificationResult(verified=False, confidence=0.0,
                                      error=resp["error"], model_used=self.current_model)
        parsed = self._parse_json(resp.get("content", ""))
        if not parsed:
            return VerificationResult(verified=False, confidence=0.0,
                                      reasoning="Failed to parse VLM response",
                                      raw_response=resp.get("content"),
                                      model_used=self.current_model)
        progress = parsed.get("current_progress", "")
        match = re.match(r'(\d+)/(\d+)', progress)
        if not match:
            return VerificationResult(verified=False, confidence=0.0,
                                      reasoning=f"Cannot parse progress: {progress}",
                                      extracted_data=parsed, model_used=self.current_model)
        cur, total = int(match.group(1)), int(match.group(2))
        target_cur, target_total = map(int, expected.split("/"))
        verified = (cur == target_cur and total >= target_total)
        conf = parsed.get("vlm_confidence", 0.5)
        return VerificationResult(
            verified=verified, confidence=conf,
            reasoning=parsed.get("explanation", ""),
            extracted_data={"progress": progress, "numeric": [cur, total], "state": parsed.get("state")},
            model_used=self.current_model,
        )

    def verify_reward_popup(self, screenshot_b64: str,
                              expected_types: Optional[List[str]] = None) -> VerificationResult:
        expected_types = expected_types or ["金币", "钻石", "材料"]
        prompt = (
            f'Analyze this Arknights Endfield screenshot for reward popup.\n'
            f'Return strict JSON:\n'
            f'{{"has_reward_popup": bool, "reward_items": [{{"name": "...", "amount": "..."}}], '
            f'"explanation": ""}}'
        )
        resp = self._call_with_retry(screenshot_b64, prompt)
        if "error" in resp:
            return VerificationResult(verified=False, confidence=0.0, error=resp["error"])
        parsed = self._parse_json(resp.get("content", ""))
        if not parsed:
            return VerificationResult(verified=False, confidence=0.0,
                                      reasoning="Failed to parse VLM response",
                                      raw_response=resp.get("content"))
        has_popup = parsed.get("has_reward_popup", False)
        items = parsed.get("reward_items", [])
        confirmed = any(
            any(et.lower() in item.get("name", "").lower() for et in expected_types)
            for item in items
        ) if items else False
        return VerificationResult(
            verified=has_popup and confirmed,
            confidence=0.9 if has_popup and confirmed else 0.3,
            reasoning=parsed.get("explanation", ""),
            extracted_data={"rewards": items},
            model_used=self.current_model,
        )

    def verify_combat_victory(self, screenshot_b64: str) -> VerificationResult:
        prompt = (
            f'Analyze this Arknights Endfield combat result screen.\n'
            f'Determine if the battle ended in victory.\n'
            f'Return strict JSON:\n'
            f'{{"is_combat_ended": bool, "is_victory": bool, "is_defeat": bool, '
            f'"visual_cues": [...], "confidence": 0.0-1.0, "explanation": ""}}'
        )
        resp = self._call_with_retry(screenshot_b64, prompt)
        if "error" in resp:
            return VerificationResult(verified=False, confidence=0.0, error=resp["error"])
        parsed = self._parse_json(resp.get("content", ""))
        if not parsed:
            return VerificationResult(verified=False, confidence=0.0,
                                      reasoning="Failed to parse VLM response")
        is_victory = parsed.get("is_victory", False)
        return VerificationResult(
            verified=is_victory,
            confidence=parsed.get("confidence", 0.5),
            reasoning=parsed.get("explanation", ""),
            extracted_data={"combat_ended": parsed.get("is_combat_ended"),
                            "cues": parsed.get("visual_cues")},
            model_used=self.current_model,
        )