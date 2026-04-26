"""
设置卡片组件模块

提供独立的设置区域卡片组件，每个卡片负责一个特定的设置功能
"""

from typing import Optional, Dict, Any, List, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QCheckBox, QFrame, QProgressBar, QGridLayout,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

# 导入主题和基础控件
try:
    from ...theme.theme_manager import ThemeManager
    from ...theme.animation_manager import AnimationManager, fade_in_widget
    from ...widgets.base_widgets import (
        PrimaryButton, SecondaryButton, CardWidget, ElevatedCardWidget, OutlinedCardWidget
    )
    from .....安卓相关.core.local_inference.model_manager import ModelManager, ModelInfo
except ImportError:
    import sys
    import os
    current_file = os.path.abspath(__file__)
    settings_dir = os.path.dirname(current_file)
    pages_dir = os.path.dirname(settings_dir)
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
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.base_widgets import (
        PrimaryButton, SecondaryButton, CardWidget, ElevatedCardWidget, OutlinedCardWidget
    )
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.model_manager import ModelManager, ModelInfo

from .validators import CacheSizeValidator, CacheTTLValidator


class AnimatedSwitch(QCheckBox):
    """带动画的开关控件"""
    
    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self._setup_style()
    
    def _setup_style(self) -> None:
        """设置开关样式"""
        self.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 44px;
                height: 24px;
                border-radius: 12px;
                background-color: #48484a;
                border: none;
                position: relative;
            }
            QCheckBox::indicator:checked {
                background-color: #4361ee;
            }
            QCheckBox::indicator::handle {
                width: 20px;
                height: 20px;
                border-radius: 10px;
                background-color: #ffffff;
                position: absolute;
                top: 2px;
                left: 2px;
            }
            QCheckBox::indicator:checked::handle {
                left: 22px;
            }
            QCheckBox::indicator:hover {
                background-color: #636366;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #5a7af0;
            }
        """)


class LocalInferenceSettingsCard(ElevatedCardWidget):
    """本地推理设置卡片"""
    
    # 信号
    settings_changed = pyqtSignal(dict)
    model_selected = pyqtSignal(str)
    download_requested = pyqtSignal(str)
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        self._config = config or {}
        self._gpu_info: Optional[Dict[str, Any]] = None
        self._gpu_meets_requirements = False
        self._model_manager: Optional[ModelManager] = None
        
        super().__init__(title="🧠 本地推理设置", parent=parent)
        
        self._theme = ThemeManager.get_instance()
        self._setup_content()
    
    def _setup_content(self) -> None:
        """设置卡片内容"""
        layout = self.get_content_layout()
        
        # GPU状态显示区域
        self._gpu_status_frame = QFrame()
        gpu_status_layout = QHBoxLayout(self._gpu_status_frame)
        gpu_status_layout.setContentsMargins(0, 0, 0, 0)
        gpu_status_layout.setSpacing(self._theme.get_spacing('md'))
        
        self._gpu_status_icon = QLabel("⏳")
        self._gpu_status_icon.setStyleSheet("font-size: 24px;")
        gpu_status_layout.addWidget(self._gpu_status_icon)
        
        self._gpu_status_text = QLabel("正在检测显卡配置...")
        self._gpu_status_text.setProperty("variant", "secondary")
        gpu_status_layout.addWidget(self._gpu_status_text)
        gpu_status_layout.addStretch()
        
        self._gpu_check_btn = SecondaryButton("重新检测")
        self._gpu_check_btn.setFixedWidth(100)
        self._gpu_check_btn.setVisible(False)
        gpu_status_layout.addWidget(self._gpu_check_btn)
        
        layout.addWidget(self._gpu_status_frame)
        
        # GPU详细信息
        self._gpu_details_frame = QFrame()
        self._gpu_details_frame.setVisible(False)
        gpu_details_layout = QVBoxLayout(self._gpu_details_frame)
        gpu_details_layout.setContentsMargins(0, 0, 0, 0)
        
        self._gpu_details_label = QLabel("")
        self._gpu_details_label.setProperty("variant", "muted")
        self._gpu_details_label.setWordWrap(True)
        gpu_details_layout.addWidget(self._gpu_details_label)
        
        layout.addWidget(self._gpu_details_frame)
        
        # 本地推理开关
        self._local_inference_frame = QFrame()
        self._local_inference_frame.setVisible(False)
        local_inf_layout = QHBoxLayout(self._local_inference_frame)
        local_inf_layout.setContentsMargins(0, 0, 0, 0)
        
        local_inf_label = QLabel("启用本地推理:")
        local_inf_label.setProperty("variant", "secondary")
        local_inf_layout.addWidget(local_inf_label)
        
        self._local_inference_switch = AnimatedSwitch()
        self._local_inference_switch.setChecked(
            self._config.get('inference', {}).get('local', {}).get('enabled', False)
        )
        local_inf_layout.addWidget(self._local_inference_switch)
        
        local_inf_tip = QLabel("使用本地GPU进行AI推理，无需网络连接")
        local_inf_tip.setProperty("variant", "muted")
        local_inf_tip.setWordWrap(True)
        local_inf_layout.addWidget(local_inf_tip, 1)
        
        layout.addWidget(self._local_inference_frame)
        
        # 模型选择区域
        self._local_model_frame = QFrame()
        self._local_model_frame.setVisible(False)
        local_model_layout = QVBoxLayout(self._local_model_frame)
        local_model_layout.setContentsMargins(0, 0, 0, 0)
        
        model_select_title = QLabel("选择本地模型:")
        model_select_title.setProperty("variant", "secondary")
        local_model_layout.addWidget(model_select_title)
        
        self._model_grid = QGridLayout()
        self._model_grid.setSpacing(self._theme.get_spacing('md'))
        local_model_layout.addLayout(self._model_grid)
        
        # 模型下载进度
        self._model_download_frame = QFrame()
        self._model_download_frame.setVisible(False)
        download_layout = QVBoxLayout(self._model_download_frame)
        download_layout.setContentsMargins(0, 0, 0, 0)
        
        self._download_status_label = QLabel("准备下载...")
        self._download_status_label.setProperty("variant", "muted")
        download_layout.addWidget(self._download_status_label)
        
        self._model_download_progress = QProgressBar()
        self._model_download_progress.setRange(0, 100)
        self._model_download_progress.setTextVisible(True)
        download_layout.addWidget(self._model_download_progress)
        
        local_model_layout.addWidget(self._model_download_frame)
        layout.addWidget(self._local_model_frame)
        
        # 保存按钮
        save_frame = QFrame()
        save_layout = QHBoxLayout(save_frame)
        save_layout.setContentsMargins(0, 0, 0, 0)
        save_layout.addStretch()
        
        self._save_btn = PrimaryButton("保存本地推理设置")
        save_layout.addWidget(self._save_btn)
        layout.addWidget(save_frame)
        
        # 连接信号
        self._local_inference_switch.stateChanged.connect(self._on_local_inference_changed)
        self._save_btn.clicked.connect(self._on_save_clicked)
    
    def update_gpu_status(self, gpu_info: Dict[str, Any]) -> None:
        """更新GPU状态显示"""
        self._gpu_info = gpu_info
        
        if gpu_info.get("available"):
            self._gpu_status_icon.setText("✅")
            self._gpu_status_text.setText("检测到NVIDIA显卡")
            self._update_gpu_details(gpu_info)
            self._gpu_details_frame.setVisible(True)
            
            if gpu_info.get("meets_requirements"):
                self._gpu_meets_requirements = True
                self._local_inference_frame.setVisible(True)
                fade_in_widget(self._local_inference_frame)
            else:
                self._gpu_meets_requirements = False
                self._gpu_status_icon.setText("⚠️")
                self._gpu_status_text.setText("显卡配置不足（需要16GB+显存）")
        else:
            self._gpu_status_icon.setText("❌")
            self._gpu_status_text.setText("未检测到NVIDIA显卡")
            self._gpu_meets_requirements = False
            error = gpu_info.get("error", "未知错误")
            self._gpu_details_label.setText(f"错误: {error}\n\n本地推理需要NVIDIA显卡和CUDA环境。")
            self._gpu_details_frame.setVisible(True)
        
        self._gpu_check_btn.setVisible(True)
    
    def _update_gpu_details(self, result: Dict[str, Any]) -> None:
        """更新GPU详情显示"""
        details = []
        
        for i, gpu in enumerate(result.get("gpus", [])):
            details.append(f"GPU {i + 1}: {gpu.get('name', 'Unknown')}")
            details.append(f"  总显存: {gpu.get('total_memory_gb', 0):.2f} GB")
            details.append(f"  可用显存: {gpu.get('free_memory_gb', 0):.2f} GB")
            if gpu.get('compute_capability'):
                details.append(f"  计算能力: {gpu['compute_capability']}")
        
        details.append(f"\nCUDA可用: {'是' if result.get('cuda_available') else '否'}")
        details.append(f"满足要求: {'是' if result.get('meets_requirements') else '否'}")
        
        recommended = result.get('recommended_model')
        if recommended:
            details.append(f"推荐模型: {recommended}")
        
        self._gpu_details_label.setText("\n".join(details))
    
    def update_model_selection(self, gpu_info: Dict[str, Any]) -> None:
        """更新模型选择UI"""
        # 清除旧的模型选择
        while self._model_grid.count():
            item = self._model_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if self._model_manager is None:
            try:
                self._model_manager = ModelManager()
            except Exception:
                return
        
        recommended = gpu_info.get("recommended_model", "qwen3.5-9b-fp16")
        models = self._model_manager.get_all_models()
        
        row, col = 0, 0
        for model in models:
            model_card = self._create_model_card(model, recommended)
            self._model_grid.addWidget(model_card, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1
    
    def _create_model_card(self, model: ModelInfo, recommended: str) -> OutlinedCardWidget:
        """创建模型选择卡片"""
        is_recommended = model.name == recommended
        is_downloaded = model.is_downloaded
        
        card = OutlinedCardWidget()
        layout = card.get_content_layout()
        
        # 模型名称
        name_label = QLabel(model.name)
        name_font = QFont()
        name_font.setBold(True)
        name_label.setFont(name_font)
        if is_recommended:
            name_label.setStyleSheet("color: #4361ee;")
        layout.addWidget(name_label)
        
        # 描述
        desc_label = QLabel(model.description)
        desc_label.setProperty("variant", "muted")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 规格信息
        specs = f"大小: {model.size_gb} GB | 量化: {model.quantization} | 推荐显存: {model.recommended_gpu_memory_gb} GB"
        specs_label = QLabel(specs)
        specs_label.setProperty("variant", "muted")
        specs_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(specs_label)
        
        # 状态标签
        status_layout = QHBoxLayout()
        if is_downloaded:
            status_label = QLabel("✓ 已下载")
            status_label.setStyleSheet("color: #2ecc71; font-size: 11px;")
            status_layout.addWidget(status_label)
        
        if is_recommended:
            rec_label = QLabel("★ 推荐")
            rec_label.setStyleSheet("color: #4361ee; font-size: 11px;")
            status_layout.addWidget(rec_label)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # 选择按钮
        select_btn = SecondaryButton("选择" if not is_downloaded else "使用")
        select_btn.setFixedHeight(28)
        select_btn.clicked.connect(lambda: self._on_model_selected(model.name))
        layout.addWidget(select_btn)
        
        # 下载按钮
        if not is_downloaded:
            download_btn = PrimaryButton("下载")
            download_btn.setFixedHeight(28)
            download_btn.clicked.connect(lambda: self._on_download_model(model.name))
            layout.addWidget(download_btn)
        
        return card
    
    def _on_local_inference_changed(self, state: int) -> None:
        """本地推理开关变更"""
        enabled = state == Qt.CheckState.Checked.value
        
        if enabled and self._gpu_meets_requirements:
            self._local_model_frame.setVisible(True)
            fade_in_widget(self._local_model_frame)
            if self._gpu_info:
                self.update_model_selection(self._gpu_info)
        else:
            self._local_model_frame.setVisible(False)
    
    def _on_model_selected(self, model_name: str) -> None:
        """模型选择"""
        self.model_selected.emit(model_name)
        QMessageBox.information(self, "成功", f"已选择模型: {model_name}")
    
    def _on_download_model(self, model_name: str) -> None:
        """开始下载模型"""
        self._model_download_frame.setVisible(True)
        self._download_status_label.setText(f"正在下载模型: {model_name}")
        self._model_download_progress.setValue(0)
        self.download_requested.emit(model_name)
    
    def update_download_progress(self, percentage: int, message: str) -> None:
        """更新下载进度"""
        self._model_download_progress.setValue(percentage)
        self._download_status_label.setText(message)
    
    def on_download_finished(self, success: bool, message: str) -> None:
        """下载完成处理"""
        if success:
            self._download_status_label.setText("✅ " + message)
            QMessageBox.information(self, "成功", "模型下载完成！")
            if self._gpu_info:
                self.update_model_selection(self._gpu_info)
        else:
            self._download_status_label.setText("❌ " + message)
            QMessageBox.warning(self, "下载失败", message)
    
    def _on_save_clicked(self) -> None:
        """保存设置"""
        settings = {
            'inference': {
                'local': {
                    'enabled': self._local_inference_switch.isChecked(),
                    'model_name': self._config.get('inference', {}).get('local', {}).get('model_name', 'qwen3.5-9b-fp16')
                }
            }
        }
        self.settings_changed.emit(settings)
        QMessageBox.information(self, "成功", "本地推理设置已保存")
    
    def get_gpu_check_button(self) -> SecondaryButton:
        """获取GPU检测按钮（用于外部连接信号）"""
        return self._gpu_check_btn
    
    def is_local_inference_enabled(self) -> bool:
        """是否启用本地推理"""
        return self._local_inference_switch.isChecked()
    
    def set_local_inference_enabled(self, enabled: bool) -> None:
        """设置本地推理开关状态"""
        self._local_inference_switch.setChecked(enabled)


class HardwareSettingsCard(CardWidget):
    """硬件加速设置卡片"""
    
    settings_changed = pyqtSignal(dict)
    
    # 选项映射
    HW_ACCEL_MODES = ['auto', 'enabled', 'disabled']
    OPENGL_MODES = ['auto', 'desktop', 'angle', 'software']
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        self._config = config or {}
        super().__init__(title="⚡ 硬件加速设置", parent=parent)
        self._theme = ThemeManager.get_instance()
        self._setup_content()
    
    def _setup_content(self) -> None:
        """设置卡片内容"""
        layout = self.get_content_layout()
        
        # 图像硬件加速
        hw_accel_frame = QFrame()
        hw_accel_layout = QHBoxLayout(hw_accel_frame)
        hw_accel_layout.setContentsMargins(0, 0, 0, 0)
        
        hw_accel_label = QLabel("图像硬件加速:")
        hw_accel_label.setProperty("variant", "secondary")
        hw_accel_label.setFixedWidth(120)
        hw_accel_layout.addWidget(hw_accel_label)
        
        self._hw_accel_combo = QComboBox()
        self._hw_accel_combo.addItems(["自动 (auto)", "启用 (enabled)", "禁用 (disabled)"])
        self._hw_accel_combo.setFixedWidth(180)
        
        current_hw_accel = self._config.get('inference', {}).get('hardware_acceleration', 'auto')
        self._hw_accel_combo.setCurrentIndex(self.HW_ACCEL_MODES.index(current_hw_accel) if current_hw_accel in self.HW_ACCEL_MODES else 0)
        
        hw_accel_layout.addWidget(self._hw_accel_combo)
        
        hw_accel_tip = QLabel("图像处理硬件加速模式（影响本地推理性能）")
        hw_accel_tip.setProperty("variant", "muted")
        hw_accel_tip.setWordWrap(True)
        hw_accel_layout.addWidget(hw_accel_tip, 1)
        
        layout.addWidget(hw_accel_frame)
        
        # UI渲染加速
        render_frame = QFrame()
        render_layout = QHBoxLayout(render_frame)
        render_layout.setContentsMargins(0, 0, 0, 0)
        
        render_label = QLabel("UI渲染加速:")
        render_label.setProperty("variant", "secondary")
        render_label.setFixedWidth(120)
        render_layout.addWidget(render_label)
        
        self._hardware_accel_switch = AnimatedSwitch("启用硬件加速")
        self._hardware_accel_switch.setChecked(
            self._config.get('rendering', {}).get('hardware_acceleration', True)
        )
        self._hardware_accel_switch.stateChanged.connect(self._on_hardware_accel_changed)
        render_layout.addWidget(self._hardware_accel_switch)
        
        render_tip = QLabel("使用GPU加速UI渲染，提升界面流畅度（推荐开启）")
        render_tip.setProperty("variant", "muted")
        render_tip.setWordWrap(True)
        render_layout.addWidget(render_tip, 1)
        
        layout.addWidget(render_frame)
        
        # 高级选项
        self._render_advanced_frame = QFrame()
        advanced_layout = QVBoxLayout(self._render_advanced_frame)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        
        # OpenGL选项
        opengl_frame = QFrame()
        opengl_layout = QHBoxLayout(opengl_frame)
        opengl_layout.setContentsMargins(0, 0, 0, 0)
        
        opengl_label = QLabel("OpenGL:")
        opengl_label.setProperty("variant", "secondary")
        opengl_label.setFixedWidth(100)
        opengl_layout.addWidget(opengl_label)
        
        self._opengl_combo = QComboBox()
        self._opengl_combo.addItems(["自动选择", "桌面OpenGL", "ANGLE (Direct3D)", "软件渲染"])
        self._opengl_combo.setFixedWidth(200)
        
        opengl_mode = self._config.get('rendering', {}).get('opengl', 'auto')
        self._opengl_combo.setCurrentIndex(self.OPENGL_MODES.index(opengl_mode) if opengl_mode in self.OPENGL_MODES else 0)
        
        opengl_layout.addWidget(self._opengl_combo)
        opengl_layout.addStretch()
        advanced_layout.addWidget(opengl_frame)
        
        # 垂直同步
        vsync_frame = QFrame()
        vsync_layout = QHBoxLayout(vsync_frame)
        vsync_layout.setContentsMargins(0, 0, 0, 0)
        
        vsync_label = QLabel("垂直同步:")
        vsync_label.setProperty("variant", "secondary")
        vsync_label.setFixedWidth(100)
        vsync_layout.addWidget(vsync_label)
        
        self._vsync_switch = AnimatedSwitch()
        self._vsync_switch.setChecked(self._config.get('rendering', {}).get('vsync', True))
        vsync_layout.addWidget(self._vsync_switch)
        
        vsync_tip = QLabel("防止画面撕裂，但可能增加输入延迟")
        vsync_tip.setProperty("variant", "muted")
        vsync_layout.addWidget(vsync_tip, 1)
        
        advanced_layout.addWidget(vsync_frame)
        layout.addWidget(self._render_advanced_frame)
        
        # 初始状态
        self._render_advanced_frame.setVisible(self._hardware_accel_switch.isChecked())
        
        # 保存按钮
        save_frame = QFrame()
        save_layout = QHBoxLayout(save_frame)
        save_layout.setContentsMargins(0, 0, 0, 0)
        save_layout.addStretch()
        
        self._save_btn = PrimaryButton("保存硬件加速设置")
        self._save_btn.clicked.connect(self._on_save_clicked)
        save_layout.addWidget(self._save_btn)
        layout.addWidget(save_frame)
    
    def _on_hardware_accel_changed(self, state: int) -> None:
        """硬件加速开关变更"""
        enabled = state == Qt.CheckState.Checked.value
        self._render_advanced_frame.setVisible(enabled)
    
    def _on_save_clicked(self) -> None:
        """保存设置"""
        settings = {
            'rendering': {
                'hardware_acceleration': self._hardware_accel_switch.isChecked(),
                'opengl': self.OPENGL_MODES[self._opengl_combo.currentIndex()],
                'vsync': self._vsync_switch.isChecked()
            },
            'inference': {
                'hardware_acceleration': self.HW_ACCEL_MODES[self._hw_accel_combo.currentIndex()]
            }
        }
        self.settings_changed.emit(settings)
        QMessageBox.information(self, "成功", "硬件加速设置已保存\n部分设置需要重启应用生效。")
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return {
            'rendering': {
                'hardware_acceleration': self._hardware_accel_switch.isChecked(),
                'opengl': self.OPENGL_MODES[self._opengl_combo.currentIndex()],
                'vsync': self._vsync_switch.isChecked()
            },
            'inference': {
                'hardware_acceleration': self.HW_ACCEL_MODES[self._hw_accel_combo.currentIndex()]
            }
        }


class CacheSettingsCard(CardWidget):
    """缓存设置卡片"""
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        self._config = config or {}
        super().__init__(title="💾 缓存设置", parent=parent)
        self._theme = ThemeManager.get_instance()
        self._setup_content()
    
    def _setup_content(self) -> None:
        """设置卡片内容"""
        layout = self.get_content_layout()
        cache_config = self._config.get('inference', {}).get('cache_settings', {})
        
        # 启用缓存开关
        enable_frame = QFrame()
        enable_layout = QHBoxLayout(enable_frame)
        enable_layout.setContentsMargins(0, 0, 0, 0)
        
        enable_label = QLabel("启用缓存:")
        enable_label.setProperty("variant", "secondary")
        enable_layout.addWidget(enable_label)
        
        self._cache_enabled_switch = AnimatedSwitch()
        self._cache_enabled_switch.setChecked(cache_config.get('enabled', True))
        enable_layout.addWidget(self._cache_enabled_switch)
        
        enable_tip = QLabel("启用推理结果缓存以提高重复查询的响应速度")
        enable_tip.setProperty("variant", "muted")
        enable_tip.setWordWrap(True)
        enable_layout.addWidget(enable_tip, 1)
        
        layout.addWidget(enable_frame)
        
        # 缓存大小设置
        size_frame = QFrame()
        size_layout = QHBoxLayout(size_frame)
        size_layout.setContentsMargins(0, 0, 0, 0)
        
        size_label = QLabel("最大缓存大小:")
        size_label.setProperty("variant", "secondary")
        size_label.setFixedWidth(120)
        size_layout.addWidget(size_label)
        
        self._cache_size_spin = QSpinBox()
        self._cache_size_spin.setRange(100, 10240)
        self._cache_size_spin.setValue(cache_config.get('max_size_mb', 2048))
        self._cache_size_spin.setSuffix(" MB")
        self._cache_size_spin.setFixedWidth(150)
        # QSpinBox 在 PyQt6 中没有 setValidator 方法，使用 setRange 替代
        # self._cache_size_spin.setValidator(CacheSizeValidator(self))
        size_layout.addWidget(self._cache_size_spin)
        
        size_tip = QLabel("缓存占用的最大磁盘空间（100MB - 10240MB）")
        size_tip.setProperty("variant", "muted")
        size_tip.setWordWrap(True)
        size_layout.addWidget(size_tip, 1)
        
        layout.addWidget(size_frame)
        
        # 缓存过期时间设置
        ttl_frame = QFrame()
        ttl_layout = QHBoxLayout(ttl_frame)
        ttl_layout.setContentsMargins(0, 0, 0, 0)
        
        ttl_label = QLabel("缓存过期时间:")
        ttl_label.setProperty("variant", "secondary")
        ttl_label.setFixedWidth(120)
        ttl_layout.addWidget(ttl_label)
        
        self._cache_ttl_spin = QSpinBox()
        self._cache_ttl_spin.setRange(1, 168)
        self._cache_ttl_spin.setValue(cache_config.get('ttl_hours', 24))
        self._cache_ttl_spin.setSuffix(" 小时")
        self._cache_ttl_spin.setFixedWidth(150)
        # QSpinBox 在 PyQt6 中没有 setValidator 方法，使用 setRange 替代
        # self._cache_ttl_spin.setValidator(CacheTTLValidator(self))
        ttl_layout.addWidget(self._cache_ttl_spin)
        
        ttl_tip = QLabel("缓存数据的有效期（1小时 - 168小时/7天）")
        ttl_tip.setProperty("variant", "muted")
        ttl_tip.setWordWrap(True)
        ttl_layout.addWidget(ttl_tip, 1)
        
        layout.addWidget(ttl_frame)
        
        # 保存按钮
        save_frame = QFrame()
        save_layout = QHBoxLayout(save_frame)
        save_layout.setContentsMargins(0, 0, 0, 0)
        save_layout.addStretch()
        
        self._save_btn = PrimaryButton("保存缓存设置")
        self._save_btn.clicked.connect(self._on_save_clicked)
        save_layout.addWidget(self._save_btn)
        layout.addWidget(save_frame)
    
    def _on_save_clicked(self) -> None:
        """保存设置"""
        settings = {
            'inference': {
                'cache_settings': {
                    'enabled': self._cache_enabled_switch.isChecked(),
                    'max_size_mb': self._cache_size_spin.value(),
                    'ttl_hours': self._cache_ttl_spin.value()
                }
            }
        }
        self.settings_changed.emit(settings)
        QMessageBox.information(self, "成功", "缓存设置已保存")
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return {
            'inference': {
                'cache_settings': {
                    'enabled': self._cache_enabled_switch.isChecked(),
                    'max_size_mb': self._cache_size_spin.value(),
                    'ttl_hours': self._cache_ttl_spin.value()
                }
            }
        }


class TouchSettingsCard(CardWidget):
    """触控设置卡片"""
    
    settings_changed = pyqtSignal(dict)
    touch_method_changed = pyqtSignal(str)
    
    TOUCH_METHODS = ["maatouch", "pc_foreground"]
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        self._config = config or {}
        super().__init__(title="🖱️ 触控设置", parent=parent)
        self._theme = ThemeManager.get_instance()
        self._setup_content()
    
    def _setup_content(self) -> None:
        """设置卡片内容"""
        layout = self.get_content_layout()
        
        # 触控方式选择
        method_frame = QFrame()
        method_layout = QHBoxLayout(method_frame)
        method_layout.setContentsMargins(0, 0, 0, 0)
        
        method_label = QLabel("触控方式:")
        method_label.setProperty("variant", "secondary")
        method_label.setFixedWidth(100)
        method_layout.addWidget(method_label)
        
        self._touch_method_combo = QComboBox()
        self._touch_method_combo.addItems(["maatouch (Android)", "pc_foreground (PC前台)"])
        self._touch_method_combo.setFixedWidth(200)
        
        touch_method = self._config.get('touch', {}).get('touch_method', 'maatouch')
        self._touch_method_combo.setCurrentIndex(1 if touch_method == 'pc_foreground' else 0)
        self._touch_method_combo.currentIndexChanged.connect(self._on_touch_method_changed)
        
        method_layout.addWidget(self._touch_method_combo)
        
        method_tip = QLabel("maatouch: 通过ADB控制Android设备 | pc_foreground: 直接控制PC窗口")
        method_tip.setProperty("variant", "muted")
        method_tip.setWordWrap(True)
        method_layout.addWidget(method_tip, 1)
        
        layout.addWidget(method_frame)
        
        # 失败时停止执行（隐藏，强制启用）
        self._fail_on_error_checkbox = QCheckBox("失败时停止执行")
        self._fail_on_error_checkbox.setChecked(
            self._config.get('touch', {}).get('fail_on_error', True)
        )
        self._fail_on_error_checkbox.setVisible(False)
        layout.addWidget(self._fail_on_error_checkbox)
        
        # 按钮区域
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        
        self._reset_btn = SecondaryButton("重置")
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        btn_layout.addWidget(self._reset_btn)
        
        self._save_btn = PrimaryButton("保存触控设置")
        self._save_btn.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(self._save_btn)
        
        layout.addWidget(btn_frame)
    
    def _on_touch_method_changed(self, index: int) -> None:
        """触控方式变更"""
        touch_method = self.TOUCH_METHODS[index]
        self.touch_method_changed.emit(touch_method)
    
    def _on_reset_clicked(self) -> None:
        """重置设置"""
        self._touch_method_combo.setCurrentIndex(0)
        self._fail_on_error_checkbox.setChecked(True)
    
    def _on_save_clicked(self) -> None:
        """保存设置"""
        touch_method = self.TOUCH_METHODS[self._touch_method_combo.currentIndex()]
        
        settings = {
            'touch': {
                'touch_method': touch_method,
                'fail_on_error': self._fail_on_error_checkbox.isChecked()
            }
        }
        self.settings_changed.emit(settings)
        QMessageBox.information(self, "成功", "触控设置已保存")
    
    def get_touch_method(self) -> str:
        """获取当前触控方式"""
        return self.TOUCH_METHODS[self._touch_method_combo.currentIndex()]
    
    def set_touch_method(self, method: str) -> None:
        """设置触控方式"""
        if method in self.TOUCH_METHODS:
            self._touch_method_combo.setCurrentIndex(self.TOUCH_METHODS.index(method))


class CloudModelSettingsCard(CardWidget):
    """云端模型设置卡片"""
    
    settings_changed = pyqtSignal(dict)
    model_changed = pyqtSignal(str)
    refresh_requested = pyqtSignal()
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        self._config = config or {}
        self._available_models: List[Dict[str, Any]] = []
        super().__init__(title="🤖 云端模型设置", parent=parent)
        self._theme = ThemeManager.get_instance()
        self._setup_content()
    
    def _setup_content(self) -> None:
        """设置卡片内容"""
        layout = self.get_content_layout()
        
        # 模型选择说明
        model_desc = QLabel("选择用于图像识别的AI模型。自动选择将使用服务器配置的默认模型。")
        model_desc.setProperty("variant", "muted")
        model_desc.setWordWrap(True)
        layout.addWidget(model_desc)
        
        # 自动选择开关
        auto_select_frame = QFrame()
        auto_select_layout = QHBoxLayout(auto_select_frame)
        auto_select_layout.setContentsMargins(0, 0, 0, 0)
        
        self._auto_select_checkbox = AnimatedSwitch("自动选择模型")
        self._auto_select_checkbox.setChecked(True)
        self._auto_select_checkbox.stateChanged.connect(self._on_auto_select_changed)
        auto_select_layout.addWidget(self._auto_select_checkbox)
        
        auto_select_tip = QLabel("(根据服务器配置自动选择)")
        auto_select_tip.setProperty("variant", "muted")
        auto_select_layout.addWidget(auto_select_tip)
        auto_select_layout.addStretch()
        layout.addWidget(auto_select_frame)
        
        # 模型选择下拉框
        model_select_frame = QFrame()
        model_select_layout = QHBoxLayout(model_select_frame)
        model_select_layout.setContentsMargins(0, 0, 0, 0)
        
        model_label = QLabel("选择模型:")
        model_label.setProperty("variant", "secondary")
        model_label.setFixedWidth(100)
        model_select_layout.addWidget(model_label)
        
        self._model_combo = QComboBox()
        self._model_combo.setFixedWidth(250)
        self._model_combo.setEnabled(False)
        self._model_combo.addItem("从服务器获取可用模型...")
        model_select_layout.addWidget(self._model_combo)
        
        self._refresh_btn = SecondaryButton("刷新")
        self._refresh_btn.setFixedWidth(80)
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)
        model_select_layout.addWidget(self._refresh_btn)
        
        model_select_layout.addStretch()
        layout.addWidget(model_select_frame)
        
        # 当前模型显示
        current_model_frame = QFrame()
        current_model_layout = QHBoxLayout(current_model_frame)
        current_model_layout.setContentsMargins(0, 0, 0, 0)
        
        current_model_label = QLabel("当前模型:")
        current_model_label.setProperty("variant", "secondary")
        current_model_label.setFixedWidth(100)
        current_model_layout.addWidget(current_model_label)
        
        self._current_model_display = QLabel("未选择")
        self._current_model_display.setProperty("variant", "primary")
        current_model_layout.addWidget(self._current_model_display)
        
        current_model_layout.addStretch()
        layout.addWidget(current_model_frame)
        
        # 保存按钮
        save_frame = QFrame()
        save_layout = QHBoxLayout(save_frame)
        save_layout.setContentsMargins(0, 0, 0, 0)
        save_layout.addStretch()
        
        self._save_btn = PrimaryButton("保存模型设置")
        self._save_btn.clicked.connect(self._on_save_clicked)
        save_layout.addWidget(self._save_btn)
        layout.addWidget(save_frame)
    
    def _on_auto_select_changed(self, state: int) -> None:
        """自动选择开关变更"""
        auto_select = state == Qt.CheckState.Checked.value
        self._model_combo.setEnabled(not auto_select)
        if auto_select:
            self._current_model_display.setText("自动选择")
        else:
            current_text = self._model_combo.currentText()
            if current_text and current_text != "从服务器获取可用模型...":
                self._current_model_display.setText(current_text)
            else:
                self._current_model_display.setText("未选择")
    
    def _on_refresh_clicked(self) -> None:
        """刷新模型列表"""
        self._refresh_btn.setEnabled(False)
        self._refresh_btn.setText("刷新中...")
        self.refresh_requested.emit()
    
    def _on_save_clicked(self) -> None:
        """保存设置"""
        auto_select = self._auto_select_checkbox.isChecked()
        selected_model = ""
        
        if not auto_select:
            selected_model = self._model_combo.currentData() or self._model_combo.currentText()
            if not selected_model or selected_model == "从服务器获取可用模型...":
                QMessageBox.warning(self, "警告", "请选择一个模型或启用自动选择")
                return
        
        settings = {
            'model': {
                'selected_model': selected_model if not auto_select else "",
                'auto_select': auto_select
            }
        }
        
        self.settings_changed.emit(settings)
        self.model_changed.emit(selected_model)
        QMessageBox.information(self, "成功", "模型设置已保存")
    
    def update_available_models(self, models: List[Dict[str, Any]], default_model: str = "") -> None:
        """更新可用模型列表"""
        self._available_models = models
        self._model_combo.clear()
        
        if not models:
            self._model_combo.addItem("无可用模型")
            self._model_combo.setEnabled(False)
        else:
            for model in models:
                model_name = model.get('name', 'Unknown')
                tier = model.get('tier', 'base')
                display_text = f"{model_name} ({tier})"
                self._model_combo.addItem(display_text, model_name)
            
            if default_model:
                for i in range(self._model_combo.count()):
                    if self._model_combo.itemData(i) == default_model:
                        self._model_combo.setCurrentIndex(i)
                        if self._auto_select_checkbox.isChecked():
                            self._current_model_display.setText(f"自动选择 ({default_model})")
                        break
            
            self._model_combo.setEnabled(not self._auto_select_checkbox.isChecked())
        
        self._refresh_btn.setEnabled(True)
        self._refresh_btn.setText("刷新")
    
    def set_auto_select(self, auto_select: bool) -> None:
        """设置自动选择状态"""
        self._auto_select_checkbox.setChecked(auto_select)
        self._model_combo.setEnabled(not auto_select)
    
    def is_auto_select(self) -> bool:
        """是否启用自动选择"""
        return self._auto_select_checkbox.isChecked()
    
    def get_selected_model(self) -> str:
        """获取当前选择的模型"""
        if self._auto_select_checkbox.isChecked():
            return ""
        return self._model_combo.currentData() or self._model_combo.currentText()


class LogSettingsCard(CardWidget):
    """日志设置卡片"""
    
    settings_changed = pyqtSignal(dict)
    
    LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        self._config = config or {}
        super().__init__(title="📝 日志设置", parent=parent)
        self._theme = ThemeManager.get_instance()
        self._setup_content()
    
    def _setup_content(self) -> None:
        """设置卡片内容"""
        layout = self.get_content_layout()
        
        # 日志级别选择
        level_frame = QFrame()
        level_layout = QHBoxLayout(level_frame)
        level_layout.setContentsMargins(0, 0, 0, 0)
        
        level_label = QLabel("日志级别:")
        level_label.setProperty("variant", "secondary")
        level_label.setFixedWidth(100)
        level_layout.addWidget(level_label)
        
        self._log_level_combo = QComboBox()
        self._log_level_combo.addItems(self.LOG_LEVELS)
        
        log_level = self._config.get('logging', {}).get('level', 'INFO')
        self._log_level_combo.setCurrentText(log_level)
        self._log_level_combo.currentIndexChanged.connect(self._on_log_level_changed)
        
        level_layout.addWidget(self._log_level_combo)
        
        level_tip = QLabel("设置日志记录的详细程度")
        level_tip.setProperty("variant", "muted")
        level_layout.addWidget(level_tip, 1)
        
        layout.addWidget(level_frame)
        
        # 日志文件路径显示
        path_frame = QFrame()
        path_layout = QHBoxLayout(path_frame)
        path_layout.setContentsMargins(0, 0, 0, 0)
        
        path_label = QLabel("日志路径:")
        path_label.setProperty("variant", "secondary")
        path_label.setFixedWidth(100)
        path_layout.addWidget(path_label)
        
        self._log_path_display = QLabel("logs/")
        self._log_path_display.setProperty("variant", "muted")
        path_layout.addWidget(self._log_path_display)
        
        path_layout.addStretch()
        layout.addWidget(path_frame)
    
    def _on_log_level_changed(self, index: int) -> None:
        """日志级别变更"""
        log_level = self.LOG_LEVELS[index]
        settings = {
            'logging': {
                'level': log_level
            }
        }
        self.settings_changed.emit(settings)
    
    def get_log_level(self) -> str:
        """获取当前日志级别"""
        return self._log_level_combo.currentText()
    
    def set_log_level(self, level: str) -> None:
        """设置日志级别"""
        if level in self.LOG_LEVELS:
            self._log_level_combo.setCurrentText(level)


class VersionSettingsCard(CardWidget):
    """版本信息卡片"""
    
    check_update_requested = pyqtSignal()
    update_requested = pyqtSignal()
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        self._config = config or {}
        self._current_version = "未知"
        self._latest_version = "未知"
        self._has_update = False
        
        super().__init__(title="📦 版本信息", parent=parent)
        self._theme = ThemeManager.get_instance()
        self._setup_content()
    
    def _setup_content(self) -> None:
        """设置卡片内容"""
        layout = self.get_content_layout()
        
        # 当前版本
        current_frame = QFrame()
        current_layout = QHBoxLayout(current_frame)
        current_layout.setContentsMargins(0, 0, 0, 0)
        
        current_label = QLabel("当前版本:")
        current_label.setProperty("variant", "secondary")
        current_label.setFixedWidth(100)
        current_layout.addWidget(current_label)
        
        self._current_version_display = QLabel("加载中...")
        self._current_version_display.setProperty("variant", "primary")
        current_layout.addWidget(self._current_version_display)
        
        current_layout.addStretch()
        layout.addWidget(current_frame)
        
        # 最新版本
        latest_frame = QFrame()
        latest_layout = QHBoxLayout(latest_frame)
        latest_layout.setContentsMargins(0, 0, 0, 0)
        
        latest_label = QLabel("最新版本:")
        latest_label.setProperty("variant", "secondary")
        latest_label.setFixedWidth(100)
        latest_layout.addWidget(latest_label)
        
        self._latest_version_display = QLabel("检查中...")
        self._latest_version_display.setProperty("variant", "muted")
        latest_layout.addWidget(self._latest_version_display)
        
        latest_layout.addStretch()
        layout.addWidget(latest_frame)
        
        # 更新状态
        self._update_status_display = QLabel("")
        self._update_status_display.setProperty("variant", "muted")
        layout.addWidget(self._update_status_display)
        
        # 更新进度条
        self._update_progress = QProgressBar()
        self._update_progress.setRange(0, 100)
        self._update_progress.setValue(0)
        self._update_progress.setTextVisible(True)
        self._update_progress.setVisible(False)
        layout.addWidget(self._update_progress)
        
        # 版本操作按钮
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        
        self._check_update_btn = SecondaryButton("检查更新")
        self._check_update_btn.clicked.connect(self._on_check_update_clicked)
        btn_layout.addWidget(self._check_update_btn)
        
        self._update_btn = PrimaryButton("更新到最新版本")
        self._update_btn.setEnabled(False)
        self._update_btn.clicked.connect(self._on_update_clicked)
        btn_layout.addWidget(self._update_btn)
        
        layout.addWidget(btn_frame)
    
    def _on_check_update_clicked(self) -> None:
        """检查更新按钮点击"""
        self._update_status_display.setText("正在检查更新...")
        self._update_status_display.setStyleSheet(f"color: {self._theme.get_color('primary')};")
        self.check_update_requested.emit()
    
    def _on_update_clicked(self) -> None:
        """更新按钮点击"""
        reply = QMessageBox.question(
            self,
            "确认更新",
            "确定要更新到最新版本吗？这将覆盖本地文件！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._update_btn.setEnabled(False)
            self._check_update_btn.setEnabled(False)
            self._update_progress.setVisible(True)
            self._update_progress.setValue(0)
            self._update_status_display.setText("正在更新...")
            self.update_requested.emit()
    
    def set_current_version(self, version: str) -> None:
        """设置当前版本"""
        self._current_version = version
        self._current_version_display.setText(version)
    
    def set_latest_version(self, version: str, has_update: bool = False) -> None:
        """设置最新版本"""
        self._latest_version = version
        self._latest_version_display.setText(version)
        self._has_update = has_update
        
        if has_update:
            self._update_status_display.setText("发现新版本！")
            self._update_status_display.setStyleSheet(f"color: {self._theme.get_color('success')};")
            self._update_btn.setEnabled(True)
        else:
            self._update_status_display.setText("已是最新版本")
            self._update_status_display.setStyleSheet(f"color: {self._theme.get_color('text_muted')};")
            self._update_btn.setEnabled(False)
    
    def set_update_error(self, error_msg: str) -> None:
        """设置更新错误状态"""
        self._update_status_display.setText(f"检查失败: {error_msg}")
        self._update_status_display.setStyleSheet(f"color: {self._theme.get_color('danger')};")
        self._update_btn.setEnabled(False)
    
    def set_update_progress(self, progress: int) -> None:
        """设置更新进度"""
        self._update_progress.setValue(progress)
    
    def set_update_complete(self, success: bool) -> None:
        """设置更新完成状态"""
        self._update_progress.setVisible(False)
        self._check_update_btn.setEnabled(True)
        
        if success:
            self._update_status_display.setText("更新完成！")
            self._update_status_display.setStyleSheet(f"color: {self._theme.get_color('success')};")
            QMessageBox.information(self, "成功", "更新完成！")
        else:
            self._update_status_display.setText("更新失败")
            self._update_status_display.setStyleSheet(f"color: {self._theme.get_color('danger')};")
            QMessageBox.critical(self, "失败", "更新失败，请重试")
