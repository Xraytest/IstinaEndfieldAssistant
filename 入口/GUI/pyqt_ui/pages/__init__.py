"""
页面组件模块
提供 Material Design 3 风格的 PyQt6 页面组件
"""

from .device_page import DevicePage
from .task_page import TaskPage
from .auth_page import AuthPage
from .settings_page import SettingsPage
from .cloud_page import CloudPage


__all__ = [
    # 页面组件
    'DevicePage',
    'TaskPage',
    'AuthPage',
    'SettingsPage',
    'CloudPage',
]