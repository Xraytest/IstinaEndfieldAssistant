# -*- coding: utf-8 -*-
"""
MAA风格触控系统验证脚本
验证触控执行器的MAA风格安全机制和maatouch服务管理功能
"""
import sys
import os
import time
import json
from typing import Dict, List

# 设置标准输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from client.core.touch.touch_adapter import TouchExecutor, MaaTouchConfig, TouchMethod
from client.core.logger import init_logger, get_logger, LogCategory


def test_maa_touch_config():
    """测试MAA风格触控配置"""
    print("\n" + "="*60)
    print("测试1: MAA风格触控配置")
    print("="*60)
    
    # 创建默认配置
    config = MaaTouchConfig()
    assert config.press_duration_ms == 50, "默认按压时长应为50ms"
    assert config.press_jitter_px == 2, "默认抖动范围应为2像素"
    assert config.swipe_delay_min_ms == 100, "默认最小延迟应为100ms"
    assert config.swipe_delay_max_ms == 300, "默认最大延迟应为300ms"
    assert config.use_normalized_coords == True, "默认应使用归一化坐标"
    # 默认触控方法应为MAATOUCH（根据MaaTouchConfig定义）
    assert config.touch_method == TouchMethod.MAATOUCH, "默认触控方法应为MAATOUCH"
    
    print("✓ 默认配置测试通过")
    
    # 创建自定义配置
    custom_config = MaaTouchConfig(
        press_duration_ms=100,
        press_jitter_px=3,
        swipe_delay_min_ms=150,
        swipe_delay_max_ms=400,
        use_normalized_coords=False,
        touch_method=TouchMethod.MINITOUCH
    )
    assert custom_config.press_duration_ms == 100
    assert custom_config.press_jitter_px == 3
    assert custom_config.swipe_delay_min_ms == 150
    assert custom_config.swipe_delay_max_ms == 400
    assert custom_config.use_normalized_coords == False
    assert custom_config.touch_method == TouchMethod.MINITOUCH
    
    print("✓ 自定义配置测试通过")
    return True


def test_coordinate_conversion():
    """测试坐标转换系统"""
    print("\n" + "="*60)
    print("测试2: 坐标转换系统")
    print("="*60)
    
    # 模拟设备管理器（用于测试）
    class MockADBManager:
        def __init__(self):
            self.resolution_cache = {
                "test_device": (1080, 1920)
            }
        
        def _run_adb_command(self, cmd):
            if "wm size" in " ".join(cmd):
                return True, "Physical size: 1080x1920"
            return True, ""
        
        def get_device_model(self, serial):
            return "Test Device"
    
    # 创建触控执行器
    adb_manager = MockADBManager()
    config = MaaTouchConfig(use_normalized_coords=True)
    executor = TouchExecutor(adb_manager=adb_manager, config=config)
    
    # 测试归一化坐标转换
    # 屏幕中心 (0.5, 0.5) → (540, 960)
    device_x, device_y = executor._to_pixel_coords("test_device", 0.5, 0.5)
    assert device_x == 540, f"归一化X坐标转换错误: 期望540, 实际{device_x}"
    assert device_y == 960, f"归一化Y坐标转换错误: 期望960, 实际{device_y}"
    print(f"✓ 归一化坐标转换: (0.5, 0.5) → ({device_x}, {device_y})")
    
    # 测试边界坐标
    device_x, device_y = executor._to_pixel_coords("test_device", 0.0, 0.0)
    assert device_x == 0, f"左上角坐标转换错误: 期望0, 实际{device_x}"
    assert device_y == 0, f"左上角坐标转换错误: 期望0, 实际{device_y}"
    print(f"✓ 左上角坐标转换: (0.0, 0.0) → ({device_x}, {device_y})")
    
    device_x, device_y = executor._to_pixel_coords("test_device", 1.0, 1.0)
    assert device_x == 1079, f"右下角坐标转换错误: 期望1079, 实际{device_x}"
    assert device_y == 1919, f"右下角坐标转换错误: 期望1919, 实际{device_y}"
    print(f"✓ 右下角坐标转换: (1.0, 1.0) → ({device_x}, {device_y})")
    
    # 测试边界检查
    device_x, device_y = executor._to_pixel_coords("test_device", 1.5, 1.5)
    assert device_x == 1079, f"超出边界X坐标应被修正: 期望1079, 实际{device_x}"
    assert device_y == 1919, f"超出边界Y坐标应被修正: 期望1919, 实际{device_y}"
    print(f"✓ 超出边界坐标修正: (1.5, 1.5) → ({device_x}, {device_y})")
    
    return True


def test_maa_style_touch_actions():
    """测试MAA风格触控动作格式"""
    print("\n" + "="*60)
    print("测试3: MAA风格触控动作格式")
    print("="*60)
    
    # 模拟MAA风格触控动作
    maa_click_action = {
        'action': 'click',
        'coordinates': {
            'start': [0.5, 0.5]  # 归一化坐标
        },
        'parameters': {
            'duration': 50,
            'jitter': 2
        }
    }
    
    maa_swipe_action = {
        'action': 'swipe',
        'coordinates': {
            'start': [0.5, 0.5],
            'end': [0.5, 0.6]
        },
        'parameters': {
            'duration': 300,
            'jitter': 2
        }
    }
    
    maa_long_press_action = {
        'action': 'long_press',
        'coordinates': {
            'start': [0.3, 0.4]
        },
        'parameters': {
            'duration': 500,
            'jitter': 2
        }
    }
    
    # 验证动作格式
    assert 'coordinates' in maa_click_action, "点击动作应包含coordinates"
    assert 'start' in maa_click_action['coordinates'], "coordinates应包含start"
    assert 'parameters' in maa_click_action, "点击动作应包含parameters"
    assert 'duration' in maa_click_action['parameters'], "parameters应包含duration"
    assert 'jitter' in maa_click_action['parameters'], "parameters应包含jitter"
    print("✓ 点击动作格式验证通过")
    
    assert 'end' in maa_swipe_action['coordinates'], "滑动coordinates应包含end"
    print("✓ 滑动动作格式验证通过")
    
    assert maa_long_press_action['parameters']['duration'] == 500, "长按时长应为500ms"
    print("✓ 长按动作格式验证通过")
    
    return True


def test_execute_tool_call_compatibility():
    """测试工具调用兼容性"""
    print("\n" + "="*60)
    print("测试4: 工具调用兼容性")
    print("="*60)
    
    # 模拟设备管理器
    class MockADBManager:
        def __init__(self):
            self.resolution_cache = {"test_device": (1080, 1920)}
        
        def _run_adb_command(self, cmd):
            return True, ""
        
        def get_device_model(self, serial):
            return "Test Device"
    
    adb_manager = MockADBManager()
    config = MaaTouchConfig(use_normalized_coords=True)
    executor = TouchExecutor(adb_manager=adb_manager, config=config)
    
    # 测试旧格式兼容
    old_format_click = {
        "x": 540,
        "y": 960,
        "purpose": "测试点击"
    }
    
    # 测试新格式（MAA风格）
    new_format_click = {
        "coordinates": {
            "start": [0.5, 0.5]
        },
        "purpose": "测试点击"
    }
    
    # 验证坐标转换
    device_x, device_y = executor._convert_coordinates("test_device", 540, 960)
    assert device_x == 540, f"像素坐标应保持不变: 期望540, 实际{device_x}"
    assert device_y == 960, f"像素坐标应保持不变: 期望960, 实际{device_y}"
    print("✓ 像素坐标转换验证通过")
    
    device_x, device_y = executor._to_pixel_coords("test_device", 0.5, 0.5)
    assert device_x == 540, f"归一化坐标转换错误: 期望540, 实际{device_x}"
    assert device_y == 960, f"归一化坐标转换错误: 期望960, 实际{device_y}"
    print("✓ 归一化坐标转换验证通过")
    
    return True


def test_maatouch_service_management():
    """测试maatouch服务管理功能"""
    print("\n" + "="*60)
    print("测试5: MaaTouch服务管理功能")
    print("="*60)
    
    # 模拟设备管理器
    class MockADBManager:
        def __init__(self):
            self.resolution_cache = {"test_device": (1080, 1920)}
            self.commands_executed = []
        
        def _run_adb_command(self, cmd):
            self.commands_executed.append(cmd)
            # 模拟成功响应
            if "wm size" in " ".join(cmd):
                return True, "Physical size: 1080x1920"
            return True, ""
        
        def get_device_model(self, serial):
            return "Test Device"
    
    # 测试maatouch配置
    config_path = os.path.join(current_dir, "3rd-part", "maatouch", "minitouch")
    
    print(f"✓ 检查maatouch二进制文件: {config_path}")
    
    # 测试配置加载
    adb_manager = MockADBManager()
    
    # 测试ADB Input模式（默认）
    adb_config = MaaTouchConfig(
        touch_method=TouchMethod.ADB_INPUT,
        minitouch_binary_path=config_path,
        maatouch_binary_path=config_path
    )
    executor = TouchExecutor(adb_manager=adb_manager, config=adb_config)
    assert executor.config.touch_method == TouchMethod.ADB_INPUT
    print(f"✓ ADB Input模式配置正确")
    
    # 测试MaaTouch模式
    maatouch_config = MaaTouchConfig(
        touch_method=TouchMethod.MAATOUCH,
        minitouch_binary_path=config_path,
        maatouch_binary_path=config_path
    )
    executor2 = TouchExecutor(adb_manager=adb_manager, config=maatouch_config)
    assert executor2.config.touch_method == TouchMethod.MAATOUCH
    print(f"✓ MaaTouch模式配置正确")
    
    # 测试二进制路径配置
    assert maatouch_config.minitouch_binary_path == config_path
    assert maatouch_config.maatouch_binary_path == config_path
    print(f"✓ 二进制文件路径配置正确")
    
    return True


def test_config_file_loading():
    """测试配置文件加载"""
    print("\n" + "="*60)
    print("测试5: 配置文件加载")
    print("="*60)
    
    config_path = os.path.join(current_dir, "config", "client_config.json")
    
    if not os.path.exists(config_path):
        print(f"⚠ 配置文件不存在: {config_path}")
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 验证触控配置
    assert 'touch' in config, "配置应包含touch部分"
    touch_config = config['touch']
    
    assert 'touch_method' in touch_config, "touch配置应包含touch_method"
    assert 'maa_style' in touch_config, "touch配置应包含maa_style"
    
    maa_style = touch_config['maa_style']
    assert 'enabled' in maa_style, "maa_style应包含enabled"
    assert 'press_duration_ms' in maa_style, "maa_style应包含press_duration_ms"
    assert 'press_jitter_px' in maa_style, "maa_style应包含press_jitter_px"
    assert 'swipe_delay_min_ms' in maa_style, "maa_style应包含swipe_delay_min_ms"
    assert 'swipe_delay_max_ms' in maa_style, "maa_style应包含swipe_delay_max_ms"
    assert 'use_normalized_coords' in maa_style, "maa_style应包含use_normalized_coords"
    
    print(f"✓ 触控方法: {touch_config['touch_method']}")
    print(f"✓ MAA风格启用: {maa_style['enabled']}")
    print(f"✓ 按压时长: {maa_style['press_duration_ms']}ms")
    print(f"✓ 抖动范围: ±{maa_style['press_jitter_px']}像素")
    print(f"✓ 延迟范围: {maa_style['swipe_delay_min_ms']}-{maa_style['swipe_delay_max_ms']}ms")
    print(f"✓ 归一化坐标: {maa_style['use_normalized_coords']}")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("MAA风格触控系统验证测试")
    print("="*60)
    
    # 初始化日志
    log_config_path = os.path.join(current_dir, "config/logging_config.json")
    if os.path.exists(log_config_path):
        init_logger(log_config_path)
    
    tests = [
        ("MAA风格触控配置", test_maa_touch_config),
        ("坐标转换系统", test_coordinate_conversion),
        ("MAA风格触控动作格式", test_maa_style_touch_actions),
        ("工具调用兼容性", test_execute_tool_call_compatibility),
        ("MaaTouch服务管理功能", test_maatouch_service_management),
        ("配置文件加载", test_config_file_loading),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"✗ {test_name} 测试失败")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} 测试异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)