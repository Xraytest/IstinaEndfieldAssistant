"""
设置页面 - 重构版

处理配置选项、版本信息、更新功能、本地推理设置和硬件加速设置

特性:
- Material Design 3 风格卡片式布局
- 本地推理设置（GPU检测、模型选择、下载管理）
- 硬件加速设置
- 丰富的动画效果
- 自动保存配置
- 模块化设计：使用独立的设置卡片组件

重构改进:
- 代码从1749行减少到约400行
- 提取公共worker到workers.py
- 提取设置卡片到settings_cards.py
- 添加输入验证器
- 简化异常处理
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame,
    QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

# 导入主题和基础控件
try:
    from ..theme.theme_manager import ThemeManager
    from ..theme.animation_manager import AnimationManager, fade_in_widget
    from ..widgets.base_widgets import ElevatedCardWidget
    from .settings.workers import GPUCheckWorker, ModelDownloadWorker
    from .settings.settings_cards import (
        LocalInferenceSettingsCard,
        HardwareSettingsCard,
        CacheSettingsCard,
        TouchSettingsCard,
        CloudModelSettingsCard,
        LogSettingsCard,
        VersionSettingsCard,
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
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.theme.animation_manager import AnimationManager, fade_in_widget
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.base_widgets import ElevatedCardWidget
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.pages.settings.workers import GPUCheckWorker, ModelDownloadWorker
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.pages.settings.settings_cards import (
        LocalInferenceSettingsCard,
        HardwareSettingsCard,
        CacheSettingsCard,
        TouchSettingsCard,
        CloudModelSettingsCard,
        LogSettingsCard,
        VersionSettingsCard,
    )


class SettingsPage(QWidget):
    """
    设置页面（重构版）
    
    功能：
    - 配置选项列表（使用独立的设置卡片组件）
    - 本地推理设置（GPU检测、模型选择）
    - 硬件加速设置
    - 触控设置
    - 云端模型设置
    - 日志设置
    - 版本信息和更新功能
    - 丰富的动画效果
    
    信号：
    - settings_changed(dict): 设置变更信号
    - check_update_requested(): 检查更新请求信号
    - update_requested(): 更新请求信号
    - touch_method_changed(str): 触控方式变更信号
    - model_changed(str): 模型选择变更信号
    - local_inference_changed(bool): 本地推理开关变更信号
    - hardware_acceleration_changed(bool): 硬件加速变更信号
    """
    
    # 自定义信号
    settings_changed = pyqtSignal(dict)
    check_update_requested = pyqtSignal()
    update_requested = pyqtSignal()
    touch_method_changed = pyqtSignal(str)
    model_changed = pyqtSignal(str)
    local_inference_changed = pyqtSignal(bool)
    hardware_acceleration_changed = pyqtSignal(bool)
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        初始化设置页面
        
        Args:
            parent: 父控件
            config: 当前配置字典
        """
        super().__init__(parent)
        
        self._config = config or {}
        self._theme = ThemeManager.get_instance()
        self._anim_manager = AnimationManager.get_instance()
        
        # Worker线程
        self._check_worker: Optional[GPUCheckWorker] = None
        self._download_worker: Optional[ModelDownloadWorker] = None
        
        # 设置卡片引用
        self._local_inference_card: Optional[LocalInferenceSettingsCard] = None
        self._hardware_card: Optional[HardwareSettingsCard] = None
        self._cache_card: Optional[CacheSettingsCard] = None
        self._touch_card: Optional[TouchSettingsCard] = None
        self._cloud_model_card: Optional[CloudModelSettingsCard] = None
        self._log_card: Optional[LogSettingsCard] = None
        self._version_card: Optional[VersionSettingsCard] = None
        
        self._setup_ui()
        self._setup_connections()
        
        # 启动时检查GPU（异步）
        QTimer.singleShot(100, self._start_gpu_check)
    
    def _setup_ui(self) -> None:
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
        title_label = QLabel("设置")
        title_font = QFont(self._theme.get_font_family(), self._theme.get_font_size('headline_medium'))
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setProperty("variant", "header")
        main_layout.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel("配置应用程序的各项功能和偏好设置")
        subtitle_label.setProperty("variant", "muted")
        main_layout.addWidget(subtitle_label)
        
        main_layout.addSpacing(self._theme.get_spacing('md'))
        
        # === 本地推理设置卡片 ===
        self._local_inference_card = LocalInferenceSettingsCard(self._config, self)
        self._local_inference_card.settings_changed.connect(self._on_local_inference_settings_changed)
        self._local_inference_card.model_selected.connect(self._on_model_selected)
        self._local_inference_card.download_requested.connect(self._on_download_requested)
        main_layout.addWidget(self._local_inference_card)
        
        # === 硬件加速设置卡片 ===
        self._hardware_card = HardwareSettingsCard(self._config, self)
        self._hardware_card.settings_changed.connect(self._on_hardware_settings_changed)
        main_layout.addWidget(self._hardware_card)
        
        # === 缓存设置卡片 ===
        self._cache_card = CacheSettingsCard(self._config, self)
        self._cache_card.settings_changed.connect(self._on_cache_settings_changed)
        main_layout.addWidget(self._cache_card)
        
        # === 触控设置卡片 ===
        self._touch_card = TouchSettingsCard(self._config, self)
        self._touch_card.settings_changed.connect(self._on_touch_settings_changed)
        self._touch_card.touch_method_changed.connect(self.touch_method_changed)
        main_layout.addWidget(self._touch_card)
        
        # === 云端模型设置卡片 ===
        self._cloud_model_card = CloudModelSettingsCard(self._config, self)
        self._cloud_model_card.settings_changed.connect(self._on_cloud_model_settings_changed)
        self._cloud_model_card.model_changed.connect(self.model_changed)
        self._cloud_model_card.refresh_requested.connect(self._on_refresh_models_requested)
        main_layout.addWidget(self._cloud_model_card)
        
        # === 日志设置卡片 ===
        self._log_card = LogSettingsCard(self._config, self)
        self._log_card.settings_changed.connect(self._on_log_settings_changed)
        main_layout.addWidget(self._log_card)
        
        # === 版本信息卡片 ===
        self._version_card = VersionSettingsCard(self._config, self)
        self._version_card.check_update_requested.connect(self.check_update_requested)
        self._version_card.update_requested.connect(self.update_requested)
        main_layout.addWidget(self._version_card)
        
        main_layout.addStretch()
        
        # 设置主布局
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self._scroll_area)
    
    def _setup_connections(self) -> None:
        """设置信号连接"""
        # 连接本地推理卡片的GPU检测按钮
        if self._local_inference_card:
            self._local_inference_card.get_gpu_check_button().clicked.connect(self._start_gpu_check)
    
    # === GPU检测相关方法 ===
    
    def _start_gpu_check(self) -> None:
        """开始GPU检测"""
        if self._local_inference_card:
            self._local_inference_card._gpu_status_icon.setText("⏳")
            self._local_inference_card._gpu_status_text.setText("正在检测显卡配置...")
            self._local_inference_card.get_gpu_check_button().setVisible(False)
        
        self._check_worker = GPUCheckWorker(self)
        self._check_worker.finished_signal.connect(self._on_gpu_check_finished)
        self._check_worker.error_signal.connect(self._on_gpu_check_error)
        self._check_worker.start()
    
    def _on_gpu_check_finished(self, result: Dict[str, Any]) -> None:
        """GPU检测完成"""
        self._check_worker = None
        
        if self._local_inference_card:
            self._local_inference_card.update_gpu_status(result)
    
    def _on_gpu_check_error(self, error: str) -> None:
        """GPU检测错误"""
        self._check_worker = None
        
        if self._local_inference_card:
            self._local_inference_card._gpu_status_icon.setText("❌")
            self._local_inference_card._gpu_status_text.setText("检测失败")
            self._local_inference_card._gpu_details_label.setText(f"错误详情:\n{error}")
            self._local_inference_card._gpu_details_frame.setVisible(True)
            self._local_inference_card.get_gpu_check_button().setVisible(True)
    
    # === 模型下载相关方法 ===
    
    def _on_download_requested(self, model_name: str) -> None:
        """处理模型下载请求"""
        self._download_worker = ModelDownloadWorker(model_name, self)
        self._download_worker.progress_signal.connect(self._on_download_progress)
        self._download_worker.finished_signal.connect(self._on_download_finished)
        self._download_worker.start()
    
    def _on_download_progress(self, percentage: int, message: str) -> None:
        """下载进度更新"""
        if self._local_inference_card:
            self._local_inference_card.update_download_progress(percentage, message)
    
    def _on_download_finished(self, success: bool, message: str) -> None:
        """下载完成"""
        self._download_worker = None
        
        if self._local_inference_card:
            self._local_inference_card.on_download_finished(success, message)
    
    def _on_model_selected(self, model_name: str) -> None:
        """模型被选择"""
        self._config.setdefault('inference', {}).setdefault('local', {})['model_name'] = model_name
        self.settings_changed.emit({
            'inference': {
                'local': {
                    'model_name': model_name
                }
            }
        })
    
    # === 设置变更处理方法 ===
    
    def _on_local_inference_settings_changed(self, settings: Dict[str, Any]) -> None:
        """本地推理设置变更"""
        self._config.update(settings)
        self.local_inference_changed.emit(
            settings.get('inference', {}).get('local', {}).get('enabled', False)
        )
        self.settings_changed.emit(settings)
    
    def _on_hardware_settings_changed(self, settings: Dict[str, Any]) -> None:
        """硬件加速设置变更"""
        self._config.update(settings)
        self.hardware_acceleration_changed.emit(
            settings.get('rendering', {}).get('hardware_acceleration', True)
        )
        self.settings_changed.emit(settings)
    
    def _on_cache_settings_changed(self, settings: Dict[str, Any]) -> None:
        """缓存设置变更"""
        self._config.update(settings)
        self.settings_changed.emit(settings)
    
    def _on_touch_settings_changed(self, settings: Dict[str, Any]) -> None:
        """触控设置变更"""
        self._config.update(settings)
        self.settings_changed.emit(settings)
    
    def _on_cloud_model_settings_changed(self, settings: Dict[str, Any]) -> None:
        """云端模型设置变更"""
        self._config.update(settings)
        self.settings_changed.emit(settings)
    
    def _on_log_settings_changed(self, settings: Dict[str, Any]) -> None:
        """日志设置变更"""
        self._config.update(settings)
        self.settings_changed.emit(settings)
    
    def _on_refresh_models_requested(self) -> None:
        """刷新模型列表请求"""
        self.settings_changed.emit({'refresh_models': True})
    
    # === 公共方法 ===
    
    def set_current_version(self, version: str) -> None:
        """设置当前版本"""
        if self._version_card:
            self._version_card.set_current_version(version)
    
    def set_latest_version(self, version: str, has_update: bool = False) -> None:
        """设置最新版本"""
        if self._version_card:
            self._version_card.set_latest_version(version, has_update)
    
    def set_update_error(self, error_msg: str) -> None:
        """设置更新错误状态"""
        if self._version_card:
            self._version_card.set_update_error(error_msg)
    
    def set_update_progress(self, progress: int) -> None:
        """设置更新进度"""
        if self._version_card:
            self._version_card.set_update_progress(progress)
    
    def set_update_complete(self, success: bool) -> None:
        """设置更新完成状态"""
        if self._version_card:
            self._version_card.set_update_complete(success)
    
    def update_available_models(self, models: list, default_model: str = "") -> None:
        """更新可用模型列表"""
        if self._cloud_model_card:
            self._cloud_model_card.update_available_models(models, default_model)
    
    def set_auto_select(self, auto_select: bool) -> None:
        """设置自动选择状态"""
        if self._cloud_model_card:
            self._cloud_model_card.set_auto_select(auto_select)
    
    def get_selected_model(self) -> str:
        """获取当前选择的模型"""
        if self._cloud_model_card:
            return self._cloud_model_card.get_selected_model()
        return ""
    
    def is_auto_select(self) -> bool:
        """是否启用自动选择"""
        if self._cloud_model_card:
            return self._cloud_model_card.is_auto_select()
        return True
    
    def get_touch_method(self) -> str:
        """获取当前触控方式"""
        if self._touch_card:
            return self._touch_card.get_touch_method()
        return "maatouch"
    
    def set_touch_method(self, method: str) -> None:
        """设置触控方式"""
        if self._touch_card:
            self._touch_card.set_touch_method(method)
    
    def get_log_level(self) -> str:
        """获取当前日志级别"""
        if self._log_card:
            return self._log_card.get_log_level()
        return "INFO"
    
    def set_log_level(self, level: str) -> None:
        """设置日志级别"""
        if self._log_card:
            self._log_card.set_log_level(level)
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        config = self._config.copy()
        
        # 合并各卡片的配置
        if self._hardware_card:
            config.update(self._hardware_card.get_config())
        if self._cache_card:
            config.update(self._cache_card.get_config())
        
        # 添加其他设置
        config['touch'] = {
            'touch_method': self.get_touch_method(),
            'fail_on_error': True  # 默认值
        }
        config['logging'] = {
            'level': self.get_log_level()
        }
        config['model'] = {
            'selected_model': self.get_selected_model(),
            'auto_select': self.is_auto_select()
        }
        
        return config
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config = config
        # 各卡片会自动从配置中读取值
    
    def set_animation_enabled(self, enabled: bool) -> None:
        """设置动画启用状态"""
        self._anim_manager.set_enabled(enabled)
    
    def closeEvent(self, event) -> None:
        """关闭事件处理"""
        # 取消正在进行的任务
        if self._check_worker and self._check_worker.isRunning():
            self._check_worker.terminate()
            self._check_worker.wait()
        
        if self._download_worker and self._download_worker.isRunning():
            self._download_worker.cancel()
            self._download_worker.terminate()
            self._download_worker.wait()
        
        event.accept()
