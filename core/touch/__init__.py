"""触控子系统"""

from .touch_executor import TouchExecutor
from .touch_adapter import TouchAdapter
from .maafw_touch_adapter import MaaFwTouchExecutor, MaaFwTouchConfig

__all__ = [
    'TouchExecutor', 'TouchAdapter',
    'MaaFwTouchExecutor', 'MaaFwTouchConfig'
]
