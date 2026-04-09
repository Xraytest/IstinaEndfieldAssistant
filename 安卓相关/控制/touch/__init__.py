"""触控子系统 - 使用MaaFramework库管理触控

可选触控方式：
- 安卓设备: MaaTouch (通过MaaFramework AdbController)
- PC前台: Win32Controller (通过MaaFramework Win32Controller)

推荐使用TouchManager统一管理触控操作。
"""

from .touch_manager import TouchManager, TouchDeviceType
from .maafw_touch_adapter import MaaFwTouchExecutor, MaaFwTouchConfig
from .maafw_win32_adapter import MaaFwWin32Executor, MaaFwWin32Config

# 兼容别名
TouchExecutor = MaaFwTouchExecutor
TouchConfig = MaaFwTouchConfig

__all__ = [
    # 统一触控管理器
    'TouchManager', 'TouchDeviceType',
    # Android触控
    'MaaFwTouchExecutor', 'MaaFwTouchConfig',
    # PC触控
    'MaaFwWin32Executor', 'MaaFwWin32Config',
    # 兼容别名
    'TouchExecutor', 'TouchConfig'
]
