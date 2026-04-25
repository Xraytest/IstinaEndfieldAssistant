"""
IstinaEndfieldAssistant 客户端GUI - PyQt6版本
"""
import sys
import os
import time
import json

# 添加安卓相关目录到Python路径
istina_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
安卓相关_dir = os.path.join(istina_root, "安卓相关")
入口_dir = os.path.join(istina_root, "入口")
if 安卓相关_dir not in sys.path:
    sys.path.insert(0, 安卓相关_dir)
if 入口_dir not in sys.path:
    sys.path.insert(0, 入口_dir)

# 导入PyQt6 UI模块
try:
    from GUI.pyqt_ui import run_application, PyQt6Application
except ImportError:
    # 尝试相对导入
    from pyqt_ui import run_application, PyQt6Application

# 导入业务逻辑模块
from core.logger import init_logger, get_logger, LogCategory, LogLevel
from 控制.adb_manager import ADBDeviceManager
from 图像传递.screen_capture import ScreenCapture
from 控制.touch import TouchManager, TouchDeviceType
from 控制.touch.maafw_touch_adapter import MaaFwTouchExecutor, MaaFwTouchConfig
from 控制.touch.maafw_win32_adapter import MaaFwWin32Executor, MaaFwWin32Config
from core.cloud.task_manager import TaskManager
from core.communication.communicator import ClientCommunicator
from core.cloud.managers.auth_manager import AuthManager
from core.cloud.managers.device_manager import DeviceManager
from core.cloud.managers.execution_manager import ExecutionManager
from core.cloud.managers.task_queue_manager import TaskQueueManager


def load_config(config_file: str) -> dict:
    """加载配置文件"""
    config_path = os.path.join(istina_root, config_file)
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # 返回默认配置
        return {
            "server": {"host": "127.0.0.1", "port": 9999},
            "adb": {"path": "3rd-part/ADB/adb.exe", "timeout": 10},
            "git": {"path": "3rd-part/Git/bin/git.exe"},
            "screen": {"quality": 80, "max_size": 1024},
            "touch": {
                "touch_method": "maatouch",
                "maa_style": {
                    "enabled": True,
                    "press_duration_ms": 50,
                    "swipe_delay_min_ms": 100,
                    "swipe_delay_max_ms": 300
                },
                "swipe_duration_ms": 300,
                "long_press_duration_ms": 500
            },
            "communication": {"password": "default_password"}
        }


def main():
    """主函数 - 启动PyQt6 GUI应用"""
    # 初始化日志系统
    init_logger()
    logger = get_logger()
    
    logger.info(LogCategory.MAIN, "IstinaEndfieldAssistant 客户端启动 (PyQt6版本)")
    
    # 加载配置
    config = load_config("config/client_config.json")
    logger.debug(LogCategory.MAIN, "配置文件加载完成")
    
    try:
        # 初始化核心功能模块
        
        # ADB路径
        adb_path = os.path.join(istina_root, config['adb']['path'])
        
        if not os.path.exists(adb_path):
            logger.exception(LogCategory.MAIN, "ADB可执行文件不存在", adb_path=adb_path)
            print(f"[错误] ADB可执行文件不存在: {adb_path}")
            return 1
        
        logger.debug(LogCategory.MAIN, "初始化ADB设备管理器", adb_path=adb_path)
        adb_manager = ADBDeviceManager(
            adb_path=adb_path,
            timeout=config['adb']['timeout']
        )
        
        logger.debug(LogCategory.MAIN, "初始化屏幕捕获模块")
        screen_capture = ScreenCapture(adb_manager=adb_manager)
        
        logger.debug(LogCategory.MAIN, "初始化触控管理器")
        touch_executor = TouchManager()
        
        logger.debug(LogCategory.MAIN, "初始化任务管理模块")
        task_manager = TaskManager(
            config_dir=os.path.join(istina_root, "入口", "config"),
            data_dir=os.path.join(istina_root, "入口", "data")
        )
        
        logger.debug(LogCategory.MAIN, "初始化通信模块")
        communicator = ClientCommunicator(
            host=config['server']['host'],
            port=config['server']['port'],
            password=config.get('communication', {}).get('password', 'default_password'),
            timeout=300
        )
        
        # 初始化业务逻辑组件
        logger.debug(LogCategory.MAIN, "初始化认证管理模块")
        auth_manager = AuthManager(communicator, config)
        
        logger.debug(LogCategory.MAIN, "初始化设备管理模块")
        device_manager = DeviceManager(adb_manager, config)
        
        logger.debug(LogCategory.MAIN, "初始化任务队列管理模块")
        task_queue_manager = TaskQueueManager(task_manager)
        
        logger.debug(LogCategory.MAIN, "初始化执行管理模块")
        execution_manager = ExecutionManager(
            device_manager,
            screen_capture,
            touch_executor,
            task_queue_manager,
            communicator,
            auth_manager,
            config
        )
        
        logger.info(LogCategory.MAIN, "所有组件初始化完成")
        
    except Exception as e:
        logger.exception(LogCategory.MAIN, "管理器初始化失败", exc_info=True)
        print(f"[错误] 管理器初始化失败: {e}")
        return 1
    
    # 启动PyQt6应用
    try:
        exit_code = run_application(
            auth_manager=auth_manager,
            device_manager=device_manager,
            execution_manager=execution_manager,
            task_queue_manager=task_queue_manager,
            communicator=communicator,
            screen_capture=screen_capture,
            config=config
        )
        
        logger.info(LogCategory.MAIN, f"应用退出，退出码: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.exception(LogCategory.MAIN, "应用启动失败", exc_info=True)
        print(f"[错误] 应用启动失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())