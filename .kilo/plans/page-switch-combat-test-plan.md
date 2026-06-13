# 页面切换与代理作战测试落实方案（端侧实测版）

## 一、测试目标

针对**页面切换任务执行**和**代理作战**核心流程，使用**真实端侧模型加载**执行端到端测试，所有操作落实到游戏并验证状态变化。

**核心原则**:
- ✅ 端侧模型真实加载（llama-cpp-python, GGUF）
- ✅ 所有操作实际执行到游戏（ADB/MAA 触控）
- ✅ 执行后验证游戏状态变化（截图对比/元素识别）

---

## 二、核心流程分析

### 2.1 页面切换流程 (ExplorationEngine)

```
截图 → 本地 VLM 识别元素 → 点击元素 → 等待 → 截图验证新页面 → 记录边 → 返回
```

**关键方法**:
- `_navigate_and_explore()` - 导航 + 探索
- `_execute_tap()` / `_execute_back()` - 执行操作
- `_analyze_current_page()` - 页面分析
- `LocalInferenceEngine` - 本地 VLM 推理

### 2.2 代理作战流程 (CombatLoop)

```
截图 → 本地 VLM 判断状态 → 本地 VLM 生成指令 → 执行 3C 动作 → 截图验证 → 循环
```

**关键方法**:
- `VLMController.evaluate_combat_state()` - 战斗状态判断（本地模型）
- `VLMController.get_combat_instruction()` - 指令生成（本地模型）
- `CombatController.execute_action()` - 3C 动作执行
- `CombatLoop._loop()` - 主循环

### 2.3 修改再验证循环

```
修改配置/代码 → 启动本地模型 → 执行游戏操作 → 截图验证 → 记录结果
```

---

## 三、测试环境要求

| 组件 | 要求 |
|---|---|
| **本地模型** | qwen3.5-2b 或更大 (GGUF, `models/` 目录) |
| **推理引擎** | llama-cpp-python 已安装 |
| **设备** | ADB 连接的安卓设备/模拟器 |
| **触控** | MAA Framework 或 ADB input |
| **游戏** | 明日方舟：终末地 运行中 |

---

## 四、测试用例设计

### 4.1 端侧实测用例（必须真实执行）

| 测试场景 | 测试步骤 | 验证方法 | 预计时间 |
|---|---|---|---|
| **T1: 本地模型加载** | 启动 LocalInferenceEngine → 加载 GGUF 模型 | 检查 `model_path` 存在，生成测试文本 | 30 秒 |
| **T2: 截图→推理→点击** | 截图 → 本地 VLM 识别 → 点击识别的元素 | 对比点击前后截图哈希变化 | 2 分钟 |
| **T3: 页面切换循环** | 连续切换 5 个页面 | 验证 page_tree.json 记录 5 个页面 | 5 分钟 |
| **T4: 战斗状态判断** | 进入战斗 → 本地 VLM 判断 | 验证返回 `is_combat=true` | 1 分钟 |
| **T5: 3C 动作执行** | 执行 move_left/skill_1/jump | 截图验证角色位置/技能特效变化 | 3 分钟 |
| **T6: 完整战斗循环** | 战斗→移动→技能→击败 | 验证战斗胜利画面 | 10 分钟 |
| **T7: 每日任务完成** | 导航→执行任务→领取奖励 | 验证任务进度=10/10，奖励弹窗出现 | 15 分钟 |
| **T8: 奖励实际到账** | 领取前截图→领取→领取后截图 | 对比奖励图标/数量变化 | 5 分钟 |

---

## 五、结果验证标准

### 5.1 验证层级

```
Level 1: 操作执行验证 → 点击/滑动是否实际执行
Level 2: 界面变化验证 → 截图哈希/页面名称是否变化
Level 3: 业务目标验证 → 任务进度/奖励数量是否变化
Level 4: 持久化验证 → 存档/数据库是否更新
```

### 5.2 每日任务完成验证流程

```python
# tests/e2e/local/test_daily_tasks.py

def test_daily_task_completion(local_engine, device, screen_capture):
    """T7: 每日任务完成验证"""
    
    # === 步骤 1: 记录初始状态 ===
    initial_state = capture_task_state(device, screen_capture, local_engine)
    # initial_state = {
    #     "task_progress": "5/10",
    #     "reward_claimed": False,
    #     "screenshot_hash": "abc123"
    # }
    
    # === 步骤 2: 执行任务 ===
    result = execute_daily_task(local_engine, device)
    assert result.success is True
    
    # === 步骤 3: 验证任务进度 ===
    final_state = capture_task_state(device, screen_capture, local_engine)
    
    # 验证点 1: 进度变化
    assert final_state["task_progress"] == "10/10", "任务进度未达到 10/10"
    assert final_state["task_progress"] != initial_state["task_progress"], "任务进度无变化"
    
    # === 步骤 4: 领取奖励 ===
    claim_result = claim_reward(local_engine, device)
    assert claim_result.success is True
    
    # === 步骤 5: 验证奖励弹窗 ===
    reward_popup = detect_reward_popup(screen_capture, local_engine)
    assert reward_popup is not None, "未检测到奖励弹窗"
    assert reward_popup["reward_type"] in ["金币", "钻石", "材料"], "奖励类型异常"
    
    # === 步骤 6: 关闭弹窗并验证 ===
    close_reward_popup(local_engine, device)
    time.sleep(2.0)
    
    # === 步骤 7: 最终状态验证 ===
    post_claim_state = capture_task_state(device, screen_capture, local_engine)
    assert post_claim_state["reward_claimed"] is True, "奖励未标记为已领取"
    
    # === 步骤 8: 持久化验证 (可选) ===
    # 检查游戏存档/数据库确认奖励实际到账
    verify_reward_in_inventory(device, local_engine, reward_popup["reward_type"])


def capture_task_state(device, screen_capture, local_engine):
    """捕获当前任务状态"""
    screenshot = screen_capture.capture_screen(device)
    img_b64 = base64.b64encode(screenshot).decode()
    
    # 使用本地 VLM 识别任务进度
    result = local_engine.process(img_b64, prompt="""
    分析当前每日任务状态，返回 JSON:
    {"task_progress": "x/y", "reward_claimed": true/false, "task_name": "..."}
    """)
    
    return json.loads(result.text)


def verify_reward_in_inventory(device, local_engine, reward_type):
    """验证奖励实际到账（持久化验证）"""
    # 导航到背包/仓库页面
    navigate_to_inventory(device, local_engine)
    time.sleep(2.0)
    
    # 截图并识别奖励数量
    screenshot = screen_capture.capture_screen(device)
    img_b64 = base64.b64encode(screenshot).decode()
    
    result = local_engine.process(img_b64, prompt=f"""
    识别背包中{reward_type}的数量，返回 JSON:
    {{"item_type": "{reward_type}", "count": 123}}
    """)
    
    inventory_state = json.loads(result.text)
    
    # 验证数量增加（与测试前对比）
    assert inventory_state["count"] > initial_inventory_count, f"{reward_type}数量未增加"
```

### 5.3 战斗胜利验证流程

```python
# tests/e2e/local/test_full_combat.py

def test_combat_victory(local_engine, device, screen_capture):
    """T6: 完整战斗循环 + 胜利验证"""
    
    # === 步骤 1: 战前状态 ===
    pre_combat = capture_combat_state(device, screen_capture, local_engine)
    # pre_combat = {
    #     "character_hp": 100,
    #     "enemy_count": 5,
    #     "battle_status": "not_started"
    # }
    
    # === 步骤 2: 进入战斗 ===
    enter_combat(local_engine, device)
    
    # === 步骤 3: 执行战斗循环 ===
    for i in range(20):  # 最多 20 轮
        screenshot = screen_capture.capture_screen(device)
        img_b64 = base64.b64encode(screenshot).decode()
        
        # 本地 VLM 判断战斗状态
        state = local_engine.process(img_b64, prompt="""
        判断战斗状态，返回 JSON:
        {"is_combat": bool, "enemy_count": int, "victory_visible": bool}
        """)
        combat_state = json.loads(state.text)
        
        if combat_state["victory_visible"]:
            break  # 胜利，退出循环
        
        # 本地 VLM 生成战斗指令
        action = local_engine.process(img_b64, prompt="""
        生成战斗指令，返回 JSON:
        {"action": "skill_1/move/attack", "target": "..."}
        """)
        
        execute_action(device, json.loads(action.text))
    
    # === 步骤 4: 验证胜利 ===
    final_screenshot = screen_capture.capture_screen(device)
    img_b64 = base64.b64encode(final_screenshot).decode()
    
    victory_check = local_engine.process(img_b64, prompt="""
    检查是否出现胜利画面，返回 JSON:
    {"victory_confirmed": bool, "victory_text": "胜利/Victory/战斗结束"}
    """)
    
    victory_state = json.loads(victory_check.text)
    assert victory_state["victory_confirmed"] is True, "未检测到胜利画面"
    
    # === 步骤 5: 验证奖励获取 ===
    reward_result = collect_combat_rewards(local_engine, device)
    assert reward_result["rewards_collected"] is True
    
    # === 步骤 6: 持久化验证 ===
    # 检查战斗记录/任务进度更新
    verify_mission_progress(device, local_engine)
```

### 5.4 验证检查清单

执行测试后必须验证：

- [ ] **操作执行**: ADB/MAA 点击日志确认
- [ ] **界面变化**: 前后截图哈希不同
- [ ] **任务进度**: VLM 识别进度从 x/y 变为 10/10
- [ ] **奖励弹窗**: 检测到奖励弹窗 UI
- [ ] **奖励到账**: 背包中对应物品数量增加
- [ ] **战斗胜利**: 检测到"胜利"字样/UI
- [ ] **持久化**: 游戏存档/数据库更新确认

**示例测试代码**:

```python
# tests/unit/core/test_combat_controller.py
class TestCombatController:
    def test_execute_tap_action(self, mock_touch_executor):
        """测试点击动作执行"""
        combat = CombatController(mock_touch_executor, device_width=1920, device_height=1080)
        result = combat.execute_action("skill_1")
        mock_touch_executor.safe_press.assert_called_once_with(200, 950, 50)
        assert result is True

    def test_execute_swipe_action(self, mock_touch_executor):
        """测试滑动物作执行"""
        combat = CombatController(mock_touch_executor)
        result = combat.execute_action("move_left", {"duration": 300})
        mock_touch_executor.safe_swipe.assert_called_once_with(500, 500, 100, 500, 300)
        assert result is True

    def test_execute_unknown_action(self, mock_touch_executor):
        """测试未知动作"""
        combat = CombatController(mock_touch_executor)
        result = combat.execute_action("unknown_action")
        assert result is False


# tests/unit/core/test_agent_executor.py
class TestAgentExecutor:
    def test_execute_tap_coordinate_scaling(self, mock_screen_capture, mock_touch_executor, mock_communicator):
        """测试点击坐标缩放"""
        agent = AgentExecutor(mock_communicator, mock_screen_capture, mock_touch_executor)
        mock_communicator.send_request.return_value = {
            "status": "success",
            "reply": "Done",
            "actions": [{"type": "tap", "params": {"x": 0.5, "y": 0.5}}]  # 归一化坐标
        }
        mock_screen_capture.capture_screen.return_value = b"fake_image"
        result = agent.send_instruction("点击按钮")
        # 验证 0.5, 0.5 被缩放为设备坐标
        expected_x = int(0.5 * 1920 / 1920)
        expected_y = int(0.5 * 1080 / 1080)
        mock_touch_executor.safe_press.assert_called_once_with(expected_x, expected_y)
```

### 4.2 测试脚本结构

```
tests/e2e/local/
  conftest.py                      #  fixtures: 真实模型加载、设备连接
  test_model_load.py               # T1: 本地模型加载验证
  test_page_switch.py              # T2-T3: 页面切换实测
  test_combat_state.py             # T4: 战斗状态判断
  test_3c_actions.py               # T5: 3C 动作执行
  test_full_combat.py              # T6: 完整战斗循环
  results/                         # 验证结果（截图/日志）
```

### 4.3 测试脚本示例

```python
# tests/e2e/local/conftest.py
@pytest.fixture(scope="module")
def local_inference_engine():
    """真实加载本地模型"""
    engine = LocalInferenceEngine(model_path="models/qwen3.5-2b/xxx.gguf")
    engine.load_model()
    assert engine.is_loaded()
    yield engine
    engine.unload()

@pytest.fixture(scope="module")
def device_connection():
    """连接真实设备"""
    device_serial = "emulator-5554"
    adb.connect(device_serial)
    yield device_serial
    adb.disconnect(device_serial)

# tests/e2e/local/test_page_switch.py
def test_click_and_verify(local_inference_engine, device_connection, screen_capture):
    """T2: 截图→推理→点击→验证"""
    # 1. 截图
    screenshot = screen_capture.capture_screen(device_connection)
    img_b64 = base64.b64encode(screenshot).decode()
    
    # 2. 本地 VLM 识别元素
    result = local_inference_engine.process(img_b64, prompt="识别所有可点击按钮")
    assert result.status == "success"
    element = result.touch_actions[0]  # 获取第一个可点击元素
    
    # 3. 执行点击
    adb.tap(device_connection, element["x"], element["y"])
    time.sleep(2.0)
    
    # 4. 验证：截图对比
    new_screenshot = screen_capture.capture_screen(device_connection)
    old_hash = hashlib.md5(screenshot).hexdigest()
    new_hash = hashlib.md5(new_screenshot).hexdigest()
    assert old_hash != new_hash, "页面未发生变化"
```

---

## 五、实施计划

### 阶段 1：环境准备（1 天）

**任务**:
1. 确认本地模型文件存在 (`models/`)
2. 确认 llama-cpp-python 已安装
3. 确认 ADB 设备连接正常
4. 创建 `tests/e2e/local/` 目录结构

**验收**: `python -c "from llama_cpp import Llama; print('OK')"`

### 阶段 2：基础测试脚本（2 天）

**任务**:
1. 实现 `conftest.py` fixtures（真实模型加载、设备连接）
2. 实现 `test_model_load.py` - 模型加载验证
3. 实现 `test_page_switch.py` - 页面切换实测
4. 实现 `test_3c_actions.py` - 3C 动作执行

**验收**: 所有脚本可执行，截图验证通过

### 阶段 3：完整流程测试（2 天）

**任务**:
1. 实现 `test_combat_state.py` - 战斗状态判断
2. 实现 `test_full_combat.py` - 完整战斗循环
3. 建立结果记录模板 (`results/`)
4. 添加修改后验证脚本

**验收**: 完整战斗流程可执行并验证胜利

---

## 六、运行命令

```bash
# 阶段 1：环境验证
python -c "from llama_cpp import Llama; Llama('models/xxx.gguf'); print('模型加载 OK')"
adb devices  # 确认设备连接

# 阶段 2：基础测试
pytest tests/e2e/local/test_model_load.py -v
pytest tests/e2e/local/test_page_switch.py -v
pytest tests/e2e/local/test_3c_actions.py -v

# 阶段 3：完整流程 + 结果验证
pytest tests/e2e/local/test_combat_state.py -v
pytest tests/e2e/local/test_full_combat.py -v
pytest tests/e2e/local/test_daily_tasks.py -v  # 每日任务完成验证
pytest tests/e2e/local/test_reward_verification.py -v  # 奖励到账验证

# 修改后完整验证（含所有验证层级）
pytest tests/e2e/local/ -v --tb=short

# 生成验证报告
pytest tests/e2e/local/ --html=tests/e2e/results/report.html
```

---

## 七、预期结果

| 阶段 | 用例数 | 通过标准 | 执行时间 |
|---|---|---|---|
| 模型加载 | 1 | 模型成功加载 | <30 秒 |
| 基础操作 | 3 | 操作执行 + 界面变化 | <5 分钟 |
| 战斗流程 | 2 | 战斗胜利 + 奖励获取 | <15 分钟 |
| 任务完成 | 2 | 任务进度 10/10 + 奖励到账 | <20 分钟 |
| **完整验证** | **8** | **所有验证层级通过** | **<45 分钟** |

### 验证层级要求

- ✅ Level 1: 操作执行验证 - ADB/MAA日志确认
- ✅ Level 2: 界面变化验证 - 截图哈希对比
- ✅ Level 3: 业务目标验证 - 任务进度/奖励数量
- ✅ Level 4: 持久化验证 - 背包物品数量增加

---

## 八、风险与应对

| 风险 | 应对 |
|---|---|
| 模型加载失败 | 检查 GGUF 文件完整性，确认 llama-cpp-python 版本 |
| 设备连接断开 | 测试前执行 `adb reconnect` |
| 操作执行失败 | 检查触控权限，使用 ADB input fallback |
| VLM 识别不准确 | 增加 prompt 优化，多次识别取平均 |
| 验证误报/漏报 | 使用多模态验证（截图 + OCR+ 模板匹配） |
| 游戏状态异常 | 添加异常检测器自动恢复 |
| 测试时间过长 | 并行执行独立测试用例 |
| 奖励数量验证困难 | 测试前手动记录初始数量，对比差值 |

---

## 九、验证报告模板

测试完成后生成报告包含：

```markdown
# 测试结果报告

## 环境信息
- 模型：qwen3.5-2b-Q8_K_XL.gguf
- 设备：emulator-5554
- 游戏版本：1.0.0

## 测试用例结果

### T7: 每日任务完成
- [x] 任务进度从 5/10 → 10/10 ✓
- [x] 奖励弹窗检测到 ✓
- [x] 奖励类型：金币 x100 ✓
- [x] 背包金币数量：1000 → 1100 ✓

### T6: 战斗胜利
- [x] 战斗状态判断正确 ✓
- [x] 技能执行成功 ✓
- [x] 胜利画面检测到 ✓
- [x] 战斗奖励领取 ✓

## 截图证据
- 战前：tests/e2e/results/combat_pre.png
- 战后：tests/e2e/results/combat_post.png
- 奖励弹窗：tests/e2e/results/reward_popup.png
- 背包对比：tests/e2e/results/inventory_before_after.png
```
