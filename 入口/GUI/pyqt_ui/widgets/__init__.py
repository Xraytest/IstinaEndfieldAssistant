"""
自定义控件模块
提供 Material Design 3 风格的自定义 PyQt6 控件
"""

from .base_widgets import (
    BaseButton,
    PrimaryButton,
    SecondaryButton,
    TextButton,
    DangerButton,
    CardWidget,
    ElevatedCardWidget,
    OutlinedCardWidget,
    NavigationButton,
    HorizontalSeparator,
)

from .device_preview import (
    DevicePreviewWidget,
)

from .task_list import (
    TaskListItem,
    DragDropTaskList,
    TaskListWidget,
)

from .log_display import (
    LogDisplayWidget,
    SimpleLogDisplay,
)

from .status_indicator import (
    StatusIndicatorWidget,
    ConnectionStatusIndicator,
    DualStatusIndicator,
)


__all__ = [
    # 基础按钮
    'BaseButton',
    'PrimaryButton',
    'SecondaryButton',
    'TextButton',
    'DangerButton',
    'NavigationButton',
    'HorizontalSeparator',
    # 卡片容器
    'CardWidget',
    'ElevatedCardWidget',
    'OutlinedCardWidget',
    # 设备预览
    'DevicePreviewWidget',
    # 任务列表
    'TaskListItem',
    'DragDropTaskList',
    'TaskListWidget',
    # 日志显示
    'LogDisplayWidget',
    'SimpleLogDisplay',
    # 状态指示器
    'StatusIndicatorWidget',
    'ConnectionStatusIndicator',
    'DualStatusIndicator',
]