"""
模型管理页面 - 管理本地AI模型的下载、删除和查看

功能：
- 显示可用模型列表（从model_manager获取）
- 显示已下载模型和可下载模型
- 提供下载按钮（调用model_manager.download_model）
- 提供删除按钮（删除本地模型文件）
- 显示模型信息（大小、版本、状态）
"""

from typing import Optional, Dict, Any, List, Callable
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QMessageBox,
    QGridLayout,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
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

# 导入模型管理模块
try:
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.model_manager import ModelManager, ModelInfo
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.gpu_checker import GPUChecker
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


class ModelCard(OutlinedCardWidget):
    """模型卡片控件"""
    
    download_requested = pyqtSignal(str)  # 下载请求信号
    delete_requested = pyqtSignal(str)    # 删除请求信号
    use_requested = pyqtSignal(str)       # 使用请求信号
    
    def __init__(self, model_info: ModelInfo, is_recommended: bool = False, parent=None):
        super().__init__(parent)
        self._model_info = model_info
        self._is_recommended = is_recommended
        self._theme = ThemeManager.get_instance()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = self.get_content_layout()
        
        # 模型名称和状态
        header_layout = QHBoxLayout()
        
        name_label = QLabel(self._model_info.name)
        name_font = QFont(self._theme.get_font_family(), self._theme.get_font_size('title_medium'))
        name_font.setBold(True)
        name_label.setFont(name_font)
        if self._is_recommended:
            name_label.setStyleSheet("color: #4361ee;")
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        # 状态标签
        if self._model_info.is_downloaded:
            status_label = QLabel("✓ 已下载")
            status_label.setStyleSheet("color: #2ecc71; font-size: 12px;")
        else:
            status_label = QLabel("未下载")
            status_label.setStyleSheet("color: #999999; font-size: 12px;")
        header_layout.addWidget(status_label)
        
        layout.addLayout(header_layout)
        
        # 描述
        desc_label = QLabel(self._model_info.description)
        desc_label.setProperty("variant", "muted")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 规格信息
        specs_text = (
            f"大小: {self._model_info.size_gb} GB | "
            f"量化: {self._model_info.quantization} | "
            f"参数: {self._model_info.parameters} | "
            f"推荐显存: {self._model_info.recommended_gpu_memory_gb} GB"
        )
        specs_label = QLabel(specs_text)
        specs_label.setProperty("variant", "muted")
        specs_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(specs_label)
        
        # 推荐标签
        if self._is_recommended:
            rec_label = QLabel("★ 推荐模型")
            rec_label.setStyleSheet("color: #4361ee; font-size: 11px;")
            layout.addWidget(rec_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        if self._model_info.is_downloaded:
            # 已下载：显示使用和删除按钮
            use_btn = PrimaryButton("使用")
            use_btn.setFixedHeight(32)
            use_btn.clicked.connect(lambda: self.use_requested.emit(self._model_info.name))
            button_layout.addWidget(use_btn)
            
            delete_btn = DangerButton("删除")
            delete_btn.setFixedHeight(32)
            delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._model_info.name))
            button_layout.addWidget(delete_btn)
        else:
            # 未下载：显示下载按钮
            download_btn = PrimaryButton("下载")
            download_btn.setFixedHeight(32)
            download_btn.clicked.connect(lambda: self.download_requested.emit(self._model_info.name))
            button_layout.addWidget(download_btn)
        
        layout.addLayout(button_layout)
    
    def get_model_name(self) -> str:
        """获取模型名称"""
        return self._model_info.name


class ModelManagerPage(QWidget):
    """
    模型管理页面
    
    功能：
    - 显示所有可用模型
    - 显示已下载和可下载模型
    - 下载/删除模型
    - 显示模型详细信息
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
        
        self._setup_ui()
        self._setup_style()
        self._refresh_model_list()
    
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
        
        # 下载进度区域（默认隐藏）
        self._download_progress_frame = QFrame()
        self._download_progress_frame.setVisible(False)
        download_layout = QVBoxLayout(self._download_progress_frame)
        download_layout.setContentsMargins(0, 0, 0, 0)
        download_layout.setSpacing(self._theme.get_spacing('sm'))
        
        self._download_status_label = QLabel("准备下载...")
        self._download_status_label.setProperty("variant", "muted")
        download_layout.addWidget(self._download_status_label)
        
        self._download_progress_bar = QProgressBar()
        self._download_progress_bar.setRange(0, 100)
        self._download_progress_bar.setTextVisible(True)
        download_layout.addWidget(self._download_progress_bar)
        
        self._animated_progress_bar = AnimatedProgressBar(self._download_progress_bar)
        
        main_layout.addWidget(self._download_progress_frame)
        
        # 模型列表区域
        models_title = QLabel("可用模型")
        models_title_font = QFont(self._theme.get_font_family(), self._theme.get_font_size('title_large'))
        models_title_font.setBold(True)
        models_title.setFont(models_title_font)
        main_layout.addWidget(models_title)
        
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
        count_label = QLabel(f"已安装模型: {usage['model_count']} 个")
        count_label.setProperty("variant", "muted")
        size_layout.addWidget(count_label)
        
        layout.addLayout(size_layout)
        
        return card
    
    def _setup_style(self):
        """设置样式"""
        # 进度条样式
        self._download_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #48484a;
                border-radius: 4px;
                background-color: #2c2c2e;
                height: 24px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4361ee;
                border-radius: 3px;
            }
        """)
    
    def _refresh_model_list(self):
        """刷新模型列表"""
        # 清除旧的模型卡片
        while self._models_grid.count():
            item = self._models_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._model_cards.clear()
        
        # 获取推荐模型
        gpu_result = self._gpu_checker.check_gpu_availability()
        self._recommended_model = gpu_result.get('recommended_model')
        
        # 获取所有模型
        models = self._model_manager.get_all_models()
        
        # 添加模型卡片到网格
        row = 0
        col = 0
        
        for model in models:
            is_recommended = model.name == self._recommended_model
            card = ModelCard(model, is_recommended)
            
            # 连接信号
            card.download_requested.connect(self._on_download_requested)
            card.delete_requested.connect(self._on_delete_requested)
            card.use_requested.connect(self._on_use_requested)
            
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
    
    def _on_download_requested(self, model_name: str):
        """处理下载请求"""
        # 确认下载
        model_info = self._model_manager.get_model_info(model_name)
        if not model_info:
            QMessageBox.warning(self, "错误", f"未知模型: {model_name}")
            return
        
        reply = QMessageBox.question(
            self,
            "确认下载",
            f"确定要下载模型 {model_name} 吗？\n"
            f"大小: {model_info.size_gb} GB\n"
            f"下载可能需要较长时间。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._start_download(model_name)
    
    def _start_download(self, model_name: str):
        """开始下载模型"""
        self._download_progress_frame.setVisible(True)
        self._download_status_label.setText(f"正在下载模型: {model_name}")
        self._animated_progress_bar.set_value_animated(0)
        
        # 禁用所有下载按钮
        for card in self._model_cards.values():
            card.setEnabled(False)
        
        self._download_worker = ModelDownloadWorker(model_name, self._model_manager, self)
        self._download_worker.progress_signal.connect(self._on_download_progress)
        self._download_worker.finished_signal.connect(self._on_download_finished)
        self._download_worker.start()
    
    def _on_download_progress(self, percentage: int, message: str):
        """下载进度更新"""
        self._animated_progress_bar.set_value_animated(percentage)
        self._download_status_label.setText(message)
    
    def _on_download_finished(self, success: bool, message: str):
        """下载完成"""
        self._download_worker = None
        
        # 启用所有卡片
        for card in self._model_cards.values():
            card.setEnabled(True)
        
        if success:
            self._download_status_label.setText("✅ " + message)
            QMessageBox.information(self, "成功", f"模型下载完成！\n{message}")
            # 刷新列表
            self._refresh_model_list()
        else:
            self._download_status_label.setText("❌ " + message)
            QMessageBox.warning(self, "下载失败", message)
        
        # 隐藏进度条
        QTimer.singleShot(3000, lambda: self._download_progress_frame.setVisible(False))
    
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
        
        event.accept()


# 导入QTimer用于延迟隐藏进度条
from PyQt6.QtCore import QTimer


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
