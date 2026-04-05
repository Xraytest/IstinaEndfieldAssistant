# -*- coding: utf-8 -*-
"""
测试 ClientLogger.error() 方法
验证 logger.error() 方法是否正常工作
"""
import sys
import os

# 设置标准输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from core.logger import init_logger, get_logger, LogCategory


def test_logger_error_method():
    """测试 logger.error() 方法是否存在且可正常调用"""
    print("\n" + "="*60)
    print("测试: ClientLogger.error() 方法")
    print("="*60)
    
    # 初始化日志
    init_logger("config/client_config.json")
    logger = get_logger()
    
    # 检查 error 方法是否存在
    assert hasattr(logger, 'error'), "ClientLogger 应该有 error 方法"
    print("✓ ClientLogger.error() 方法存在")
    
    # 测试调用 error 方法（无异常信息）
    try:
        logger.error(LogCategory.MAIN, "测试错误消息1")
        print("✓ logger.error() 无异常信息调用成功")
    except Exception as e:
        print(f"✗ logger.error() 无异常信息调用失败: {e}")
        return False
    
    # 测试调用 error 方法（带额外参数）
    try:
        logger.error(LogCategory.MAIN, "测试错误消息2", param1="value1", param2="value2")
        print("✓ logger.error() 带额外参数调用成功")
    except Exception as e:
        print(f"✗ logger.error() 带额外参数调用失败: {e}")
        return False
    
    # 测试调用 error 方法（带异常信息）
    try:
        logger.error(LogCategory.MAIN, "测试错误消息3", exc_info=True)
        print("✓ logger.error() 带异常信息调用成功")
    except Exception as e:
        print(f"✗ logger.error() 带异常信息调用失败: {e}")
        return False
    
    # 测试在 touch_adapter.py 中的使用场景
    try:
        logger.error(LogCategory.MAIN, "MAA DLL 加载失败")
        print("✓ touch_adapter.py 场景调用成功")
    except Exception as e:
        print(f"✗ touch_adapter.py 场景调用失败: {e}")
        return False
    
    print("\n" + "="*60)
    print("所有测试通过!")
    print("="*60)
    return True


if __name__ == "__main__":
    success = test_logger_error_method()
    sys.exit(0 if success else 1)