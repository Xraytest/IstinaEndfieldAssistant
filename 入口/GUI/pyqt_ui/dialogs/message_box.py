"""
自定义消息框
基于 QMessageBox 的 Material Design 3 风格消息框
"""

from typing import Optional
from PyQt6.QtWidgets import QMessageBox, QWidget
from PyQt6.QtCore import Qt

# 支持两种导入方式
try:
    from ..theme.theme_manager import ThemeManager
except ImportError:
    import sys
    import os
    # 计算项目根目录路径
    current_file = os.path.abspath(__file__)
    dialogs_dir = os.path.dirname(current_file)
    pyqt_ui_dir = os.path.dirname(dialogs_dir)
    gui_dir = os.path.dirname(pyqt_ui_dir)
    entry_dir = os.path.dirname(gui_dir)
    istina_dir = os.path.dirname(entry_dir)
    project_root = os.path.dirname(istina_dir)
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if istina_dir not in sys.path:
        sys.path.insert(0, istina_dir)
    
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.theme.theme_manager import ThemeManager


class MessageBox(QMessageBox):
    """
    Material Design 3 风格的消息框
    
    提供信息、警告、错误、成功等类型的消息显示
    
    使用方法：
    - MessageBox.info(parent, "标题", "消息内容")
    - MessageBox.warning(parent, "标题", "警告内容")
    - MessageBox.error(parent, "标题", "错误内容")
    - MessageBox.success(parent, "标题", "成功内容")
    - MessageBox.question(parent, "标题", "确认内容")
    """
    
    # 消息类型常量
    TYPE_INFO = "info"
    TYPE_WARNING = "warning"
    TYPE_ERROR = "error"
    TYPE_SUCCESS = "success"
    TYPE_QUESTION = "question"
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "",
        message: str = "",
        message_type: str = TYPE_INFO
    ) -> None:
        """
        初始化消息框
        
        Args:
            parent: 父控件
            title: 标题
            message: 消息内容
            message_type: 消息类型
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._message_type = message_type
        
        # 设置标题和消息
        self.setWindowTitle(title)
        self.setText(message)
        
        # 设置图标和按钮
        self._setup_type()
        self._setup_style()
    
    def _setup_type(self) -> None:
        """根据消息类型设置图标和按钮"""
        if self._message_type == self.TYPE_INFO:
            self.setIcon(QMessageBox.Icon.Information)
            self.setStandardButtons(QMessageBox.StandardButton.Ok)
            
        elif self._message_type == self.TYPE_WARNING:
            self.setIcon(QMessageBox.Icon.Warning)
            self.setStandardButtons(QMessageBox.StandardButton.Ok)
            
        elif self._message_type == self.TYPE_ERROR:
            self.setIcon(QMessageBox.Icon.Critical)
            self.setStandardButtons(QMessageBox.StandardButton.Ok)
            
        elif self._message_type == self.TYPE_SUCCESS:
            # QMessageBox没有成功图标，使用信息图标
            self.setIcon(QMessageBox.Icon.Information)
            self.setStandardButtons(QMessageBox.StandardButton.Ok)
            # 设置成功样式
            self.setProperty("messageType", "success")
            self.style().unpolish(self)
            self.style().polish(self)
            
        elif self._message_type == self.TYPE_QUESTION:
            self.setIcon(QMessageBox.Icon.Question)
            self.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            self.setDefaultButton(QMessageBox.StandardButton.No)
    
    def _setup_style(self) -> None:
        """设置样式"""
        # 应用Material Design 3风格
        self.setProperty("class", "messageBox")
        self.style().unpolish(self)
        self.style().polish(self)
        
        # 设置最小宽度
        self.setMinimumWidth(300)
    
    @classmethod
    def info(
        cls,
        parent: Optional[QWidget] = None,
        title: str = "信息",
        message: str = ""
    ) -> QMessageBox.StandardButton:
        """
        显示信息消息框
        
        Args:
            parent: 父控件
            title: 标题
            message: 消息内容
            
        Returns:
            用户点击的按钮
        """
        box = cls(parent, title, message, cls.TYPE_INFO)
        return box.exec()
    
    @classmethod
    def warning(
        cls,
        parent: Optional[QWidget] = None,
        title: str = "警告",
        message: str = ""
    ) -> QMessageBox.StandardButton:
        """
        显示警告消息框
        
        Args:
            parent: 父控件
            title: 标题
            message: 消息内容
            
        Returns:
            用户点击的按钮
        """
        box = cls(parent, title, message, cls.TYPE_WARNING)
        return box.exec()
    
    @classmethod
    def error(
        cls,
        parent: Optional[QWidget] = None,
        title: str = "错误",
        message: str = ""
    ) -> QMessageBox.StandardButton:
        """
        显示错误消息框
        
        Args:
            parent: 父控件
            title: 标题
            message: 消息内容
            
        Returns:
            用户点击的按钮
        """
        box = cls(parent, title, message, cls.TYPE_ERROR)
        return box.exec()
    
    @classmethod
    def success(
        cls,
        parent: Optional[QWidget] = None,
        title: str = "成功",
        message: str = ""
    ) -> QMessageBox.StandardButton:
        """
        显示成功消息框
        
        Args:
            parent: 父控件
            title: 标题
            message: 消息内容
            
        Returns:
            用户点击的按钮
        """
        box = cls(parent, title, message, cls.TYPE_SUCCESS)
        return box.exec()
    
    @classmethod
    def question(
        cls,
        parent: Optional[QWidget] = None,
        title: str = "确认",
        message: str = "",
        default_no: bool = True
    ) -> QMessageBox.StandardButton:
        """
        显示确认消息框
        
        Args:
            parent: 父控件
            title: 标题
            message: 消息内容
            default_no: 默认按钮是否为No
            
        Returns:
            用户点击的按钮
        """
        box = cls(parent, title, message, cls.TYPE_QUESTION)
        if not default_no:
            box.setDefaultButton(QMessageBox.StandardButton.Yes)
        result = box.exec()
        return result
    
    @classmethod
    def confirm(
        cls,
        parent: Optional[QWidget] = None,
        title: str = "确认",
        message: str = ""
    ) -> bool:
        """
        显示确认消息框并返回布尔值
        
        Args:
            parent: 父控件
            title: 标题
            message: 消息内容
            
        Returns:
            用户是否点击了Yes
        """
        result = cls.question(parent, title, message)
        return result == QMessageBox.StandardButton.Yes


# 提供便捷的函数接口
def show_info(parent: Optional[QWidget] = None, title: str = "信息", message: str = "") -> None:
    """显示信息消息框"""
    MessageBox.info(parent, title, message)


def show_warning(parent: Optional[QWidget] = None, title: str = "警告", message: str = "") -> None:
    """显示警告消息框"""
    MessageBox.warning(parent, title, message)


def show_error(parent: Optional[QWidget] = None, title: str = "错误", message: str = "") -> None:
    """显示错误消息框"""
    MessageBox.error(parent, title, message)


def show_success(parent: Optional[QWidget] = None, title: str = "成功", message: str = "") -> None:
    """显示成功消息框"""
    MessageBox.success(parent, title, message)


def ask_question(parent: Optional[QWidget] = None, title: str = "确认", message: str = "") -> bool:
    """显示确认消息框并返回布尔值"""
    return MessageBox.confirm(parent, title, message)