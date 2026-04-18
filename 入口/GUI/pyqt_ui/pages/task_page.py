"""
任务管理页面
管理任务队列、执行控制和任务详情显示
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
    QSizePolicy,
    QMessageBox,
    QProgressBar,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

# 支持两种导入方式
try:
    from ..theme.theme_manager import ThemeManager
    from ..widgets.base_widgets import PrimaryButton, SecondaryButton, DangerButton, CardWidget
    from ..widgets.task_list import TaskListWidget, TaskListItem, DragDropTaskList
    from ..widgets.status_indicator import StatusIndicatorWidget
except ImportError:
    from theme.theme_manager import ThemeManager
    from widgets.base_widgets import PrimaryButton, SecondaryButton, DangerButton, CardWidget
    from widgets.task_list import TaskListWidget, TaskListItem, DragDropTaskList
    from widgets.status_indicator import StatusIndicatorWidget


class TaskPage(QWidget):
    """
    任务管理页面
    
    功能：
    - 任务列表（使用TaskListWidget）
    - 任务详情面板
    - 任务操作按钮（添加、启动、停止、删除）
    - 任务进度显示
    - 执行次数设置
    
    信号：
    - task_added(dict): 任务添加信号
    - task_started(str): 任务启动信号
    - task_stopped(str): 任务停止信号
    - task_deleted(str): 任务删除信号
    - execution_count_changed(int): 执行次数变更信号
    """
    
    # 自定义信号
    task_added = pyqtSignal(dict)               # 任务添加信号
    task_started = pyqtSignal(str)              # 任务启动信号（任务ID）
    task_stopped = pyqtSignal(str)              # 任务停止信号（任务ID）
    task_deleted = pyqtSignal(str)              # 任务删除信号（任务ID）
    task_reordered = pyqtSignal(list)           # 任务重排序信号
    execution_count_changed = pyqtSignal(int)   # 执行次数变更信号
    start_execution_requested = pyqtSignal()    # 启动执行请求
    stop_execution_requested = pyqtSignal()     # 停止执行请求
    
    # 任务状态常量
    STATUS_IDLE = "idle"
    STATUS_RUNNING = "running"
    STATUS_PAUSED = "paused"
    
    def __init__(
        self,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        初始化任务管理页面
        
        Args:
            parent: 父控件
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._execution_status: str = self.STATUS_IDLE
        self._current_task_id: Optional[str] = None
        self._execution_count: int = 1
        self._infinite_loop: bool = False
        
        self._setup_ui()
        self._setup_style()
        self._setup_connections()
    
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
        
        # === 顶部：执行状态和控制 ===
        top_frame = QFrame()
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 执行状态指示器
        self._status_indicator = StatusIndicatorWidget(
            initial_status=StatusIndicatorWidget.STATUS_DISCONNECTED,
            show_text=True,
            enable_animation=True
        )
        top_layout.addWidget(self._status_indicator)
        
        # 当前任务标签
        self._current_task_label = QLabel("当前任务: 无")
        self._current_task_label.setProperty("variant", "secondary")
        top_layout.addWidget(self._current_task_label)
        
        top_layout.addStretch()
        
        main_layout.addWidget(top_frame)
        
        # === 中间：分割区域 ===
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：任务队列
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # 右侧：任务详情和执行控制
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割比例
        splitter.setSizes([400, 300])
        
        main_layout.addWidget(splitter, stretch=1)
    
    def _create_left_panel(self) -> QWidget:
        """创建左侧面板（任务队列）"""
        panel = CardWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm')
        )
        layout.setSpacing(self._theme.get_spacing('sm'))
        
        # 任务队列标题
        queue_title = QLabel("任务队列")
        queue_title.setProperty("variant", "header")
        layout.addWidget(queue_title)
        
        # 任务列表组件（支持拖拽排序）
        self._task_list = DragDropTaskList()
        self._task_list.setMinimumHeight(250)
        layout.addWidget(self._task_list, stretch=1)
        
        # 队列信息
        self._queue_info_label = QLabel("队列: 0个任务")
        self._queue_info_label.setProperty("variant", "muted")
        layout.addWidget(self._queue_info_label)
        
        # 任务操作按钮
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(self._theme.get_spacing('sm'))
        
        self._add_task_btn = PrimaryButton("添加任务")
        btn_layout.addWidget(self._add_task_btn)
        
        self._edit_task_btn = SecondaryButton("设置选中")
        btn_layout.addWidget(self._edit_task_btn)
        
        self._delete_task_btn = DangerButton("删除选中")
        btn_layout.addWidget(self._delete_task_btn)
        
        btn_layout.addStretch()
        layout.addWidget(btn_frame)
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """创建右侧面板（任务详情和执行控制）"""
        panel = CardWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm')
        )
        layout.setSpacing(self._theme.get_spacing('md'))
        
        # === 任务详情区域 ===
        details_group = QGroupBox("任务详情")
        details_layout = QVBoxLayout(details_group)
        details_layout.setContentsMargins(
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm')
        )
        details_layout.setSpacing(self._theme.get_spacing('xs'))
        
        # 任务名称
        name_frame = QFrame()
        name_layout = QHBoxLayout(name_frame)
        name_layout.setContentsMargins(0, 0, 0, 0)
        
        name_label = QLabel("任务名称:")
        name_label.setProperty("variant", "secondary")
        name_layout.addWidget(name_label)
        
        self._task_name_display = QLabel("-")
        self._task_name_display.setProperty("variant", "primary")
        name_layout.addWidget(self._task_name_display)
        
        name_layout.addStretch()
        details_layout.addWidget(name_frame)
        
        # 任务状态
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        status_label = QLabel("任务状态:")
        status_label.setProperty("variant", "secondary")
        status_layout.addWidget(status_label)
        
        self._task_status_display = QLabel("-")
        self._task_status_display.setProperty("variant", "primary")
        status_layout.addWidget(self._task_status_display)
        
        status_layout.addStretch()
        details_layout.addWidget(status_frame)
        
        # 任务进度
        progress_frame = QFrame()
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(self._theme.get_spacing('xs'))
        
        progress_label_frame = QFrame()
        progress_label_layout = QHBoxLayout(progress_label_frame)
        progress_label_layout.setContentsMargins(0, 0, 0, 0)
        
        progress_label = QLabel("任务进度:")
        progress_label.setProperty("variant", "secondary")
        progress_label_layout.addWidget(progress_label)
        
        self._progress_percent_label = QLabel("0%")
        self._progress_percent_label.setProperty("variant", "primary")
        progress_label_layout.addWidget(self._progress_percent_label)
        
        progress_label_layout.addStretch()
        progress_layout.addWidget(progress_label_frame)
        
        self._task_progress_bar = QProgressBar()
        self._task_progress_bar.setMinimum(0)
        self._task_progress_bar.setMaximum(100)
        self._task_progress_bar.setValue(0)
        self._task_progress_bar.setTextVisible(False)
        progress_layout.addWidget(self._task_progress_bar)
        
        details_layout.addWidget(progress_frame)
        
        layout.addWidget(details_group)
        
        # === 执行控制区域 ===
        exec_group = QGroupBox("执行控制")
        exec_layout = QVBoxLayout(exec_group)
        exec_layout.setContentsMargins(
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm')
        )
        exec_layout.setSpacing(self._theme.get_spacing('sm'))
        
        # 启动/停止按钮
        self._start_btn = PrimaryButton("▶ 启动执行")
        exec_layout.addWidget(self._start_btn)
        
        self._stop_btn = DangerButton("■ 停止执行")
        self._stop_btn.setEnabled(False)
        exec_layout.addWidget(self._stop_btn)
        
        # 执行次数设置
        count_frame = QFrame()
        count_layout = QHBoxLayout(count_frame)
        count_layout.setContentsMargins(0, 0, 0, 0)
        count_layout.setSpacing(self._theme.get_spacing('sm'))
        
        count_label = QLabel("执行次数:")
        count_label.setProperty("variant", "secondary")
        count_layout.addWidget(count_label)
        
        self._execution_spinbox = QSpinBox()
        self._execution_spinbox.setMinimum(1)
        self._execution_spinbox.setMaximum(99)
        self._execution_spinbox.setValue(self._execution_count)
        self._execution_spinbox.setFixedWidth(80)
        count_layout.addWidget(self._execution_spinbox)
        
        # 持续循环复选框
        self._infinite_checkbox = QCheckBox("持续循环")
        self._infinite_checkbox.setChecked(self._infinite_loop)
        count_layout.addWidget(self._infinite_checkbox)
        
        count_layout.addStretch()
        exec_layout.addWidget(count_frame)
        
        layout.addWidget(exec_group)
        
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
        
        for group in self.findChildren(QGroupBox):
            group.setStyleSheet(group_style)
        
        # 设置进度条样式
        self._task_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #48484a;
                border-radius: 4px;
                background-color: #2c2c2e;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #4361ee;
                border-radius: 3px;
            }
        """)
        
        # 设置SpinBox样式
        self._execution_spinbox.setStyleSheet("""
            QSpinBox {
                border: 1px solid #48484a;
                border-radius: 4px;
                background-color: #2c2c2e;
                color: #ffffff;
                padding: 4px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #3a3a3c;
                border: none;
                width: 20px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #4a4a4c;
            }
        """)
        
        # 设置CheckBox样式
        self._infinite_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #48484a;
                border-radius: 4px;
                background-color: #2c2c2e;
            }
            QCheckBox::indicator:checked {
                background-color: #4361ee;
                border-color: #4361ee;
            }
            QCheckBox::indicator:hover {
                border-color: #636366;
            }
        """)
    
    def _setup_connections(self) -> None:
        """设置信号连接"""
        # 任务列表信号
        self._task_list.itemDoubleClicked.connect(self._on_task_double_clicked)
        self._task_list.task_order_changed.connect(self._on_task_reordered)
        self._task_list.task_selected.connect(self._on_task_selection_changed)
        
        # 按钮点击信号
        self._add_task_btn.clicked.connect(self._on_add_task_clicked)
        self._edit_task_btn.clicked.connect(self._on_edit_task_clicked)
        self._delete_task_btn.clicked.connect(self._on_delete_task_clicked)
        self._start_btn.clicked.connect(self._on_start_clicked)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        
        # 执行次数变更
        self._execution_spinbox.valueChanged.connect(self._on_execution_count_changed)
        self._infinite_checkbox.stateChanged.connect(self._on_infinite_loop_changed)
    
    # === 信号处理方法 ===
    
    def _on_task_double_clicked(self, item: QListWidgetItem) -> None:
        """任务双击处理"""
        if isinstance(item, TaskListItem):
            self._current_task_id = item.task_id
            self.task_started.emit(item.task_id)
    
    def _on_task_reordered(self, tasks: List[str]) -> None:
        """任务重排序处理"""
        self.task_reordered.emit(tasks)
        self._update_queue_info()
    
    def _on_task_selection_changed(self, task_id: str) -> None:
        """任务选择变化处理"""
        # 查找选中的任务项
        for i in range(self._task_list.count()):
            item = self._task_list.item(i)
            if isinstance(item, TaskListItem) and item.task_id == task_id:
                self._update_task_details(item)
                break
    
    def _on_add_task_clicked(self) -> None:
        """添加任务按钮点击"""
        # 这里可以弹出对话框让用户选择任务
        # 简化处理：发送空任务信号，由外部处理
        self.task_added.emit({})
    
    def _on_edit_task_clicked(self) -> None:
        """编辑任务按钮点击"""
        selected_items = self._task_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个任务")
            return
        
        item = selected_items[0]
        if isinstance(item, TaskListItem):
            # 这里可以弹出编辑对话框
            # 简化处理：发送信号由外部处理
            pass
    
    def _on_delete_task_clicked(self) -> None:
        """删除任务按钮点击"""
        selected_items = self._task_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个任务")
            return
        
        item = selected_items[0]
        if isinstance(item, TaskListItem):
            self._task_list.takeItem(self._task_list.row(item))
            self.task_deleted.emit(item.task_id)
            self._update_queue_info()
    
    def _on_start_clicked(self) -> None:
        """启动执行按钮点击"""
        if self._task_list.count() == 0:
            QMessageBox.warning(self, "警告", "任务队列为空，请先添加任务")
            return
        
        self._execution_status = self.STATUS_RUNNING
        self._update_execution_status()
        self.start_execution_requested.emit()
    
    def _on_stop_clicked(self) -> None:
        """停止执行按钮点击"""
        self._execution_status = self.STATUS_IDLE
        self._update_execution_status()
        self.stop_execution_requested.emit()
    
    def _on_execution_count_changed(self, value: int) -> None:
        """执行次数变更"""
        self._execution_count = value
        self.execution_count_changed.emit(value)
    
    def _on_infinite_loop_changed(self, state: int) -> None:
        """持续循环变更"""
        self._infinite_loop = state == Qt.CheckState.Checked.value
        if self._infinite_loop:
            self._execution_spinbox.setEnabled(False)
        else:
            self._execution_spinbox.setEnabled(True)
    
    # === 内部方法 ===
    
    def _update_queue_info(self) -> None:
        """更新队列信息"""
        count = self._task_list.count()
        self._queue_info_label.setText(f"队列: {count}个任务")
    
    def _update_task_details(self, item: TaskListItem) -> None:
        """更新任务详情显示"""
        self._task_name_display.setText(item.task_name)
        
        # 状态显示
        status_names = {
            TaskListItem.STATUS_PENDING: "待执行",
            TaskListItem.STATUS_RUNNING: "执行中",
            TaskListItem.STATUS_COMPLETED: "已完成",
            TaskListItem.STATUS_FAILED: "失败",
            TaskListItem.STATUS_PAUSED: "已暂停",
        }
        status_text = status_names.get(item.status, "未知")
        self._task_status_display.setText(status_text)
        
        # 进度显示
        self._task_progress_bar.setValue(item.progress)
        self._progress_percent_label.setText(f"{item.progress}%")
    
    def _update_execution_status(self) -> None:
        """更新执行状态显示"""
        if self._execution_status == self.STATUS_RUNNING:
            self._status_indicator.set_status(StatusIndicatorWidget.STATUS_CONNECTED)
            self._status_indicator.set_status_text("执行中")
            self._start_btn.setEnabled(False)
            self._stop_btn.setEnabled(True)
        elif self._execution_status == self.STATUS_PAUSED:
            self._status_indicator.set_status(StatusIndicatorWidget.STATUS_CONNECTING)
            self._status_indicator.set_status_text("已暂停")
            self._start_btn.setEnabled(True)
            self._stop_btn.setEnabled(True)
        else:
            self._status_indicator.set_status(StatusIndicatorWidget.STATUS_DISCONNECTED)
            self._status_indicator.set_status_text("待执行")
            self._start_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
    
    # === 公共方法 ===
    
    def add_task(self, task_id: str, task_name: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        添加任务到队列
        
        Args:
            task_id: 任务唯一标识
            task_name: 任务显示名称
            data: 任务附加数据
        """
        item = TaskListItem(
            task_id=task_id,
            task_name=task_name,
            status=TaskListItem.STATUS_PENDING,
            data=data
        )
        self._task_list.addItem(item)
        self._update_queue_info()
    
    def remove_task(self, task_id: str) -> None:
        """
        从队列移除任务
        
        Args:
            task_id: 任务唯一标识
        """
        for i in range(self._task_list.count()):
            item = self._task_list.item(i)
            if isinstance(item, TaskListItem) and item.task_id == task_id:
                self._task_list.takeItem(i)
                self._update_queue_info()
                return
    
    def update_task_status(self, task_id: str, status: str, progress: int = 0) -> None:
        """
        更新任务状态
        
        Args:
            task_id: 任务唯一标识
            status: 任务状态
            progress: 任务进度 (0-100)
        """
        for i in range(self._task_list.count()):
            item = self._task_list.item(i)
            if isinstance(item, TaskListItem) and item.task_id == task_id:
                item.set_status(status)
                item.set_progress(progress)
                
                # 如果是当前选中的任务，更新详情显示
                if self._task_list.currentItem() == item:
                    self._update_task_details(item)
                
                return
    
    def set_current_task(self, task_id: str, task_name: str) -> None:
        """
        设置当前执行的任务
        
        Args:
            task_id: 任务唯一标识
            task_name: 任务显示名称
        """
        self._current_task_id = task_id
        self._current_task_label.setText(f"当前任务: {task_name}")
    
    def clear_current_task(self) -> None:
        """清除当前任务显示"""
        self._current_task_id = None
        self._current_task_label.setText("当前任务: 无")
    
    def clear_queue(self) -> None:
        """清空任务队列"""
        self._task_list.clear()
        self._update_queue_info()
    
    def get_task_queue(self) -> List[str]:
        """获取任务队列（任务ID列表）"""
        tasks = []
        for i in range(self._task_list.count()):
            item = self._task_list.item(i)
            if isinstance(item, TaskListItem):
                tasks.append(item.task_id)
        return tasks
    
    def get_execution_count(self) -> int:
        """获取执行次数"""
        return self._execution_count
    
    def is_infinite_loop(self) -> bool:
        """是否持续循环"""
        return self._infinite_loop
    
    def set_execution_running(self, is_running: bool) -> None:
        """
        设置执行状态
        
        Args:
            is_running: 是否正在执行
        """
        self._execution_status = self.STATUS_RUNNING if is_running else self.STATUS_IDLE
        self._update_execution_status()
    
    def get_execution_status(self) -> str:
        """获取执行状态"""
        return self._execution_status