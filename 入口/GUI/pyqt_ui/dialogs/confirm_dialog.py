"""
确认对话框
Material Design 3 风格的确认对话框
"""

from typing import Optional, Callable
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal

# 支持两种导入方式
try:
    from ..theme.theme_manager import ThemeManager
    from ..widgets.base_widgets import PrimaryButton, SecondaryButton, DangerButton
except ImportError:
    from theme.theme_manager import ThemeManager
    from widgets.base_widgets import PrimaryButton, SecondaryButton, DangerButton


class ConfirmDialog(QDialog):
    """
    Material Design 3 风格的确认对话框
    
    提供确认、取消、删除等操作的对话框
    
    使用方法：
    dialog = ConfirmDialog(parent, "确认删除", "确定要删除这个项目吗？")
    if dialog.exec() == ConfirmDialog.RESULT_CONFIRM:
        # 执行确认操作
    """
    
    # 结果常量
    RESULT_CONFIRM = QDialog.DialogCode.Accepted
    RESULT_CANCEL = QDialog.DialogCode.Rejected
    
    # 对话框类型常量
    TYPE_NORMAL = "normal"      # 普通确认（确认/取消）
    TYPE_DANGER = "danger"      # 危险操作确认（删除/取消）
    TYPE_INFO = "info"          # 信息确认（知道了/取消）
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "确认",
        message: str = "",
        dialog_type: str = TYPE_NORMAL,
        confirm_text: str = "确认",
        cancel_text: str = "取消"
    ) -> None:
        """
        初始化确认对话框
        
        Args:
            parent: 父控件
            title: 标题
            message: 消息内容
            dialog_type: 对话框类型 (normal, danger, info)
            confirm_text: 确认按钮文本
            cancel_text: 取消按钮文本
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._dialog_type = dialog_type
        self._confirm_text = confirm_text
        self._cancel_text = cancel_text
        
        # 设置窗口属性
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(350)
        
        # 设置UI
        self._setup_ui()
        self._setup_style()
    
    def _setup_ui(self) -> None:
        """设置UI结构"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            self._theme.get_spacing('padding_lg'),
            self._theme.get_spacing('padding_lg'),
            self._theme.get_spacing('padding_lg'),
            self._theme.get_spacing('padding_lg')
        )
        main_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 消息内容
        self._message_label = QLabel(self._message_text)
        self._message_label.setWordWrap(True)
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        main_layout.addWidget(self._message_label)
        
        # 添加弹性空间
        main_layout.addStretch()
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(self._theme.get_spacing('sm'))
        button_layout.addStretch()
        
        # 取消按钮
        self._cancel_button = SecondaryButton(self._cancel_text, self)
        self._cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self._cancel_button)
        
        # 确认按钮
        if self._dialog_type == self.TYPE_DANGER:
            self._confirm_button = DangerButton(self._confirm_text, self)
        else:
            self._confirm_button = PrimaryButton(self._confirm_text, self)
        self._confirm_button.clicked.connect(self.accept)
        button_layout.addWidget(self._confirm_button)
        
        main_layout.addLayout(button_layout)
    
    def _setup_style(self) -> None:
        """设置样式"""
        self.setProperty("class", "confirmDialog")
        self.style().unpolish(self)
        self.style().polish(self)
    
    @property
    def _message_text(self) -> str:
        """获取消息文本"""
        # 从窗口标题获取，或使用默认消息
        return self.text() if hasattr(self, 'text') else ""
    
    def set_message(self, message: str) -> None:
        """
        设置消息内容
        
        Args:
            message: 消息内容
        """
        self._message_label.setText(message)
    
    def set_confirm_text(self, text: str) -> None:
        """
        设置确认按钮文本
        
        Args:
            text: 确认按钮文本
        """
        self._confirm_text = text
        self._confirm_button.setText(text)
    
    def set_cancel_text(self, text: str) -> None:
        """
        设置取消按钮文本
        
        Args:
            text: 取消按钮文本
        """
        self._cancel_text = text
        self._cancel_button.setText(text)
    
    @classmethod
    def confirm(
        cls,
        parent: Optional[QWidget] = None,
        title: str = "确认",
        message: str = "",
        confirm_text: str = "确认",
        cancel_text: str = "取消"
    ) -> bool:
        """
        显示确认对话框并返回结果
        
        Args:
            parent: 父控件
            title: 标题
            message: 消息内容
            confirm_text: 确认按钮文本
            cancel_text: 取消按钮文本
            
        Returns:
            用户是否点击了确认按钮
        """
        dialog = cls(
            parent, title, message, cls.TYPE_NORMAL,
            confirm_text, cancel_text
        )
        dialog.set_message(message)
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted
    
    @classmethod
    def confirm_delete(
        cls,
        parent: Optional[QWidget] = None,
        title: str = "确认删除",
        message: str = "确定要删除吗？此操作无法撤销。",
        confirm_text: str = "删除",
        cancel_text: str = "取消"
    ) -> bool:
        """
        显示删除确认对话框
        
        Args:
            parent: 父控件
            title: 标题
            message: 消息内容
            confirm_text: 确认按钮文本
            cancel_text: 取消按钮文本
            
        Returns:
            用户是否点击了删除按钮
        """
        dialog = cls(
            parent, title, message, cls.TYPE_DANGER,
            confirm_text, cancel_text
        )
        dialog.set_message(message)
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted
    
    @classmethod
    def confirm_exit(
        cls,
        parent: Optional[QWidget] = None,
        title: str = "确认退出",
        message: str = "确定要退出应用程序吗？"
    ) -> bool:
        """
        显示退出确认对话框
        
        Args:
            parent: 父控件
            title: 标题
            message: 消息内容
            
        Returns:
            用户是否点击了确认按钮
        """
        return cls.confirm(parent, title, message, "退出", "取消")
    
    @classmethod
    def confirm_save(
        cls,
        parent: Optional[QWidget] = None,
        title: str = "保存更改",
        message: str = "是否保存更改？"
    ) -> bool:
        """
        显示保存确认对话框
        
        Args:
            parent: 父控件
            title: 标题
            message: 消息内容
            
        Returns:
            用户是否点击了保存按钮
        """
        return cls.confirm(parent, title, message, "保存", "不保存")


class ProgressDialog(QDialog):
    """
    Material Design 3 风格的进度对话框
    
    用于显示长时间操作的进度
    
    使用方法：
    dialog = ProgressDialog(parent, "正在处理...")
    dialog.set_progress(50, "处理中...")
    dialog.exec()
    """
    
    # 信号
    cancelled = pyqtSignal()
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "处理中",
        message: str = "请稍候...",
        show_cancel: bool = True
    ) -> None:
        """
        初始化进度对话框
        
        Args:
            parent: 父控件
            title: 标题
            message: 消息内容
            show_cancel: 是否显示取消按钮
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._show_cancel = show_cancel
        self._progress_value: int = 0
        
        # 设置窗口属性
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)
        
        # 设置UI
        self._setup_ui()
        self._setup_style()
    
    def _setup_ui(self) -> None:
        """设置UI结构"""
        from PyQt6.QtWidgets import QProgressBar
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            self._theme.get_spacing('padding_lg'),
            self._theme.get_spacing('padding_lg'),
            self._theme.get_spacing('padding_lg'),
            self._theme.get_spacing('padding_lg')
        )
        main_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 消息内容
        self._message_label = QLabel(self._message_text)
        self._message_label.setWordWrap(True)
        main_layout.addWidget(self._message_label)
        
        # 进度条
        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        main_layout.addWidget(self._progress_bar)
        
        # 取消按钮（可选）
        if self._show_cancel:
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
            self._cancel_button = SecondaryButton("取消", self)
            self._cancel_button.clicked.connect(self._on_cancel)
            button_layout.addWidget(self._cancel_button)
            
            main_layout.addLayout(button_layout)
    
    def _setup_style(self) -> None:
        """设置样式"""
        self.setProperty("class", "progressDialog")
        self.style().unpolish(self)
        self.style().polish(self)
    
    @property
    def _message_text(self) -> str:
        """获取消息文本"""
        return ""
    
    def set_message(self, message: str) -> None:
        """
        设置消息内容
        
        Args:
            message: 消息内容
        """
        self._message_label.setText(message)
    
    def set_progress(self, value: int, message: Optional[str] = None) -> None:
        """
        设置进度值
        
        Args:
            value: 进度值 (0-100)
            message: 可选的消息内容
        """
        self._progress_value = value
        self._progress_bar.setValue(value)
        
        if message:
            self.set_message(message)
    
    def get_progress(self) -> int:
        """获取当前进度值"""
        return self._progress_value
    
    def _on_cancel(self) -> None:
        """处理取消按钮点击"""
        self.cancelled.emit()
        self.reject()
    
    def complete(self, message: str = "完成") -> None:
        """
        完成进度
        
        Args:
            message: 完成消息
        """
        self.set_progress(100, message)
        # 短暂延迟后关闭
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, self.accept)


# 提供便捷的函数接口
def confirm_action(
    parent: Optional[QWidget] = None,
    title: str = "确认",
    message: str = ""
) -> bool:
    """显示确认对话框"""
    return ConfirmDialog.confirm(parent, title, message)


def confirm_delete(
    parent: Optional[QWidget] = None,
    title: str = "确认删除",
    message: str = "确定要删除吗？此操作无法撤销。"
) -> bool:
    """显示删除确认对话框"""
    return ConfirmDialog.confirm_delete(parent, title, message)


def confirm_exit(
    parent: Optional[QWidget] = None,
    title: str = "确认退出",
    message: str = "确定要退出应用程序吗？"
) -> bool:
    """显示退出确认对话框"""
    return ConfirmDialog.confirm_exit(parent, title, message)