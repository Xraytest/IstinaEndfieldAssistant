"""触控子系统 - 统一使用MaaFramework库"""

from .maafw_touch_adapter import MaaFwTouchExecutor, MaaFwTouchConfig
from .maafw_win32_adapter import MaaFwWin32Executor, MaaFwWin32Config

__all__ = [
    'MaaFwTouchExecutor', 'MaaFwTouchConfig',
    'MaaFwWin32Executor', 'MaaFwWin32Config'
]
