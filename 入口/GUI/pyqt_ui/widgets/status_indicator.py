"""
状态指示器组件
显示连接状态（圆形图标 + 文字），支持状态切换动画
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QPropertyAnimation, QVariantAnimation
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QBrush

# 支持两种导入方式
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


class StatusIndicatorWidget(QWidget):
    """
    状态指示器组件
    
    功能：
    - 显示连接状态（圆形图标 + 文字）
    - 状态颜色：绿色(连接)、黄色(连接中)、红色(断开)
    - 支持状态切换动画
    
    信号：
    - status_changed(str): 状态改变信号
    """
    
    # 状态常量
    STATUS_CONNECTED = "connected"       # 已连接
    STATUS_CONNECTING = "connecting"      # 连接中
    STATUS_DISCONNECTED = "disconnected"  # 断开连接
    STATUS_ERROR = "error"                # 错误
    
    # 自定义信号
    status_changed = pyqtSignal(str)
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        initial_status: str = STATUS_DISCONNECTED,
        show_text: bool = True,
        indicator_size: int = 12,
        enable_animation: bool = True
    ) -> None:
        """
        初始化状态指示器
        
        Args:
            parent: 父控件
            initial_status: 初始状态
            show_text: 是否显示状态文字
            indicator_size: 指示器大小（像素）
            enable_animation: 是否启用动画
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._current_status: str = initial_status
        self._show_text: bool = show_text
        self._indicator_size: int = indicator_size
        self._enable_animation: bool = enable_animation
        
        # 动画相关
        self._animation_timer: Optional[QTimer] = None
        self._animation_phase: int = 0
        self._pulse_opacity: float = 1.0
        
        self._setup_ui()
        self._update_indicator()
        
        # 如果初始状态是连接中，启动动画
        if initial_status == self.STATUS_CONNECTING and self._enable_animation:
            self._start_animation()
    
    def _setup_ui(self) -> None:
        """设置UI结构"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self._theme.get_spacing('xs'))
        
        # 圆形指示器
        self._indicator_label = QLabel()
        self._indicator_label.setFixedSize(self._indicator_size, self._indicator_size)
        self._indicator_label.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self._indicator_label)
        
        # 状态文字
        if self._show_text:
            self._status_text = QLabel(self._get_status_text())
            self._status_text.setProperty("variant", "secondary")
            self._status_text.style().unpolish(self._status_text)
            self._status_text.style().polish(self._status_text)
            layout.addWidget(self._status_text)
        
        layout.addStretch()
    
    def _get_status_color(self) -> str:
        """获取当前状态对应的颜色"""
        colors = {
            self.STATUS_CONNECTED: self._theme.get_color('success'),      # 绿色
            self.STATUS_CONNECTING: self._theme.get_color('warning'),     # 黄色
            self.STATUS_DISCONNECTED: self._theme.get_color('danger'),    # 红色
            self.STATUS_ERROR: self._theme.get_color('danger_light'),     # 浅红色
        }
        return colors.get(self._current_status, self._theme.get_color('text_muted'))
    
    def _get_status_text(self) -> str:
        """获取状态显示文本"""
        texts = {
            self.STATUS_CONNECTED: "已连接",
            self.STATUS_CONNECTING: "连接中...",
            self.STATUS_DISCONNECTED: "未连接",
            self.STATUS_ERROR: "连接错误",
        }
        return texts.get(self._current_status, "未知")
    
    def _create_indicator_image(self, opacity: float = 1.0) -> QImage:
        """
        创建指示器图像
        
        Args:
            opacity: 透明度 (0.0 - 1.0)
        
        Returns:
            QImage: 指示器图像
        """
        size = self._indicator_size
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        
        color = QColor(self._get_status_color())
        color.setAlphaF(opacity)
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # 绘制圆形
        margin = 1  # 边缘留一点空间
        painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)
        painter.end()
        
        return image
    
    def _update_indicator(self) -> None:
        """更新指示器显示"""
        image = self._create_indicator_image(self._pulse_opacity)
        self._indicator_label.setPixmap(QPixmap.fromImage(image))
        
        if self._show_text:
            self._status_text.setText(self._get_status_text())
    
    def _start_animation(self) -> None:
        """启动连接中动画"""
        if not self._enable_animation:
            return
        
        if self._animation_timer is None:
            self._animation_timer = QTimer(self)
            self._animation_timer.timeout.connect(self._on_animation_tick)
        
        self._animation_phase = 0
        self._animation_timer.start(100)  # 100ms 间隔
    
    def _stop_animation(self) -> None:
        """停止动画"""
        if self._animation_timer:
            self._animation_timer.stop()
            self._animation_timer = None
        
        self._pulse_opacity = 1.0
        self._update_indicator()
    
    def _on_animation_tick(self) -> None:
        """动画定时器回调"""
        # 脉冲动画：透明度在 0.3 到 1.0 之间变化
        self._animation_phase += 1
        
        # 使用正弦函数模拟脉冲效果
        # phase 从 0 到 10 循环
        phase_in_cycle = self._animation_phase % 10
        
        # 透明度变化：0.3 -> 1.0 -> 0.3
        if phase_in_cycle < 5:
            # 上升阶段
            self._pulse_opacity = 0.3 + (phase_in_cycle / 5) * 0.7
        else:
            # 下降阶段
            self._pulse_opacity = 1.0 - ((phase_in_cycle - 5) / 5) * 0.7
        
        self._update_indicator()
    
    # === 公共方法 ===
    
    def set_status(self, status: str) -> None:
        """
        设置状态
        
        Args:
            status: 新状态 (connected/connecting/disconnected/error)
        """
        if status == self._current_status:
            return
        
        old_status = self._current_status
        self._current_status = status
        
        # 停止之前的动画
        self._stop_animation()
        
        # 如果是连接中状态，启动动画
        if status == self.STATUS_CONNECTING and self._enable_animation:
            self._start_animation()
        
        self._update_indicator()
        self.status_changed.emit(status)
    
    def set_connected(self) -> None:
        """设置为已连接状态"""
        self.set_status(self.STATUS_CONNECTED)
    
    def set_connecting(self) -> None:
        """设置为连接中状态"""
        self.set_status(self.STATUS_CONNECTING)
    
    def set_disconnected(self) -> None:
        """设置为断开连接状态"""
        self.set_status(self.STATUS_DISCONNECTED)
    
    def set_error(self) -> None:
        """设置为错误状态"""
        self.set_status(self.STATUS_ERROR)
    
    def get_status(self) -> str:
        """获取当前状态"""
        return self._current_status
    
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._current_status == self.STATUS_CONNECTED
    
    def set_indicator_size(self, size: int) -> None:
        """设置指示器大小"""
        self._indicator_size = size
        self._indicator_label.setFixedSize(size, size)
        self._update_indicator()
    
    def set_enable_animation(self, enable: bool) -> None:
        """设置是否启用动画"""
        self._enable_animation = enable
        
        if not enable:
            self._stop_animation()
        elif self._current_status == self.STATUS_CONNECTING:
            self._start_animation()
    
    # === 重写事件处理 ===
    
    def sizeHint(self) -> QSize:
        """建议大小"""
        width = self._indicator_size + self._theme.get_spacing('xs')
        if self._show_text:
            width += 80  # 大约文字宽度
        return QSize(width, self._indicator_size + 4)


class ConnectionStatusIndicator(StatusIndicatorWidget):
    """
    连接状态指示器
    
    专门用于显示设备/网络连接状态
    """
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        connection_type: str = "device"
    ) -> None:
        """
        初始化连接状态指示器
        
        Args:
            parent: 父控件
            connection_type: 连接类型 (device/network/server)
        """
        self._connection_type = connection_type
        super().__init__(parent)
    
    def _get_status_text(self) -> str:
        """获取状态显示文本"""
        base_texts = {
            self.STATUS_CONNECTED: "已连接",
            self.STATUS_CONNECTING: "连接中...",
            self.STATUS_DISCONNECTED: "未连接",
            self.STATUS_ERROR: "连接错误",
        }
        
        base_text = base_texts.get(self._current_status, "未知")
        
        # 根据连接类型添加前缀
        type_prefixes = {
            "device": "设备",
            "network": "网络",
            "server": "服务器",
        }
        prefix = type_prefixes.get(self._connection_type, "")
        
        return f"{prefix}{base_text}" if prefix else base_text


class DualStatusIndicator(QWidget):
    """
    双状态指示器
    
    显示两个独立的状态（如设备状态和网络状态）
    """
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        labels: tuple = ("设备", "网络")
    ) -> None:
        """
        初始化双状态指示器
        
        Args:
            parent: 父控件
            labels: 两个状态的标签
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._labels = labels
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self._theme.get_spacing('lg'))
        
        # 第一个状态指示器
        self._indicator1 = StatusIndicatorWidget(show_text=True)
        label1 = QLabel(self._labels[0])
        label1.setProperty("variant", "muted")
        label1.style().unpolish(label1)
        label1.style().polish(label1)
        layout.addWidget(label1)
        layout.addWidget(self._indicator1)
        
        # 分隔符
        separator = QLabel("|")
        separator.setProperty("variant", "muted")
        separator.style().unpolish(separator)
        separator.style().polish(separator)
        layout.addWidget(separator)
        
        # 第二个状态指示器
        self._indicator2 = StatusIndicatorWidget(show_text=True)
        label2 = QLabel(self._labels[1])
        label2.setProperty("variant", "muted")
        label2.style().unpolish(label2)
        label2.style().polish(label2)
        layout.addWidget(label2)
        layout.addWidget(self._indicator2)
        
        layout.addStretch()
    
    def set_first_status(self, status: str) -> None:
        """设置第一个状态"""
        self._indicator1.set_status(status)
    
    def set_second_status(self, status: str) -> None:
        """设置第二个状态"""
        self._indicator2.set_status(status)
    
    def get_first_indicator(self) -> StatusIndicatorWidget:
        """获取第一个指示器"""
        return self._indicator1
    
    def get_second_indicator(self) -> StatusIndicatorWidget:
        """获取第二个指示器"""
        return self._indicator2