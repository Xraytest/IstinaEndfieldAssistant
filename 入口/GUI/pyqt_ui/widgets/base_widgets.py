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
    """
    
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
    
    def toggle_selected(self) -> None:
        """切换选中状态"""
        self.set_selected(not self._selected)


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