"""
模型管理页面 - 管理本地AI模型的下载、删除和查看

功能：
- 显示可用模型列表（从model_manager获取）
- 显示已下载模型和可下载模型
- 提供下载按钮（调用model_manager.download_model）
- 提供删除按钮（删除本地模型文件）
- 显示模型信息（大小、版本、状态）
- 搜索和排序功能
- 批量操作（批量下载、删除）
- 下载状态持久化

重构说明：
- 使用模块化设计，将ModelCard、ModelFilter、BatchOperationManager分离到单独文件
- 修复QTimer导入位置问题
- 添加搜索、排序、批量操作功能
- 支持下载状态持久化
"""

from typing import Optional, Dict, Any, List
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QProgressBar, QScrollArea, QMessageBox,
    QGridLayout, QSizePolicy, QLineEdit, QComboBox,
    QCheckBox, QSpacerItem, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont

# 支持两种导入方式
try:
    from ..theme.theme_manager import ThemeManager
    from ..theme.animation_manager import (
        AnimationManager, AnimatedProgressBar, fade_in_widget
    )
    from ..widgets.base_widgets import (
        PrimaryButton, SecondaryButton, DangerButton, CardWidget,
        ElevatedCardWidget, OutlinedCardWidget, HorizontalSeparator
    )
    from .model_manager import (
        ModelCard, ModelFilter, SortOrder,
        BatchOperationManager, BatchOperationType,
        DownloadStateManager
    )
    from ...安卓相关.core.local_inference.model_manager import ModelManager, ModelInfo
    from ...安卓相关.core.local_inference.gpu_checker import GPUChecker
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
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.theme.animation_manager import (
        AnimationManager, AnimatedProgressBar, fade_in_widget
    )
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.base_widgets import (
        PrimaryButton, SecondaryButton, DangerButton, CardWidget,
        ElevatedCardWidget, OutlinedCardWidget, HorizontalSeparator
    )
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.pages.model_manager import (
        ModelCard, ModelFilter, SortOrder,
        BatchOperationManager, BatchOperationType,
        DownloadStateManager
    )
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.model_manager import ModelManager, ModelInfo
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.gpu_checker import GPUChecker


class ModelDownloadWorker(QThread):
    """模型下载工作线程"""
    
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, model_name: str, model_manager: ModelManager, parent=None):
        super().__init__(parent)
        self._model_name = model_name
        self._model_manager = model_manager
        self._cancelled = False
    
    def run(self):
        """执行模型下载"""
        try:
            def progress_callback(percentage: int, message: str):
                if not self._cancelled:
                    self.progress_signal.emit(percentage, message)
            
            result = self._model_manager.download_model(self._model_name, progress_callback)
            
            if self._cancelled:
                self.finished_signal.emit(False, "下载已取消")
            elif result:
                self.finished_signal.emit(True, "下载完成")
            else:
                self.finished_signal.emit(False, "下载失败")
                
        except Exception as e:
            self.finished_signal.emit(False, str(e))
    
    def cancel(self):
        """取消下载"""
        self._cancelled = True


class ModelManagerPage(QWidget):
    """
    模型管理页面
    
    功能：
    - 显示所有可用模型
    - 搜索和排序
    - 批量操作
    - 下载状态持久化
    """
    
    # 信号
    model_changed = pyqtSignal(str)  # 模型选择变更
    settings_changed = pyqtSignal(dict)  # 设置变更
    
    def __init__(self, parent: Optional[QWidget] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._anim_manager = AnimationManager.get_instance()
        self._config = config or {}
        
        # 模型管理器
        models_dir = self._config.get('model', {}).get('models_dir', 'models')
        self._model_manager = ModelManager(models_dir=models_dir)
        
        # GPU检测器
        self._gpu_checker = GPUChecker()
        self._recommended_model: Optional[str] = None
        
        # 下载工作线程
        self._download_worker: Optional[ModelDownloadWorker] = None
        
        # 模型卡片字典
        self._model_cards: Dict[str, ModelCard] = {}
        
        # 所有模型列表（原始数据）
        self._all_models: List[ModelInfo] = []
        
        # 过滤器和排序
        self._model_filter = ModelFilter()
        
        # 批量操作管理器
        self._batch_manager = BatchOperationManager(self._model_manager, self)
        
        # 下载状态管理器
        self._download_state_manager = DownloadStateManager()
        
        # 批量选择模式
        self._batch_mode = False
        self._selected_models: set = set()
        
        self._setup_ui()
        self._setup_style()
        self._setup_connections()
        self._refresh_model_list()
        self._check_resumable_downloads()
    
    def _setup_ui(self):
        """设置UI结构"""
        # 主布局使用滚动区域
        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # 内容容器
        self._content_widget = QWidget()
        self._scroll_area.setWidget(self._content_widget)
        
        main_layout = QVBoxLayout(self._content_widget)
        main_layout.setContentsMargins(
            self._theme.get_spacing('padding_xl'),
            self._theme.get_spacing('padding_xl'),
            self._theme.get_spacing('padding_xl'),
            self._theme.get_spacing('padding_xl')
        )
        main_layout.setSpacing(self._theme.get_spacing('lg'))
        
        # 页面标题
        title_label = QLabel("模型管理")
        title_font = QFont(self._theme.get_font_family(), self._theme.get_font_size('headline_medium'))
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setProperty("variant", "header")
        main_layout.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel("管理本地AI推理模型，下载或删除模型文件")
        subtitle_label.setProperty("variant", "muted")
        main_layout.addWidget(subtitle_label)
        
        main_layout.addSpacing(self._theme.get_spacing('md'))
        
        # 磁盘使用情况卡片
        self._disk_usage_card = self._create_disk_usage_section()
        main_layout.addWidget(self._disk_usage_card)
        
        # 搜索和排序工具栏
        toolbar_layout = self._create_toolbar()
        main_layout.addLayout(toolbar_layout)
        
        # 批量操作工具栏（默认隐藏）
        self._batch_toolbar = self._create_batch_toolbar()
        self._batch_toolbar.setVisible(False)
        main_layout.addWidget(self._batch_toolbar)
        
        # 下载进度区域（默认隐藏）
        self._download_progress_frame = self._create_download_progress_section()
        self._download_progress_frame.setVisible(False)
        main_layout.addWidget(self._download_progress_frame)
        
        # 批量操作进度区域（默认隐藏）
        self._batch_progress_frame = self._create_batch_progress_section()
        self._batch_progress_frame.setVisible(False)
        main_layout.addWidget(self._batch_progress_frame)
        
        # 模型列表区域
        models_title_layout = QHBoxLayout()
        models_title = QLabel("可用模型")
        models_title_font = QFont(self._theme.get_font_family(), self._theme.get_font_size('title_large'))
        models_title_font.setBold(True)
        models_title.setFont(models_title_font)
        models_title_layout.addWidget(models_title)
        
        models_title_layout.addStretch()
        
        # 模型数量标签
        self._model_count_label = QLabel("0 个模型")
        self._model_count_label.setProperty("variant", "muted")
        models_title_layout.addWidget(self._model_count_label)
        
        main_layout.addLayout(models_title_layout)
        
        # 空状态提示
        self._empty_state_widget = self._create_empty_state_widget()
        main_layout.addWidget(self._empty_state_widget)
        
        # 模型网格
        self._models_grid = QGridLayout()
        self._models_grid.setSpacing(self._theme.get_spacing('lg'))
        main_layout.addLayout(self._models_grid)
        
        # 刷新按钮
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        
        self._refresh_btn = SecondaryButton("🔄 刷新列表")
        self._refresh_btn.clicked.connect(self._refresh_model_list)
        refresh_layout.addWidget(self._refresh_btn)
        
        main_layout.addLayout(refresh_layout)
        
        main_layout.addStretch()
        
        # 设置主布局
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self._scroll_area)
    
    def _create_disk_usage_section(self) -> CardWidget:
        """创建磁盘使用情况区域"""
        card = CardWidget(title="💾 磁盘使用情况")
        layout = card.get_content_layout()
        
        # 获取磁盘使用情况
        usage = self._model_manager.get_disk_usage()
        
        # 总大小
        size_layout = QHBoxLayout()
        
        size_label = QLabel("已用空间:")
        size_label.setProperty("variant", "secondary")
        size_layout.addWidget(size_label)
        
        self._disk_usage_label = QLabel(f"{usage['total_size_gb']:.2f} GB")
        self._disk_usage_label.setProperty("variant", "primary")
        size_font = QFont()
        size_font.setBold(True)
        self._disk_usage_label.setFont(size_font)
        size_layout.addWidget(self._disk_usage_label)
        
        size_layout.addStretch()
        
        # 模型数量
        self._installed_count_label = QLabel(f"已安装模型: {usage['model_count']} 个")
        self._installed_count_label.setProperty("variant", "muted")
        size_layout.addWidget(self._installed_count_label)
        
        layout.addLayout(size_layout)
        
        return card
    
    def _create_toolbar(self) -> QHBoxLayout:
        """创建搜索和排序工具栏"""
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 搜索框
        search_container = QFrame()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(8, 4, 8, 4)
        search_layout.setSpacing(8)
        
        search_icon = QLabel("🔍")
        search_layout.addWidget(search_icon)
        
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索模型名称或描述...")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setFixedWidth(280)
        search_layout.addWidget(self._search_input)
        
        # 搜索框样式
        search_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self._theme.get_color('bg_secondary')};
                border: 1px solid {self._theme.get_color('border_color')};
                border-radius: 8px;
            }}
            QLineEdit {{
                border: none;
                background: transparent;
                color: {self._theme.get_color('text_primary')};
                padding: 4px;
            }}
            QLineEdit::placeholder {{
                color: {self._theme.get_color('text_muted')};
            }}
        """)
        
        toolbar_layout.addWidget(search_container)
        
        # 排序下拉框
        sort_label = QLabel("排序:")
        sort_label.setProperty("variant", "secondary")
        toolbar_layout.addWidget(sort_label)
        
        self._sort_combo = QComboBox()
        self._sort_combo.setFixedWidth(150)
        
        # 添加排序选项
        for order in SortOrder:
            self._sort_combo.addItem(
                ModelFilter.get_sort_order_display_name(order),
                order
            )
        
        toolbar_layout.addWidget(self._sort_combo)
        
        toolbar_layout.addStretch()
        
        # 批量操作按钮
        self._batch_mode_btn = SecondaryButton("批量操作")
        self._batch_mode_btn.setCheckable(True)
        self._batch_mode_btn.clicked.connect(self._toggle_batch_mode)
        toolbar_layout.addWidget(self._batch_mode_btn)
        
        return toolbar_layout
    
    def _create_batch_toolbar(self) -> QFrame:
        """创建批量操作工具栏"""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(self._theme.get_spacing('md'))
        
        # 全选/取消全选
        self._select_all_checkbox = QCheckBox("全选")
        self._select_all_checkbox.stateChanged.connect(self._on_select_all_changed)
        layout.addWidget(self._select_all_checkbox)
        
        layout.addSpacing(16)
        
        # 选中数量标签
        self._selected_count_label = QLabel("已选择: 0")
        self._selected_count_label.setProperty("variant", "muted")
        layout.addWidget(self._selected_count_label)
        
        layout.addStretch()
        
        # 批量下载按钮
        self._batch_download_btn = PrimaryButton("批量下载")
        self._batch_download_btn.setToolTip("下载选中的未下载模型")
        self._batch_download_btn.clicked.connect(self._on_batch_download)
        layout.addWidget(self._batch_download_btn)
        
        # 批量删除按钮
        self._batch_delete_btn = DangerButton("批量删除")
        self._batch_delete_btn.setToolTip("删除选中的已下载模型")
        self._batch_delete_btn.clicked.connect(self._on_batch_delete)
        layout.addWidget(self._batch_delete_btn)
        
        # 取消按钮
        cancel_btn = SecondaryButton("取消")
        cancel_btn.clicked.connect(self._exit_batch_mode)
        layout.addWidget(cancel_btn)
        
        # 样式
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self._theme.get_color('bg_secondary')};
                border: 1px solid {self._theme.get_color('border_color')};
                border-radius: 8px;
            }}
        """)
        
        return frame
    
    def _create_download_progress_section(self) -> QFrame:
        """创建下载进度区域"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self._theme.get_spacing('sm'))
        
        self._download_status_label = QLabel("准备下载...")
        self._download_status_label.setProperty("variant", "muted")
        layout.addWidget(self._download_status_label)
        
        self._download_progress_bar = QProgressBar()
        self._download_progress_bar.setRange(0, 100)
        self._download_progress_bar.setTextVisible(True)
        layout.addWidget(self._download_progress_bar)
        
        self._animated_progress_bar = AnimatedProgressBar(self._download_progress_bar)
        
        return frame
    
    def _create_batch_progress_section(self) -> QFrame:
        """创建批量操作进度区域"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(self._theme.get_spacing('sm'))
        
        self._batch_status_label = QLabel("批量操作中...")
        self._batch_status_label.setProperty("variant", "secondary")
        layout.addWidget(self._batch_status_label)
        
        self._batch_progress_bar = QProgressBar()
        self._batch_progress_bar.setRange(0, 100)
        self._batch_progress_bar.setTextVisible(True)
        layout.addWidget(self._batch_progress_bar)
        
        self._batch_detail_label = QLabel("")
        self._batch_detail_label.setProperty("variant", "muted")
        self._batch_detail_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self._batch_detail_label)
        
        # 取消按钮
        cancel_btn = SecondaryButton("取消批量操作")
        cancel_btn.clicked.connect(self._batch_manager.cancel_operation)
        layout.addWidget(cancel_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        # 样式
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self._theme.get_color('bg_secondary')};
                border: 1px solid {self._theme.get_color('border_color')};
                border-radius: 8px;
            }}
            QProgressBar {{
                border: 1px solid {self._theme.get_color('border_color')};
                border-radius: 4px;
                background-color: {self._theme.get_color('bg_primary')};
                height: 24px;
                text-align: center;
                color: {self._theme.get_color('text_primary')};
            }}
            QProgressBar::chunk {{
                background-color: {self._theme.get_color('primary')};
                border-radius: 3px;
            }}
        """)
        
        return frame
    
    def _create_empty_state_widget(self) -> QWidget:
        """创建空状态提示"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(self._theme.get_spacing('md'))
        
        icon_label = QLabel("📦")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        text_label = QLabel("暂无模型")
        text_label.setProperty("variant", "muted")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_font = QFont(self._theme.get_font_family(), self._theme.get_font_size('title_medium'))
        text_label.setFont(text_font)
        layout.addWidget(text_label)
        
        hint_label = QLabel("请尝试调整搜索条件或刷新列表")
        hint_label.setProperty("variant", "muted")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(hint_label)
        
        widget.setVisible(False)
        return widget
    
    def _setup_style(self):
        """设置样式"""
        # 进度条样式
        self._download_progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {self._theme.get_color('border_color')};
                border-radius: 4px;
                background-color: {self._theme.get_color('bg_secondary')};
                height: 24px;
                text-align: center;
                color: {self._theme.get_color('text_primary')};
            }}
            QProgressBar::chunk {{
                background-color: {self._theme.get_color('primary')};
                border-radius: 3px;
            }}
        """)
    
    def _setup_connections(self):
        """设置信号连接"""
        # 搜索框
        self._search_input.textChanged.connect(self._on_search_text_changed)
        
        # 排序下拉框
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        
        # 批量操作管理器
        self._batch_manager.operation_started.connect(self._on_batch_operation_started)
        self._batch_manager.operation_progress.connect(self._on_batch_operation_progress)
        self._batch_manager.operation_item_finished.connect(self._on_batch_operation_item_finished)
        self._batch_manager.operation_finished.connect(self._on_batch_operation_finished)
        self._batch_manager.operation_cancelled.connect(self._on_batch_operation_cancelled)
    
    def _refresh_model_list(self):
        """刷新模型列表"""
        # 清除旧的模型卡片
        while self._models_grid.count():
            item = self._models_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._model_cards.clear()
        
        # 获取推荐模型
        try:
            gpu_result = self._gpu_checker.check_gpu_availability()
            self._recommended_model = gpu_result.get('recommended_model')
        except Exception:
            self._recommended_model = None
        
        # 设置推荐模型到过滤器
        self._model_filter.set_recommended_model(self._recommended_model)
        
        # 获取所有模型
        self._all_models = self._model_manager.get_all_models()
        
        # 应用过滤和排序
        filtered_models = self._model_filter.apply(self._all_models)
        
        # 更新模型数量标签
        self._model_count_label.setText(f"{len(filtered_models)} 个模型")
        
        # 显示或隐藏空状态
        if len(filtered_models) == 0:
            self._empty_state_widget.setVisible(True)
            if self._all_models:
                # 有模型但被过滤掉了
                self._empty_state_widget.findChild(QLabel, "", Qt.FindChildOption.FindDirectChildrenOnly).setText("🔍")
                self._empty_state_widget.findChildren(QLabel)[1].setText("没有找到匹配的模型")
                self._empty_state_widget.findChildren(QLabel)[2].setText("请尝试调整搜索条件")
        else:
            self._empty_state_widget.setVisible(False)
        
        # 添加模型卡片到网格
        row = 0
        col = 0
        
        for model in filtered_models:
            is_recommended = model.name == self._recommended_model
            card = ModelCard(
                model,
                is_recommended=is_recommended,
                show_checkbox=self._batch_mode,
                parent=self
            )
            
            # 连接信号
            card.download_requested.connect(self._on_download_requested)
            card.delete_requested.connect(self._on_delete_requested)
            card.use_requested.connect(self._on_use_requested)
            card.selection_changed.connect(self._on_model_selection_changed)
            
            # 恢复选择状态
            if self._batch_mode and model.name in self._selected_models:
                card.set_selected(True)
            
            # 检查是否有可恢复的下载
            if self._download_state_manager.has_resumable_download(model.name):
                progress = self._download_state_manager.get_resumable_progress(model.name)
                card.update_download_progress(progress, f"可恢复下载 ({progress}%)")
            
            self._models_grid.addWidget(card, row, col)
            self._model_cards[model.name] = card
            
            col += 1
            if col > 1:  # 每行2个
                col = 0
                row += 1
        
        # 更新磁盘使用情况
        self._update_disk_usage()
    
    def _update_disk_usage(self):
        """更新磁盘使用情况显示"""
        usage = self._model_manager.get_disk_usage()
        self._disk_usage_label.setText(f"{usage['total_size_gb']:.2f} GB")
        self._installed_count_label.setText(f"已安装模型: {usage['model_count']} 个")
    
    def _on_search_text_changed(self, text: str):
        """搜索文本变更"""
        self._model_filter.set_search_text(text)
        self._refresh_model_list()
    
    def _on_sort_changed(self, index: int):
        """排序方式变更"""
        order = self._sort_combo.currentData()
        if order:
            self._model_filter.set_sort_order(order)
            self._refresh_model_list()
    
    def _toggle_batch_mode(self):
        """切换批量操作模式"""
        self._batch_mode = self._batch_mode_btn.isChecked()
        self._batch_toolbar.setVisible(self._batch_mode)
        
        if not self._batch_mode:
            # 退出批量模式，清空选择
            self._selected_models.clear()
            self._update_selected_count()
        
        self._refresh_model_list()
    
    def _exit_batch_mode(self):
        """退出批量操作模式"""
        self._batch_mode = False
        self._batch_mode_btn.setChecked(False)
        self._batch_toolbar.setVisible(False)
        self._selected_models.clear()
        self._update_selected_count()
        self._refresh_model_list()
    
    def _on_select_all_changed(self, state):
        """全选状态变更"""
        select_all = state == Qt.CheckState.Checked.value
        
        for model_name, card in self._model_cards.items():
            card.set_selected(select_all)
            if select_all:
                self._selected_models.add(model_name)
            else:
                self._selected_models.discard(model_name)
        
        self._update_selected_count()
    
    def _on_model_selection_changed(self, model_name: str, selected: bool):
        """模型选择状态变更"""
        if selected:
            self._selected_models.add(model_name)
        else:
            self._selected_models.discard(model_name)
        
        self._update_selected_count()
    
    def _update_selected_count(self):
        """更新选中数量显示"""
        count = len(self._selected_models)
        self._selected_count_label.setText(f"已选择: {count}")
        
        # 更新全选复选框状态
        if count == 0:
            self._select_all_checkbox.setChecked(False)
        elif count == len(self._model_cards):
            self._select_all_checkbox.setChecked(True)
    
    def _on_batch_download(self):
        """批量下载"""
        if not self._selected_models:
            QMessageBox.information(self, "提示", "请先选择要下载的模型")
            return
        
        # 获取选中的未下载模型
        models_to_download = []
        for model_name in self._selected_models:
            card = self._model_cards.get(model_name)
            if card and not card.is_downloaded():
                models_to_download.append(model_name)
        
        if not models_to_download:
            QMessageBox.information(self, "提示", "选中的模型都已下载")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认批量下载",
            f"确定要下载 {len(models_to_download)} 个模型吗？\n"
            f"这可能需要较长时间。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._batch_manager.start_batch_download(models_to_download)
    
    def _on_batch_delete(self):
        """批量删除"""
        if not self._selected_models:
            QMessageBox.information(self, "提示", "请先选择要删除的模型")
            return
        
        # 获取选中的已下载模型
        models_to_delete = []
        for model_name in self._selected_models:
            card = self._model_cards.get(model_name)
            if card and card.is_downloaded():
                models_to_delete.append(model_name)
        
        if not models_to_delete:
            QMessageBox.information(self, "提示", "选中的模型都未下载")
            return
        
        # 确认对话框
        reply = QMessageBox.warning(
            self,
            "确认批量删除",
            f"确定要删除 {len(models_to_delete)} 个模型吗？\n"
            f"此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._batch_manager.start_batch_delete(models_to_delete)
    
    def _on_batch_operation_started(self, operation_type: BatchOperationType, count: int):
        """批量操作开始"""
        self._batch_progress_frame.setVisible(True)
        self._batch_mode_btn.setEnabled(False)
        
        if operation_type == BatchOperationType.DOWNLOAD:
            self._batch_status_label.setText(f"正在批量下载 {count} 个模型...")
        else:
            self._batch_status_label.setText(f"正在批量删除 {count} 个模型...")
        
        self._batch_progress_bar.setValue(0)
        self._batch_detail_label.setText("准备开始...")
    
    def _on_batch_operation_progress(self, model_name: str, progress: int, message: str):
        """批量操作进度更新"""
        self._batch_detail_label.setText(f"{model_name}: {message}")
        
        # 更新对应卡片的进度
        card = self._model_cards.get(model_name)
        if card:
            card.update_download_progress(progress, message)
    
    def _on_batch_operation_item_finished(self, model_name: str, success: bool, message: str):
        """批量操作单项完成"""
        # 更新进度条
        items = self._batch_manager.get_items()
        total = len(items)
        completed = sum(1 for item in items.values() if item.status in ["success", "failed"])
        
        if total > 0:
            progress = int(completed / total * 100)
            self._batch_progress_bar.setValue(progress)
        
        # 更新卡片状态
        card = self._model_cards.get(model_name)
        if card:
            if success:
                card.update_download_progress(100, message)
            else:
                card.update_download_progress(0, f"失败: {message}")
    
    def _on_batch_operation_finished(self, all_success: bool, success_count: int, total_count: int):
        """批量操作完成"""
        self._batch_progress_frame.setVisible(False)
        self._batch_mode_btn.setEnabled(True)
        
        if all_success:
            QMessageBox.information(
                self,
                "批量操作完成",
                f"成功完成 {success_count}/{total_count} 个操作"
            )
        else:
            QMessageBox.warning(
                self,
                "批量操作完成",
                f"完成 {success_count}/{total_count} 个操作，部分操作失败"
            )
        
        # 刷新列表
        self._refresh_model_list()
        
        # 退出批量模式
        self._exit_batch_mode()
    
    def _on_batch_operation_cancelled(self):
        """批量操作取消"""
        self._batch_status_label.setText("批量操作已取消")
        self._batch_detail_label.setText("正在停止...")
    
    def _on_download_requested(self, model_name: str):
        """处理下载请求"""
        # 确认下载
        model_info = self._model_manager.get_model_info(model_name)
        if not model_info:
            QMessageBox.warning(self, "错误", f"未知模型: {model_name}")
            return
        
        # 检查是否有可恢复的下载
        resumable = self._download_state_manager.has_resumable_download(model_name)
        
        message = f"确定要下载模型 {model_name} 吗？\n大小: {model_info.size_gb} GB\n"
        if resumable:
            progress = self._download_state_manager.get_resumable_progress(model_name)
            message += f"检测到可恢复下载（{progress}%），将继续下载。\n"
        message += "下载可能需要较长时间。"
        
        reply = QMessageBox.question(
            self,
            "确认下载",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._start_download(model_name)
    
    def _start_download(self, model_name: str):
        """开始下载模型"""
        self._download_progress_frame.setVisible(True)
        self._download_status_label.setText(f"正在下载模型: {model_name}")
        self._animated_progress_bar.set_value_animated(0)
        
        # 更新卡片状态
        card = self._model_cards.get(model_name)
        if card:
            card.set_downloading(True)
        
        # 禁用所有下载按钮
        for c in self._model_cards.values():
            if not c.is_downloaded():
                c.setEnabled(False)
        
        # 保存下载状态
        self._download_state_manager.mark_downloading(model_name, 0)
        
        self._download_worker = ModelDownloadWorker(model_name, self._model_manager, self)
        self._download_worker.progress_signal.connect(
            lambda p, m: self._on_download_progress(model_name, p, m)
        )
        self._download_worker.finished_signal.connect(
            lambda s, m: self._on_download_finished(model_name, s, m)
        )
        self._download_worker.start()
    
    def _on_download_progress(self, model_name: str, percentage: int, message: str):
        """下载进度更新"""
        self._animated_progress_bar.set_value_animated(percentage)
        self._download_status_label.setText(message)
        
        # 更新卡片进度
        card = self._model_cards.get(model_name)
        if card:
            card.update_download_progress(percentage, message)
        
        # 更新下载状态
        self._download_state_manager.update_progress(model_name, percentage, 0)
    
    def _on_download_finished(self, model_name: str, success: bool, message: str):
        """下载完成"""
        self._download_worker = None
        
        # 启用所有卡片
        for card in self._model_cards.values():
            card.setEnabled(True)
            card.set_downloading(False)
        
        # 更新下载状态
        if success:
            self._download_state_manager.mark_completed(model_name)
            self._download_status_label.setText("✅ " + message)
            QMessageBox.information(self, "成功", f"模型下载完成！\n{message}")
        else:
            self._download_state_manager.mark_failed(model_name, message)
            self._download_status_label.setText("❌ " + message)
            QMessageBox.warning(self, "下载失败", message)
        
        # 隐藏进度条
        QTimer.singleShot(3000, lambda: self._download_progress_frame.setVisible(False))
        
        # 刷新列表
        self._refresh_model_list()
    
    def _on_delete_requested(self, model_name: str):
        """处理删除请求"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除模型 {model_name} 吗？\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self._model_manager.delete_model(model_name)
            if success:
                # 清除下载状态
                self._download_state_manager.remove_state(model_name)
                QMessageBox.information(self, "成功", f"模型 {model_name} 已删除")
                self._refresh_model_list()
            else:
                QMessageBox.warning(self, "失败", f"删除模型 {model_name} 失败")
    
    def _on_use_requested(self, model_name: str):
        """处理使用请求"""
        # 更新配置
        self.model_changed.emit(model_name)
        
        # 发送设置变更信号
        self.settings_changed.emit({
            'inference': {
                'local': {
                    'model_name': model_name
                }
            }
        })
        
        QMessageBox.information(self, "成功", f"已选择模型: {model_name}\n设置将在下次推理时生效。")
    
    def _check_resumable_downloads(self):
        """检查可恢复的下载"""
        resumable = self._download_state_manager.get_resumable_downloads()
        if resumable:
            model_names = [s.model_name for s in resumable]
            reply = QMessageBox.question(
                self,
                "发现可恢复的下载",
                f"发现 {len(resumable)} 个未完成的下载:\n" +
                "\n".join([f"- {s.model_name} ({s.progress}%)" for s in resumable]) +
                "\n\n是否继续下载？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 继续第一个可恢复的下载
                for state in resumable:
                    if state.model_name in self._model_cards:
                        self._start_download(state.model_name)
                        break
    
    def get_current_model(self) -> Optional[str]:
        """获取当前选中的模型"""
        return self._config.get('inference', {}).get('local', {}).get('model_name')
    
    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        self._config = config
    
    def closeEvent(self, event):
        """关闭事件处理"""
        # 取消正在进行的下载
        if self._download_worker and self._download_worker.isRunning():
            self._download_worker.cancel()
            self._download_worker.terminate()
            self._download_worker.wait()
        
        # 清理批量操作
        self._batch_manager.cleanup()
        
        event.accept()


if __name__ == "__main__":
    # 测试模型管理页面
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 应用主题
    ThemeManager.get_instance().apply_theme(app)
    
    # 创建测试配置
    test_config = {
        'model': {
            'models_dir': 'test_models'
        },
        'inference': {
            'local': {
                'model_name': 'qwen3.5-9b-fp16'
            }
        }
    }
    
    # 创建并显示页面
    page = ModelManagerPage(config=test_config)
    page.setWindowTitle("模型管理页面测试")
    page.resize(1000, 800)
    page.show()
    
    sys.exit(app.exec())
