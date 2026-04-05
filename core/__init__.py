"""核心功能模块 - 基础设施层"""

from .logger import init_logger, get_logger, LogCategory, LogLevel
from .adb_manager import ADBDeviceManager
from .screen_capture import ScreenCapture
from .touch import (
    TouchManager, TouchDeviceType,
    TouchExecutor, MaaFwTouchExecutor, MaaFwTouchConfig,
    MaaFwWin32Executor, MaaFwWin32Config, TouchConfig
)
from .communication import ClientCommunicator

__all__ = [
    'init_logger', 'get_logger', 'LogCategory', 'LogLevel',
    'ADBDeviceManager', 'ScreenCapture',
    # 触控系统
    'TouchManager', 'TouchDeviceType',
    'TouchExecutor', 'MaaFwTouchExecutor', 'MaaFwTouchConfig',
    'MaaFwWin32Executor', 'MaaFwWin32Config', 'TouchConfig',
    'ClientCommunicator'
]
