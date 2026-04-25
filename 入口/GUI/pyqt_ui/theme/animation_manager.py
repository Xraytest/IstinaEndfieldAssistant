"""
动画管理器 - 提供PyQt6动画效果和过渡动画

功能:
- 页面切换动画（淡入淡出、滑动）
- 按钮悬停效果
- 开关切换动画
- 进度条动画
- 通知提示动画
- 可配置的动画开关
"""

from typing import Optional, Callable, Union
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect, QApplication
from PyQt6.QtCore import (
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QSequentialAnimationGroup, pyqtSignal, QObject, Qt, QTimer,
    QPoint, QRect
)
from PyQt6.QtGui import QColor


class AnimationConfig:
    """动画配置类"""
    
    def __init__(self):
        self.enabled = True
        self.duration_fast = 150
        self.duration_normal = 250
        self.duration_slow = 400
        self.easing_curve = QEasingCurve.Type.OutCubic
        self.fade_enabled = True
        self.slide_enabled = True
        self.scale_enabled = True
        self.hover_enabled = True


class AnimationManager(QObject):
    """
    动画管理器 - 单例模式
    
    管理所有UI动画效果，支持全局启用/禁用
    """
    
    _instance: Optional['AnimationManager'] = None
    
    def __new__(cls) -> 'AnimationManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        super().__init__()
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True
        self._config = AnimationConfig()
        self._active_animations: list = []
    
    @classmethod
    def get_instance(cls) -> 'AnimationManager':
        """获取动画管理器单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    # === 配置管理 ===
    
    def is_enabled(self) -> bool:
        """检查动画是否启用"""
        return self._config.enabled
    
    def set_enabled(self, enabled: bool) -> None:
        """设置动画启用状态"""
        self._config.enabled = enabled
    
    def get_config(self) -> AnimationConfig:
        """获取动画配置"""
        return self._config
    
    def update_config(self, **kwargs) -> None:
        """更新动画配置"""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
    
    # === 基础动画方法 ===
    
    def fade_in(
        self,
        widget: QWidget,
        duration: Optional[int] = None,
        callback: Optional[Callable] = None
    ) -> QPropertyAnimation:
        """
        淡入动画
        
        Args:
            widget: 目标控件
            duration: 动画时长（毫秒）
            callback: 动画完成回调
        """
        if not self._config.enabled or not self._config.fade_enabled:
            widget.setVisible(True)
            if callback:
                callback()
            return None
        
        # 创建透明度效果
        opacity_effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(opacity_effect)
        opacity_effect.setOpacity(0.0)
        widget.setVisible(True)
        
        # 创建动画
        anim = QPropertyAnimation(opacity_effect, b"opacity")
        anim.setDuration(duration or self._config.duration_normal)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(self._config.easing_curve)
        
        if callback:
            anim.finished.connect(callback)
        
        self._active_animations.append(anim)
        anim.finished.connect(lambda: self._remove_animation(anim))
        anim.start()
        
        return anim
    
    def fade_out(
        self,
        widget: QWidget,
        duration: Optional[int] = None,
        callback: Optional[Callable] = None,
        hide_after: bool = True
    ) -> QPropertyAnimation:
        """
        淡出动画
        
        Args:
            widget: 目标控件
            duration: 动画时长（毫秒）
            callback: 动画完成回调
            hide_after: 动画完成后是否隐藏控件
        """
        if not self._config.enabled or not self._config.fade_enabled:
            if hide_after:
                widget.setVisible(False)
            if callback:
                callback()
            return None
        
        opacity_effect = widget.graphicsEffect()
        if not isinstance(opacity_effect, QGraphicsOpacityEffect):
            opacity_effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(opacity_effect)
        
        anim = QPropertyAnimation(opacity_effect, b"opacity")
        anim.setDuration(duration or self._config.duration_normal)
        anim.setStartValue(opacity_effect.opacity())
        anim.setEndValue(0.0)
        anim.setEasingCurve(self._config.easing_curve)
        
        def on_finished():
            if hide_after:
                widget.setVisible(False)
            if callback:
                callback()
        
        anim.finished.connect(on_finished)
        self._active_animations.append(anim)
        anim.finished.connect(lambda: self._remove_animation(anim))
        anim.start()
        
        return anim
    
    def slide_in(
        self,
        widget: QWidget,
        direction: Qt.Edge = Qt.Edge.LeftEdge,
        duration: Optional[int] = None,
        callback: Optional[Callable] = None
    ) -> QPropertyAnimation:
        """
        滑入动画
        
        Args:
            widget: 目标控件
            direction: 滑入方向
            duration: 动画时长（毫秒）
            callback: 动画完成回调
        """
        if not self._config.enabled or not self._config.slide_enabled:
            widget.setVisible(True)
            if callback:
                callback()
            return None
        
        # 获取父控件尺寸
        parent = widget.parentWidget()
        if not parent:
            return None
        
        widget_width = widget.width()
        widget_height = widget.height()
        
        # 计算起始位置
        start_pos = widget.pos()
        end_pos = widget.pos()
        
        if direction == Qt.Edge.LeftEdge:
            start_pos.setX(-widget_width)
        elif direction == Qt.Edge.RightEdge:
            start_pos.setX(parent.width())
        elif direction == Qt.Edge.TopEdge:
            start_pos.setY(-widget_height)
        elif direction == Qt.Edge.BottomEdge:
            start_pos.setY(parent.height())
        
        widget.move(start_pos)
        widget.setVisible(True)
        
        # 创建位置动画
        anim = QPropertyAnimation(widget, b"pos")
        anim.setDuration(duration or self._config.duration_normal)
        anim.setStartValue(start_pos)
        anim.setEndValue(end_pos)
        anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
        if callback:
            anim.finished.connect(callback)
        
        self._active_animations.append(anim)
        anim.finished.connect(lambda: self._remove_animation(anim))
        anim.start()
        
        return anim
    
    def slide_out(
        self,
        widget: QWidget,
        direction: Qt.Edge = Qt.Edge.LeftEdge,
        duration: Optional[int] = None,
        callback: Optional[Callable] = None,
        hide_after: bool = True
    ) -> QPropertyAnimation:
        """
        滑出动画
        
        Args:
            widget: 目标控件
            direction: 滑出方向
            duration: 动画时长（毫秒）
            callback: 动画完成回调
            hide_after: 动画完成后是否隐藏控件
        """
        if not self._config.enabled or not self._config.slide_enabled:
            if hide_after:
                widget.setVisible(False)
            if callback:
                callback()
            return None
        
        parent = widget.parentWidget()
        if not parent:
            return None
        
        widget_width = widget.width()
        widget_height = widget.height()
        
        start_pos = widget.pos()
        end_pos = widget.pos()
        
        if direction == Qt.Edge.LeftEdge:
            end_pos.setX(-widget_width)
        elif direction == Qt.Edge.RightEdge:
            end_pos.setX(parent.width())
        elif direction == Qt.Edge.TopEdge:
            end_pos.setY(-widget_height)
        elif direction == Qt.Edge.BottomEdge:
            end_pos.setY(parent.height())
        
        anim = QPropertyAnimation(widget, b"pos")
        anim.setDuration(duration or self._config.duration_normal)
        anim.setStartValue(start_pos)
        anim.setEndValue(end_pos)
        anim.setEasingCurve(self._config.easing_curve)
        
        def on_finished():
            if hide_after:
                widget.setVisible(False)
            if callback:
                callback()
        
        anim.finished.connect(on_finished)
        self._active_animations.append(anim)
        anim.finished.connect(lambda: self._remove_animation(anim))
        anim.start()
        
        return anim
    
    def page_transition(
        self,
        old_widget: QWidget,
        new_widget: QWidget,
        direction: Qt.Edge = Qt.Edge.RightEdge,
        duration: Optional[int] = None
    ) -> QParallelAnimationGroup:
        """
        页面切换动画
        
        Args:
            old_widget: 当前页面
            new_widget: 新页面
            direction: 切换方向
            duration: 动画时长（毫秒）
        """
        if not self._config.enabled:
            old_widget.setVisible(False)
            new_widget.setVisible(True)
            return None
        
        duration = duration or self._config.duration_slow
        
        # 创建动画组
        group = QParallelAnimationGroup()
        
        # 旧页面滑出
        old_anim = self.slide_out(old_widget, direction, duration, hide_after=True)
        if old_anim:
            group.addAnimation(old_anim)
        
        # 新页面滑入（从相反方向）
        opposite_direction = {
            Qt.Edge.LeftEdge: Qt.Edge.RightEdge,
            Qt.Edge.RightEdge: Qt.Edge.LeftEdge,
            Qt.Edge.TopEdge: Qt.Edge.BottomEdge,
            Qt.Edge.BottomEdge: Qt.Edge.TopEdge
        }.get(direction, Qt.Edge.LeftEdge)
        
        new_anim = self.slide_in(new_widget, opposite_direction, duration)
        if new_anim:
            group.addAnimation(new_anim)
        
        self._active_animations.append(group)
        group.finished.connect(lambda: self._remove_animation(group))
        group.start()
        
        return group
    
    def pulse(
        self,
        widget: QWidget,
        duration: Optional[int] = None,
        callback: Optional[Callable] = None
    ) -> QSequentialAnimationGroup:
        """
        脉冲动画（缩放效果）
        
        Args:
            widget: 目标控件
            duration: 动画时长（毫秒）
            callback: 动画完成回调
        """
        if not self._config.enabled or not self._config.scale_enabled:
            if callback:
                callback()
            return None
        
        duration = duration or self._config.duration_fast
        
        group = QSequentialAnimationGroup()
        
        # 放大
        anim_up = QPropertyAnimation(widget, b"minimumWidth")
        anim_up.setDuration(duration // 2)
        anim_up.setStartValue(widget.width())
        anim_up.setEndValue(int(widget.width() * 1.05))
        anim_up.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # 恢复
        anim_down = QPropertyAnimation(widget, b"minimumWidth")
        anim_down.setDuration(duration // 2)
        anim_down.setStartValue(int(widget.width() * 1.05))
        anim_down.setEndValue(widget.width())
        anim_down.setEasingCurve(QEasingCurve.Type.InQuad)
        
        group.addAnimation(anim_up)
        group.addAnimation(anim_down)
        
        if callback:
            group.finished.connect(callback)
        
        self._active_animations.append(group)
        group.finished.connect(lambda: self._remove_animation(group))
        group.start()
        
        return group
    
    def shake(
        self,
        widget: QWidget,
        duration: Optional[int] = None,
        intensity: int = 10
    ) -> QSequentialAnimationGroup:
        """
        抖动动画（用于错误提示）
        
        Args:
            widget: 目标控件
            duration: 动画时长（毫秒）
            intensity: 抖动幅度
        """
        if not self._config.enabled:
            return None
        
        duration = duration or self._config.duration_normal
        original_pos = widget.pos()
        
        group = QSequentialAnimationGroup()
        
        # 左右抖动
        for i in range(4):
            offset = intensity if i % 2 == 0 else -intensity
            anim = QPropertyAnimation(widget, b"pos")
            anim.setDuration(duration // 8)
            anim.setStartValue(widget.pos())
            anim.setEndValue(original_pos + QPoint(offset, 0))
            group.addAnimation(anim)
        
        # 回到原位
        anim_final = QPropertyAnimation(widget, b"pos")
        anim_final.setDuration(duration // 8)
        anim_final.setStartValue(widget.pos())
        anim_final.setEndValue(original_pos)
        group.addAnimation(anim_final)
        
        self._active_animations.append(group)
        group.finished.connect(lambda: self._remove_animation(group))
        group.start()
        
        return group
    
    def _remove_animation(self, animation) -> None:
        """从活动动画列表中移除"""
        if animation in self._active_animations:
            self._active_animations.remove(animation)
    
    def stop_all(self) -> None:
        """停止所有动画"""
        for anim in self._active_animations[:]:
            anim.stop()
        self._active_animations.clear()


class AnimatedButtonMixin:
    """
    动画按钮混入类
    
    为按钮添加悬停和点击动画效果
    """
    
    def __init__(self):
        self._anim_manager = AnimationManager.get_instance()
        self._original_geometry = None
        self._hover_scale = 1.02
    
    def setup_animations(self, button):
        """设置按钮动画"""
        if not self._anim_manager.is_enabled():
            return
        
        # 保存原始尺寸
        self._original_geometry = button.geometry()
        
        # 安装事件过滤器
        button.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """事件过滤器 - 处理悬停效果"""
        if not self._anim_manager.is_enabled():
            return False
        
        from PyQt6.QtCore import QEvent
        
        if event.type() == QEvent.Type.HoverEnter:
            self._on_hover_enter(obj)
        elif event.type() == QEvent.Type.HoverLeave:
            self._on_hover_leave(obj)
        
        return False
    
    def _on_hover_enter(self, button):
        """悬停进入效果"""
        if not self._anim_manager._config.hover_enabled:
            return
        
        # 创建缩放动画
        anim = QPropertyAnimation(button, b"geometry")
        anim.setDuration(self._anim_manager._config.duration_fast)
        
        original = button.geometry()
        new_width = int(original.width() * self._hover_scale)
        new_height = int(original.height() * self._hover_scale)
        new_x = original.x() - (new_width - original.width()) // 2
        new_y = original.y() - (new_height - original.height()) // 2
        
        anim.setStartValue(original)
        anim.setEndValue(QRect(new_x, new_y, new_width, new_height))
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim.start()
    
    def _on_hover_leave(self, button):
        """悬停离开效果"""
        if not self._anim_manager._config.hover_enabled:
            return
        
        if self._original_geometry:
            anim = QPropertyAnimation(button, b"geometry")
            anim.setDuration(self._anim_manager._config.duration_fast)
            anim.setStartValue(button.geometry())
            anim.setEndValue(self._original_geometry)
            anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            anim.start()


class AnimatedProgressBar:
    """
    动画进度条
    
    为进度条添加平滑的动画过渡
    """
    
    def __init__(self, progress_bar):
        self._progress_bar = progress_bar
        self._anim_manager = AnimationManager.get_instance()
        self._current_animation: Optional[QPropertyAnimation] = None
    
    def set_value_animated(self, value: int, duration: Optional[int] = None) -> QPropertyAnimation:
        """
        设置进度条值（带动画）
        
        Args:
            value: 目标值
            duration: 动画时长（毫秒）
        """
        if not self._anim_manager.is_enabled():
            self._progress_bar.setValue(value)
            return None
        
        # 停止当前动画
        if self._current_animation:
            self._current_animation.stop()
        
        anim = QPropertyAnimation(self._progress_bar, b"value")
        anim.setDuration(duration or self._anim_manager._config.duration_normal)
        anim.setStartValue(self._progress_bar.value())
        anim.setEndValue(value)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        
        self._current_animation = anim
        return anim
    
    def pulse_animation(self, duration: int = 1000) -> QPropertyAnimation:
        """
        脉冲动画（不确定进度）
        
        Args:
            duration: 脉冲周期（毫秒）
        """
        if not self._anim_manager.is_enabled():
            return None
        
        anim = QPropertyAnimation(self._progress_bar, b"value")
        anim.setDuration(duration)
        anim.setStartValue(0)
        anim.setEndValue(100)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.setLoopCount(-1)  # 无限循环
        anim.start()
        
        self._current_animation = anim
        return anim
    
    def stop_animation(self) -> None:
        """停止动画"""
        if self._current_animation:
            self._current_animation.stop()
            self._current_animation = None


class NotificationAnimator:
    """
    通知动画器
    
    为通知提示添加动画效果
    """
    
    def __init__(self):
        self._anim_manager = AnimationManager.get_instance()
    
    def show_notification(
        self,
        widget: QWidget,
        duration: int = 3000,
        auto_hide: bool = True
    ) -> None:
        """
        显示通知（带动画）
        
        Args:
            widget: 通知控件
            duration: 显示时长（毫秒）
            auto_hide: 是否自动隐藏
        """
        # 淡入
        self._anim_manager.fade_in(widget, self._anim_manager._config.duration_normal)
        
        # 自动隐藏
        if auto_hide:
            QTimer.singleShot(duration, lambda: self.hide_notification(widget))
    
    def hide_notification(self, widget: QWidget) -> None:
        """隐藏通知（带动画）"""
        self._anim_manager.fade_out(
            widget,
            self._anim_manager._config.duration_normal,
            hide_after=True
        )


# 便捷函数
def get_animation_manager() -> AnimationManager:
    """获取动画管理器实例"""
    return AnimationManager.get_instance()


def fade_in_widget(widget: QWidget, duration: int = 250) -> Optional[QPropertyAnimation]:
    """便捷函数：控件淡入"""
    return AnimationManager.get_instance().fade_in(widget, duration)


def fade_out_widget(widget: QWidget, duration: int = 250, hide_after: bool = True) -> Optional[QPropertyAnimation]:
    """便捷函数：控件淡出"""
    return AnimationManager.get_instance().fade_out(widget, duration, hide_after=hide_after)


def slide_in_widget(
    widget: QWidget,
    direction: Qt.Edge = Qt.Edge.LeftEdge,
    duration: int = 250
) -> Optional[QPropertyAnimation]:
    """便捷函数：控件滑入"""
    return AnimationManager.get_instance().slide_in(widget, direction, duration)


def slide_out_widget(
    widget: QWidget,
    direction: Qt.Edge = Qt.Edge.LeftEdge,
    duration: int = 250,
    hide_after: bool = True
) -> Optional[QPropertyAnimation]:
    """便捷函数：控件滑出"""
    return AnimationManager.get_instance().slide_out(widget, direction, duration, hide_after=hide_after)
