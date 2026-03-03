"""
测试 MAA DLL 是否能正常加载和工作
"""
import sys
import os

# 添加当前目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 添加 maa_integration 到路径
maa_integration_path = os.path.join(current_dir, 'maa_integration')
if maa_integration_path not in sys.path:
    sys.path.insert(0, maa_integration_path)

try:
    from maa_integration.asst import Asst
    print("MAA DLL imported successfully")
    
    # 测试加载 DLL
    maa_path = maa_integration_path
    if Asst.load(maa_path):
        print("MAA DLL loaded successfully")
        
        # 创建实例
        maa = Asst()
        print("MAA instance created successfully")
        
        # 获取版本
        version = maa.get_version()
        print(f"MAA version: {version}")
        
        # 清理
        del maa
        print("Test completed successfully")
    else:
        print("MAA DLL load failed")
        
except ImportError as e:
    print(f"MAA DLL import failed: {e}")
except Exception as e:
    print(f"MAA DLL test failed: {e}")