#!/usr/bin/env python3
"""
智能元素检测 + LLM 决策 测试脚本

演示流程：
1. 截图
2. 检测 UI 元素（OCR + 模板匹配）
3. 构建 LLM 上下文
4. LLM 根据元素坐标自主决策
5. 执行操作
"""

import sys
import json
from pathlib import Path
from typing import List, Dict

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from core.adb_utils import adb_screencap
from core.smart_element_detector import SmartElementDetector, Element
from core.vlm_client import VLMClient


def test_element_detection():
    """测试元素检测功能"""
    print("=" * 60)
    print("智能元素检测 + LLM 决策 测试")
    print("=" * 60)
    
    # 1. 初始化检测器
    detector = SmartElementDetector()
    
    # 2. 截图
    print("\n[1] 截取屏幕...")
    img_bytes = adb_screencap(serial="192.168.1.12:16512")
    if img_bytes is None:
        print("  [ERROR] 截图失败")
        return
    
    import cv2
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    print(f"  [OK] 截图成功，尺寸：{img.shape[1]}x{img.shape[0]}")
    
    # 3. 检测元素
    print("\n[2] 检测 UI 元素...")
    elements = detector.detect_all_elements(img)
    print(f"  检测到 {len(elements)} 个元素:")
    
    for i, elem in enumerate(elements[:10]):  # 只显示前 10 个
        print(f"    {i+1}. [{elem.element_type}] {elem.name} @ ({elem.x}, {elem.y}) "
              f"置信度={elem.confidence:.2f}")
    
    if len(elements) > 10:
        print(f"    ... 还有 {len(elements) - 10} 个元素")
    
    # 4. 查找特定元素
    print("\n[3] 查找特定元素...")
    
    # 查找任务相关元素
    quest_elem = detector.find_element_by_name(elements, ["任务", "quest", "委托"])
    if quest_elem:
        print(f"  ✓ 找到任务元素：{quest_elem.name} @ {quest_elem.center}")
    else:
        print(f"  ✗ 未找到任务元素，使用备选坐标")
        fallback_coords = detector.get_element_or_fallback(elements, "quest_icon")
        print(f"    备选坐标：{fallback_coords}")
    
    # 查找领取按钮
    claim_elem = detector.find_element_by_name(elements, ["领取", "claim", "收取"])
    if claim_elem:
        print(f"  ✓ 找到领取按钮：{claim_elem.name} @ {claim_elem.center}")
    else:
        print(f"  ✗ 未找到领取按钮")
    
    # 5. 构建 LLM 上下文
    print("\n[4] 构建 LLM 上下文...")
    prompt = detector.build_llm_context(elements, "打开每日任务面板")
    print(f"  提示词长度：{len(prompt)} 字符")
    
    # 6. LLM 决策
    print("\n[5] LLM 决策...")
    # 这里应该调用 LLM API
    # response = call_llm(prompt)
    # decision = json.loads(response)
    
    # 模拟 LLM 返回
    mock_decision = {
        "action": "tap",
        "target_element": quest_elem.name if quest_elem else "quest_icon",
        "coords": list(quest_elem.center) if quest_elem else [860, 80],
        "reason": "检测到任务元素，点击打开任务面板"
    }
    
    print(f"  决策结果:")
    print(f"    动作：{mock_decision['action']}")
    print(f"    目标：{mock_decision['target_element']}")
    print(f"    坐标：{mock_decision['coords']}")
    print(f"    原因：{mock_decision['reason']}")
    
    # 7. 执行操作（可选）
    execute = input("\n[6] 是否执行点击操作？(y/n): ")
    if execute.lower() == 'y':
        from core.adb_utils import adb_tap
        x, y = mock_decision['coords']
        success = adb_tap(x, y, serial="192.168.1.12:16512")
        print(f"  {'[OK]' if success else '[FAIL]'} 点击 ({x}, {y})")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


def compare_old_vs_new():
    """对比旧方案（硬编码坐标）和新方案（元素检测）"""
    print("\n" + "=" * 60)
    print("方案对比")
    print("=" * 60)
    
    print("""
旧方案（硬编码坐标）:
  ✗ 坐标固定，UI 变化后失效
  ✗ 需要手动验证和更新坐标
  ✗ 无法适应不同分辨率
  ✗ 无法处理动态 UI 布局

新方案（元素检测 + LLM 决策）:
  ✓ OCR 识别文字元素及其坐标
  ✓ 模板匹配识别图标元素及其坐标  
  ✓ LLM 根据元素自主决策点击位置
  ✓ 3CUI 坐标作为降级备选
  ✓ 适应 UI 变化和不同分辨率
  
示例流程:
  1. 截图 → 2. 元素检测 → 3. 构建上下文 → 4. LLM 决策 → 5. 执行操作
  
元素检测结果示例:
  [text] "每日任务" @ (120, 180) 置信度=0.95
  [text] "领取" @ (800, 900) 置信度=0.90
  [icon] "quest_icon" @ (860, 80) 置信度=0.85
  
LLM 决策示例:
  {
    "action": "tap",
    "target_element": "每日任务",
    "coords": [120, 180],  // 使用检测到的坐标，而非硬编码
    "reason": "检测到'每日任务'文字元素，点击打开任务面板"
  }
    """)


if __name__ == "__main__":
    import numpy as np
    
    test_element_detection()
    compare_old_vs_new()
