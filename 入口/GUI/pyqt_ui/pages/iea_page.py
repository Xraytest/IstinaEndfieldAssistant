"""
IEA任务链推理页面
整合设备连接和任务链推理功能于一个页面内
"""

from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QGroupBox,
    QSplitter,
    QFrame,
    QMessageBox,
    QProgressBar,
    QTreeWidget,
    QTreeWidgetItem,
    QComboBox,
    QTextEdit,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

# 支持两种导入方式
try:
    from ..theme.theme_manager import ThemeManager
    from ..widgets.base_widgets import PrimaryButton, SecondaryButton, DangerButton, CardWidget
    from ..widgets.task_list import TaskListItem, DragDropTaskList
    from ..widgets.device_preview import DevicePreviewWidget
    from ..widgets.status_indicator import ConnectionStatusIndicator, StatusIndicatorWidget
except ImportError:
    import sys
    import os
    # 计算项目根目录路径
    current_file = os.path.abspath(__file__)
    pages_dir = os.path.dirname(current_file)
    pyqt_ui_dir = os.path.dirname(pages_dir)
    gui_dir = os.path.dirname(pyqt_ui_dir)
    entry_dir = os.path.dirname(gui_dir)
    istina_dir = os.path.dirname(entry_dir)
    project_root = os.path.dirname(istina_dir)
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if istina_dir not in sys.path:
        sys.path.insert(0, istina_dir)
    
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.theme.theme_manager import ThemeManager
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.base_widgets import PrimaryButton, SecondaryButton, DangerButton, CardWidget
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.task_list import TaskListItem, DragDropTaskList
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.device_preview import DevicePreviewWidget
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.status_indicator import ConnectionStatusIndicator, StatusIndicatorWidget


class IEAPage(QWidget):
    """
    IEA任务链推理页面 - 整合设备连接与任务链推理

    布局：
    ┌─────────────────────────────────────────────────────────────┐
    │  [设备状态] [执行状态] 当前任务: xxx          [连接模式▼]     │
    ├──────────┬──────────────────────────────┬───────────────────┤
    │ 设备列表  │                              │   任务队列         │
    │ [扫描]   │      屏幕预览                 │   [添加] [删除]    │
    │ [连接]   │                              │   ┌───────────┐    │
    │ [断开]   │                              │   │ 任务1     │    │
    │          │                              │   │ 任务2     │    │
    │ 手动输入: │                              │   └───────────┘    │
    │ [      ] │                              │                   │
    ├──────────┤                              ├───────────────────┤
    │ 任务详情 │                              │   执行控制         │
    │ 名称: -  │                              │   [▶ 启动推理]     │
    │ 状态: -  │                              │   [■ 停止推理]     │
    │ 进度:    │                              │   次数: [1] [循环] │
    └──────────┴──────────────────────────────┴───────────────────┤
    │ 推理日志                                      [清空]        │
    └─────────────────────────────────────────────────────────────┘
    """

    # 设备相关信号
    connect_requested = pyqtSignal(str)
    disconnect_requested = pyqtSignal()
    scan_requested = pyqtSignal()
    device_selected = pyqtSignal(str)
    screenshot_requested = pyqtSignal()

    # 任务链相关信号
    task_added = pyqtSignal(dict)
    task_started = pyqtSignal(str)
    task_stopped = pyqtSignal(str)
    task_deleted = pyqtSignal(str)
    task_reordered = pyqtSignal(list)
    execution_count_changed = pyqtSignal(int)
    start_execution_requested = pyqtSignal()
    stop_execution_requested = pyqtSignal()

    MODE_ANDROID = "android"
    MODE_PC = "pc_foreground"

    STATUS_IDLE = "idle"
    STATUS_RUNNING = "running"
    STATUS_PAUSED = "paused"

    def __init__(self, parent: Optional[QWidget] = None, connection_mode: str = MODE_ANDROID) -> None:
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._connection_mode = connection_mode
        self._is_connected = False
        self._current_device = None
        self._device_info = {}
        self._execution_status = self.STATUS_IDLE
        self._current_task_id = None
        self._execution_count = 1
        self._infinite_loop = False

        self._setup_ui()
        self._setup_style()
        self._setup_connections()
        self._update_mode_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # === 顶部状态栏 ===
        top_bar = self._create_top_bar()
        main_layout.addWidget(top_bar)

        # === 主分割区域 ===
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：设备连接
        left_panel = self._create_device_panel()
        main_splitter.addWidget(left_panel)

        # 中间：屏幕预览
        center_panel = self._create_preview_panel()
        main_splitter.addWidget(center_panel)

        # 右侧：任务队列和执行控制
        right_panel = self._create_task_panel()
        main_splitter.addWidget(right_panel)

        main_splitter.setSizes([280, 520, 300])
        main_layout.addWidget(main_splitter, stretch=1)

        # === 底部日志 ===
        log_panel = self._create_log_panel()
        main_layout.addWidget(log_panel)

    def _create_top_bar(self) -> QWidget:
        """创建顶部状态栏"""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 设备状态
        self._device_status_indicator = ConnectionStatusIndicator(connection_type="device")
        layout.addWidget(self._device_status_indicator)

        # 执行状态
        self._execution_status_indicator = StatusIndicatorWidget(
            initial_status=StatusIndicatorWidget.STATUS_DISCONNECTED,
            show_text=True,
            enable_animation=True
        )
        layout.addWidget(self._execution_status_indicator)

        # 当前任务
        self._current_task_label = QLabel("当前任务: 无")
        self._current_task_label.setProperty("variant", "secondary")
        layout.addWidget(self._current_task_label)

        layout.addStretch()

        # 连接模式选择
        mode_label = QLabel("连接模式:")
        mode_label.setProperty("variant", "secondary")
        layout.addWidget(mode_label)

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Android设备", "PC前台模式"])
        self._mode_combo.setCurrentIndex(0 if self._connection_mode == self.MODE_ANDROID else 1)
        self._mode_combo.setFixedWidth(130)
        layout.addWidget(self._mode_combo)

        return frame

    def _create_device_panel(self) -> QWidget:
        """创建设备连接面板（左侧）"""
        panel = CardWidget()
        layout = panel.get_content_layout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 标题
        title = QLabel("设备连接")
        title.setProperty("variant", "header")
        layout.addWidget(title)

        # 设备列表
        self._device_tree = QTreeWidget()
        self._device_tree.setHeaderLabels(["设备", "状态"])
        self._device_tree.setRootIsDecorated(False)
        self._device_tree.setAlternatingRowColors(True)
        self._device_tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self._device_tree.setColumnWidth(0, 140)
        self._device_tree.setColumnWidth(1, 80)
        self._device_tree.setMaximumHeight(150)
        layout.addWidget(self._device_tree)

        # PC模式提示
        self._pc_hint = QLabel("PC模式：直接控制Endfield窗口")
        self._pc_hint.setProperty("variant", "muted")
        self._pc_hint.setWordWrap(True)
        self._pc_hint.setVisible(False)
        layout.addWidget(self._pc_hint)

        # 手动输入
        input_frame = QFrame()
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(6)

        self._manual_input = QLineEdit()
        self._manual_input.setPlaceholderText("设备序列号/IP")
        input_layout.addWidget(self._manual_input)

        self._manual_connect_btn = SecondaryButton("连接")
        self._manual_connect_btn.setFixedWidth(50)
        input_layout.addWidget(self._manual_connect_btn)

        layout.addWidget(input_frame)

        # 控制按钮
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)

        self._scan_btn = SecondaryButton("扫描")
        self._scan_btn.setFixedWidth(50)
        btn_layout.addWidget(self._scan_btn)

        self._connect_btn = PrimaryButton("连接")
        btn_layout.addWidget(self._connect_btn, stretch=1)

        self._disconnect_btn = DangerButton("断开")
        self._disconnect_btn.setEnabled(False)
        btn_layout.addWidget(self._disconnect_btn, stretch=1)

        layout.addWidget(btn_frame)

        # 设备信息
        info_group = QGroupBox("设备信息")
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(4)

        self._serial_label = QLabel("序列号: -")
        self._serial_label.setProperty("variant", "secondary")
        info_layout.addWidget(self._serial_label)

        self._resolution_label = QLabel("分辨率: -")
        self._resolution_label.setProperty("variant", "secondary")
        info_layout.addWidget(self._resolution_label)

        layout.addWidget(info_group)
        layout.addStretch()

        return panel

    def _create_preview_panel(self) -> QWidget:
        """创建屏幕预览面板（中间）"""
        panel = CardWidget()
        layout = panel.get_content_layout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 预览组件
        self._preview_widget = DevicePreviewWidget(auto_refresh_interval=500)
        self._preview_widget.setMinimumHeight(300)
        layout.addWidget(self._preview_widget, stretch=1)

        return panel

    def _create_task_panel(self) -> QWidget:
        """创建任务面板（右侧）"""
        panel = CardWidget()
        layout = panel.get_content_layout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 任务队列标题
        queue_header = QFrame()
        queue_header_layout = QHBoxLayout(queue_header)
        queue_header_layout.setContentsMargins(0, 0, 0, 0)

        queue_title = QLabel("任务队列")
        queue_title.setProperty("variant", "header")
        queue_header_layout.addWidget(queue_title)

        queue_header_layout.addStretch()

        self._queue_count_label = QLabel("0个任务")
        self._queue_count_label.setProperty("variant", "muted")
        queue_header_layout.addWidget(self._queue_count_label)

        layout.addWidget(queue_header)

        # 任务列表
        self._task_list = DragDropTaskList()
        layout.addWidget(self._task_list, stretch=1)

        # 任务操作按钮
        task_btn_frame = QFrame()
        task_btn_layout = QHBoxLayout(task_btn_frame)
        task_btn_layout.setContentsMargins(0, 0, 0, 0)
        task_btn_layout.setSpacing(8)

        self._add_task_btn = PrimaryButton("添加任务")
        task_btn_layout.addWidget(self._add_task_btn)

        self._delete_task_btn = DangerButton("删除")
        self._delete_task_btn.setFixedWidth(60)
        task_btn_layout.addWidget(self._delete_task_btn)

        layout.addWidget(task_btn_frame)

        # 选中的任务详情
        details_group = QGroupBox("当前任务")
        details_layout = QVBoxLayout(details_group)
        details_layout.setSpacing(6)

        self._task_name_display = QLabel("-")
        self._task_name_display.setProperty("variant", "primary")
        details_layout.addWidget(self._task_name_display)

        self._task_status_display = QLabel("状态: -")
        self._task_status_display.setProperty("variant", "secondary")
        details_layout.addWidget(self._task_status_display)

        # 进度条
        progress_frame = QFrame()
        progress_layout = QHBoxLayout(progress_frame)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)

        self._task_progress_bar = QProgressBar()
        self._task_progress_bar.setMinimum(0)
        self._task_progress_bar.setMaximum(100)
        self._task_progress_bar.setValue(0)
        self._task_progress_bar.setTextVisible(False)
        self._task_progress_bar.setFixedHeight(6)
        progress_layout.addWidget(self._task_progress_bar, stretch=1)

        self._progress_percent_label = QLabel("0%")
        self._progress_percent_label.setProperty("variant", "secondary")
        self._progress_percent_label.setFixedWidth(35)
        progress_layout.addWidget(self._progress_percent_label)

        details_layout.addWidget(progress_frame)
        layout.addWidget(details_group)

        # 执行控制
        exec_group = QGroupBox("执行控制")
        exec_layout = QVBoxLayout(exec_group)
        exec_layout.setSpacing(8)

        self._start_btn = PrimaryButton("▶ 启动推理")
        exec_layout.addWidget(self._start_btn)

        self._stop_btn = DangerButton("■ 停止推理")
        self._stop_btn.setEnabled(False)
        exec_layout.addWidget(self._stop_btn)

        # 执行设置
        settings_frame = QFrame()
        settings_layout = QHBoxLayout(settings_frame)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(8)

        count_label = QLabel("次数:")
        count_label.setProperty("variant", "secondary")
        settings_layout.addWidget(count_label)

        self._execution_spinbox = QSpinBox()
        self._execution_spinbox.setMinimum(1)
        self._execution_spinbox.setMaximum(99)
        self._execution_spinbox.setValue(1)
        self._execution_spinbox.setFixedWidth(50)
        settings_layout.addWidget(self._execution_spinbox)

        self._infinite_checkbox = QCheckBox("循环")
        settings_layout.addWidget(self._infinite_checkbox)

        settings_layout.addStretch()
        exec_layout.addWidget(settings_frame)

        layout.addWidget(exec_group)

        return panel

    def _create_log_panel(self) -> QWidget:
        """创建日志面板"""
        panel = CardWidget()
        layout = panel.get_content_layout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # 日志头部
        log_header = QFrame()
        log_header_layout = QHBoxLayout(log_header)
        log_header_layout.setContentsMargins(0, 0, 0, 0)

        log_title = QLabel("推理日志")
        log_title.setProperty("variant", "header")
        log_header_layout.addWidget(log_title)

        log_header_layout.addStretch()

        self._clear_log_btn = QPushButton("清空")
        self._clear_log_btn.setFixedWidth(50)
        self._clear_log_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #48484a;
                border-radius: 4px;
                color: #98989d;
                padding: 2px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3a3a3c;
                color: #ffffff;
            }
        """)
        log_header_layout.addWidget(self._clear_log_btn)

        layout.addWidget(log_header)

        # 日志文本
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(100)
        self._log_text.setPlaceholderText("推理日志将显示在这里...")
        layout.addWidget(self._log_text)

        return panel

    def _setup_style(self) -> None:
        """设置样式"""
        # 设备树样式
        self._device_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #48484a;
                border-radius: 6px;
                background-color: #2c2c2e;
            }
            QTreeWidget::item {
                padding: 6px;
                border: none;
            }
            QTreeWidget::item:selected {
                background-color: #4361ee;
                color: white;
                border-radius: 4px;
            }
            QTreeWidget::item:hover:!selected {
                background-color: #3a3a3c;
                border-radius: 4px;
            }
            QTreeWidget::header {
                background-color: #3a3a3c;
                border-bottom: 1px solid #48484a;
                padding: 4px;
            }
        """)

        # 进度条样式
        self._task_progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #2c2c2e;
            }
            QProgressBar::chunk {
                background-color: #4361ee;
                border-radius: 3px;
            }
        """)

        # 复选框样式
        self._infinite_checkbox.setStyleSheet("""
            QCheckBox {
                color: #98989d;
                spacing: 4px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #48484a;
                border-radius: 4px;
                background-color: #2c2c2e;
            }
            QCheckBox::indicator:checked {
                background-color: #4361ee;
                border-color: #4361ee;
            }
        """)

        # SpinBox样式
        self._execution_spinbox.setStyleSheet("""
            QSpinBox {
                border: 1px solid #48484a;
                border-radius: 4px;
                background-color: #2c2c2e;
                color: #ffffff;
                padding: 2px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #3a3a3c;
                border: none;
                width: 16px;
            }
        """)

        # 日志样式
        self._log_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #48484a;
                border-radius: 6px;
                background-color: #1c1c1e;
                color: #98989d;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                padding: 4px;
            }
        """)

        # 分组框样式
        group_style = """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #48484a;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 6px;
                padding-bottom: 6px;
                padding-left: 10px;
                padding-right: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
                color: #98989d;
                font-size: 11px;
            }
        """
        for group in self.findChildren(QGroupBox):
            group.setStyleSheet(group_style)

    def _setup_connections(self) -> None:
        """设置信号连接"""
        # 设备相关
        self._scan_btn.clicked.connect(self.scan_requested.emit)
        self._connect_btn.clicked.connect(self._on_connect_clicked)
        self._disconnect_btn.clicked.connect(self.disconnect_requested.emit)
        self._manual_connect_btn.clicked.connect(self._on_manual_connect_clicked)
        self._device_tree.itemSelectionChanged.connect(self._on_device_selection_changed)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self._preview_widget.screenshot_requested.connect(self.screenshot_requested.emit)

        # 任务相关
        self._add_task_btn.clicked.connect(self.task_added.emit)
        self._delete_task_btn.clicked.connect(self._on_delete_task_clicked)
        self._task_list.task_selected.connect(self._on_task_selected)
        self._task_list.task_order_changed.connect(self.task_reordered.emit)
        self._task_list.itemDoubleClicked.connect(self._on_task_double_clicked)
        self._start_btn.clicked.connect(self._on_start_clicked)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        self._execution_spinbox.valueChanged.connect(self.execution_count_changed.emit)
        self._infinite_checkbox.stateChanged.connect(self._on_infinite_changed)
        self._clear_log_btn.clicked.connect(self._log_text.clear)

    def _update_mode_ui(self) -> None:
        """根据连接模式更新UI"""
        is_android = self._connection_mode == self.MODE_ANDROID
        self._device_tree.setVisible(is_android)
        self._scan_btn.setVisible(is_android)
        self._pc_hint.setVisible(not is_android)
        self._connect_btn.setText("连接设备" if is_android else "连接窗口")

    def _on_connect_clicked(self) -> None:
        """连接按钮点击"""
        if self._connection_mode == self.MODE_PC:
            self.connect_requested.emit("Endfield")
        else:
            selected = self._device_tree.selectedItems()
            if selected:
                self.connect_requested.emit(selected[0].text(0))
            elif self._manual_input.text().strip():
                self.connect_requested.emit(self._manual_input.text().strip())
            else:
                QMessageBox.warning(self, "提示", "请选择设备或输入序列号")

    def _on_manual_connect_clicked(self) -> None:
        """手动连接"""
        device = self._manual_input.text().strip()
        if device:
            self.connect_requested.emit(device)

    def _on_device_selection_changed(self) -> None:
        """设备选择变化"""
        selected = self._device_tree.selectedItems()
        if selected:
            self.device_selected.emit(selected[0].text(0))

    def _on_mode_changed(self, index: int) -> None:
        """模式切换"""
        self._connection_mode = self.MODE_ANDROID if index == 0 else self.MODE_PC
        self._update_mode_ui()

    def _on_task_selected(self, task_id: str) -> None:
        """任务选中"""
        for i in range(self._task_list.count()):
            item = self._task_list.item(i)
            if isinstance(item, TaskListItem) and item.task_id == task_id:
                self._update_task_details(item)
                break

    def _on_task_double_clicked(self, item: QListWidgetItem) -> None:
        """任务双击"""
        if isinstance(item, TaskListItem):
            self.task_started.emit(item.task_id)

    def _on_delete_task_clicked(self) -> None:
        """删除任务"""
        selected = self._task_list.selectedItems()
        if not selected:
            return
        item = selected[0]
        if isinstance(item, TaskListItem):
            self._task_list.takeItem(self._task_list.row(item))
            self.task_deleted.emit(item.task_id)
            self._update_queue_count()

    def _on_start_clicked(self) -> None:
        """启动推理"""
        if not self._is_connected:
            QMessageBox.warning(self, "提示", "请先连接设备")
            return
        if self._task_list.count() == 0:
            QMessageBox.warning(self, "提示", "请先添加任务")
            return
        self._execution_status = self.STATUS_RUNNING
        self._update_execution_status()
        self.start_execution_requested.emit()
        self.append_log("启动任务链推理", "INFO")

    def _on_stop_clicked(self) -> None:
        """停止推理"""
        self._execution_status = self.STATUS_IDLE
        self._update_execution_status()
        self.stop_execution_requested.emit()
        self.append_log("停止任务链推理", "INFO")

    def _on_infinite_changed(self, state: int) -> None:
        """循环模式变化"""
        self._infinite_loop = state == Qt.CheckState.Checked.value
        self._execution_spinbox.setEnabled(not self._infinite_loop)

    def _update_task_details(self, item: TaskListItem) -> None:
        """更新任务详情显示"""
        self._task_name_display.setText(item.task_name)
        status_map = {
            TaskListItem.STATUS_PENDING: "待执行",
            TaskListItem.STATUS_RUNNING: "执行中",
            TaskListItem.STATUS_COMPLETED: "已完成",
            TaskListItem.STATUS_FAILED: "失败",
            TaskListItem.STATUS_PAUSED: "已暂停",
        }
        self._task_status_display.setText(f"状态: {status_map.get(item.status, '未知')}")
        self._task_progress_bar.setValue(item.progress)
        self._progress_percent_label.setText(f"{item.progress}%")

    def _update_execution_status(self) -> None:
        """更新执行状态"""
        if self._execution_status == self.STATUS_RUNNING:
            self._execution_status_indicator.set_status(StatusIndicatorWidget.STATUS_CONNECTED)
            self._execution_status_indicator.set_status_text("推理中")
            self._start_btn.setEnabled(False)
            self._stop_btn.setEnabled(True)
        else:
            self._execution_status_indicator.set_status(StatusIndicatorWidget.STATUS_DISCONNECTED)
            self._execution_status_indicator.set_status_text("待执行")
            self._start_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)

    def _update_queue_count(self) -> None:
        """更新任务数量"""
        count = self._task_list.count()
        self._queue_count_label.setText(f"{count}个任务")

    # === 公共方法 ===

    def update_device_list(self, devices: List[Any]) -> None:
        """更新设备列表"""
        self._device_tree.clear()
        for device in devices:
            if isinstance(device, dict):
                serial = device.get('serial', 'Unknown')
                status = device.get('status', 'Unknown')
            else:
                serial = getattr(device, 'serial', 'Unknown')
                status = getattr(device, 'status', 'Unknown')
            item = QTreeWidgetItem([serial, status])
            if status == 'device':
                item.setForeground(1, QColor(self._theme.get_color('success')))
            elif status == 'offline':
                item.setForeground(1, QColor(self._theme.get_color('danger')))
            self._device_tree.addTopLevelItem(item)

    def set_connected(self, is_connected: bool, device_info: Optional[Dict[str, Any]] = None) -> None:
        """设置连接状态"""
        self._is_connected = is_connected
        self._device_info = device_info or {}

        if is_connected:
            self._device_status_indicator.set_connected()
            self._disconnect_btn.setEnabled(True)
            self._connect_btn.setEnabled(False)
            self._scan_btn.setEnabled(False)

            self._current_device = device_info.get('serial', 'Unknown') if device_info else 'Unknown'
            self._serial_label.setText(f"序列号: {self._current_device}")
            self._resolution_label.setText(f"分辨率: {device_info.get('resolution', '-')}")
            self._preview_widget.set_device_status(f"已连接: {self._current_device}", connected=True)
            self.start_preview_refresh()
            self.append_log(f"设备已连接: {self._current_device}", "SUCCESS")
        else:
            self._device_status_indicator.set_disconnected()
            self._disconnect_btn.setEnabled(False)
            self._connect_btn.setEnabled(True)
            self._scan_btn.setEnabled(True)

            self._current_device = None
            self._serial_label.setText("序列号: -")
            self._resolution_label.setText("分辨率: -")
            self._preview_widget.set_device_status("未连接", connected=False)
            self.stop_preview_refresh()
            self.append_log("设备已断开", "INFO")

    def update_preview(self, image_data: bytes) -> None:
        """更新预览"""
        self._preview_widget.update_image(image_data)

    def start_preview_refresh(self) -> None:
        """启动预览刷新"""
        self._preview_widget.start_auto_refresh()

    def stop_preview_refresh(self) -> None:
        """停止预览刷新"""
        self._preview_widget.stop_auto_refresh()

    def add_task(self, task_id: str, task_name: str, data: Optional[Dict[str, Any]] = None) -> None:
        """添加任务"""
        item = TaskListItem(
            task_id=task_id,
            task_name=task_name,
            status=TaskListItem.STATUS_PENDING,
            data=data
        )
        self._task_list.addItem(item)
        self._update_queue_count()
        self.append_log(f"添加任务: {task_name}", "INFO")

    def update_task_status(self, task_id: str, status: str, progress: int = 0) -> None:
        """更新任务状态"""
        for i in range(self._task_list.count()):
            item = self._task_list.item(i)
            if isinstance(item, TaskListItem) and item.task_id == task_id:
                item.set_status(status)
                item.set_progress(progress)
                if self._task_list.currentItem() == item:
                    self._update_task_details(item)
                return

    def set_current_task(self, task_id: str, task_name: str) -> None:
        """设置当前任务"""
        self._current_task_id = task_id
        self._current_task_label.setText(f"当前任务: {task_name}")

    def clear_current_task(self) -> None:
        """清除当前任务"""
        self._current_task_id = None
        self._current_task_label.setText("当前任务: 无")

    def clear_queue(self) -> None:
        """清空队列"""
        self._task_list.clear()
        self._update_queue_count()

    def get_task_queue(self) -> List[str]:
        """获取任务队列"""
        return [self._task_list.item(i).task_id for i in range(self._task_list.count())
                if isinstance(self._task_list.item(i), TaskListItem)]

    def set_execution_running(self, is_running: bool) -> None:
        """设置执行状态"""
        self._execution_status = self.STATUS_RUNNING if is_running else self.STATUS_IDLE
        self._update_execution_status()

    def append_log(self, message: str, level: str = "INFO") -> None:
        """添加日志"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        colors = {"INFO": "#98989d", "SUCCESS": "#34c759", "WARNING": "#ff9500", "ERROR": "#ff3b30"}
        color = colors.get(level, "#98989d")
        self._log_text.append(
            f'<span style="color: #636366;">[{timestamp}]</span> '
            f'<span style="color: {color};">[{level}]</span> {message}'
        )
        scrollbar = self._log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log(self) -> None:
        """清空日志"""
        self._log_text.clear()
