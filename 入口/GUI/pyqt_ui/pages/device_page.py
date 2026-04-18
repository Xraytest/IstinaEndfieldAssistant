"""
设备管理页面
管理设备连接、屏幕预览和设备信息显示
"""

from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QGroupBox,
    QSplitter,
    QFrame,
    QComboBox,
    QSizePolicy,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

# 支持两种导入方式
try:
    from ..theme.theme_manager import ThemeManager
    from ..widgets.base_widgets import PrimaryButton, SecondaryButton, DangerButton, CardWidget
    from ..widgets.device_preview import DevicePreviewWidget
    from ..widgets.status_indicator import ConnectionStatusIndicator
except ImportError:
    from theme.theme_manager import ThemeManager
    from widgets.base_widgets import PrimaryButton, SecondaryButton, DangerButton, CardWidget
    from widgets.device_preview import DevicePreviewWidget
    from widgets.status_indicator import ConnectionStatusIndicator


class DevicePage(QWidget):
    """
    设备管理页面
    
    功能：
    - 设备连接状态显示（使用ConnectionStatusIndicator）
    - 设备屏幕预览区域（使用DevicePreviewWidget）
    - 设备信息面板（分辨率、连接方式等）
    - 连接/断开按钮
    - ADB配置区域
    
    信号：
    - connect_requested(str): 连接请求信号，携带设备序列号
    - disconnect_requested(): 断开连接请求信号
    - scan_requested(): 扫描设备请求信号
    - device_selected(str): 设备选择信号
    """
    
    # 自定义信号
    connect_requested = pyqtSignal(str)  # 连接请求信号，参数为设备序列号
    disconnect_requested = pyqtSignal()  # 断开连接请求信号
    scan_requested = pyqtSignal()        # 扫描设备请求信号
    device_selected = pyqtSignal(str)    # 设备选择信号
    
    # 连接模式常量
    MODE_ANDROID = "android"
    MODE_PC = "pc_foreground"
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        connection_mode: str = MODE_ANDROID
    ) -> None:
        """
        初始化设备管理页面
        
        Args:
            parent: 父控件
            connection_mode: 连接模式 (android 或 pc_foreground)
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._connection_mode = connection_mode
        self._is_connected: bool = False
        self._current_device: Optional[str] = None
        self._device_info: Dict[str, Any] = {}
        
        self._setup_ui()
        self._setup_style()
        self._setup_connections()
        
        # 根据连接模式切换UI
        self._update_mode_ui()
    
    def _setup_ui(self) -> None:
        """设置UI结构"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md')
        )
        main_layout.setSpacing(self._theme.get_spacing('md'))
        
        # === 顶部：连接状态和控制 ===
        top_frame = QFrame()
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 连接状态指示器
        self._status_indicator = ConnectionStatusIndicator(
            connection_type="device"
        )
        top_layout.addWidget(self._status_indicator)
        
        # 连接模式选择
        mode_frame = QFrame()
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(self._theme.get_spacing('sm'))
        
        mode_label = QLabel("连接模式:")
        mode_label.setProperty("variant", "secondary")
        mode_layout.addWidget(mode_label)
        
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Android设备", "PC前台模式"])
        self._mode_combo.setCurrentIndex(0 if self._connection_mode == self.MODE_ANDROID else 1)
        self._mode_combo.setFixedWidth(150)
        mode_layout.addWidget(self._mode_combo)
        
        top_layout.addWidget(mode_frame)
        top_layout.addStretch()
        
        main_layout.addWidget(top_frame)
        
        # === 中间：分割区域 ===
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：设备列表和控制
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # 右侧：屏幕预览
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割比例
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter, stretch=1)
        
        # === 底部：设备信息面板 ===
        info_panel = self._create_info_panel()
        main_layout.addWidget(info_panel)
    
    def _create_left_panel(self) -> QWidget:
        """创建左侧面板（设备列表和控制按钮）"""
        panel = CardWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm')
        )
        layout.setSpacing(self._theme.get_spacing('sm'))
        
        # Android模式：设备列表区域
        self._device_list_group = QGroupBox("可用设备")
        device_list_layout = QVBoxLayout(self._device_list_group)
        device_list_layout.setContentsMargins(
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm')
        )
        device_list_layout.setSpacing(self._theme.get_spacing('xs'))
        
        # 设备树形列表
        self._device_tree = QTreeWidget()
        self._device_tree.setHeaderLabels(["设备序列号", "型号", "状态"])
        self._device_tree.setRootIsDecorated(False)
        self._device_tree.setAlternatingRowColors(True)
        self._device_tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self._device_tree.setMinimumHeight(150)
        
        # 设置列宽
        self._device_tree.setColumnWidth(0, 200)
        self._device_tree.setColumnWidth(1, 150)
        self._device_tree.setColumnWidth(2, 100)
        
        device_list_layout.addWidget(self._device_tree)
        
        # 手动输入区域
        manual_frame = QFrame()
        manual_layout = QHBoxLayout(manual_frame)
        manual_layout.setContentsMargins(0, 0, 0, 0)
        manual_layout.setSpacing(self._theme.get_spacing('sm'))
        
        manual_label = QLabel("手动输入:")
        manual_label.setProperty("variant", "secondary")
        manual_layout.addWidget(manual_label)
        
        self._manual_input = QLineEdit()
        self._manual_input.setPlaceholderText("输入设备序列号或IP地址")
        self._manual_input.setFixedWidth(200)
        manual_layout.addWidget(self._manual_input)
        
        self._manual_connect_btn = SecondaryButton("连接")
        self._manual_connect_btn.setFixedWidth(80)
        manual_layout.addWidget(self._manual_connect_btn)
        
        manual_layout.addStretch()
        device_list_layout.addWidget(manual_frame)
        
        layout.addWidget(self._device_list_group)
        
        # PC模式：窗口连接区域
        self._pc_group = QGroupBox("PC窗口连接")
        pc_layout = QVBoxLayout(self._pc_group)
        pc_layout.setContentsMargins(
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm')
        )
        pc_layout.setSpacing(self._theme.get_spacing('sm'))
        
        # 窗口标题显示
        window_frame = QFrame()
        window_layout = QHBoxLayout(window_frame)
        window_layout.setContentsMargins(0, 0, 0, 0)
        
        window_label = QLabel("目标窗口: Endfield")
        window_label.setProperty("variant", "header")
        window_layout.addWidget(window_label)
        
        window_layout.addStretch()
        pc_layout.addWidget(window_frame)
        
        # PC模式说明
        info_label = QLabel("PC前台模式：直接控制PC上的Endfield游戏窗口，无需Android设备。")
        info_label.setProperty("variant", "muted")
        info_label.setWordWrap(True)
        pc_layout.addWidget(info_label)
        
        tip_label = QLabel("请确保Endfield游戏窗口已打开。")
        tip_label.setProperty("variant", "muted")
        tip_label.setWordWrap(True)
        pc_layout.addWidget(tip_label)
        
        layout.addWidget(self._pc_group)
        
        # 操作按钮区域
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(self._theme.get_spacing('md'))
        
        self._scan_btn = PrimaryButton("扫描设备")
        btn_layout.addWidget(self._scan_btn)
        
        self._connect_btn = PrimaryButton("连接选中设备")
        btn_layout.addWidget(self._connect_btn)
        
        self._disconnect_btn = DangerButton("断开连接")
        self._disconnect_btn.setEnabled(False)
        btn_layout.addWidget(self._disconnect_btn)
        
        btn_layout.addStretch()
        layout.addWidget(btn_frame)
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """创建右侧面板（屏幕预览）"""
        panel = CardWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm')
        )
        layout.setSpacing(self._theme.get_spacing('sm'))
        
        # 预览标题
        preview_title = QLabel("屏幕预览")
        preview_title.setProperty("variant", "header")
        layout.addWidget(preview_title)
        
        # 设备预览组件
        self._preview_widget = DevicePreviewWidget(
            auto_refresh_interval=500
        )
        self._preview_widget.setMinimumHeight(300)
        layout.addWidget(self._preview_widget, stretch=1)
        
        return panel
    
    def _create_info_panel(self) -> QWidget:
        """创建设备信息面板"""
        panel = CardWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm')
        )
        layout.setSpacing(self._theme.get_spacing('lg'))
        
        # 设备信息标题
        info_title = QLabel("设备信息")
        info_title.setProperty("variant", "header")
        layout.addWidget(info_title)
        
        # 分隔符
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setProperty("variant", "separator")
        layout.addWidget(separator)
        
        # 设备序列号
        self._serial_label = QLabel("序列号: -")
        self._serial_label.setProperty("variant", "secondary")
        layout.addWidget(self._serial_label)
        
        # 设备分辨率
        self._resolution_label = QLabel("分辨率: -")
        self._resolution_label.setProperty("variant", "secondary")
        layout.addWidget(self._resolution_label)
        
        # 连接方式
        self._method_label = QLabel("连接方式: -")
        self._method_label.setProperty("variant", "secondary")
        layout.addWidget(self._method_label)
        
        layout.addStretch()
        
        return panel
    
    def _setup_style(self) -> None:
        """设置样式"""
        # 页面样式通过QApplication全局应用，这里只设置特定控件样式
        
        # 设置分组框样式
        group_style = """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #48484a;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """
        
        self._device_list_group.setStyleSheet(group_style)
        self._pc_group.setStyleSheet(group_style)
        
        # 设置设备树样式
        self._device_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #48484a;
                border-radius: 4px;
                background-color: #2c2c2e;
            }
            QTreeWidget::item {
                padding: 4px;
                border: none;
            }
            QTreeWidget::item:selected {
                background-color: #4361ee;
                color: white;
            }
            QTreeWidget::item:hover:!selected {
                background-color: #3a3a3c;
            }
            QTreeWidget::header {
                background-color: #2c2c2e;
                border-bottom: 1px solid #48484a;
            }
        """)
    
    def _setup_connections(self) -> None:
        """设置信号连接"""
        # 按钮点击信号
        self._scan_btn.clicked.connect(self._on_scan_clicked)
        self._connect_btn.clicked.connect(self._on_connect_clicked)
        self._disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        self._manual_connect_btn.clicked.connect(self._on_manual_connect_clicked)
        
        # 设备树选择信号
        self._device_tree.itemSelectionChanged.connect(self._on_device_selection_changed)
        
        # 连接模式切换
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        
        # 预览刷新信号
        self._preview_widget.refresh_requested.connect(self._on_refresh_requested)
    
    def _update_mode_ui(self) -> None:
        """根据连接模式更新UI显示"""
        if self._connection_mode == self.MODE_ANDROID:
            self._device_list_group.setVisible(True)
            self._pc_group.setVisible(False)
            self._scan_btn.setVisible(True)
            self._connect_btn.setText("连接选中设备")
        else:
            self._device_list_group.setVisible(False)
            self._pc_group.setVisible(True)
            self._scan_btn.setVisible(False)
            self._connect_btn.setText("连接窗口")
    
    # === 信号处理方法 ===
    
    def _on_scan_clicked(self) -> None:
        """扫描设备按钮点击"""
        self.scan_requested.emit()
    
    def _on_connect_clicked(self) -> None:
        """连接按钮点击"""
        if self._connection_mode == self.MODE_PC:
            # PC模式：直接连接窗口
            self.connect_requested.emit("Endfield")
        else:
            # Android模式：连接选中设备
            selected_items = self._device_tree.selectedItems()
            if selected_items:
                device_serial = selected_items[0].text(0)
                self.connect_requested.emit(device_serial)
            else:
                # 尝试使用手动输入
                manual_device = self._manual_input.text().strip()
                if manual_device:
                    self.connect_requested.emit(manual_device)
                else:
                    QMessageBox.warning(self, "警告", "请先选择一个设备或手动输入设备序列号")
    
    def _on_disconnect_clicked(self) -> None:
        """断开连接按钮点击"""
        self.disconnect_requested.emit()
    
    def _on_manual_connect_clicked(self) -> None:
        """手动连接按钮点击"""
        device_serial = self._manual_input.text().strip()
        if device_serial:
            self.connect_requested.emit(device_serial)
        else:
            QMessageBox.warning(self, "警告", "请输入设备序列号或IP地址")
    
    def _on_device_selection_changed(self) -> None:
        """设备选择变化"""
        selected_items = self._device_tree.selectedItems()
        if selected_items:
            device_serial = selected_items[0].text(0)
            self.device_selected.emit(device_serial)
    
    def _on_mode_changed(self, index: int) -> None:
        """连接模式切换"""
        self._connection_mode = self.MODE_ANDROID if index == 0 else self.MODE_PC
        self._update_mode_ui()
    
    def _on_refresh_requested(self) -> None:
        """预览刷新请求"""
        # 这里可以触发截图刷新
        pass
    
    # === 公共方法 ===
    
    def update_device_list(self, devices: List[Dict[str, Any]]) -> None:
        """
        更新设备列表
        
        Args:
            devices: 设备列表，每个设备包含 serial, model, status 等字段
        """
        self._device_tree.clear()
        
        for device in devices:
            item = QTreeWidgetItem([
                device.get('serial', 'Unknown'),
                device.get('model', 'Unknown'),
                device.get('status', 'Unknown')
            ])
            
            # 根据状态设置颜色
            status = device.get('status', '')
            if status == 'device':
                item.setForeground(2, QColor(self._theme.get_color('success')))
            elif status == 'offline':
                item.setForeground(2, QColor(self._theme.get_color('danger')))
            else:
                item.setForeground(2, QColor(self._theme.get_color('warning')))
            
            self._device_tree.addTopLevelItem(item)
    
    def set_connected(self, is_connected: bool, device_info: Optional[Dict[str, Any]] = None) -> None:
        """
        设置连接状态
        
        Args:
            is_connected: 是否已连接
            device_info: 设备信息字典
        """
        self._is_connected = is_connected
        self._device_info = device_info or {}
        
        if is_connected:
            self._status_indicator.set_connected()
            self._disconnect_btn.setEnabled(True)
            self._connect_btn.setEnabled(False)
            self._scan_btn.setEnabled(False)
            
            # 更新设备信息显示
            if device_info:
                self._current_device = device_info.get('serial', 'Unknown')
                self._serial_label.setText(f"序列号: {self._current_device}")
                resolution = device_info.get('resolution', '-')
                self._resolution_label.setText(f"分辨率: {resolution}")
                method = device_info.get('method', self._connection_mode)
                method_text = "ADB" if method == self.MODE_ANDROID else "PC窗口"
                self._method_label.setText(f"连接方式: {method_text}")
                
                # 更新预览状态
                self._preview_widget.set_device_status(f"已连接: {self._current_device}", connected=True)
        else:
            self._status_indicator.set_disconnected()
            self._disconnect_btn.setEnabled(False)
            self._connect_btn.setEnabled(True)
            self._scan_btn.setEnabled(True)
            
            # 清空设备信息显示
            self._current_device = None
            self._serial_label.setText("序列号: -")
            self._resolution_label.setText("分辨率: -")
            self._method_label.setText("连接方式: -")
            
            # 更新预览状态
            self._preview_widget.set_device_status("未连接", connected=False)
    
    def update_preview_image(self, image_data: bytes) -> None:
        """
        更新预览图像
        
        Args:
            image_data: 图像数据（bytes格式）
        """
        self._preview_widget.update_image(image_data)
    
    def start_preview_refresh(self) -> None:
        """启动预览自动刷新"""
        self._preview_widget.start_auto_refresh()
    
    def stop_preview_refresh(self) -> None:
        """停止预览自动刷新"""
        self._preview_widget.stop_auto_refresh()
    
    def get_connection_mode(self) -> str:
        """获取当前连接模式"""
        return self._connection_mode
    
    def set_connection_mode(self, mode: str) -> None:
        """
        设置连接模式
        
        Args:
            mode: 连接模式 (android 或 pc_foreground)
        """
        self._connection_mode = mode
        self._mode_combo.setCurrentIndex(0 if mode == self.MODE_ANDROID else 1)
        self._update_mode_ui()
    
    def get_current_device(self) -> Optional[str]:
        """获取当前连接的设备"""
        return self._current_device
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._is_connected