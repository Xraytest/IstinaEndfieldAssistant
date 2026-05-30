"""
IstinaEndfieldAssistant Client GUI - PyQt6 Version
"""
import sys
import os
import json

# Force stdio to be unbuffered for immediate output
sys.stdout.reconfigure(line_buffering=True)

# Add src directory to Python path
# __file__ = src/gui/pyqt6/main.py
# dirname 4 times to get project root, then join with src
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

print("[IMPORT] Importing dependencies...")

# Import business logic modules
from core.logger import init_logger, get_logger, LogCategory, LogLevel
from device.adb_manager import ADBDeviceManager
from screenshot.screen_capture import ScreenCapture
from device.touch import TouchManager, TouchDeviceType
from core.communication.communicator import ClientCommunicator
from core.cloud.managers.auth_manager import AuthManager
from core.cloud.managers.device_manager import DeviceManager

print("[IMPORT] All dependencies imported successfully")


def load_config(config_file: str) -> dict:
    """Load configuration file"""
    config_path = os.path.join(project_root, config_file)
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Return default configuration
        return {
            "server": {"host": "127.0.0.1", "port": 9999},
            "adb": {"path": "3rd-party/adb/adb.exe", "timeout": 10},
            "git": {"path": "3rd-party/git/bin/git.exe"},
            "screen": {"use_original_resolution": True},
            "touch": {
                "maa_style": {
                    "enabled": True,
                    "press_duration_ms": 50,
                    "press_jitter_px": 2,
                    "swipe_delay_min_ms": 100,
                    "swipe_delay_max_ms": 300,
                    "use_normalized_coords": True
                },
                "fail_on_error": True
            },
            "communication": {"password": "default_password"},
            "client": {
                "client_name": "IEA_Client",
                "registered": False
            },
            "inference": {
                "mode": "auto",
                "local_inference_enabled": False,
                "local": {"enabled": False, "model_name": "", "gpu_layers": -1}
            },
            "first_run": {
                "local_inference_prompt_shown": False
            },
            "security": {
                "enable_safe_press": True,
                "enable_jitter": True
            },
            "rendering": {
                "hardware_acceleration": True,
                "vsync": True,
                "animation_enabled": True
            }
        }


def main():
    """Main function - Start PyQt6 GUI application"""
    
    print("=" * 70)
    print("ISTINA ENDFIELD ASSISTANT - STARTING")
    print("=" * 70)
    
    # Initialize logging system
    print("[MAIN] Initializing logger...")
    init_logger()
    logger = get_logger()
    
    logger.info(LogCategory.MAIN, "IstinaEndfieldAssistant client started (Agent Mode)")
    
    # Load configuration
    print("[MAIN] Loading configuration...")
    config = load_config("config/client_config.json")
    logger.debug(LogCategory.MAIN, "Configuration file loaded successfully")
    print(f"[MAIN] Config loaded OK")
    
    try:
        # Initialize core function modules
        
        # ADB path
        adb_path = os.path.join(project_root, config['adb']['path'])
        
        if not os.path.exists(adb_path):
            logger.error(LogCategory.MAIN, f"ADB executable does not exist: {adb_path}")
            print(f"[Error] ADB executable does not exist: {adb_path}")
            return 1
        
        print("[MAIN] Initializing core modules (ADB, ScreenCapture, TouchManager)...")
        logger.debug(LogCategory.MAIN, "Initializing ADB device manager", adb_path=adb_path)
        adb_manager = ADBDeviceManager(
            adb_path=adb_path,
            timeout=config['adb']['timeout']
        )
        
        logger.debug(LogCategory.MAIN, "Initializing screen capture module")
        screen_capture = ScreenCapture(adb_manager=adb_manager)
        
        logger.debug(LogCategory.MAIN, "Initializing touch manager")
        touch_executor = TouchManager()

        logger.debug(LogCategory.MAIN, "Linking screen capture to MAA touch manager")
        screen_capture.set_touch_manager(touch_executor)

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
        
        logger.info(LogCategory.MAIN, "All components initialized successfully")
        print("[MAIN] All core modules initialized successfully")
        
    except Exception as e:
        logger.exception(LogCategory.MAIN, "Manager initialization failed", exc_info=True)
        print(f"[Error] Manager initialization failed: {e}")
        return 1
    
    # Start PyQt6 application
    from gui.pyqt6.app_main import run_application
    
    print(f"\n[MAIN] Starting PyQt6 application...")
    
    try:
        from core.cloud.agent_executor import AgentExecutor
        
        logger.debug(LogCategory.MAIN, "Initializing Agent Executor")
        agent_executor = AgentExecutor(
            communicator=communicator,
            screen_capture=screen_capture,
            touch_executor=touch_executor,
            config=config
        )
        
        print(f"[MAIN] Calling run_application() - window should appear now...")
        exit_code = run_application(
            auth_manager=auth_manager,
            device_manager=device_manager,
            agent_executor=agent_executor,
            communicator=communicator,
            screen_capture=screen_capture,
            touch_executor=touch_executor,
            config=config
        )
        
        logger.info(LogCategory.MAIN, f"Application exited, exit code: {exit_code}")
        print(f"[MAIN] Application exited with code: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.exception(LogCategory.MAIN, "Application startup failed", exc_info=True)
        print(f"[Error] Application startup failed: {e}")
        return 1


if __name__ == "__main__":
    import json
    sys.exit(main())