# VLM 起末判定机制实现总结

生成时间：2026-06-14

## Stop Hook 条件

**"修正流程，一个行为的起末由 vlm 判定"**

## 实现概述

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `config/standard_flows/flows_config.json` | 添加 `vlm_verify` 和 `vlm_verify_prompt` 配置 |
| `scripts/standard_flow_engine.py` | 修改 tap 动作处理逻辑，添加 `_vlm_verify_result` 方法 |
| `src/core/vlm_decider.py` | 添加 `decide(img, prompt)` 简化方法 |

### 核心设计

**行为起始判定** (VLM 确认):
```python
vlm_confirm = step_cfg.get("vlm_confirm", False)
vlm_prompt = step_cfg.get("vlm_prompt", "...")
# 调用 _vlm_confirm_target() 确认目标元素可见
```

**行为结束判定** (VLM 验证):
```python
vlm_verify = step_cfg.get("vlm_verify", False)
vlm_verify_prompt = step_cfg.get("vlm_verify_prompt", "...")
# 调用 _vlm_verify_result() 验证操作结果
```

### 配置示例

```json
{
  "id": "open_quest_panel",
  "action": "tap",
  "coords": "{{nav_coords.quest_icon}}",
  "vlm_confirm": true,
  "vlm_prompt": "确认画面右上角有任务图标 (黄色感叹号或任务按钮)",
  "vlm_verify": true,
  "vlm_verify_prompt": "验证任务面板已打开（画面中有任务列表或任务相关 UI 元素）"
}
```

### 执行流程

```
[VLM-START] 确认画面右上角有任务图标
[VLM-OK] 检测到黄色感叹号任务按钮
[TAP] 点击 [860, 80]
[VLM-END] 验证任务面板已打开
[VLM-VERIFIED] 任务列表已显示：检测到任务列表 UI 元素
[OK] VLM 验证通过
```

## 已配置流程

### 覆盖范围 (10 个关键导航 tap 步骤)

| 流程 | 步骤 ID | 坐标 | 起始确认 | 结束验证 |
|------|--------|------|---------|---------|
| daily_quest | open_quest_panel | quest_icon | ✅ 任务图标 | ✅ 面板打开 |
| weekly_quest | open_quest_panel | quest_icon | ✅ 任务图标 | ✅ 面板打开 |
| weekly_quest | switch_to_weekly | weekly_tab | ✅ 周常标签 | ✅ 切换成功 |
| resource_collection | open_menu | menu_icon | ✅ 菜单图标 | ✅ 菜单打开 |
| base_management | open_menu | menu_icon | ✅ 菜单图标 | ✅ 菜单打开 |
| character_ascension | open_menu | menu_icon | ✅ 菜单图标 | ✅ 菜单打开 |
| weapon_crafting | open_menu | menu_icon | ✅ 菜单图标 | ✅ 菜单打开 |
| event_rewards | open_events | event_icon | ✅ 活动图标 | ✅ 面板打开 |
| delivery_mission | open_menu | menu_icon | ✅ 菜单图标 | ✅ 菜单打开 |
| dungeon_grinding | open_map | city_map | ✅ 地图按钮 | ✅ 地图打开 |

### 统计

- **总步骤数**: 10 个 tap 步骤
- **覆盖流程**: 9 个流程 (auto_move 无导航 tap)
- **VLM 调用**: 每次执行需要 20 次 VLM 调用 (10 起始 +10 结束)

## 影响分析

### 正面影响

1. **行为完整性**: 每个行为由 VLM 完整判定起始和结束
2. **错误检测**: 语义级验证，避免"点击成功但结果错误"
3. **可追溯性**: 完整 VLM 判定链日志

### 负面影响

1. **性能开销**: 每个步骤 2 次 VLM 调用，+30-180 秒/流程
2. **依赖增加**: VLM 服务故障时所有步骤失败
3. **代码重复**: 点击逻辑在多个分支中重复

### 风险点

1. **状态不一致**: 起始通过但验证失败时，已执行操作但未达预期
2. **无恢复逻辑**: 验证失败后无自动重试
3. **误判累积**: 两次 VLM 调用的误判概率累积

## 后续优化建议

1. **添加恢复逻辑**: VLM 验证失败时自动重试或回退
2. **重构重复代码**: 提取点击 + 验证为子方法
3. **性能优化**: 使用更快的本地模型或 OpenCV+VLM 混合验证
4. **完善测试**: 覆盖所有 VLM 判定场景
5. **配置策略**: 关键步骤 VLM 双判定，非关键步骤 OpenCV

## 验证命令

```bash
# 配置检查
python scripts/test_all_flows.py

# 执行测试（需要 VLM 服务）
python scripts/standard_flow_engine.py --flow daily_quest --local-only
```

## 相关文档

- `docs/VLM_START_END_IMPACT_ANALYSIS.md`: 详细影响分析
- `docs/STANDARD_FLOW_VERIFICATION.md`: 标准流执行验证报告
- `docs/STANDARD_FLOW_MAAEND_DESIGN.md`: MaaEnd 设计模式完善报告

---

*修改时间：2026-06-14*
*Stop hook 条件："修正流程，一个行为的起末由 vlm 判定"*
