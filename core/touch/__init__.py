"""触控子系统"""

from .touch_executor import TouchExecutor
from .touch_adapter import TouchExecutor as TouchAdapter  # 别名兼容
from .touch_adapter import MaaTouchConfig
from .maafw_touch_adapter import MaaFwTouchExecutor, MaaFwTouchConfig

__all__ = [
    'TouchExecutor', 'TouchAdapter', 'MaaTouchConfig',
    'MaaFwTouchExecutor', 'MaaFwTouchConfig'
]
