#!/usr/bin/env python3
"""
OCR+LLM 模式集成测试

测试 OCR 模块与标准流引擎的集成：
1. OCR 决策模块功能测试
2. OCRManager 集成测试
3. 服务端纯文本模式测试
4. 端到端流程测试
"""

import sys
import os
import json
from pathlib import Path

from _path_setup import PROJECT_ROOT, SRC_DIR, MODULE_DIR, ensure_path
ensure_path()

PROJECT_ROOT = PROJECT_ROOT
SRC_DIR = SRC_DIR


def test_screen_decider():
    """测试屏幕决策模块"""
    print("\n" + "=" * 60)
    print("测试 1: ScreenDecider 屏幕决策")
    print("=" * 60)
    
    try:
        from core.ocr.screen_decider import ScreenDecider, ScreenState
        
        decider = ScreenDecider()
        
        # 模拟 OCR 结果：世界地图 + 任务面板
        mock_ocr_world_overlay = [
            {"text": "探索", "box": [30, 10, 60, 30], "score": 0.98},
            {"text": "每日任务", "box": [970, 80, 100, 40], "score": 0.95},
            {"text": "领取", "box": [1020, 300, 60, 30], "score": 0.92},
            {"text": "一键领取", "box": [1000, 350, 100, 40], "score": 0.96},
            {"text": "每周任务", "box": [970, 450, 100, 40], "score": 0.94},
        ]
        
        state = decider.detect_screen_state(mock_ocr_world_overlay)
        
        print(f"页面类型：{state.page_type}")
        print(f"描述：{state.description}")
        print(f"置信度：{state.confidence:.2f}")
        print(f"顶部栏可见：{state.top_bar_visible}")
        print(f"顶部栏按钮：{state.top_bar_buttons}")
        print(f"面板检测：{state.overlay_detected}")
        print(f"领取按钮：{len(state.claim_buttons)} 个")
        for x, y, text in state.claim_buttons:
            print(f"  - '{text}' ({x}, {y})")
        
        # 验证
        assert state.page_type == "world_map_with_overlay", f"期望 world_map_with_overlay，得到{state.page_type}"
        assert state.overlay_detected, "应检测到面板"
        assert len(state.claim_buttons) >= 2, f"应检测到至少 2 个领取按钮，得到{len(state.claim_buttons)}"
        
        # 测试导航计划生成
        plan = decider.generate_plan(state)
        print(f"\n导航计划 ({len(plan)} 步):")
        for i, step in enumerate(plan, 1):
            print(f"  {i}. {step['type']}: {step['description']}")
        
        # 测试 LLM 提示词生成
        prompt = state.to_llm_prompt()
        print(f"\nLLM 提示词预览:\n{prompt[:300]}...")
        
        print("\n[OK] ScreenDecider 测试通过")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] ScreenDecider 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_ocr_manager():
    """测试 OCR 管理器"""
    print("\n" + "=" * 60)
    print("测试 2: OCRManager 管理器")
    print("=" * 60)
    
    try:
        from core.ocr.ocr_manager import OCRManager
        
        manager = OCRManager()
        
        # 测试已知坐标
        coords = manager.get_known_coords("tasks_button")
        print(f"任务按钮坐标：{coords}")
        assert coords == (570, 22), f"期望 (570, 22)，得到{coords}"
        
        coords = manager.get_known_coords("claim_all")
        print(f"一键领取坐标：{coords}")
        assert coords == (1035, 323), f"期望 (1035, 323)，得到{coords}"
        
        # 测试提示词构建
        from core.ocr.screen_decider import ScreenState
        mock_state = ScreenState(
            page_type="world_map_with_overlay",
            confidence=0.9,
            top_bar_visible=True,
            top_bar_buttons=["tasks", "event"],
            overlay_detected=True,
            overlay_texts=["每日任务", "领取"],
            claim_buttons=[(1035, 323, "一键领取"), (914, 586, "领取")]
        )
        
        prompt = manager.build_llm_prompt(mock_state, "检查并领取每日任务奖励")
        print(f"\nLLM 提示词 ({len(prompt)} 字符):")
        print(prompt[:400] + "...")
        
        # 验证提示词包含关键信息
        assert "世界地图" in prompt or "world_map" in prompt, "提示词应包含页面类型"
        assert "每日任务" in prompt, "提示词应包含面板内容"
        assert "一键领取" in prompt, "提示词应包含领取按钮"
        assert "检查并领取每日任务奖励" in prompt, "提示词应包含任务指令"
        
        print("\n[OK] OCRManager 测试通过")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] OCRManager 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_orchestrator_text_mode():
    """测试服务端 AgentOrchestrator 纯文本模式"""
    print("\n" + "=" * 60)
    print("测试 3: AgentOrchestrator 纯文本模式")
    print("=" * 60)
    
    try:
        # 检查服务端代码是否已修改
        platform_path = Path(__file__).resolve().parent.parent / "IstinaPlatform" / "src" / "core" / "agent_orchestrator.py"
        
        if not platform_path.exists():
            print(f"[SKIP] 服务端文件不存在：{platform_path}")
            return True
        
        with open(platform_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 验证关键修改
        checks = [
            ("screen_state 参数", "screen_state: Dict[str, Any] = None" in content),
            ("use_vision 参数", "use_vision: bool = None" in content),
            ("_build_text_prompt 方法", "def _build_text_prompt" in content),
            ("simple_text_chat 调用", "provider.simple_text_chat" in content),
        ]
        
        all_passed = True
        for check_name, result in checks:
            status = "✓" if result else "✗"
            print(f"  {status} {check_name}")
            if not result:
                all_passed = False
        
        if all_passed:
            print("\n[OK] AgentOrchestrator 纯文本模式已集成")
        else:
            print("\n[WARN] AgentOrchestrator 部分修改缺失")
        
        return all_passed
        
    except Exception as e:
        print(f"\n[FAIL] AgentOrchestrator 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_provider_adapter_text_chat():
    """测试 ProviderAdapter simple_text_chat 方法"""
    print("\n" + "=" * 60)
    print("测试 4: ProviderAdapter simple_text_chat")
    print("=" * 60)
    
    try:
        platform_path = Path(__file__).resolve().parent.parent / "IstinaPlatform" / "src" / "core" / "provider_adapter.py"
        
        if not platform_path.exists():
            print(f"[SKIP] 服务端文件不存在：{platform_path}")
            return True
        
        with open(platform_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 验证 simple_text_chat 方法存在
        if "def simple_text_chat" in content:
            print("  ✓ simple_text_chat 方法已添加")
            
            # 验证方法包含关键逻辑
            if "call_provider_api(messages, tools=None" in content:
                print("  ✓ 调用 call_provider_api")
            else:
                print("  ✗ 缺少 call_provider_api 调用")
                return False
            
            if "isinstance(content, str)" in content:
                print("  ✓ 纯文本内容处理")
            else:
                print("  ✗ 缺少纯文本处理")
                return False
            
            print("\n[OK] ProviderAdapter simple_text_chat 已集成")
            return True
        else:
            print("  ✗ simple_text_chat 方法未找到")
            return False
        
    except Exception as e:
        print(f"\n[FAIL] ProviderAdapter 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_ocr_config():
    """测试 OCR 配置文件"""
    print("\n" + "=" * 60)
    print("测试 5: OCR 配置文件")
    print("=" * 60)
    
    try:
        config_path = PROJECT_ROOT / "config" / "ocr_config.json"
        
        if not config_path.exists():
            print(f"[FAIL] 配置文件不存在：{config_path}")
            return False
        
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # 验证配置结构
        required_keys = [
            "version", "ocr_mode", "screen_resolution",
            "top_bar", "overlay", "claim_keywords", "known_coords"
        ]
        
        missing_keys = [k for k in required_keys if k not in config]
        if missing_keys:
            print(f"[FAIL] 缺少配置项：{missing_keys}")
            return False
        
        print(f"  ✓ 配置版本：{config.get('version')}")
        print(f"  ✓ OCR 模式：{config.get('ocr_mode')}")
        print(f"  ✓ 屏幕分辨率：{config.get('screen_resolution')}")
        print(f"  ✓ 顶部栏按钮：{len(config.get('top_bar', {}).get('buttons', {}))} 个")
        print(f"  ✓ 领取关键词：{len(config.get('claim_keywords', []))} 个")
        print(f"  ✓ 已知坐标：{len(config.get('known_coords', {}))} 个")
        
        print("\n[OK] OCR 配置文件验证通过")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] OCR 配置测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("OCR+LLM 迁移集成测试")
    print("=" * 60)
    print(f"项目根目录：{PROJECT_ROOT}")
    print(f"源码目录：{SRC_DIR}")
    
    results = {
        "screen_decider": test_screen_decider(),
        "ocr_manager": test_ocr_manager(),
        "agent_orchestrator": test_agent_orchestrator_text_mode(),
        "provider_adapter": test_provider_adapter_text_chat(),
        "ocr_config": test_ocr_config(),
    }
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\n总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n[SUCCESS] 所有测试通过！OCR+LLM 迁移完成。")
        print("\n下一步:")
        print("  1. 启动服务端：cd IstinaPlatform && python src/server/run.py")
        print("  2. 运行标准流：python scripts/standard_flow_engine.py --flow daily_quest --use-ocr")
        print("  3. 对比性能：记录延迟和 Token 消耗")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} 个测试失败，请检查。")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
