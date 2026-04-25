"""GUI入口模块

提供两种GUI实现:
- PyQt6版本 (推荐): pyqt_ui模块
- Tkinter版本 (旧版): ui模块
"""

# 默认导出PyQt6版本
from .pyqt_ui import (
    PyQt6Application,
    MainWindow,
    ThemeManager,
    run_application,
)

__all__ = [
    'PyQt6Application',
    'MainWindow',
    'ThemeManager',
    'run_application',
]