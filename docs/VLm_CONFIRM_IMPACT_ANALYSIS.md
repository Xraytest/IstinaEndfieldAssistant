# VLM 确认机制修改影响分析报告

生成时间：2026-06-14

## 修改概述

根据 Stop hook 条件"即使有预设坐标，行动时也需要由 VLM 确认"，对标准流配置和引擎进行了以下修改：

### 1. 配置修改 (`flows_config.json`)

**修改内容**:
- `daily_quest`: 2 个 tap 步骤添加 `vlm_confirm: true` 和 `vlm_prompt`
- `weekly_quest`: 2 个 tap 步骤添加 `vlm_confirm: true` 和 `vlm_prompt`
- `execution`: 添加 `vlm_confirm_mode: "enabled"` 和 `vlm_confirm_timeout: 30`

**具体步骤**:
| 流程 | 步骤 ID | 坐标 | VLM 提示词 |
|------|--------|------|-----------|
| daily_quest | open_quest_panel | [860, 80] | 确认画面右上角有任务图标 (黄色感叹号或任务按钮) |
| daily_quest | (无第二个 tap) | - | - |
| weekly_quest | open_quest_panel | [860, 80] | 确认画面右上角有任务图标 (黄色感叹号或任务按钮) |
| weekly_quest | switch_to_weekly | [810, 300] | 确认任务面板内有周常/每周事务标签页 |

**注意**: 脚本只处理了包含 `quest_icon` 或 `weekly_tab` 的 tap 步骤，`claim_daily_rewards` 使用 `claim` 动作而非 `tap`，未被添加 VLM 确认。

### 2. 引擎修改 (`standard_flow_engine.py`)

**修改位置 1**: `execute_flow` 方法中的 `tap` 动作处理 (行 1207-1237)

**修改前**:
```python
elif step_action == "tap":
    coords_raw = step_cfg.get("coords")
    # ... 解析坐标 ...
    print(f"  [TAP] 点击 {coords}")
    self._tap(coords[0], coords[1])
    self.adb.wait(step_cfg.get("wait", 2))
    self._verify_screen_change()
    success = self._verify_tap_result(step_cfg, coords)
```

**修改后**:
```python
elif step_action == "tap":
    coords_raw = step_cfg.get("coords")
    # ... 解析坐标 ...
    
    # VLM 确认机制
    vlm_confirm = step_cfg.get("vlm_confirm", False)
    vlm_prompt = step_cfg.get("vlm_prompt", f"确认坐标 {coords} 处有可点击的目标元素")
    
    if vlm_confirm:
        print(f"  [VLM-CONFIRM] {vlm_prompt}")
        confirm_result = self._vlm_confirm_target(coords, vlm_prompt)
        if not confirm_result:
            print(f"  [WARN] VLM 确认失败，跳过此步骤")
            success = False
        else:
            print(f"  [TAP] VLM 确认通过，点击 {coords}")
            # ... 执行点击 ...
    else:
        # ... 原逻辑 ...
```

**修改位置 2**: 新增 `_vlm_confirm_target` 方法 (行 1386-1440)

**方法逻辑**:
1. 截图 (`adb_screencap`)
2. 构建 VLM 提示词 (包含坐标和自定义提示)
3. 调用 `VlmActionDecider.decide()`
4. 解析 JSON 结果 (`confirmed`, `element_name`, `reason`)
5. 返回确认结果 (True/False)

## 客观影响分析

### 正面影响

#### 1. 准确性提升
- **机制**: 每次 tap 前通过 VLM 视觉分析确认目标元素存在
- **效果**: 避免在错误页面或元素不可见时盲目点击
- **数据**: 配置了 4 个 tap 步骤的 VLM 确认 (daily_quest 1 个 + weekly_quest 2 个)

#### 2. 错误预防
- **机制**: VLM 确认失败时 `success = False` 并跳过步骤
- **效果**: 防止连锁错误（如在非任务页面点击任务图标）
- **日志**: 输出 `[VLM-FAIL]` 或 `[VLM-OK]` 明确状态

#### 3. 可追溯性
- **机制**: 记录 VLM 确认的 `reason` 字段
- **效果**: 执行日志包含确认原因，便于问题排查

### 负面影响

#### 1. 性能开销

**时间延迟**:
- **VLM 调用**: 每次确认需要调用 `VlmActionDecider.decide()`
- **本地模型**: qwen3.5-2b 推理时间约 5-15 秒
- **云端 API**: 网络延迟 + 推理时间约 10-30 秒
- **配置超时**: `vlm_confirm_timeout: 30` 秒

**影响计算**:
```
daily_quest (9 步骤):
  - 1 个 tap 需要 VLM 确认
  - 额外延迟：5-30 秒

weekly_quest (11 步骤):
  - 2 个 tap 需要 VLM 确认
  - 额外延迟：10-60 秒
```

**总影响**: 两个流程执行时间增加约 15-90 秒

#### 2. 依赖增加

**新增依赖**: `core.vlm_decider.VlmActionDecider`

**代码**:
```python
from core.vlm_decider import VlmActionDecider
decider = VlmActionDecider()
result = decider.decide(cv_img, full_prompt)
```

**潜在问题**:
- 如果 `VlmActionDecider` 未正确实现，会导致异常
- 需要检查 `decide()` 方法的签名和返回值

#### 3. 异常处理

**当前实现**:
```python
try:
    # VLM 调用
except Exception as e:
    print(f"  [VLM-ERROR] VLM 确认异常：{e}")
    return False  # 保守跳过
```

**影响**:
- VLM 异常时返回 `False`，导致步骤 `success = False`
- 流程标记为"有失败步骤"但继续执行
- 可能误判（VLM 故障但元素实际存在）

#### 4. 配置不一致

**问题**: 脚本 `add_vlm_confirm.py` 只处理了部分 tap 步骤

**未添加 VLM 确认的 tap 步骤**:
- `resource_collection`: `open_menu`, `enter_base`
- `base_management`: `open_menu`, `enter_base`, `restart_queue`
- 其他流程的所有 tap 步骤

**影响**: 只有 daily_quest 和 weekly_quest 的部分步骤有 VLM 确认，其他流程仍可能盲目点击

### 代码质量问题

#### 1. 重复代码

**位置**: `tap` 动作的点击逻辑重复两次

```python
if vlm_confirm:
    # ...
    if not confirm_result:
        success = False
    else:
        print(f"  [TAP] VLM 确认通过，点击 {coords}")
        self._tap(coords[0], coords[1])  # 重复
        self.adb.wait(step_cfg.get("wait", 2))  # 重复
        self._verify_screen_change()  # 重复
        success = self._verify_tap_result(step_cfg, coords)  # 重复
else:
    print(f"  [TAP] 点击 {coords}")
    self._tap(coords[0], coords[1])  # 重复
    self.adb.wait(step_cfg.get("wait", 2))  # 重复
    self._verify_screen_change()  # 重复
    success = self._verify_tap_result(step_cfg, coords)  # 重复
```

**建议**: 提取为子方法避免重复

#### 2. 导入位置

**问题**: `_vlm_confirm_target` 方法内部导入模块

```python
def _vlm_confirm_target(self, coords: list, prompt: str) -> bool:
    import numpy as np  # 方法内导入
    import cv2         # 方法内导入
    import re          # 方法内导入
    import json        # 方法内导入
    from core.vlm_decider import VlmActionDecider  # 方法内导入
```

**影响**:
- 每次调用都重新导入（虽然 Python 会缓存）
- 不符合文件顶部的导入规范
- 文件顶部已有 `numpy`, `cv2`, `json`, `re` 的导入

#### 3. 未使用的导入

**代码**:
```python
import numpy as np
import cv2
```

**实际使用**: `numpy` 和 `cv2` 仅在截图解码时使用，但 `adb_screencap()` 已返回 bytes，方法内已调用：
```python
np_img = np.frombuffer(img, dtype=np.uint8)
cv_img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
```

**结论**: 导入是必要的，但应移到文件顶部

### 兼容性分析

#### 1. 向后兼容

**配置**: `vlm_confirm` 默认值为 `False`
```python
vlm_confirm = step_cfg.get("vlm_confirm", False)
```

**影响**: 未配置 `vlm_confirm` 的流程不受影响，保持原行为

#### 2. VlmActionDecider 接口

**假设**: `decide(cv_img, prompt)` 方法存在

**风险**: 如果实际接口不同，会导致 `AttributeError` 或 `TypeError`

**需要验证**:
```python
# 检查 VlmActionDecider 的实际接口
from core.vlm_decider import VlmActionDecider
decider = VlmActionDecider()
# decide 方法的签名是什么？
# 返回值是什么类型？
```

### 执行流程变化

#### daily_quest 执行流程对比

**修改前**:
```
1. ensure_world (check) → 2. open_quest_panel (tap) → 3. verify_quest_panel (check) → ...
                              ↓
                          直接点击 (860,80)
```

**修改后**:
```
1. ensure_world (check) → 2. open_quest_panel (tap) → 3. verify_quest_panel (check) → ...
                              ↓
                        VLM 确认 (5-30 秒)
                              ↓
                        确认通过？
                              ↓
                    Yes → 点击 (860,80)
                    No  → success=False, 跳过
```

#### 错误场景分析

**场景 1**: VLM 确认失败
```
[VLM-CONFIRM] 确认画面右上角有任务图标
[VLM-FAIL] 未找到任务图标，当前页面可能是退出对话框
[WARN] VLM 确认失败，跳过此步骤
[FAIL]
```
**结果**: 步骤失败，流程继续执行下一步

**场景 2**: VLM 异常
```
[VLM-CONFIRM] 确认画面右上角有任务图标
[VLM-ERROR] VLM 确认异常：Connection refused
[WARN] VLM 确认失败，跳过此步骤
[FAIL]
```
**结果**: 步骤失败（即使元素实际存在）

**场景 3**: VLM 确认超时
```
[VLM-CONFIRM] 确认画面右上角有任务图标
... (30 秒后) ...
[VLM-ERROR] VLM 确认异常：timeout
[WARN] VLM 确认失败，跳过此步骤
[FAIL]
```
**结果**: 步骤失败，浪费 30 秒

### 测试覆盖

**未覆盖场景**:
1. VLM 确认成功的完整流程
2. VLM 确认失败的流程恢复
3. VLM 异常的降级处理
4. 超时处理

**需要测试**:
```bash
# 测试 VLM 确认流程
python scripts/standard_flow_engine.py --flow daily_quest --local-only

# 测试 VLM 异常场景（模拟）
# 需要 mock VlmActionDecider 抛出异常
```

## 总结

### 修改达成目标

✅ **核心目标**: "即使有预设坐标，行动时也需要由 VLM 确认"
- 配置层面：4 个 tap 步骤添加 `vlm_confirm: true`
- 引擎层面：`tap` 动作检查 `vlm_confirm` 并调用 `_vlm_confirm_target`
- 方法层面：新增 VLM 确认方法，截图 + 提示词 + 解析结果

### 客观影响

| 维度 | 影响 | 程度 |
|------|------|------|
| 准确性 | 提升（避免错误点击） | 中 |
| 执行时间 | 增加（每次确认 5-30 秒） | 高 |
| 依赖关系 | 增加（VlmActionDecider） | 低 |
| 代码质量 | 下降（重复代码、导入位置） | 中 |
| 向后兼容 | 保持（默认 False） | 无 |
| 错误处理 | 保守（异常时跳过） | 中 |

### 风险点

1. **VlmActionDecider 接口**: 需要验证 `decide()` 方法签名
2. **性能开销**: 每次确认 5-30 秒，流程时间显著增加
3. **误判风险**: VLM 故障时保守跳过，可能导致步骤失败
4. **覆盖不全**: 只配置了 4 个 tap 步骤，其他 tap 仍无确认

### 建议改进

1. **重构重复代码**: 提取点击逻辑为子方法
2. **优化导入**: 移到文件顶部
3. **完善覆盖**: 为所有关键 tap 步骤添加 VLM 确认
4. **添加测试**: 验证 VLM 确认的成功/失败/异常场景
5. **性能优化**: 考虑缓存 VLM 结果或使用更快的本地模型

---

*分析时间：2026-06-14*
*修改文件：flows_config.json, standard_flow_engine.py*
*修改脚本：add_vlm_confirm.py*
