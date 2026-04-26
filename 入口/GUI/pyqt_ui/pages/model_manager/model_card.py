"""
模型卡片组件

提供模型信息的展示和操作按钮
遵循 Material Design 3 设计规范
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QProgressBar, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

# 支持两种导入方式
try:
    from ...theme.theme_manager import ThemeManager
    from ...theme.animation_manager import AnimationManager
    from ...widgets.base_widgets import (
        PrimaryButton, SecondaryButton, DangerButton, OutlinedCardWidget
    )
    from .....安卓相关.core.local_inference.model_manager import ModelInfo
except ImportError:
    import sys
    import os
    current_file = os.path.abspath(__file__)
    model_manager_dir = os.path.dirname(current_file)
    pages_dir = os.path.dirname(model_manager_dir)
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
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.theme.animation_manager import AnimationManager
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.base_widgets import (
        PrimaryButton, SecondaryButton, DangerButton, OutlinedCardWidget
    )
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.model_manager import ModelInfo


class ModelCard(OutlinedCardWidget):
    """
    模型卡片控件
    
    功能：
    - 显示模型信息（名称、描述、大小、量化方式等）
    - 显示下载状态
    - 提供操作按钮（下载、删除、使用）
    - 支持选择模式（复选框）
    - 支持详细信息展开/折叠
    """
    
    # 信号
    download_requested = pyqtSignal(str)      # 下载请求信号
    delete_requested = pyqtSignal(str)        # 删除请求信号
    use_requested = pyqtSignal(str)           # 使用请求信号
    selection_changed = pyqtSignal(str, bool) # 选择状态变更（模型名，是否选中）
    details_toggled = pyqtSignal(str, bool)   # 详情展开/折叠
    
    def __init__(
        self,
        model_info: ModelInfo,
        is_recommended: bool = False,
        show_checkbox: bool = False,
        parent: Optional[QWidget] = None
    ):
        """
        初始化模型卡片
        
        Args:
            model_info: 模型信息
            is_recommended: 是否为推荐模型
            show_checkbox: 是否显示复选框
            parent: 父控件
        """
        super().__init__(parent)
        self._model_info = model_info
        self._is_recommended = is_recommended
        self._show_checkbox = show_checkbox
        self._is_selected = False
        self._is_expanded = False
        self._is_downloading = False
        self._download_progress = 0
        
        self._theme = ThemeManager.get_instance()
        self._anim_manager = AnimationManager.get_instance()
        
        self._setup_ui()
        self._setup_style()
    
    def _setup_ui(self):
        """设置UI结构"""
        layout = self.get_content_layout()
        
        # 头部区域（复选框 + 名称 + 状态）
        header_layout = QHBoxLayout()
        header_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 复选框
        if self._show_checkbox:
            self._checkbox = QCheckBox()
            self._checkbox.setChecked(self._is_selected)
            self._checkbox.stateChanged.connect(self._on_selection_changed)
            header_layout.addWidget(self._checkbox)
        
        # 模型名称
        name_label = QLabel(self._model_info.name)
        name_font = QFont(
            self._theme.get_font_family(),
            self._theme.get_font_size('title_medium')
        )
        name_font.setBold(True)
        name_label.setFont(name_font)
        if self._is_recommended:
            name_label.setStyleSheet(f"color: {self._theme.get_color('primary')};")
        header_layout.addWidget(name_label)
        
        # 推荐标签
        if self._is_recommended:
            rec_label = QLabel("★")
            rec_label.setStyleSheet(f"color: {self._theme.get_color('primary')}; font-size: 14px;")
            header_layout.addWidget(rec_label)
        
        header_layout.addStretch()
        
        # 状态标签
        self._status_label = QLabel()
        self._update_status_label()
        header_layout.addWidget(self._status_label)
        
        layout.addLayout(header_layout)
        
        # 描述
        desc_label = QLabel(self._model_info.description)
        desc_label.setProperty("variant", "muted")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 规格信息
        specs_layout = QHBoxLayout()
        specs_layout.setSpacing(self._theme.get_spacing('lg'))
        
        size_label = QLabel(f"📦 {self._model_info.size_gb} GB")
        size_label.setProperty("variant", "muted")
        size_label.setStyleSheet("font-size: 11px;")
        specs_layout.addWidget(size_label)
        
        quant_label = QLabel(f"🔧 {self._model_info.quantization}")
        quant_label.setProperty("variant", "muted")
        quant_label.setStyleSheet("font-size: 11px;")
        specs_layout.addWidget(quant_label)
        
        param_label = QLabel(f"🧠 {self._model_info.parameters}")
        param_label.setProperty("variant", "muted")
        param_label.setStyleSheet("font-size: 11px;")
        specs_layout.addWidget(param_label)
        
        gpu_label = QLabel(f"💾 {self._model_info.recommended_gpu_memory_gb} GB")
        gpu_label.setProperty("variant", "muted")
        gpu_label.setStyleSheet("font-size: 11px;")
        specs_layout.addWidget(gpu_label)
        
        specs_layout.addStretch()
        layout.addLayout(specs_layout)
        
        # 下载进度条（默认隐藏）
        self._progress_frame = QFrame()
        self._progress_frame.setVisible(False)
        progress_layout = QVBoxLayout(self._progress_frame)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(self._theme.get_spacing('xs'))
        
        self._progress_label = QLabel("准备下载...")
        self._progress_label.setProperty("variant", "muted")
        self._progress_label.setStyleSheet("font-size: 11px;")
        progress_layout.addWidget(self._progress_label)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFixedHeight(20)
        progress_layout.addWidget(self._progress_bar)
        
        layout.addWidget(self._progress_frame)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        if self._model_info.is_downloaded:
            # 已下载：显示使用和删除按钮
            use_btn = PrimaryButton("使用")
            use_btn.setFixedHeight(32)
            use_btn.setFixedWidth(80)
            use_btn.clicked.connect(lambda: self.use_requested.emit(self._model_info.name))
            button_layout.addWidget(use_btn)
            
            delete_btn = DangerButton("删除")
            delete_btn.setFixedHeight(32)
            delete_btn.setFixedWidth(80)
            delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._model_info.name))
            button_layout.addWidget(delete_btn)
        else:
            # 未下载：显示下载按钮
            self._download_btn = PrimaryButton("下载")
            self._download_btn.setFixedHeight(32)
            self._download_btn.setFixedWidth(80)
            self._download_btn.clicked.connect(self._on_download_clicked)
            button_layout.addWidget(self._download_btn)
        
        layout.addLayout(button_layout)
    
    def _setup_style(self):
        """设置样式"""
        # 进度条样式
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {self._theme.get_color('border_color')};
                border-radius: 4px;
                background-color: {self._theme.get_color('bg_secondary')};
                height: 20px;
                text-align: center;
                color: {self._theme.get_color('text_primary')};
            }}
            QProgressBar::chunk {{
                background-color: {self._theme.get_color('primary')};
                border-radius: 3px;
            }}
        """)
    
    def _update_status_label(self):
        """更新状态标签"""
        if self._is_downloading:
            self._status_label.setText("⏳ 下载中...")
            self._status_label.setStyleSheet(
                f"color: {self._theme.get_color('info')}; font-size: 12px;"
            )
        elif self._model_info.is_downloaded:
            self._status_label.setText("✓ 已下载")
            self._status_label.setStyleSheet(
                f"color: {self._theme.get_color('success')}; font-size: 12px;"
            )
        else:
            self._status_label.setText("未下载")
            self._status_label.setStyleSheet(
                f"color: {self._theme.get_color('text_muted')}; font-size: 12px;"
            )
    
    def _on_selection_changed(self, state):
        """处理选择状态变更"""
        self._is_selected = state == Qt.CheckState.Checked.value
        self.selection_changed.emit(self._model_info.name, self._is_selected)
    
    def _on_download_clicked(self):
        """处理下载按钮点击"""
        if not self._is_downloading:
            self.download_requested.emit(self._model_info.name)
    
    def set_selected(self, selected: bool):
        """设置选择状态"""
        self._is_selected = selected
        if hasattr(self, '_checkbox'):
            self._checkbox.setChecked(selected)
    
    def is_selected(self) -> bool:
        """获取选择状态"""
        return self._is_selected
    
    def set_downloading(self, downloading: bool):
        """设置下载状态"""
        self._is_downloading = downloading
        self._update_status_label()
        
        if downloading:
            self._progress_frame.setVisible(True)
            if hasattr(self, '_download_btn'):
                self._download_btn.setEnabled(False)
                self._download_btn.setText("下载中...")
        else:
            self._progress_frame.setVisible(False)
            if hasattr(self, '_download_btn'):
                self._download_btn.setEnabled(True)
                self._download_btn.setText("下载")
    
    def update_download_progress(self, percentage: int, message: str):
        """更新下载进度"""
        self._download_progress = percentage
        self._progress_bar.setValue(percentage)
        self._progress_label.setText(message)
    
    def get_model_name(self) -> str:
        """获取模型名称"""
        return self._model_info.name
    
    def get_model_info(self) -> ModelInfo:
        """获取模型信息"""
        return self._model_info
    
    def is_downloaded(self) -> bool:
        """检查模型是否已下载"""
        return self._model_info.is_downloaded
    
    def set_checkbox_visible(self, visible: bool):
        """设置复选框可见性"""
        if hasattr(self, '_checkbox'):
            self._checkbox.setVisible(visible)
