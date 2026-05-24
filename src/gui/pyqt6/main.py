"""
IstinaEndfieldAssistant Client GUI - PyQt6 Version
"""
import sys
import os
import time
import json

# Add src directory to Python path
istina_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src_dir = os.path.join(istina_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import business logic modules
from core.logger import init_logger, get_logger, LogCategory, LogLevel
from device.adb_manager import ADBDeviceManager
from screenshot.screen_capture import ScreenCapture
from device.touch import TouchManager, TouchDeviceType
from device.touch.maafw_touch_adapter import MaaFwTouchExecutor, MaaFwTouchConfig
from device.touch.maafw_win32_adapter import MaaFwWin32Executor, MaaFwWin32Config
from core.cloud.task_manager import TaskManager
from core.communication.communicator import ClientCommunicator
from core.cloud.managers.auth_manager import AuthManager
from core.cloud.managers.device_manager import DeviceManager
from core.cloud.managers.execution_manager import ExecutionManager
from core.cloud.managers.task_queue_manager import TaskQueueManager


def load_config(config_file: str) -> dict:
    """Load configuration file"""
    config_path = os.path.join(istina_root, config_file)
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Return default configuration
        return {
            "server": {"host": "127.0.0.1", "port": 9999},
            "adb": {"path": "3rd-party/adb/adb.exe", "timeout": 10},
            "git": {"path": "3rd-party/git/bin/git.exe"},
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
    """Main function - Start PyQt6 GUI application"""
    # Initialize logging system
    init_logger()
    logger = get_logger()
    
    logger.info(LogCategory.MAIN, "IstinaEndfieldAssistant client started (PyQt6 version)")
    
    # Load configuration
    config = load_config("config/client_config.json")
    logger.debug(LogCategory.MAIN, "Configuration file loaded successfully")
    
    try:
        # Initialize core function modules
        
        # ADB path
        adb_path = os.path.join(istina_root, config['adb']['path'])
        
        if not os.path.exists(adb_path):
            logger.error(LogCategory.MAIN, f"ADB executable does not exist: {adb_path}")
            print(f"[Error] ADB executable does not exist: {adb_path}")
            return 1
        
        logger.debug(LogCategory.MAIN, "Initializing ADB device manager", adb_path=adb_path)
        adb_manager = ADBDeviceManager(
            adb_path=adb_path,
            timeout=config['adb']['timeout']
        )
        
        logger.debug(LogCategory.MAIN, "Initializing screen capture module")
        screen_capture = ScreenCapture(adb_manager=adb_manager)
        
        logger.debug(LogCategory.MAIN, "Initializing touch manager")
        touch_executor = TouchManager()
        
        logger.debug(LogCategory.MAIN, "Initializing task management module")
        task_manager = TaskManager(
            config_dir=os.path.join(istina_root, "config"),
            data_dir=os.path.join(istina_root, "data")
        )
        
        logger.debug(LogCategory.MAIN, "Initializing communication module")
        communicator = ClientCommunicator(
            host=config['server']['host'],
            port=config['server']['port'],
            password=config.get('communication', {}).get('password', 'default_password'),
            timeout=300
        )
        
        # Initialize business logic components
        logger.debug(LogCategory.MAIN, "Initializing authentication management module")
        auth_manager = AuthManager(communicator, config)
        
        logger.debug(LogCategory.MAIN, "Initializing device management module")
        device_manager = DeviceManager(adb_manager, config)
        
        logger.debug(LogCategory.MAIN, "Initializing task queue management module")
        task_queue_manager = TaskQueueManager(task_manager)
        
        logger.debug(LogCategory.MAIN, "Initializing execution management module")
        execution_manager = ExecutionManager(
            device_manager,
            screen_capture,
            touch_executor,
            task_queue_manager,
            communicator,
            auth_manager,
            config
        )
        
        logger.info(LogCategory.MAIN, "All components initialized successfully")
        
    except Exception as e:
        logger.exception(LogCategory.MAIN, "Manager initialization failed", exc_info=True)
        print(f"[Error] Manager initialization failed: {e}")
        return 1
    
    # Start PyQt6 application
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
        
        logger.info(LogCategory.MAIN, f"Application exited, exit code: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.exception(LogCategory.MAIN, "Application startup failed", exc_info=True)
        print(f"[Error] Application startup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
