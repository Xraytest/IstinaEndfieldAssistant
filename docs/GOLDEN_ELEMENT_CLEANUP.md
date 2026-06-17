# 金色元素检测代码清理报告

> 清理时间：2026-06-17  
> 清理原因：金色元素检测已被证明不可靠，项目已转向基于 YOLO + OCR + VLM 的多模态分析方案

---

## 清理范围

### ✅ 已完成清理的核心文件

| 文件 | 清理内容 | 状态 |
|------|---------|------|
| `scripts/standard_flow_engine.py` | 删除 `_detect_golden()` 方法、更新相关方法签名 | ✅ 完成 |
| `src/core/screen_analysis/advanced_analyzer.py` | 删除 `ColorFeatures` 中的 golden_* 字段 | ✅ 完成 |
| `src/core/page_analyzer.py` | 删除退出对话框检测中的金色元素验证 | ✅ 完成 |

### 📝 保留的测试/诊断脚本（含金色元素代码）

以下脚本为历史测试工具，保留原状供参考：

- `scripts/capture_diagnosis.py` - 诊断工具
- `scripts/calibrate_coords.py` - 坐标校准工具
- `scripts/detect_ui_elements.py` - UI 元素检测工具
- `scripts/find_menu_buttons.py` - 菜单按钮查找工具
- `scripts/diagnose_adb_tap.py` - ADB 点击诊断工具
- 等其他 20+ 个测试脚本

---

## 清理详情

### 1. standard_flow_engine.py

**删除的内容：**
- `_detect_golden()` 方法（~30 行 OpenCV HSV 颜色检测代码）
- `analyze()` 方法中的金色元素检测调用
- `result["golden_elements"]` 字段
- `"golden"` source 标记

**更新的方法签名：**
```python
# 之前
def _vlm_classify(self, img, golden_elements: list, yolo_objects: list, ocr_text: str) -> str:
def _classify_by_keywords(self, ocr_text: str, golden_elements: list, yolo_objects: list) -> str:

# 之后
def _vlm_classify(self, img, yolo_objects: list, ocr_text: str) -> str:
def _classify_by_keywords(self, ocr_text: str, yolo_objects: list) -> str:
```

**删除的逻辑：**
- `golden_summary` 变量及其在 VLM prompt 中的使用
- `gold_count = len(golden_elements)` 变量
- 基于金色元素数量的页面类型判断（exit_dialog, world, quest_panel）

### 2. advanced_analyzer.py

**删除的字段（ColorFeatures 数据类）：**
```python
# 已删除
golden_count: int = 0           # 金色元素数量
golden_ratio: float = 0.0       # 金色元素总面积占比
golden_entropy: float = 0.0     # 金色元素空间分布熵
```

**删除的配置（PAGE_PROFILES）：**
```python
# 已删除所有页面类型中的 "golden_count" 范围定义
"golden_count": (18, 22),  # 金色元素范围
```

**删除的检测逻辑：**
- HSV 颜色空间金色元素检测（~30 行）
- 金色元素数量和面积计算
- 金色元素空间分布熵计算
- 基于金色元素数量的页面评分逻辑

### 3. page_analyzer.py

**删除的内容：**
- 退出对话框检测中的"金色轮廓"回退逻辑
- `min_contours: 1` 配置（至少 1 个金色元素的要求）

---

## 决策器输入元素变化

### 清理前（14 个元素）

```
1. 截图 (Screenshot)
2. 用户指令 (User Instruction)
3. YOLO 检测结果 ← 保留
4. 金色元素检测 ← 已删除
5. OCR 文本 ← 保留
6. 空间布局特征 ← 保留
7. 颜色特征（HSV 直方图等）← 保留（不含金色）
8. 纹理特征 ← 保留
9. 模板匹配 ← 保留
10. 流程配置 ← 保留
11. 设备信息 ← 保留
12. 会话历史 ← 保留
13. 系统提示词 ← 保留
14. 推理参数 ← 保留
```

### 清理后（13 个元素）

```
1. 截图 (Screenshot)
2. 用户指令 (User Instruction)
3. YOLO 检测结果
4. OCR 文本
5. 空间布局特征
6. 颜色特征（HSV 直方图等，不含金色元素）
7. 纹理特征
8. 模板匹配
9. 流程配置
10. 设备信息
11. 会话历史
12. 系统提示词
13. 推理参数
```

---

## 影响分析

### 正面影响
- ✅ 减少不可靠的页面类型判断逻辑
- ✅ 降低代码复杂度（删除 ~100 行代码）
- ✅ 统一使用 YOLO + OCR + VLM 的多模态方案
- ✅ 减少 OpenCV 颜色阈值调优的维护成本

### 潜在风险
- ⚠️ 部分测试脚本可能无法运行（需手动更新或废弃）
- ⚠️ 历史依赖金色元素计数的页面特征采集需要重新进行

---

## 后续建议

1. **更新文档**：更新 QWEN.md 中的决策器输入元素说明
2. **清理测试脚本**：批量删除或更新 scripts/ 目录下的测试工具
3. **重新采集页面特征**：使用新的特征集（不含金色元素）重新采集 PageProfiles
4. **验证功能**：运行标准流引擎验证页面检测功能正常

---

## 验证命令

```bash
# 检查核心文件是否还有 golden 引用
grep -r "golden" IstinaEndfieldAssistant/src/core/ --include="*.py"
grep -r "detect_golden" IstinaEndfieldAssistant/scripts/standard_flow_engine.py

# 运行标准流验证
cd IstinaEndfieldAssistant
python scripts/standard_flow_engine.py --flow daily_quest --local-only
```

---

*报告生成：2026-06-17*
