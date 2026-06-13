# VLM 验证核心方案（基于 cherryin.ai Qwen3.5-27B Free）

## 一、需求分析

### 1.1 核心要求 ✓已确认

| 需求 | 描述 | 当前状态 |
|---|---|---|
| **VLM 为核心** | 验证逻辑围绕 VLM 推理展开，而非 OCR/规则 | ❌ 待实现 |
| **指定模型** | 使用 `qwen/qwen3.5-27b(free)` - 免费层 | ✅ skill 已配置 |
| **验证目标** | 任务完成度验证、奖励到账确认、战斗胜利判定 | ❌ 待实现 |
| **可回退修正** | 如果主模型不可用，需自动降级或修复 | ❌ 待实现 |

### 1.2 端点矩阵（来自 subagent-qwen skill）

```
主力视觉模型 → qwen/qwen3.5-27b(free)  [Cherryin 直连]
              qwen/qwen3-vl-235b-a22b-instruct [Cherryin 直连]
              
Cherryin.ai 直连 URL: https://open.cherryin.cc/v1
API Key: sk-SHYG0HNKhAEPXbEHOdlLcggKXYlyEGJyolvGjh0T2r5FQOst
超时：180 秒
```

---

## 二、架构设计（不变）
```
...
```

---

## 二、架构设计

```
verification_core/
├── vlm_verifier.py        # VLM 验证器（核心）
│   ├── VLMVerifier
│   │   ├── verify_task_progress(...)
│   │   ├── verify_reward_claimed(...)
│   │   ├── verify_combat_victory(...)
│   │   └── verify_inventory_change(...)
│   │
│   └── ModelEndpointManager
│       ├── select_model()           # 选择可用的免费模型
│       ├── fallback_chain()         # 回退链
│       └── health_check()           # 健康检查
│
├── verification_prompts/
│   ├── task_progress.json           # 任务进度验证 prompt
│   ├── reward_popup.json            # 奖励弹窗判断 prompt
│   ├── combat_victory.json          # 战斗胜利判断 prompt
│   └── inventory_count.json         # 背包数量识别 prompt
│
├── verification_result/
│   ├── VerificationResult dataclass
│   ├── ConfidenceScore enum
│   └── ResultAggregator             # 多轮验证聚合
│
└── integration/
    ├── subagent_integration.py      # 子智能机制集成
    └── direct_vlm_integration.py    # direct_vlm.py 集成
```

---

## 三、Model Endpoint Management（已确认配置）

### 3.1 免费模型可用性检查

```python
class ModelEndpointManager:
    """管理 VLM 验证模型端点"""
    
    # Cherryin.ai 免费模型（来自 AGENTS.md）
    FREE_MODELS = [
        "qwen/qwen3.5-27b(free)",           # ✅ 主力视觉模型 (27B)
        "qwen/qwen3-vl-235b-a22b-instruct", # 旗舰 VL - 可能非 free
        "cherryin/qwen3.5-9b-free",         # 备用轻量免费 (9B)
    ]
    
    PAID_MODELS = [
        "qwen/qwen3-vl-plus",               # 高精度视觉
        "qwen/qwen3.6-plus",                # 综合能力
    ]
    
    def __init__(self):
        self.endpoint = CHERRYIN_API_URL     # https://open.cherryin.cc/v1
        self.api_key = CHERRYIN_API_KEY      # sk-SHYG0HNKhAEPXbEHOdlLcggKXYlyEGJyolvGjh0T2r5FQOst
        
    def verify_model_status(self):
        """检查 qwen/qwen3.5-27b(free) 是否可用"""
        test_response = requests.post(
            f"{self.endpoint}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "qwen/qwen3.5-27b(free)",
                "messages": [{"role": "user", "content": "hello"}],
                "max_tokens": 10
            },
            timeout=30
        )
        return test_response.status_code == 200
    
    def _health_check(self, model_name: str) -> bool:
        """对模型进行健康检查"""
        try:
            response = requests.post(
                f"{self.endpoint}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": "回答：1+1=?"}],
                    "max_tokens": 10
                },
                timeout=15
            )
            return response.status_code == 200 and ("2" in response.json().get("choices", [{}])[0].get("message", {}).get("content", ""))
        except Exception as e:
            logger.warning(f"模型 {model_name} 不健康：{e}")
            return False
```
    
    SUBAGENT_MODELS = [
        "Qwen3-VL-235B-A22B",            # 子智能旗舰视觉模型
        "Qwen3.6-Plus-image",            # 图像理解+生成
    ]
    
    def __init__(self, config_path="config/client_config.json"):
        self.config = load_config(config_path)
        self.current_model = None
        self.available_models = []
        
    def check_free_model_availability(self):
        """
        检查免费模型是否可用
        返回第一个可用的免费模型名称
        """
        for model in self.FREE_MODELS:
            if self._health_check(model):
                return model
        return None
    
    def _health_check(self, model_name: str) -> bool:
        """
        对模型进行健康检查
        发送简单测试请求，验证响应
        """
        test_prompt = "请回答：1+1=?"
        try:
            response = self._call_vlm(model_name, test_prompt, timeout=10)
            return "2" in response.text or response.status == "success"
        except Exception as e:
            logger.warning(f"模型 {model_name} 不健康：{e}")
            return False
    
    def get_fallback_chain(self, primary_model: str) -> List[str]:
        """获取回退链"""
        if primary_model in self.FREE_MODELS:
            remaining_free = [m for m in self.FREE_MODELS if m != primary_model]
            return remaining_free + self.PAID_MODELS[:2]
        elif primary_model in self.PAID_MODELS:
            return self.PAID_MODELS[1:] + self.FREE_MODELS
        else:
            return self.FREE_MODELS
        
    def select_best_model(self, task_type: str) -> str:
        """根据任务类型选择合适的模型"""
        if task_type == "vision_heavy":  # 复杂 UI 分析
            if self._health_check("cherryin/qwen3-vl-plus"):
                return "cherryin/qwen3-vl-plus"
            return self.get_fallback_chain("cherryin/qwen3-vl-plus")[0]
            
        elif task_type == "text_reasoning":  # 任务进度假设与推理
            free_model = self.check_free_model_availability()
            return free_model or self.PAID_MODELS[0]
            
        else:  # 通用验证
            return self.check_free_model_availability() or self.FREE_MODELS[0]
```

### 3.2 subagent-qwen integration（直接复用）

```python
class SubagentVerificationIntegration:
    """直接使用已配置的 subagent-qwen skill"""
    
    def __init__(self):
        from subagent_qwen import SubAgentQwen
        self.agent = SubAgentQwen(
            endpoint_cherryin="https://open.cherryin.cc/v1",
            cherryin_api_key="sk-SHYG0HNKhAEPXbEHOdlLcggKXYlyEGJyolvGjh0T2r5FQOst"
        )
        
    def verify_with_model(self, screenshot_b64: str, verification_task: str) -> Dict:
        """
        使用指定的 Cherryin 模型验证截图
        
        Args:
            screenshot_b64: 截图 base64
            verification_task: "验证每日任务进度是否为 10/10"
            
        Returns:
            {
                "verifier_confirmed": True,
                "reasoning": "检测到任务文本显示 10/10...",
                "confidence": 0.95,
                "extracted_value": {"progress": "10/10"}
            }
        """
        messages = [
            {
                "role": "system",
                "content": self._build_system_prompt(verification_task)
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": verification_task},
                    {"type": "image_url", "image_url": 
                        {"url": f"data:image/png;base64,{screenshot_b64}"}}
                ]
            }
        ]
        
        # 直接使用 qwen/qwen3.5-27b(free)
        result = self.agent.chat(
            model="qwen/qwen3.5-27b(free)",
            messages=messages,
            temperature=0.1
        )
        
        return self._parse_verification_response(result)
```

---

## 四、VLM Verifier 实现

### 4.1 核心验证器

```python
@dataclass
class VerificationResult:
    """验证结果数据结构"""
    verified: bool
    confidence: float              # 置信度 0.0-1.0
    reasoning: str                 # VLM 的解释说明
    extracted_data: Optional[Dict] = None  # 提取的结构化数据
    raw_response: Optional[str] = None    # VLM 原始回复
    model_used: Optional[str] = None      # 使用的模型名称


class VLMVerifier:
    """VLM 为核心的验证器"""
    
    def __init__(self, endpoint_manager: ModelEndpointManager):
        self.endpoint_mgr = endpoint_manager
        self.current_model = endpoint_mgr.check_free_model_availability()
        
    def verify_task_progress(self, screenshot_b64: str, expected_progress: str) -> VerificationResult:
        """
        验证任务进度
        
        Expected: "10/10"
        """
        prompt_template = load_prompt("task_progress.json")
        prompt = prompt_template.format(expected=expected_progress)
        
        response = self._call_vlm_with_retry(screenshot_b64, prompt)
        result = self._parse_json_response(response.text)
        
        # 验证提取的数据
        actual_progress = result.get("current_progress", "")
        progress_match = re.match(r'(\d+)/(\d+)', actual_progress)
        
        if not progress_match:
            return VerificationResult(
                verified=False,
                confidence=0.0,
                reasoning=f"无法解析进度数值：{actual_progress}",
                raw_response=response.text,
                model_used=self.current_model
            )
        
        current, total = int(progress_match.group(1)), int(progress_match.group(2))
        target_current, target_total = map(int, expected_progress.split('/'))
        
        verified = (current == target_current and total >= target_total)
        confidence = self._calculate_confidence(verified, result.get("vlm_confidence", 0.5))
        
        return VerificationResult(
            verified=verified,
            confidence=confidence,
            reasoning=result.get("explanation", ""),
            extracted_data={"progress": actual_progress, "numeric": (current, total)},
            raw_response=response.text,
            model_used=self.current_model
        )
    
    def verify_reward_popup(self, screenshot_b64: str, expected_reward_types: List[str]) -> VerificationResult:
        """验证奖励弹窗类型"""
        prompt = """
        检测画面中的奖励弹窗信息，返回 JSON:
        {
            "has_reward_popup": true/false,
            "reward_items": [
                {"name": "金币", "amount": "x100"},
                {"name": "钻石", "amount": "+50"}
            ],
            "explanation": "画面显示了..."
        }
        """
        response = self._call_vlm_with_retry(screenshot_b64, prompt)
        result = json.loads(response.text)
        
        has_popup = result.get("has_reward_popup", False)
        detected_rewards = result.get("reward_items", [])
        
        # 检查是否有匹配的预期奖励
        confirmed_matching = any(
            any(exp_type.lower() in item["name"].lower() 
                for exp_type in expected_reward_types)
            for item in detected_rewards
        )
        
        return VerificationResult(
            verified=has_popup and confirmed_matching,
            confidence=0.9 if has_popup else 0.3,
            reasoning=result.get("explanation", ""),
            extracted_data={"rewards": detected_rewards},
            raw_response=response.text,
            model_used=self.current_model
        )
    
    def verify_combat_victory(self, screenshot_b64: str) -> VerificationResult:
        """验证战斗胜利"""
        prompt = """
        这是战斗结束后的画面吗？如果是胜利，返回 true。
        返回 JSON:
        {
            "is_combat_ended": true/false,
            "is_victory": true/false,
            "defeat_details": "",
            "visual_cues": ["文字提示", "界面颜色", "按钮位置"],
            "explanation": ""
        }
        """
        response = self._call_vlm_with_retry(screenshot_b64, prompt)
        result = json.loads(response.text)
        
        is_victory = result.get("is_victory", False)
        
        return VerificationResult(
            verified=is_victory,
            confidence=0.95 if is_victory else 0.4,
            reasoning=result.get("explanation", ""),
            extracted_data={
                "combat_ended": result.get("is_combat_ended"),
                "visual_cues": result.get("visual_cues")
            },
            raw_response=response.text,
            model_used=self.current_model
        )
    
    def verify_inventory_item_count(self, screenshot_b64: str, item_name: str) -> VerificationResult:
        """验证背包中某物品数量"""
        prompt = f"""
        检测背包中「{item_name}」的数量。可能存在多个格子，统计总数。
        返回 JSON:
        {{
            "detected": true/false,
            "item_name": "{item_name}",
            "total_count": 123,
            "individual_grids": [
                {{"name": "金币券", "count": 50}},
                {{"name": "金币券", "count": 30}}
            ],
            "explanation": "",
            "confidence_note": "OCR/VLM 的信心程度"
        }}
        """
        response = self._call_vlm_with_retry(screenshot_b64, prompt)
        result = json.loads(response.text)
        
        detected = result.get("detected", False)
        count = result.get("total_count", 0)
        
        return VerificationResult(
            verified=detected and count > 0,
            confidence=float(result.get("confidence_note", "0.5")),
            reasoning=result.get("explanation", ""),
            extracted_data={"item_count": count, "grids": result.get("individual_grids", [])},
            raw_response=response.text,
            model_used=self.current_model
        )
```

### 4.2 重试与降级机制

```python
def _call_vlm_with_retry(self, screenshot_b64: str, prompt: str, max_retries: int = 3) -> Response:
    """
    带重试的 VLM 调用
    失败时按回退链切换模型
    """
    models_to_try = [self.current_model] + self.endpoint_mgr.get_fallback_chain(self.current_model)
    
    for i, model in enumerate(models_to_try[:max_retries]):
        try:
            response = self._call_vlm(model, screenshot_b64, prompt, timeout=30)
            
            # 验证响应质量
            if self._is_valid_response(response):
                self.current_model = model  # 更新当前模型
                return response
            else:
                logger.warning(f"模型 {model} 返回无效响应，尝试下一个")
                
        except Exception as e:
            logger.warning(f"模型 {model} 调用失败：{e}")
            continue
    
    raise VerificationError(f"所有模型都不可用，最后尝试：{models_to_try[-1]}")
```

---

## 五、Prompt 模板（verification_prompts/）

### 5.1 task_progress.json
```json
{
  "system": "你是一名游戏验证助手。你需要从截图中识别任务进度并返回结构化数据。",
  "user_template": "
  这是一张《明日方舟：终末地》的游戏截图。
  
  【验证任务】
  确认当前显示的每日任务进度是否为 \"{expected}\"
  
  【输出格式】
  返回严格的 JSON:
  {{
    \"matches_expected\": true/false,
    \"current_progress\": \"x/y 格式的字符串\",
    \"numeric_progress\": [x, y],
    \"task_name\": \"任务标题文本\",
    \"state\": \"not_started/in_progress/completed/claimed\",
    \"vlm_confidence\": 0.0-1.0,
    \"explanation\": \"简短解释你的判断依据\"
  }}
  
  【注意事项】
  - 必须准确提取数字
  - 如果找不到进度信息，返回 matches_expected=false
  - state 字段必须从四个值中选一个
  
  开始分析截图：
  "
}
```

### 5.2 combat_victory.json
```json
{
  "system": "你是战斗状态判断专家。能够识别胜利/失败/进行中三种状态。",
  "user_template": "
  分析这张战斗结束的截图，判断战斗状态：
  
  【关键特征】
  1. Victory/胜利 字样或中文「胜利」「通关成功」
  2. Defeat/失败 字样或红色警告框
  3. 结算奖励区域（表示已结束）
  4. 角色动画是否停止（表示结束）
  
  【输出 JSON】
  {{
    "is_combat_ended": true/false,
    "is_victory": true/false,
    "is_defeat": true/false,
    "visual_cues": [看到的英文/中文关键词、颜色倾向、UI 元素],
    "confidence": 0.0-1.0,
    "explanation": "判断理由"
  }}
  "
}
```

---

## 六、验证流程整合

```python
class DailyTaskVerificationPipeline:
    """日常任务验证流水线"""
    
    def __init__(self, verifier: VLMVerifier):
        self.verifier = verifier
        
    def run_full_verification(self, 
                               before_screenshot: bytes,
                               after_screenshot: bytes,
                               claim_screenshot: bytes,
                               task_definition: TaskDefinition) -> VerificationReport:
        """
        执行完整验证流程
        
        步骤:
        1. 验证初始状态 (before_screenshot)
        2. 验证任务完成后状态 (after_screenshot)  
        3. 验证奖励弹窗出现 (claim_screenshot)
        4. 对比前后状态变化
        """
        results = []
        
        # Step 1: 初始状态验证
        initial = self.verifier.verify_task_progress(
            base64.b64encode(before_screenshot).decode(),
            "0/10"
        )
        results.append(("initial_state", initial))
        
        # Step 2: 任务完成后验证
        completed = self.verifier.verify_task_progress(
            base64.b64encode(after_screenshot).decode(),
            "10/10"
        )
        results.append(("completed_state", completed))
        
        # Step 3: 领取奖励弹窗验证
        claim = self.verifier.verify_reward_popup(
            base64.b64encode(claim_screenshot).decode(),
            ["金币", "钻石", "材料"]
        )
        results.append(("reward_popup", claim))
        
        # aggregate_results(results)
        report = self._generate_report(task_definition.name, results)
        
        return report
```

---

## 七、Implementation Phased Plan（已调整为 Cherryin qwen3.5-27b(free)）

### Phase 0: 预验证检查（0.5 天，必须首先执行）

1. ✅ **验证 cherryin.ai 连接可用性**
   ```bash
   curl -X POST https://open.cherryin.cc/v1/chat/completions \
     -H "Authorization: Bearer sk-SHYG0HNKhAEPXbEHOdlLcggKXYlyEGJyolvGjh0T2r5FQOst" \
     -H "Content-Type: application/json" \
     -d '{"model": "qwen/qwen3.5-27b(free)", "messages": [{"role":"user","content":"hello"}]}'
   ```

2. ✅ **确认 API Key 有效性**
   - 如果返回 401/403 → 需要刷新 key (从配置中获取 new key)
   - 如果超时→网络问题，切用本地 New API 3000

3. ✅ **测试图像上传能力**
   - 用一张 100x100 的基截图测试 multi-modal 是否生效
   - 如失败→检查 model 是否支持 vision

### Phase 1: 基础框架搭建（1.5 天）

1. `ModelEndpointManager` - Cherryin api 健康检查和模型选择
2. `VLMVerifier` 基类 - 实现 `_call_vlm_with_retry()` 逻辑
3. ⏳ `verification_prompts/` - 创建 prompt 模板文件
4. ⏳ 单元测试 - mock 响应进行基本逻辑测试

### Phase 2: 核心验证器开发（2 天）

1. `verify_task_progress()` - 任务进度提取与数值比较
2. `verify_reward_popup()` - 奖励弹窗检测
3. `verify_combat_victory()` - 战斗胜利判断
4. 端到端真实截图测试（需游戏录屏素材）

### Phase 3: Pipeline 整合（1 周）

1. DailyTaskVerificationPipeline 完整流程
2. BattleLoopVerificationPipeline 战斗循环验证
3. ConfidenceScore aggregator - 多轮验证聚合决策
4. Error handling 与 fallback to subagent

---

## 八、待明确问题

请确认以下事项后再开始编码：

1. **API Key 时效性**: current key `sk-SHYG0HNKhAEPXbEHOdlLcggKXYlyEGJyolvGjh0T2r5FQOst` 是否需要定期刷新？如何获取新的 key?

2. **免费额度限制**: `qwen/qwen3.5-27b(free)` 是否有每日调用次数限制？需要监控用量吗？

3. **视觉能力验证**: skill 文档说该模型支持 image input，但需要实际测试确认 multi-modal 能否正常工作？

4. **置信度校准**: 是否需要收集一批已标注的测试截图，用来校准 VLM 输出的 confidence score 与实际准确率的关系？

请回复确认后我将开始第一阶段实施。
