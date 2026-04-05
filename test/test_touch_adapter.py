"""
测试触控适配器
"""
import sys
import os

from core.touch.touch_adapter import TouchExecutor, MaaTouchConfig, TouchMethod

class MockADBManager:
    def __init__(self):
        self.adb_path = "adb"
    
    def _run_adb_command(self, cmd):
        print(f"ADB command: {cmd}")
        return True, ""

def test_touch_adapter():
    """测试触控适配器"""
    print("创建触控适配器...")
    
    # 创建配置
    config = MaaTouchConfig(
        touch_method=TouchMethod.MAATOUCH,
        use_normalized_coords=True
    )
    
    # 创建 ADB 管理器
    adb_manager = MockADBManager()
    
    # 创建触控执行器
    executor = TouchExecutor(adb_manager=adb_manager, config=config)
    
    print("触控适配器创建成功")
    
    # 测试点击
    print("测试点击...")
    try:
        success = executor.safe_press("127.0.0.1:5555", 500, 500, "测试点击")
        print(f"点击结果: {success}")
    except Exception as e:
        print(f"点击异常: {e}")
    
    # 测试滑动
    print("测试滑动...")
    try:
        success = executor.safe_swipe("127.0.0.1:5555", 100, 100, 800, 800, 300, "测试滑动")
        print(f"滑动结果: {success}")
    except Exception as e:
        print(f"滑动异常: {e}")
    
    print("测试完成")

if __name__ == "__main__":
    test_touch_adapter()