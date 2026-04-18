"""
拖拽排序任务列表组件
使用 QListWidget 实现拖拽排序，支持任务项的添加、删除、编辑和右键菜单
"""

from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMenu,
    QAbstractItemView,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QIcon, QColor, QFont

# 支持两种导入方式
try:
    from ..theme.theme_manager import ThemeManager
except ImportError:
    from theme.theme_manager import ThemeManager


class TaskListItem(QListWidgetItem):
    """
    任务列表项
    
    存储任务的完整信息，包括名称、状态、进度等
    """
    
    # 任务状态常量
    STATUS_PENDING = "pending"      # 待执行
    STATUS_RUNNING = "running"      # 执行中
    STATUS_COMPLETED = "completed"  # 已完成
    STATUS_FAILED = "failed"        # 失败
    STATUS_PAUSED = "paused"        # 已暂停
    
    def __init__(
        self,
        task_id: str,
        task_name: str,
        status: str = STATUS_PENDING,
        progress: int = 0,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        初始化任务项
        
        Args:
            task_id: 任务唯一标识
            task_name: 任务显示名称
            status: 任务状态
            progress: 任务进度 (0-100)
            data: 任务附加数据
        """
        super().__init__()
        self._task_id = task_id
        self._task_name = task_name
        self._status = status
        self._progress = progress
        self._data = data or {}
        
        # 设置显示文本
        self._update_display()
        
        # 存储任务ID到item数据中
        self.setData(Qt.ItemDataRole.UserRole, task_id)
    
    def _update_display(self) -> None:
        """更新显示文本"""
        # 构建显示文本：名称 + 状态图标 + 进度
        status_icon = self._get_status_icon()
        progress_text = f" [{self._progress}%]" if self._progress > 0 else ""
        
        display_text = f"{status_icon} {self._task_name}{progress_text}"
        self.setText(display_text)
        
        # 设置字体颜色根据状态
        theme = ThemeManager.get_instance()
        color = self._get_status_color(theme)
        self.setForeground(QColor(color))
    
    def _get_status_icon(self) -> str:
        """获取状态图标字符"""
        icons = {
            self.STATUS_PENDING: "○",
            self.STATUS_RUNNING: "◐",
            self.STATUS_COMPLETED: "●",
            self.STATUS_FAILED: "✗",
            self.STATUS_PAUSED: "◇",
        }
        return icons.get(self._status, "○")
    
    def _get_status_color(self, theme: ThemeManager) -> str:
        """获取状态对应的颜色"""
        colors = {
            self.STATUS_PENDING: theme.get_color('text_secondary'),
            self.STATUS_RUNNING: theme.get_color('warning'),
            self.STATUS_COMPLETED: theme.get_color('success'),
            self.STATUS_FAILED: theme.get_color('danger'),
            self.STATUS_PAUSED: theme.get_color('text_muted'),
        }
        return colors.get(self._status, theme.get_color('text_primary'))
    
    # === 属性访问器 ===
    
    @property
    def task_id(self) -> str:
        """获取任务ID"""
        return self._task_id
    
    @property
    def task_name(self) -> str:
        """获取任务名称"""
        return self._task_name
    
    @property
    def status(self) -> str:
        """获取任务状态"""
        return self._status
    
    @property
    def progress(self) -> int:
        """获取任务进度"""
        return self._progress
    
    @property
    def data(self) -> Dict[str, Any]:
        """获取任务附加数据"""
        return self._data
    
    def set_status(self, status: str) -> None:
        """设置任务状态"""
        self._status = status
        self._update_display()
    
    def set_progress(self, progress: int) -> None:
        """设置任务进度"""
        self._progress = max(0, min(100, progress))
        self._update_display()
    
    def set_task_name(self, name: str) -> None:
        """设置任务名称"""
        self._task_name = name
        self._update_display()
    
    def set_data(self, data: Dict[str, Any]) -> None:
        """设置任务附加数据"""
        self._data = data


class DragDropTaskList(QListWidget):
    """
    支持拖拽排序的任务列表
    
    功能：
    - 使用 QListWidget 实现拖拽排序 (InternalMove 模式)
    - 显示任务项（任务名称、状态图标、进度）
    - 支持任务项的添加、删除、编辑
    - 支持右键菜单（启动、停止、删除任务）
    
    信号：
    - task_order_changed(list): 任务顺序改变信号
    - task_selected(str): 任务选中信号
    - task_action_requested(str, str): 任务操作请求信号 (task_id, action)
    """
    
    # 自定义信号
    task_order_changed = pyqtSignal(list)  # 任务ID列表
    task_selected = pyqtSignal(str)        # 任务ID
    task_action_requested = pyqtSignal(str, str)  # task_id, action
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        初始化任务列表
        
        Args:
            parent: 父控件
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        
        # 设置拖拽模式
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        # 设置默认交替背景色
        self.setAlternatingRowColors(True)
        
        # 连接信号
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.currentRowChanged.connect(self._on_row_changed)
        
        # 启用右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        self._setup_style()
    
    def _setup_style(self) -> None:
        """设置样式"""
        c = self._theme.colors
        r = self._theme.get_corner_radius('sm')
        s = self._theme.get_spacing('list_item_padding')
        
        self.setStyleSheet(f"""
            QListWidget {{
                background-color: {c['surface_container_low']};
                border: 1px solid {c['border_color']};
                border-radius: {r}px;
                padding: {s}px;
                outline: none;
            }}
            
            QListWidget::item {{
                background-color: transparent;
                border-radius: {r}px;
                padding: {s}px;
                margin: 2px 0;
            }}
            
            QListWidget::item:selected {{
                background-color: {c['selection_bg']};
                color: {c['on_primary']};
            }}
            
            QListWidget::item:hover:!selected {{
                background-color: {c['hover_bg']};
            }}
            
            QListWidget::item:alternate {{
                background-color: {c['surface_container']};
            }}
        """)
    
    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """项目点击处理"""
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id:
            self.task_selected.emit(task_id)
    
    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """项目双击处理 - 发送编辑请求"""
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id:
            self.task_action_requested.emit(task_id, "edit")
    
    def _on_row_changed(self, row: int) -> None:
        """行改变处理"""
        item = self.item(row)
        if item:
            task_id = item.data(Qt.ItemDataRole.UserRole)
            if task_id:
                self.task_selected.emit(task_id)
    
    def _show_context_menu(self, pos) -> None:
        """显示右键菜单"""
        item = self.itemAt(pos)
        if not item:
            return
        
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if not task_id:
            return
        
        # 创建菜单
        menu = QMenu(self)
        menu.setStyleSheet(self._get_menu_style())
        
        # 添加菜单项
        start_action = QAction("▶ 启动任务", menu)
        start_action.triggered.connect(lambda: self.task_action_requested.emit(task_id, "start"))
        menu.addAction(start_action)
        
        stop_action = QAction("■ 停止任务", menu)
        stop_action.triggered.connect(lambda: self.task_action_requested.emit(task_id, "stop"))
        menu.addAction(stop_action)
        
        pause_action = QAction("◇ 暂停任务", menu)
        pause_action.triggered.connect(lambda: self.task_action_requested.emit(task_id, "pause"))
        menu.addAction(pause_action)
        
        menu.addSeparator()
        
        edit_action = QAction("✎ 编辑任务", menu)
        edit_action.triggered.connect(lambda: self.task_action_requested.emit(task_id, "edit"))
        menu.addAction(edit_action)
        
        delete_action = QAction("✗ 删除任务", menu)
        delete_action.triggered.connect(lambda: self.task_action_requested.emit(task_id, "delete"))
        menu.addAction(delete_action)
        
        # 显示菜单
        menu.exec(self.mapToGlobal(pos))
    
    def _get_menu_style(self) -> str:
        """获取菜单样式"""
        c = self._theme.colors
        r = self._theme.get_corner_radius('menu')
        
        return f"""
            QMenu {{
                background-color: {c['surface_container']};
                border: 1px solid {c['border_color']};
                border-radius: {r}px;
                padding: 4px;
            }}
            
            QMenu::item {{
                background-color: transparent;
                padding: 8px 24px;
                border-radius: 4px;
            }}
            
            QMenu::item:selected {{
                background-color: {c['selection_bg']};
                color: {c['on_primary']};
            }}
            
            QMenu::separator {{
                height: 1px;
                background-color: {c['divider_color']};
                margin: 4px 8px;
            }}
        """
    
    def dropEvent(self, event) -> None:
        """拖放事件处理"""
        super().dropEvent(event)
        
        # 拖放完成后发射顺序改变信号
        task_ids = self._get_all_task_ids()
        self.task_order_changed.emit(task_ids)
    
    def _get_all_task_ids(self) -> List[str]:
        """获取所有任务ID列表"""
        task_ids = []
        for i in range(self.count()):
            item = self.item(i)
            if item:
                task_id = item.data(Qt.ItemDataRole.UserRole)
                if task_id:
                    task_ids.append(task_id)
        return task_ids
    
    # === 公共方法 ===
    
    def add_task(
        self,
        task_id: str,
        task_name: str,
        status: str = TaskListItem.STATUS_PENDING,
        progress: int = 0,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        添加任务
        
        Args:
            task_id: 任务唯一标识
            task_name: 任务显示名称
            status: 任务状态
            progress: 任务进度
            data: 任务附加数据
        """
        item = TaskListItem(task_id, task_name, status, progress, data)
        self.addItem(item)
    
    def add_task_item(self, item: TaskListItem) -> None:
        """
        添加任务项
        
        Args:
            item: TaskListItem 对象
        """
        self.addItem(item)
    
    def remove_task(self, task_id: str) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功删除
        """
        for i in range(self.count()):
            item = self.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == task_id:
                self.takeItem(i)
                return True
        return False
    
    def get_task_item(self, task_id: str) -> Optional[TaskListItem]:
        """
        获取任务项
        
        Args:
            task_id: 任务ID
            
        Returns:
            TaskListItem 或 None
        """
        for i in range(self.count()):
            item = self.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == task_id:
                return item
        return None
    
    def update_task_status(self, task_id: str, status: str) -> bool:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            
        Returns:
            bool: 是否成功更新
        """
        item = self.get_task_item(task_id)
        if item and isinstance(item, TaskListItem):
            item.set_status(status)
            return True
        return False
    
    def update_task_progress(self, task_id: str, progress: int) -> bool:
        """
        更新任务进度
        
        Args:
            task_id: 任务ID
            progress: 新进度
            
        Returns:
            bool: 是否成功更新
        """
        item = self.get_task_item(task_id)
        if item and isinstance(item, TaskListItem):
            item.set_progress(progress)
            return True
        return False
    
    def clear_all_tasks(self) -> None:
        """清除所有任务"""
        self.clear()
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        获取所有任务信息
        
        Returns:
            任务信息列表
        """
        tasks = []
        for i in range(self.count()):
            item = self.item(i)
            if item and isinstance(item, TaskListItem):
                tasks.append({
                    'id': item.task_id,
                    'name': item.task_name,
                    'status': item.status,
                    'progress': item.progress,
                    'data': item.data,
                })
        return tasks
    
    def get_selected_task_id(self) -> Optional[str]:
        """获取当前选中的任务ID"""
        item = self.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None
    
    def select_task(self, task_id: str) -> bool:
        """
        选中指定任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功选中
        """
        for i in range(self.count()):
            item = self.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == task_id:
                self.setCurrentItem(item)
                return True
        return False
    
    def set_task_order(self, task_ids: List[str]) -> None:
        """
        设置任务顺序
        
        Args:
            task_ids: 任务ID列表（按新顺序）
        """
        # 收集所有任务项
        items = []
        for i in range(self.count()):
            items.append(self.takeItem(i))
        
        # 清空列表
        self.clear()
        
        # 按新顺序添加
        for task_id in task_ids:
            for item in items:
                if item and item.data(Qt.ItemDataRole.UserRole) == task_id:
                    self.addItem(item)
                    break
    
    # === 重写事件处理 ===
    
    def sizeHint(self) -> QSize:
        """建议大小"""
        return QSize(250, 300)


class TaskListWidget(QWidget):
    """
    完整的任务列表组件（包含标题栏和操作按钮）
    
    组合 DragDropTaskList 与标题栏、操作按钮
    """
    
    # 信号转发
    task_order_changed = pyqtSignal(list)
    task_selected = pyqtSignal(str)
    task_action_requested = pyqtSignal(str, str)
    add_task_requested = pyqtSignal()
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "任务队列"
    ) -> None:
        """
        初始化任务列表组件
        
        Args:
            parent: 父控件
            title: 标题文本
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._title = title
        
        self._setup_ui()
    
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
        
        # 标题栏
        header_layout = QHBoxLayout()
        header_layout.setSpacing(self._theme.get_spacing('sm'))
        
        title_label = QLabel(self._title)
        title_label.setProperty("variant", "title")
        title_label.style().unpolish(title_label)
        title_label.style().polish(title_label)
        header_layout.addWidget(title_label)
        
        # 任务计数
        self._count_label = QLabel("(0)")
        self._count_label.setProperty("variant", "muted")
        self._count_label.style().unpolish(self._count_label)
        self._count_label.style().polish(self._count_label)
        header_layout.addWidget(self._count_label)
        
        header_layout.addStretch()
        
        # 添加任务按钮
        add_btn = QPushButton("添加")
        add_btn.setProperty("variant", "primary")
        add_btn.setFixedHeight(28)
        add_btn.clicked.connect(self.add_task_requested.emit)
        header_layout.addWidget(add_btn)
        
        main_layout.addLayout(header_layout)
        
        # 任务列表
        self._task_list = DragDropTaskList()
        self._task_list.task_order_changed.connect(self.task_order_changed.emit)
        self._task_list.task_selected.connect(self.task_selected.emit)
        self._task_list.task_action_requested.connect(self.task_action_requested.emit)
        main_layout.addWidget(self._task_list, 1)
        
        # 操作按钮栏
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(self._theme.get_spacing('sm'))
        
        edit_btn = QPushButton("设置选中")
        edit_btn.setProperty("variant", "secondary")
        edit_btn.setFixedHeight(28)
        edit_btn.clicked.connect(self._on_edit_clicked)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("删除选中")
        delete_btn.setProperty("variant", "danger")
        delete_btn.setFixedHeight(28)
        delete_btn.clicked.connect(self._on_delete_clicked)
        btn_layout.addWidget(delete_btn)
        
        main_layout.addLayout(btn_layout)
    
    def _on_edit_clicked(self) -> None:
        """编辑按钮点击"""
        task_id = self._task_list.get_selected_task_id()
        if task_id:
            self.task_action_requested.emit(task_id, "edit")
    
    def _on_delete_clicked(self) -> None:
        """删除按钮点击"""
        task_id = self._task_list.get_selected_task_id()
        if task_id:
            self.task_action_requested.emit(task_id, "delete")
    
    def _update_count_label(self) -> None:
        """更新任务计数"""
        count = self._task_list.count()
        self._count_label.setText(f"({count})")
    
    # === 公共方法（转发到内部列表） ===
    
    def add_task(
        self,
        task_id: str,
        task_name: str,
        status: str = TaskListItem.STATUS_PENDING,
        progress: int = 0,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加任务"""
        self._task_list.add_task(task_id, task_name, status, progress, data)
        self._update_count_label()
    
    def remove_task(self, task_id: str) -> bool:
        """删除任务"""
        result = self._task_list.remove_task(task_id)
        if result:
            self._update_count_label()
        return result
    
    def get_task_list(self) -> DragDropTaskList:
        """获取内部任务列表控件"""
        return self._task_list
    
    def clear_all_tasks(self) -> None:
        """清除所有任务"""
        self._task_list.clear_all_tasks()
        self._update_count_label()
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务信息"""
        return self._task_list.get_all_tasks()
    
    def update_task_status(self, task_id: str, status: str) -> bool:
        """更新任务状态"""
        return self._task_list.update_task_status(task_id, status)
    
    def update_task_progress(self, task_id: str, progress: int) -> bool:
        """更新任务进度"""
        return self._task_list.update_task_progress(task_id, progress)