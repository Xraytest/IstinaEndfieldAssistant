"""
设备预览组件
显示设备屏幕截图，支持图像缩放和适应窗口
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor

# 支持两种导入方式
try:
    from ..theme.theme_manager import ThemeManager
except ImportError:
    from theme.theme_manager import ThemeManager


class DevicePreviewWidget(QWidget):
    """
    设备屏幕预览组件
    
    功能：
    - 显示设备屏幕截图（QLabel + QImage）
    - 支持图像缩放和适应窗口
    - 显示设备状态信息（连接状态、分辨率等）
    - 提供刷新截图按钮
    
    信号：
    - image_updated(QImage): 图像更新信号
    - refresh_requested(): 刷新请求信号
    """
    
    # 自定义信号
    image_updated = pyqtSignal(QImage)
    refresh_requested = pyqtSignal()
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        auto_refresh_interval: int = 500
    ) -> None:
        """
        初始化设备预览组件
        
        Args:
            parent: 父控件
            auto_refresh_interval: 自动刷新间隔（毫秒），默认500ms
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._auto_refresh_interval = auto_refresh_interval
        self._current_image: Optional[QImage] = None
        self._current_pixmap: Optional[QPixmap] = None
        self._device_status: str = "未连接"
        self._device_resolution: Optional[str] = None
        self._is_connected: bool = False
        
        # 自动刷新定时器
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._on_auto_refresh)
        
        self._setup_ui()
        self._setup_style()
    
    def _setup_ui(self) -> None:
        """设置UI结构"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm')
        )
        main_layout.setSpacing(self._theme.get_spacing('sm'))
        
        # 状态信息栏
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(self._theme.get_spacing('sm'))
        
        # 状态指示器（圆形）
        self._status_indicator = QLabel()
        self._status_indicator.setFixedSize(12, 12)
        self._update_status_indicator()
        status_layout.addWidget(self._status_indicator)
        
        # 状态文本
        self._status_label = QLabel(self._device_status)
        self._status_label.setProperty("variant", "secondary")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)
        status_layout.addWidget(self._status_label)
        
        # 分辨率信息
        self._resolution_label = QLabel("")
        self._resolution_label.setProperty("variant", "muted")
        self._resolution_label.style().unpolish(self._resolution_label)
        self._resolution_label.style().polish(self._resolution_label)
        status_layout.addWidget(self._resolution_label)
        
        status_layout.addStretch()
        
        # 刷新按钮
        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.setProperty("variant", "secondary")
        self._refresh_btn.setFixedHeight(28)
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)
        status_layout.addWidget(self._refresh_btn)
        
        main_layout.addWidget(status_frame)
        
        # 预览图像区域
        self._image_frame = QFrame()
        self._image_frame.setMinimumHeight(150)
        image_layout = QVBoxLayout(self._image_frame)
        image_layout.setContentsMargins(0, 0, 0, 0)
        
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self._image_label.setMinimumSize(200, 150)
        image_layout.addWidget(self._image_label)
        
        main_layout.addWidget(self._image_frame, 1)
        
        # 设置初始占位图
        self._show_placeholder()
    
    def _setup_style(self) -> None:
        """设置样式"""
        c = self._theme.colors
        
        # 图像区域背景
        self._image_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {c['canvas_bg']};
                border: 1px solid {c['border_color']};
                border-radius: {self._theme.get_corner_radius('sm')}px;
            }}
        """)
        
        # 图像标签样式
        self._image_label.setStyleSheet(f"""
            QLabel {{
                background-color: {c['canvas_bg']};
                border: none;
            }}
        """)
    
    def _show_placeholder(self) -> None:
        """显示占位图"""
        c = self._theme.colors
        
        # 创建占位图像
        placeholder = QImage(200, 150, QImage.Format.Format_RGB32)
        placeholder.fill(QColor(c['canvas_bg']))
        
        painter = QPainter(placeholder)
        painter.setPen(QColor(c['text_muted']))
        font = painter.font()
        font.setPointSize(self._theme.get_font_size('body_medium'))
        painter.setFont(font)
        
        # 绘制提示文字
        text = "等待设备连接..."
        painter.drawText(
            placeholder.rect(),
            Qt.AlignmentFlag.AlignCenter,
            text
        )
        painter.end()
        
        self._current_image = placeholder
        self._update_display_image()
    
    def _update_status_indicator(self) -> None:
        """更新状态指示器颜色"""
        c = self._theme.colors
        
        if self._is_connected:
            color = c['success']  # 绿色 - 已连接
        elif self._device_status == "连接中":
            color = c['warning']  # 黄色 - 连接中
        else:
            color = c['danger']  # 红色 - 未连接
        
        # 创建圆形指示器图像
        indicator = QImage(12, 12, QImage.Format.Format_ARGB32)
        indicator.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(indicator)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 12, 12)
        painter.end()
        
        self._status_indicator.setPixmap(QPixmap.fromImage(indicator))
    
    def _update_display_image(self) -> None:
        """更新显示的图像（缩放适应窗口）"""
        if self._current_image is None or self._current_image.isNull():
            return
        
        # 获取可用显示区域大小
        available_size = self._image_label.size()
        
        # 缩放图像以适应窗口，保持宽高比
        scaled_image = self._current_image.scaled(
            available_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._current_pixmap = QPixmap.fromImage(scaled_image)
        self._image_label.setPixmap(self._current_pixmap)
        
        # 发射图像更新信号
        self.image_updated.emit(self._current_image)
    
    def _on_refresh_clicked(self) -> None:
        """刷新按钮点击处理"""
        self.refresh_requested.emit()
    
    def _on_auto_refresh(self) -> None:
        """自动刷新定时器处理"""
        if self._is_connected:
            self.refresh_requested.emit()
    
    # === 公共方法 ===
    
    def update_image(self, image_data: bytes) -> None:
        """
        更新预览图像
        
        Args:
            image_data: 图像数据（bytes格式，支持PNG/JPEG）
        """
        image = QImage.fromData(image_data)
        if not image.isNull():
            self._current_image = image
            self._update_display_image()
            
            # 更新分辨率信息
            self._device_resolution = f"{image.width()}x{image.height()}"
            self._resolution_label.setText(self._device_resolution)
    
    def update_image_from_qimage(self, image: QImage) -> None:
        """
        从QImage更新预览图像
        
        Args:
            image: QImage对象
        """
        if not image.isNull():
            self._current_image = image
            self._update_display_image()
            
            # 更新分辨率信息
            self._device_resolution = f"{image.width()}x{image.height()}"
            self._resolution_label.setText(self._device_resolution)
    
    def set_device_status(self, status: str, connected: bool = False) -> None:
        """
        设置设备状态
        
        Args:
            status: 状态文本
            connected: 是否已连接
        """
        self._device_status = status
        self._is_connected = connected
        
        self._status_label.setText(status)
        self._update_status_indicator()
        
        # 如果断开连接，显示占位图
        if not connected:
            self._show_placeholder()
            self._resolution_label.setText("")
    
    def start_auto_refresh(self) -> None:
        """启动自动刷新"""
        if self._is_connected:
            self._refresh_timer.start(self._auto_refresh_interval)
    
    def stop_auto_refresh(self) -> None:
        """停止自动刷新"""
        self._refresh_timer.stop()
    
    def set_auto_refresh_interval(self, interval_ms: int) -> None:
        """
        设置自动刷新间隔
        
        Args:
            interval_ms: 刷新间隔（毫秒）
        """
        self._auto_refresh_interval = interval_ms
        if self._refresh_timer.isActive():
            self._refresh_timer.setInterval(interval_ms)
    
    def clear_preview(self) -> None:
        """清除预览图像"""
        self._current_image = None
        self._current_pixmap = None
        self._show_placeholder()
        self._resolution_label.setText("")
    
    def get_current_image(self) -> Optional[QImage]:
        """获取当前显示的图像"""
        return self._current_image
    
    def is_connected(self) -> bool:
        """获取连接状态"""
        return self._is_connected
    
    # === 重写事件处理 ===
    
    def resizeEvent(self, event) -> None:
        """窗口大小改变时重新缩放图像"""
        super().resizeEvent(event)
        if self._current_image is not None:
            self._update_display_image()
    
    def sizeHint(self) -> QSize:
        """建议大小"""
        return QSize(300, 200)
    
    def minimumSizeHint(self) -> QSize:
        """最小大小"""
        return QSize(200, 150)