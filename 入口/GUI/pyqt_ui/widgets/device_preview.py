"""
设备预览组件
显示设备屏幕截图，支持图像缩放和适应窗口
"""

import base64
import logging
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
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QMetaObject, Qt as QtCore, QThread
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor

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


# 创建logger
logger = logging.getLogger(__name__)


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
    - _internal_update_image(bytes): 内部信号，用于线程安全更新
    - screenshot_requested(): 截图请求信号，用于从外部获取截图数据 [AutoFix 2026-04-18]
    """
    
    # 自定义信号
    image_updated = pyqtSignal(QImage)
    refresh_requested = pyqtSignal()
    _internal_update_image = pyqtSignal(bytes)  # 内部信号，用于线程安全更新
    screenshot_requested = pyqtSignal()  # [AutoFix 2026-04-18] 截图请求信号
    
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
        
        # 连接内部信号到实际处理方法
        self._internal_update_image.connect(self._process_image_update)
        
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
        status_layout.addWidget(self._status_label)
        
        # 分辨率信息
        self._resolution_label = QLabel("")
        self._resolution_label.setProperty("variant", "muted")
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
        # [AutoFix 2026-04-18] 修复：自动刷新时发射截图请求信号
        if self._is_connected:
            logger.debug("Auto refresh triggered, emitting screenshot_requested signal")
            self.screenshot_requested.emit()
            # 同时保留refresh_requested信号以兼容旧代码
            self.refresh_requested.emit()
    
    # === 公共方法 ===
    
    def update_image(self, image_data: bytes) -> None:
        """
        更新预览图像（线程安全版本）
        
        如果调用线程不是主线程，会通过信号槽机制将操作转发到主线程执行
        
        Args:
            image_data: 图像数据（bytes格式，支持PNG/JPEG，可能是base64编码）
        """
        try:
            # 检查当前线程是否是主线程
            if self.thread() is not None and self.thread() != QThread.currentThread():
                # 在非主线程中被调用，通过信号转发到主线程
                logger.debug("update_image called from non-main thread, forwarding via signal")
                self._internal_update_image.emit(image_data)
                return
            
            # 在主线程中，直接处理
            self._process_image_update(image_data)
        except Exception as e:
            logger.exception(f"Error in update_image: {e}")
    
    def _process_image_update(self, image_data: bytes) -> None:
        """
        实际处理图像更新的方法（在主线程中执行）
        
        Args:
            image_data: 图像数据（bytes格式，支持PNG/JPEG，可能是base64编码）
        """
        try:
            logger.debug(f"_process_image_update called, data type: {type(image_data)}, length: {len(image_data) if image_data else 0}")
            
            if not image_data:
                logger.warning("_process_image_update received empty image_data")
                return
            
            # 处理base64编码的数据
            raw_bytes = image_data
            if isinstance(image_data, bytes):
                # 检查是否是base64编码
                # 1. 数据长度应该是4的倍数（base64编码特性）
                # 2. 数据应该只包含base64字符集
                # 3. 原始图像数据通常以PNG或JPEG头开始
                is_likely_base64 = (
                    len(image_data) % 4 == 0 and  # base64长度是4的倍数
                    len(image_data) > 100 and     # base64编码通常较长
                    image_data[:4] not in [b'\x89PNG', b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd8\xff\xdb']  # 不是原始图像
                )
                
                if is_likely_base64:
                    try:
                        # 尝试解码base64
                        decoded = base64.b64decode(image_data, validate=True)
                        if decoded and len(decoded) > 0:
                            # 验证解码后的数据是否是有效的图像格式
                            if decoded[:4] in [b'\x89PNG', b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd8\xff\xdb']:
                                raw_bytes = decoded
                                logger.debug(f"Successfully decoded base64 data, original length: {len(image_data)}, decoded length: {len(decoded)}")
                    except Exception as e:
                        # 解码失败，使用原始数据
                        logger.debug(f"Base64 decode failed (using raw data): {e}")
                        pass
            
            image = QImage.fromData(raw_bytes)
            if not image.isNull():
                self._current_image = image
                self._update_display_image()
                
                # 更新分辨率信息
                self._device_resolution = f"{image.width()}x{image.height()}"
                self._resolution_label.setText(self._device_resolution)
                logger.debug(f"Image updated successfully: {self._device_resolution}")
            else:
                logger.error(f"Failed to create QImage from data, data length: {len(raw_bytes)}")
                # 尝试显示错误信息在预览区域
                self._show_error_placeholder("图像格式错误")
        except Exception as e:
            logger.exception(f"Error in _process_image_update: {e}")
            self._show_error_placeholder(f"图像处理错误: {str(e)}")
    
    def _show_error_placeholder(self, error_text: str) -> None:
        """显示错误占位图"""
        c = self._theme.colors
        
        # 创建错误占位图像
        placeholder = QImage(200, 150, QImage.Format.Format_RGB32)
        placeholder.fill(QColor(c['canvas_bg']))
        
        painter = QPainter(placeholder)
        painter.setPen(QColor(c['danger']))
        font = painter.font()
        font.setPointSize(self._theme.get_font_size('body_medium'))
        painter.setFont(font)
        
        # 绘制错误文字
        painter.drawText(
            placeholder.rect(),
            Qt.AlignmentFlag.AlignCenter,
            error_text
        )
        painter.end()
        
        self._current_image = placeholder
        self._update_display_image()
    
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
        # [AutoFix 2026-04-18] 修复：设备连接后自动启动预览刷新
        previous_connected = self._is_connected
        self._device_status = status
        self._is_connected = connected
        
        self._status_label.setText(status)
        self._update_status_indicator()
        
        # 如果断开连接，显示占位图并停止自动刷新
        if not connected:
            self._show_placeholder()
            self._resolution_label.setText("")
            self.stop_auto_refresh()
            logger.info("设备已断开，停止预览自动刷新")
        else:
            # 设备刚连接（之前未连接），启动自动刷新
            if not previous_connected:
                self.start_auto_refresh()
                logger.info("设备已连接，启动预览自动刷新")
    
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