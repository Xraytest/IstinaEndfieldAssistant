"""触控子系统"""

from .touch_executor import TouchExecutor
from .maafw_touch_adapter import MaaFwTouchExecutor, MaaFwTouchConfig

__all__ = [
    'TouchExecutor',
    'MaaFwTouchExecutor', 'MaaFwTouchConfig'
]
