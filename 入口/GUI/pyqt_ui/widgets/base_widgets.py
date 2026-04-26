"""
基础自定义控件
提供 Material Design 3 风格的按钮和卡片组件
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QPushButton,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtProperty
from PyQt6.QtGui import QPainter

# 支持两种导入方式：相对导入（包内使用）和绝对导入（测试使用）
try:
    from ..theme.theme_manager import ThemeManager
    from ..theme.animation_manager import AnimationManager
except ImportError:
    import sys
    import os
    # 计算项目根目录路径
    current_file = os.path.abspath(__file__)
    widgets_dir = os.path.dirname(current_file)
    pyqt_ui_dir = os.path.dirname(widgets_dir)
    gui_dir = os.path.dirname(pyqt_ui_dir)
    entry_dir = os.path.dirname(gui_dir)
    istina_dir = os.path.dirname(entry_dir)
    project_root = os.path.dirname(istina_dir)
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if istina_dir not in sys.path:
        sys.path.insert(0, istina_dir)
    
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.theme.theme_manager import ThemeManager
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.theme.animation_manager import AnimationManager


class BaseButton(QPushButton):
    """
    Material Design 3 基础按钮
    
    提供统一的按钮样式和交互行为
    """
    
    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None,
        variant: str = "primary"
    ) -> None:
        """
        初始化按钮
        
        Args:
            text: 按钮文本
            parent: 父控件
            variant: 按钮变体类型 (primary, secondary, text, danger)
        """
        super().__init__(text, parent)
        self._variant = variant
        self._theme = ThemeManager.get_instance()
        self._setup_style()
    
    def _setup_style(self) -> None:
        """设置按钮样式"""
        # 使用setProperty设置variant属性，QSS会根据属性选择样式
        self.setProperty("variant", self._variant)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    @pyqtProperty(str)
    def variant(self) -> str:
        """获取按钮变体类型"""
        return self._variant
    
    def set_variant(self, variant: str) -> None:
        """
        设置按钮变体类型
        
        Args:
            variant: 按钮变体类型 (primary, secondary, text, danger)
        """
        self._variant = variant
        self.setProperty("variant", variant)


class PrimaryButton(BaseButton):
    """Material Design 3 主要按钮（填充样式）"""
    
    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(text, parent, variant="primary")


class SecondaryButton(BaseButton):
    """Material Design 3 次级按钮（轮廓样式）"""
    
    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(text, parent, variant="secondary")


class TextButton(BaseButton):
    """Material Design 3 文本按钮（无背景）"""
    
    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(text, parent, variant="text")


class DangerButton(BaseButton):
    """Material Design 3 危险按钮（红色填充）"""
    
    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(text, parent, variant="danger")


class CardWidget(QWidget):
    """
    Material Design 3 卡片容器
    
    提供统一的卡片样式和布局
    """
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: Optional[str] = None,
        elevated: bool = False,
        outlined: bool = False
    ) -> None:
        """
        初始化卡片
        
        Args:
            parent: 父控件
            title: 卡片标题（可选）
            elevated: 是否使用提升样式
            outlined: 是否使用轮廓样式
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._title = title
        self._elevated = elevated
        self._outlined = outlined
        
        self._setup_ui()
        self._setup_style()
    
    def _setup_ui(self) -> None:
        """设置卡片UI结构"""
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(
            self._theme.get_spacing('card_padding'),
            self._theme.get_spacing('card_padding'),
            self._theme.get_spacing('card_padding'),
            self._theme.get_spacing('card_padding')
        )
        self._main_layout.setSpacing(self._theme.get_spacing('sm'))
        
        # 标题区域
        if self._title:
            self._title_label = QLabel(self._title)
            self._title_label.setProperty("variant", "title")
            self._main_layout.addWidget(self._title_label)
        
        # 内容区域
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(self._theme.get_spacing('sm'))
        self._main_layout.addWidget(self._content_widget)
    
    def _setup_style(self) -> None:
        """设置卡片样式"""
        if self._elevated:
            self.setProperty("class", "cardElevated")
        elif self._outlined:
            self.setProperty("class", "cardOutlined")
        else:
            self.setProperty("class", "card")
    
    def get_content_layout(self) -> QVBoxLayout:
        """获取内容区域布局，用于添加子控件"""
        return self._content_layout
    
    def add_widget(self, widget: QWidget) -> None:
        """
        添加控件到卡片内容区域
        
        Args:
            widget: 要添加的控件
        """
        self._content_layout.addWidget(widget)
    
    def add_layout(self, layout: QHBoxLayout | QVBoxLayout) -> None:
        """
        添加布局到卡片内容区域
        
        Args:
            layout: 要添加的布局
        """
        self._content_layout.addLayout(layout)
    
    def set_title(self, title: str) -> None:
        """
        设置卡片标题
        
        Args:
            title: 新标题文本
        """
        self._title = title
        if hasattr(self, '_title_label') and self._title_label:
            self._title_label.setText(title)
        elif title:
            # 如果之前没有标题，现在创建
            self._title_label = QLabel(title)
            self._title_label.setProperty("variant", "title")
            self._main_layout.insertWidget(0, self._title_label)


class ElevatedCardWidget(CardWidget):
    """Material Design 3 提升卡片（带阴影效果）"""
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: Optional[str] = None
    ) -> None:
        super().__init__(parent, title, elevated=True)


class OutlinedCardWidget(CardWidget):
    """Material Design 3 轮廓卡片（带边框）"""
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: Optional[str] = None
    ) -> None:
        super().__init__(parent, title, outlined=True)


class NavigationButton(BaseButton):
    """
    Material Design 3 导航按钮
    
    用于侧边导航栏，支持选中状态
    
    [修复4-3] 添加悬停和点击动画效果
    [修复5-2] 统一按钮尺寸，确保点击效果长度一致
    [修复6-1] 修复动画导致位置偏移问题 - 使用样式表动画替代geometry动画
    """
    
    # [修复5-2] 类级别的统一按钮宽度
    NAV_BUTTON_WIDTH = 180  # 固定宽度，确保所有按钮一致
    NAV_BUTTON_HEIGHT = 40  # 固定高度
    
    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None,
        icon: Optional[str] = None
    ) -> None:
        """
        初始化导航按钮
        
        Args:
            text: 按钮文本
            parent: 父控件
            icon: 图标名称（可选，待后续实现图标系统）
        """
        super().__init__(text, parent, variant="text")
        self._selected = False
        self._icon = icon
        self._setup_nav_style()
        
        # [修复6-1] 初始化动画相关属性 - 使用样式表动画，不修改geometry
        self._anim_manager = AnimationManager.get_instance()
        self._hover_animation = None
        self._click_animation = None
        
        # [修复6-1] 样式表动画属性
        self._base_bg_color = "transparent"
        self._hover_bg_color = "rgba(255, 255, 255, 0.1)"
        self._pressed_bg_color = "rgba(255, 255, 255, 0.2)"
        self._selected_bg_color = "rgba(255, 255, 255, 0.15)"
        self._is_hovered = False
        self._is_pressed = False
        
        # [修复5-2] 设置固定尺寸，确保所有按钮一致
        self.setFixedSize(self.NAV_BUTTON_WIDTH, self.NAV_BUTTON_HEIGHT)
        
        # 启用悬停事件
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
    
    def _setup_nav_style(self) -> None:
        """设置导航按钮样式"""
        self.setProperty("class", "navButton")
    
    @pyqtProperty(bool)
    def selected(self) -> bool:
        """获取选中状态"""
        return self._selected
    
    def set_selected(self, selected: bool) -> None:
        """
        设置选中状态
        
        Args:
            selected: 是否选中
        """
        self._selected = selected
        self.setProperty("selected", "true" if selected else "false")
        
        # [修复6-1] 更新样式表以反映选中状态
        if selected:
            self._update_style_with_bg(self._selected_bg_color)
        else:
            self._update_style_with_bg(self._base_bg_color)
        
        # [修复6-1] 脉冲动画改为样式表闪烁效果
        if selected and self._anim_manager.is_enabled():
            self._pulse_animation()
    
    def toggle_selected(self) -> None:
        """切换选中状态"""
        self.set_selected(not self._selected)
    
    # [修复6-1] 使用样式表动画替代geometry动画，避免位置偏移
    def enterEvent(self, event):
        """鼠标进入事件 - 悬停效果"""
        super().enterEvent(event)
        self._is_hovered = True
        if self._anim_manager.is_enabled() and self._anim_manager._config.hover_enabled:
            self._start_hover_animation(True)
    
    def leaveEvent(self, event):
        """鼠标离开事件 - 恢复效果"""
        super().leaveEvent(event)
        self._is_hovered = False
        if self._anim_manager.is_enabled() and self._anim_manager._config.hover_enabled:
            self._start_hover_animation(False)
    
    def _start_hover_animation(self, entering: bool) -> None:
        """
        启动悬停动画
        
        [修复6-1] 使用样式表动画替代geometry动画，避免位置偏移
        
        Args:
            entering: 是否进入悬停状态
        """
        # 停止之前的动画
        if self._hover_animation:
            self._hover_animation.stop()
        
        # [修复6-1] 使用样式表实现悬停效果，不修改geometry
        if entering:
            # 进入悬停状态 - 添加背景色
            bg_color = self._selected_bg_color if self._selected else self._hover_bg_color
        else:
            # 离开悬停状态 - 恢复背景色
            bg_color = self._selected_bg_color if self._selected else self._base_bg_color
        
        self._update_style_with_bg(bg_color)
    
    def _update_style_with_bg(self, bg_color: str) -> None:
        """
        更新按钮样式（带背景色）
        
        [修复6-1] 使用样式表实现视觉效果，不修改geometry
        """
        # 构建样式表
        selected_class = "navButtonSelected" if self._selected else "navButton"
        self.setStyleSheet(f"""
            QPushButton#{selected_class} {{
                background-color: {bg_color};
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                text-align: left;
                color: white;
                font-size: 14px;
            }}
            QPushButton#{selected_class}:hover {{
                background-color: {self._hover_bg_color if not self._selected else self._selected_bg_color};
            }}
            QPushButton#{selected_class}:pressed {{
                background-color: {self._pressed_bg_color};
            }}
        """)
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 点击效果"""
        super().mousePressEvent(event)
        self._is_pressed = True
        if self._anim_manager.is_enabled():
            self._start_click_animation()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        super().mouseReleaseEvent(event)
        self._is_pressed = False
        # 恢复悬停或正常状态
        if self._anim_manager.is_enabled():
            self._restore_from_click()
    
    def _start_click_animation(self) -> None:
        """
        启动点击动画效果
        
        [修复6-1] 使用样式表动画替代geometry动画，避免位置偏移
        """
        # [修复6-1] 使用样式表实现按压效果，不修改geometry
        self._update_style_with_bg(self._pressed_bg_color)
    
    def _restore_from_click(self) -> None:
        """
        从点击状态恢复
        
        [修复6-1] 使用样式表恢复，避免位置偏移
        """
        # [修复6-1] 根据当前状态恢复背景色
        if self._selected:
            bg_color = self._selected_bg_color
        elif self._is_hovered:
            bg_color = self._hover_bg_color
        else:
            bg_color = self._base_bg_color
        
        self._update_style_with_bg(bg_color)
    
    def _pulse_animation(self) -> None:
        """
        脉冲动画效果（用于选中状态）
        
        [修复6-1] 使用样式表背景色闪烁替代geometry动画，避免位置偏移
        """
        # [修复6-1] 使用QTimer实现背景色脉冲效果，不修改geometry
        from PyQt6.QtCore import QTimer
        
        # 定义脉冲颜色
        pulse_color = "rgba(255, 255, 255, 0.25)"
        
        # 先设置为脉冲颜色
        self._update_style_with_bg(pulse_color)
        
        # 使用单次定时器恢复选中状态颜色
        QTimer.singleShot(self._anim_manager._config.duration_fast,
                         lambda: self._update_style_with_bg(self._selected_bg_color))


class HorizontalSeparator(QFrame):
    """水平分割线"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setFixedHeight(1)


class VerticalSeparator(QFrame):
    """垂直分割线"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setFixedWidth(1)