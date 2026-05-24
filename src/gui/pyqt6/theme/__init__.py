"""
主题模块
提供 Material Design 3 主题系统和动画管理
"""

from .theme_manager import ThemeManager
from .animation_manager import (
    AnimationManager,
    AnimationConfig,
    AnimatedProgressBar,
    NotificationAnimator,
    fade_in_widget,
    fade_out_widget,
    slide_in_widget,
    slide_out_widget,
    get_animation_manager,
)

__all__ = [
    'ThemeManager',
    'AnimationManager',
    'AnimationConfig',
    'AnimatedProgressBar',
    'NotificationAnimator',
    'fade_in_widget',
    'fade_out_widget',
    'slide_in_widget',
    'slide_out_widget',
    'get_animation_manager',
]
