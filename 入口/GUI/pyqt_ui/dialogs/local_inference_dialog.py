"""
本地推理首次询问对话框

在客户端注册完成后显示，检测显卡配置并询问是否使用本地推理
遵循 Material Design 3 设计规范

重构说明:
- 使用从settings.workers导入的GPUCheckWorker和ModelDownloadWorker
- 消除与settings_page.py的代码重复
"""
import os
import sys
from typing import Optional, Dict, Any, List
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QTextEdit, QGroupBox, QRadioButton, QButtonGroup,
    QMessageBox, QSpacerItem, QSizePolicy, QWidget, QScrollArea,
    QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QColor

# 导入主题管理器和基础控件
from ..theme.theme_manager import ThemeManager
from ..theme.animation_manager import AnimationManager, AnimatedProgressBar, fade_in_widget
from ..widgets.base_widgets import PrimaryButton, DangerButton, SecondaryButton

# 导入本地推理模块
try:
    from .....安卓相关.core.local_inference.gpu_checker import GPUChecker
    from .....安卓相关.core.local_inference.model_manager import ModelManager, ModelInfo
    from ..pages.settings.workers import GPUCheckWorker, ModelDownloadWorker
except ImportError:
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.gpu_checker import GPUChecker
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.model_manager import ModelManager, ModelInfo
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.pages.settings.workers import GPUCheckWorker, ModelDownloadWorker


class LocalInferenceDialog(QDialog):
    """
    本地推理首次询问对话框
    
    功能:
    1. 检测显卡配置
    2. 显示GPU信息
    3. 推荐合适的模型
    4. 询问是否使用本地推理
    5. 支持模型下载
    
    Material Design 3 风格设计
    """
    
    # 用户选择结果
    CHOICE_LOCAL = "local"
    CHOICE_CLOUD = "cloud"
    CHOICE_CANCEL = "cancel"
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        auto_check: bool = True,
        show_only_once: bool = True
    ) -> None:
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            auto_check: 是否自动检测GPU
            show_only_once: 是否只显示一次（通过配置控制）
        """
        super().__init__(parent)
        
        self._gpu_info: Optional[Dict[str, Any]] = None
        self._selected_model: Optional[str] = None
        self._user_choice: str = self.CHOICE_CANCEL
        self._auto_check = auto_check
        self._show_only_once = show_only_once
        
        self._gpu_checker = GPUChecker()
        self._model_manager = ModelManager()
        self._check_worker: Optional[GPUCheckWorker] = None
        self._download_worker: Optional[ModelDownloadWorker] = None
        
        # 主题和动画管理器
        self._theme = ThemeManager.get_instance()
        self._anim_manager = AnimationManager.get_instance()
        
        self._setup_ui()
        self._apply_theme_styles()
        
        # 淡入动画
        self._setup_animation()
        
        if auto_check:
            self._start_gpu_check()
    
    def _setup_ui(self) -> None:
        """设置UI"""
        self.setWindowTitle("本地推理配置")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(self._theme.get_spacing('lg'))
        layout.setContentsMargins(
            self._theme.get_spacing('xl'),
            self._theme.get_spacing('xl'),
            self._theme.get_spacing('xl'),
            self._theme.get_spacing('xl')
        )
        
        # 标题
        title_label = QLabel("🚀 本地推理功能")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont(self._theme.get_font_family())
        title_font.setPixelSize(self._theme.font_sizes['headline_small'])
        title_font.setWeight(self._theme.font_weights['bold'])
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 说明文本
        desc_label = QLabel(
            "检测到您的电脑可能支持本地AI推理。\n"
            "本地推理可以在不依赖网络的情况下运行，响应更快，"
            "但需要一定的显卡配置。"
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_font = QFont(self._theme.get_font_family())
        desc_font.setPixelSize(self._theme.font_sizes['body_large'])
        desc_label.setFont(desc_font)
        layout.addWidget(desc_label)
        
        # GPU检测区域
        self._gpu_group = self._create_group_box("显卡检测")
        gpu_layout = QVBoxLayout(self._gpu_group)
        
        self._gpu_status_label = QLabel("正在检测显卡配置...")
        self._gpu_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gpu_layout.addWidget(self._gpu_status_label)
        
        self._gpu_progress = QProgressBar()
        self._gpu_progress.setRange(0, 0)  # 不确定进度
        self._gpu_progress.setFixedHeight(8)
        gpu_layout.addWidget(self._gpu_progress)
        
        self._gpu_details = QTextEdit()
        self._gpu_details.setReadOnly(True)
        self._gpu_details.setMaximumHeight(150)
        self._gpu_details.setVisible(False)
        gpu_layout.addWidget(self._gpu_details)
        
        layout.addWidget(self._gpu_group)
        
        # 模型选择区域
        self._model_group = self._create_group_box("模型选择")
        self._model_group.setVisible(False)
        model_layout = QVBoxLayout(self._model_group)
        
        self._model_info_label = QLabel("请选择要使用的模型:")
        model_layout.addWidget(self._model_info_label)
        
        self._model_buttons = QButtonGroup(self)
        self._model_buttons.setExclusive(True)
        
        self._model_container = QWidget()
        self._model_layout = QVBoxLayout(self._model_container)
        self._model_layout.setSpacing(self._theme.get_spacing('sm'))
        model_layout.addWidget(self._model_container)
        
        layout.addWidget(self._model_group)
        
        # 下载进度区域
        self._download_group = self._create_group_box("模型下载")
        self._download_group.setVisible(False)
        download_layout = QVBoxLayout(self._download_group)
        
        self._download_status = QLabel("准备下载...")
        download_layout.addWidget(self._download_status)
        
        self._download_progress = QProgressBar()
        self._download_progress.setRange(0, 100)
        self._download_progress.setFixedHeight(8)
        download_layout.addWidget(self._download_progress)
        
        # 包装进度条以支持动画
        self._animated_progress = AnimatedProgressBar(self._download_progress)
        
        layout.addWidget(self._download_group)
        
        # 选择按钮区域
        self._choice_group = self._create_group_box("推理模式选择")
        self._choice_group.setVisible(False)
        choice_layout = QVBoxLayout(self._choice_group)
        choice_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 本地推理选项
        self._local_radio = QRadioButton("使用本地推理（推荐）")
        self._local_radio.setChecked(True)
        choice_layout.addWidget(self._local_radio)
        
        local_desc = QLabel(
            "✓ 无需网络连接\n"
            "✓ 响应速度更快\n"
            "✓ 数据隐私更好\n"
            "⚠ 需要下载模型文件（约1-70GB）"
        )
        local_desc.setIndent(self._theme.get_spacing('lg'))
        local_desc_font = QFont(self._theme.get_font_family())
        local_desc_font.setPixelSize(self._theme.font_sizes['body_medium'])
        local_desc.setFont(local_desc_font)
        choice_layout.addWidget(local_desc)
        
        # 云端推理选项
        self._cloud_radio = QRadioButton("使用云端推理")
        choice_layout.addWidget(self._cloud_radio)
        
        cloud_desc = QLabel(
            "✓ 无需下载模型\n"
            "✓ 自动使用最新模型\n"
            "⚠ 需要网络连接\n"
            "⚠ 受服务器配额限制"
        )
        cloud_desc.setIndent(self._theme.get_spacing('lg'))
        cloud_desc_font = QFont(self._theme.get_font_family())
        cloud_desc_font.setPixelSize(self._theme.font_sizes['body_medium'])
        cloud_desc.setFont(cloud_desc_font)
        choice_layout.addWidget(cloud_desc)
        
        layout.addWidget(self._choice_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(self._theme.get_spacing('md'))
        
        self._refresh_button = SecondaryButton("重新检测")
        self._refresh_button.clicked.connect(self._start_gpu_check)
        self._refresh_button.setVisible(False)
        button_layout.addWidget(self._refresh_button)
        
        button_layout.addStretch()
        
        self._cancel_button = DangerButton("取消")
        self._cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self._cancel_button)
        
        self._confirm_button = PrimaryButton("确认")
        self._confirm_button.setDefault(True)
        self._confirm_button.clicked.connect(self._on_confirm)
        self._confirm_button.setEnabled(False)
        button_layout.addWidget(self._confirm_button)
        
        layout.addLayout(button_layout)
    
    def _create_group_box(self, title: str) -> QGroupBox:
        """
        创建Material Design 3风格的分组框
        
        Args:
            title: 分组框标题
            
        Returns:
            QGroupBox: 配置好的分组框
        """
        group = QGroupBox(title)
        group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {self._theme.get_color('surface_container')};
                color: {self._theme.get_color('text_primary')};
                border: 1px solid {self._theme.get_color('outline_variant')};
                border-radius: {self._theme.get_corner_radius('card')}px;
                margin-top: {self._theme.get_spacing('md')}px;
                padding-top: {self._theme.get_spacing('md')}px;
                font-weight: {self._theme.font_weights['semi_bold']};
                font-size: {self._theme.font_sizes['title_medium']}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {self._theme.get_spacing('md')}px;
                padding: 0 {self._theme.get_spacing('sm')}px;
                color: {self._theme.get_color('primary')};
            }}
        """)
        return group
    
    def _apply_theme_styles(self) -> None:
        """应用主题样式"""
        # 设置对话框背景
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self._theme.get_color('surface')};
            }}
            QLabel {{
                color: {self._theme.get_color('text_primary')};
                background-color: transparent;
            }}
            #titleLabel {{
                color: {self._theme.get_color('primary')};
                padding: {self._theme.get_spacing('md')}px;
            }}
            QRadioButton {{
                color: {self._theme.get_color('text_primary')};
                font-size: {self._theme.font_sizes['body_large']}px;
                spacing: {self._theme.get_spacing('sm')}px;
            }}
            QRadioButton::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 10px;
                border: 2px solid {self._theme.get_color('outline')};
                background-color: transparent;
            }}
            QRadioButton::indicator:checked {{
                background-color: {self._theme.get_color('primary')};
                border-color: {self._theme.get_color('primary')};
            }}
            QProgressBar {{
                background-color: {self._theme.get_color('surface_container_high')};
                border: none;
                border-radius: 4px;
                height: 8px;
                text-align: center;
                color: {self._theme.get_color('text_primary')};
            }}
            QProgressBar::chunk {{
                background-color: {self._theme.get_color('primary')};
                border-radius: 4px;
            }}
            QTextEdit {{
                background-color: {self._theme.get_color('surface_container')};
                color: {self._theme.get_color('text_primary')};
                border: 1px solid {self._theme.get_color('outline_variant')};
                border-radius: {self._theme.get_corner_radius('sm')}px;
                padding: {self._theme.get_spacing('sm')}px;
                font-family: {self._theme.get_mono_font_family()};
                font-size: {self._theme.font_sizes['body_small']}px;
            }}
        """)
    
    def _setup_animation(self) -> None:
        """设置入场动画"""
        if self._anim_manager.is_enabled():
            # 初始透明度为0
            self.setWindowOpacity(0.0)
            # 使用QTimer延迟启动淡入动画，确保窗口已显示
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(50, self._play_fade_in)
    
    def _play_fade_in(self) -> None:
        """播放淡入动画"""
        fade_in_widget(self, duration=self._anim_manager.get_animation_duration('dialog'))
    
    def _start_gpu_check(self) -> None:
        """开始GPU检测"""
        self._gpu_status_label.setText("正在检测显卡配置...")
        self._gpu_progress.setRange(0, 0)
        self._gpu_details.setVisible(False)
        self._model_group.setVisible(False)
        self._choice_group.setVisible(False)
        self._confirm_button.setEnabled(False)
        self._refresh_button.setVisible(False)
        
        self._check_worker = GPUCheckWorker(self)
        self._check_worker.finished_signal.connect(self._on_gpu_check_finished)
        self._check_worker.error_signal.connect(self._on_gpu_check_error)
        self._check_worker.start()
    
    def _on_gpu_check_finished(self, result: Dict[str, Any]) -> None:
        """GPU检测完成"""
        self._gpu_info = result
        self._check_worker = None
        
        self._gpu_progress.setRange(0, 100)
        self._gpu_progress.setValue(100)
        
        if result.get("available"):
            self._gpu_status_label.setText("✅ 检测到NVIDIA显卡")
            self._show_gpu_details(result)
            
            if result.get("meets_requirements"):
                self._show_model_selection(result)
                self._choice_group.setVisible(True)
                # 淡入动画
                if self._anim_manager.is_enabled():
                    fade_in_widget(self._choice_group, self._anim_manager.get_animation_duration('fast'))
                self._confirm_button.setEnabled(True)
            else:
                self._show_insufficient_gpu(result)
        else:
            self._gpu_status_label.setText("❌ 未检测到NVIDIA显卡")
            self._show_no_gpu_message(result)
        
        self._refresh_button.setVisible(True)
    
    def _on_gpu_check_error(self, error: str) -> None:
        """GPU检测错误"""
        self._check_worker = None
        self._gpu_progress.setRange(0, 100)
        self._gpu_progress.setValue(0)
        self._gpu_status_label.setText(f"❌ 检测失败: {error}")
        self._gpu_details.setText(f"错误详情:\n{error}")
        self._gpu_details.setVisible(True)
        self._refresh_button.setVisible(True)
    
    def _show_gpu_details(self, result: Dict[str, Any]) -> None:
        """显示GPU详情"""
        details = []
        details.append("=" * 50)
        details.append("显卡信息")
        details.append("=" * 50)
        
        for i, gpu in enumerate(result.get("gpus", [])):
            details.append(f"\nGPU {i + 1}:")
            details.append(f"  名称: {gpu.get('name', 'Unknown')}")
            details.append(f"  总显存: {gpu.get('total_memory_gb', 0):.2f} GB")
            details.append(f"  可用显存: {gpu.get('free_memory_gb', 0):.2f} GB")
            details.append(f"  计算能力: {gpu.get('compute_capability', 'Unknown')}")
            if gpu.get('driver_version'):
                details.append(f"  驱动版本: {gpu['driver_version']}")
            if gpu.get('cuda_version'):
                details.append(f"  CUDA版本: {gpu['cuda_version']}")
        
        details.append("\n" + "=" * 50)
        details.append(f"CUDA可用: {'是' if result.get('cuda_available') else '否'}")
        details.append(f"满足要求: {'是' if result.get('meets_requirements') else '否'}")
        
        recommended = result.get('recommended_model')
        if recommended:
            details.append(f"推荐模型: {recommended}")
        
        details.append("=" * 50)
        
        self._gpu_details.setText("\n".join(details))
        self._gpu_details.setVisible(True)
    
    def _show_model_selection(self, result: Dict[str, Any]) -> None:
        """显示模型选择"""
        # 清除旧的选择
        for button in self._model_buttons.buttons():
            self._model_buttons.removeButton(button)
            button.deleteLater()
        
        # 获取推荐模型
        recommended = result.get("recommended_model", "qwen3.5-9b-fp16")
        
        # 添加模型选项
        models = self._model_manager.get_all_models()
        
        for model in models:
            radio = QRadioButton(f"{model.name} - {model.description}")
            radio.setToolTip(
                f"大小: {model.size_gb} GB\n"
                f"量化: {model.quantization}\n"
                f"推荐显存: {model.recommended_gpu_memory_gb} GB"
            )
            radio.setStyleSheet(f"""
                QRadioButton {{
                    color: {self._theme.get_color('text_primary')};
                    font-size: {self._theme.font_sizes['body_medium']}px;
                }}
                QRadioButton::indicator {{
                    border-color: {self._theme.get_color('outline')};
                }}
                QRadioButton::indicator:checked {{
                    background-color: {self._theme.get_color('primary')};
                    border-color: {self._theme.get_color('primary')};
                }}
            """)
            
            # 检查是否已下载
            if model.is_downloaded:
                radio.setText(radio.text() + " [已下载]")
                radio.setStyleSheet(f"""
                    QRadioButton {{
                        color: {self._theme.get_color('success')};
                        font-size: {self._theme.font_sizes['body_medium']}px;
                    }}
                """)
            
            # 设置推荐模型为默认选中
            if model.name == recommended:
                radio.setChecked(True)
                radio.setText(radio.text() + " [推荐]")
            
            self._model_buttons.addButton(radio)
            self._model_layout.addWidget(radio)
        
        self._model_group.setVisible(True)
        # 淡入动画
        if self._anim_manager.is_enabled():
            fade_in_widget(self._model_group, self._anim_manager.get_animation_duration('fast'))
    
    def _show_insufficient_gpu(self, result: Dict[str, Any]) -> None:
        """显示GPU不满足要求的消息"""
        max_memory = max(
            gpu.get("total_memory_gb", 0) 
            for gpu in result.get("gpus", [])
        ) if result.get("gpus") else 0
        
        message = (
            f"⚠️ 显卡配置不足\n\n"
            f"检测到显存: {max_memory:.2f} GB\n"
            f"最低要求: {self._gpu_checker.MIN_MEMORY_GB} GB\n\n"
            f"您仍然可以使用云端推理模式。"
        )
        
        self._gpu_details.setText(message)
        self._gpu_details.setVisible(True)
        
        # 自动选择云端模式
        self._cloud_radio.setChecked(True)
        self._local_radio.setEnabled(False)
        self._choice_group.setVisible(True)
        self._confirm_button.setEnabled(True)
    
    def _show_no_gpu_message(self, result: Dict[str, Any]) -> None:
        """显示无GPU的消息"""
        error = result.get("error", "未知错误")
        
        message = (
            f"❌ 未检测到NVIDIA显卡\n\n"
            f"原因: {error}\n\n"
            f"本地推理需要NVIDIA显卡和CUDA环境。\n"
            f"您可以使用云端推理模式。"
        )
        
        self._gpu_details.setText(message)
        self._gpu_details.setVisible(True)
        
        # 自动选择云端模式
        self._cloud_radio.setChecked(True)
        self._local_radio.setEnabled(False)
        self._choice_group.setVisible(True)
        self._confirm_button.setEnabled(True)
    
    def _on_confirm(self) -> None:
        """确认按钮点击"""
        if self._local_radio.isChecked():
            # 检查是否需要下载模型
            selected_button = self._model_buttons.checkedButton()
            if selected_button:
                model_name = selected_button.text().split(" - ")[0]
                self._selected_model = model_name
                
                # 检查模型是否已下载
                if not self._model_manager.is_model_downloaded(model_name):
                    self._start_model_download(model_name)
                    return
            
            self._user_choice = self.CHOICE_LOCAL
        else:
            self._user_choice = self.CHOICE_CLOUD
        
        self.accept()
    
    def _on_cancel(self) -> None:
        """取消按钮点击"""
        self._user_choice = self.CHOICE_CANCEL
        self.reject()
    
    def _start_model_download(self, model_name: str) -> None:
        """开始模型下载"""
        self._download_group.setVisible(True)
        self._download_status.setText(f"正在下载模型: {model_name}")
        self._download_progress.setValue(0)
        
        self._confirm_button.setEnabled(False)
        self._cancel_button.setEnabled(False)
        
        self._download_worker = ModelDownloadWorker(model_name, self)
        self._download_worker.progress_signal.connect(self._on_download_progress)
        self._download_worker.finished_signal.connect(self._on_download_finished)
        self._download_worker.start()
    
    def _on_download_progress(self, percentage: int, message: str) -> None:
        """下载进度更新"""
        # 使用动画进度条
        if self._anim_manager.is_enabled():
            self._animated_progress.set_value_animated(percentage)
        else:
            self._download_progress.setValue(percentage)
        self._download_status.setText(message)
    
    def _on_download_finished(self, success: bool, message: str) -> None:
        """下载完成"""
        self._download_worker = None
        
        if success:
            self._download_status.setText("✅ " + message)
            self._user_choice = self.CHOICE_LOCAL
            self.accept()
        else:
            self._download_status.setText("❌ " + message)
            self._confirm_button.setEnabled(True)
            self._cancel_button.setEnabled(True)
            
            # 询问是否切换到云端模式
            reply = QMessageBox.question(
                self,
                "下载失败",
                f"模型下载失败: {message}\n\n是否切换到云端推理模式？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._cloud_radio.setChecked(True)
                self._user_choice = self.CHOICE_CLOUD
                self.accept()
    
    def get_user_choice(self) -> str:
        """获取用户选择"""
        return self._user_choice
    
    def get_selected_model(self) -> Optional[str]:
        """获取选中的模型"""
        return self._selected_model
    
    def get_gpu_info(self) -> Optional[Dict[str, Any]]:
        """获取GPU信息"""
        return self._gpu_info
    
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


def show_local_inference_dialog(
    parent: Optional[QWidget] = None,
    config: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    显示本地推理对话框
    
    Args:
        parent: 父窗口
        config: 配置字典，用于检查是否已显示过
        
    Returns:
        (user_choice, gpu_info, selected_model)
        user_choice: "local", "cloud", 或 "cancel"
    """
    # 检查是否已显示过
    if config:
        first_run = config.get("first_run", {})
        if first_run.get("local_inference_prompt_shown", False):
            return None, None, None
    
    dialog = LocalInferenceDialog(parent=parent)
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted:
        return (
            dialog.get_user_choice(),
            dialog.get_gpu_info(),
            dialog.get_selected_model()
        )
    else:
        return "cancel", dialog.get_gpu_info(), None


if __name__ == "__main__":
    # 测试对话框
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 应用主题
    theme_manager = ThemeManager.get_instance()
    theme_manager.apply_theme(app)
    
    choice, gpu_info, model = show_local_inference_dialog()
    
    print("\n" + "=" * 60)
    print("对话框测试结果")
    print("=" * 60)
    print(f"用户选择: {choice}")
    print(f"选中模型: {model}")
    if gpu_info:
        print(f"GPU可用: {gpu_info.get('available')}")
        print(f"满足要求: {gpu_info.get('meets_requirements')}")
    print("=" * 60)
    
    sys.exit(0)
