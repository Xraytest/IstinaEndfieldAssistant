"""
日志系统测试脚本
"""
import os
import sys
import time
import json
from datetime import datetime

# 设置控制台输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from logger import init_logger, get_logger, LogCategory, LogLevel, ClientLogger


def test_logger_initialization():
    """测试日志系统初始化"""
    print("测试日志系统初始化...")
    
    # 创建测试配置
    test_config = {
        "enabled": True,
        "log_dir": "test_logs",
        "retention_days": 3,
        "global_level": "DEBUG",
        "handlers": {
            "file": {
                "enabled": True,
                "max_size": 1024,
                "encoding": "utf-8"
            },
            "console": {
                "enabled": True,
                "level": "DEBUG"
            },
            "gui": {
                "enabled": False,
                "level": "INFO",
                "max_lines": 1000
            }
        },
        "performance": {
            "enabled": True,
            "log_slow_operations": True,
            "slow_threshold_ms": 100
        }
    }
    
    # 保存测试配置
    test_config_path = os.path.join(current_dir, "test_logging_config.json")
    with open(test_config_path, "w", encoding="utf-8") as f:
        json.dump(test_config, f, indent=2)
    
    # 初始化日志系统
    logger = init_logger(test_config_path)
    
    assert logger is not None, "日志系统初始化失败"
    assert logger._config["enabled"] == True, "日志系统未启用"
    assert logger._config["log_dir"] == "test_logs", "日志目录配置错误"
    
    print("[PASS] 日志系统初始化测试通过")
    
    # 清理测试配置
    if os.path.exists(test_config_path):
        os.remove(test_config_path)
    
    return logger


def test_log_levels():
    """测试所有日志级别"""
    print("\n测试日志级别...")
    logger = get_logger()
    
    # 测试所有级别
    logger.debug(LogCategory.MAIN, "DEBUG级别日志测试")
    logger.info(LogCategory.MAIN, "INFO级别日志测试")
    logger.warning(LogCategory.MAIN, "WARNING级别日志测试")
    logger.exception(LogCategory.MAIN, "EXCEPTION级别日志测试")
    logger.critical(LogCategory.MAIN, "CRITICAL级别日志测试")
    
    print("[PASS] 日志级别测试通过")


def test_log_categories():
    """测试所有日志分类"""
    print("\n测试日志分类...")
    logger = get_logger()
    
    # 测试所有分类
    logger.info(LogCategory.MAIN, "MAIN分类测试")
    logger.info(LogCategory.ADB, "ADB分类测试")
    logger.info(LogCategory.COMMUNICATION, "COMMUNICATION分类测试")
    logger.info(LogCategory.EXECUTION, "EXECUTION分类测试")
    logger.info(LogCategory.AUTHENTICATION, "AUTHENTICATION分类测试")
    logger.info(LogCategory.GUI, "GUI分类测试")
    logger.info(LogCategory.EXCEPTION, "EXCEPTION分类测试")
    logger.info(LogCategory.PERFORMANCE, "PERFORMANCE分类测试")
    
    print("[PASS] 日志分类测试通过")


def test_device_context():
    """测试设备上下文"""
    print("\n测试设备上下文...")
    logger = get_logger()
    
    # 设置设备上下文
    logger.set_device_context("test_device_001")
    logger.info(LogCategory.ADB, "带设备上下文的日志")
    
    # 清除设备上下文
    logger.clear_device_context()
    logger.info(LogCategory.ADB, "清除设备上下文后的日志")
    
    print("[PASS] 设备上下文测试通过")


def test_performance_logging():
    """测试性能日志"""
    print("\n测试性能日志...")
    logger = get_logger()
    
    # 记录快速操作
    start = time.time()
    time.sleep(0.01)
    logger.log_performance("fast_operation", (time.time() - start) * 1000)
    
    # 记录慢速操作（超过阈值）
    start = time.time()
    time.sleep(0.15)
    logger.log_performance("slow_operation", (time.time() - start) * 1000)
    
    # 获取性能统计
    stats = logger.get_performance_statistics("fast_operation")
    assert stats is not None, "性能统计获取失败"
    assert stats["count"] >= 1, "性能统计数量错误"
    
    print("[PASS] 性能日志测试通过")


def test_log_files():
    """测试日志文件创建"""
    print("\n测试日志文件创建...")
    logger = get_logger()
    
    # 写入一些日志
    for i in range(10):
        logger.info(LogCategory.MAIN, f"测试日志 {i}")
    
    # 检查日志文件是否创建
    log_dir = logger._config["log_dir"]
    assert os.path.exists(log_dir), "日志目录不存在"
    
    # 检查是否有日志文件
    log_files = [f for f in os.listdir(log_dir) if f.endswith(".log")]
    assert len(log_files) > 0, "没有创建日志文件"
    
    print(f"[PASS] 日志文件创建测试通过，创建了 {len(log_files)} 个日志文件")
    
    # 显示日志文件列表
    for log_file in log_files:
        file_path = os.path.join(log_dir, log_file)
        file_size = os.path.getsize(file_path)
        print(f"  - {log_file} ({file_size} bytes)")


def test_log_cleanup():
    """测试日志清理"""
    print("\n测试日志清理...")
    logger = get_logger()
    
    # 清理旧日志
    removed = logger.clean_old_logs()
    print(f"[PASS] 日志清理测试通过，清理了 {len(removed)} 个旧日志文件")


def test_log_format():
    """测试日志格式"""
    print("\n测试日志格式...")
    logger = get_logger()
    
    # 测试带额外信息的日志
    logger.info(LogCategory.MAIN, "带额外信息的日志", 
                extra_key1="value1", extra_key2=123, extra_key3=True)
    
    print("[PASS] 日志格式测试通过")


def test_exception_logging():
    """测试异常日志"""
    print("\n测试异常日志...")
    logger = get_logger()
    
    try:
        # 故意触发异常
        raise ValueError("测试异常")
    except Exception as e:
        logger.exception(LogCategory.EXCEPTION, "捕获到异常", exc_info=True)
    
    print("[PASS] 异常日志测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("日志系统功能测试")
    print("=" * 50)
    
    try:
        # 测试初始化
        logger = test_logger_initialization()
        
        # 测试各种功能
        test_log_levels()
        test_log_categories()
        test_device_context()
        test_performance_logging()
        test_log_files()
        test_log_cleanup()
        test_log_format()
        test_exception_logging()
        
        print("\n" + "=" * 50)
        print("[SUCCESS] 所有测试通过！")
        print("=" * 50)
        
        # 显示测试日志目录
        log_dir = logger._config["log_dir"]
        print(f"\n测试日志保存在: {os.path.abspath(log_dir)}")
        
        # 自动清理测试日志
        import shutil
        if os.path.exists(log_dir):
            shutil.rmtree(log_dir)
            print(f"已自动清理测试日志目录: {log_dir}")
        
        return True
        
    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)