"""触控模块 - MaaFramework触控集成"""

from .touch_manager import TouchManager, TouchDeviceType
from .maafw_touch_adapter import MaaFwTouchExecutor, MaaFwTouchConfig
from .maafw_win32_adapter import MaaFwWin32Executor, MaaFwWin32Config

__all__ = [
    'TouchManager',
    'TouchDeviceType',
    'MaaFwTouchExecutor',
    'MaaFwTouchConfig',
    'MaaFwWin32Executor',
    'MaaFwWin32Config'
]