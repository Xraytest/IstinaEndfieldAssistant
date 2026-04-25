"""
本地推理首次询问对话框

在客户端注册完成后显示，检测显卡配置并询问是否使用本地推理
"""
import os
import sys
from typing import Optional, Callable, Dict, Any, List
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QGroupBox, QRadioButton, QButtonGroup,
    QMessageBox, QSpacerItem, QSizePolicy, QWidget, QScrollArea,
    QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QColor

# 导入本地推理模块
try:
    from .....安卓相关.core.local_inference.gpu_checker import GPUChecker
    from .....安卓相关.core.local_inference.model_manager import ModelManager, ModelInfo
except ImportError:
    # 相对导入失败时使用绝对路径
    import sys
    current_file = os.path.abspath(__file__)
    dialogs_dir = os.path.dirname(current_file)
    pyqt_ui_dir = os.path.dirname(dialogs_dir)
    gui_dir = os.path.dirname(pyqt_ui_dir)
    entry_dir = os.path.dirname(gui_dir)
    istina_dir = os.path.dirname(entry_dir)
    project_root = os.path.dirname(istina_dir)
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if istina_dir not in sys.path:
        sys.path.insert(0, istina_dir)
    
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.gpu_checker import GPUChecker
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.model_manager import ModelManager, ModelInfo


class GPUCheckWorker(QThread):
    """GPU检测工作线程"""
    
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._checker = GPUChecker()
    
    def run(self):
        """执行GPU检测"""
        try:
            result = self._checker.check_gpu_availability()
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))


class ModelDownloadWorker(QThread):
    """模型下载工作线程"""
    
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, model_name: str, parent=None):
        super().__init__(parent)
        self._model_name = model_name
        self._manager = ModelManager()
        self._cancelled = False
    
    def run(self):
        """执行模型下载"""
        try:
            def progress_callback(percentage: int, message: str):
                if not self._cancelled:
                    self.progress_signal.emit(percentage, message)
            
            result = self._manager.download_model(self._model_name, progress_callback)
            
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


class LocalInferenceDialog(QDialog):
    """
    本地推理首次询问对话框
    
    功能:
    1. 检测显卡配置
    2. 显示GPU信息
    3. 推荐合适的模型
    4. 询问是否使用本地推理
    5. 支持模型下载
    """
    
    # 用户选择结果
    CHOICE_LOCAL = "local"
    CHOICE_CLOUD = "cloud"
    CHOICE_CANCEL = "cancel"
    
    def __init__(
        self,
        parent=None,
        auto_check: bool = True,
        show_only_once: bool = True
    ):
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
        
        self._setup_ui()
        self._setup_styles()
        
        if auto_check:
            self._start_gpu_check()
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("本地推理配置")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("🚀 本地推理功能")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 说明文本
        desc_label = QLabel(
            "检测到您的电脑可能支持本地AI推理。\n"
            "本地推理可以在不依赖网络的情况下运行，响应更快，"
            "但需要一定的显卡配置。"
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label)
        
        # GPU检测区域
        self._gpu_group = QGroupBox("显卡检测")
        gpu_layout = QVBoxLayout(self._gpu_group)
        
        self._gpu_status_label = QLabel("正在检测显卡配置...")
        self._gpu_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gpu_layout.addWidget(self._gpu_status_label)
        
        self._gpu_progress = QProgressBar()
        self._gpu_progress.setRange(0, 0)  # 不确定进度
        gpu_layout.addWidget(self._gpu_progress)
        
        self._gpu_details = QTextEdit()
        self._gpu_details.setReadOnly(True)
        self._gpu_details.setMaximumHeight(150)
        self._gpu_details.setVisible(False)
        gpu_layout.addWidget(self._gpu_details)
        
        layout.addWidget(self._gpu_group)
        
        # 模型选择区域
        self._model_group = QGroupBox("模型选择")
        self._model_group.setVisible(False)
        model_layout = QVBoxLayout(self._model_group)
        
        self._model_info_label = QLabel("请选择要使用的模型:")
        model_layout.addWidget(self._model_info_label)
        
        self._model_buttons = QButtonGroup(self)
        self._model_buttons.setExclusive(True)
        
        self._model_container = QWidget()
        self._model_layout = QVBoxLayout(self._model_container)
        self._model_layout.setSpacing(5)
        model_layout.addWidget(self._model_container)
        
        layout.addWidget(self._model_group)
        
        # 下载进度区域
        self._download_group = QGroupBox("模型下载")
        self._download_group.setVisible(False)
        download_layout = QVBoxLayout(self._download_group)
        
        self._download_status = QLabel("准备下载...")
        download_layout.addWidget(self._download_status)
        
        self._download_progress = QProgressBar()
        self._download_progress.setRange(0, 100)
        download_layout.addWidget(self._download_progress)
        
        layout.addWidget(self._download_group)
        
        # 选择按钮区域
        self._choice_group = QGroupBox("推理模式选择")
        self._choice_group.setVisible(False)
        choice_layout = QVBoxLayout(self._choice_group)
        
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
        local_desc.setIndent(20)
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
        cloud_desc.setIndent(20)
        choice_layout.addWidget(cloud_desc)
        
        layout.addWidget(self._choice_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self._refresh_button = QPushButton("重新检测")
        self._refresh_button.clicked.connect(self._start_gpu_check)
        self._refresh_button.setVisible(False)
        button_layout.addWidget(self._refresh_button)
        
        button_layout.addStretch()
        
        self._cancel_button = QPushButton("取消")
        self._cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self._cancel_button)
        
        self._confirm_button = QPushButton("确认")
        self._confirm_button.setDefault(True)
        self._confirm_button.clicked.connect(self._on_confirm)
        self._confirm_button.setEnabled(False)
        button_layout.addWidget(self._confirm_button)
        
        layout.addLayout(button_layout)
    
    def _setup_styles(self):
        """设置样式"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            #titleLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333;
                padding: 10px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                padding: 8px 20px;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QPushButton#cancelButton {
                background-color: #f44336;
            }
            QPushButton#cancelButton:hover {
                background-color: #da190b;
            }
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 3px;
                background-color: #fafafa;
                font-family: Consolas, Monaco, monospace;
                font-size: 12px;
            }
        """)
        
        self._cancel_button.setObjectName("cancelButton")
    
    def _start_gpu_check(self):
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
    
    def _on_gpu_check_finished(self, result: Dict[str, Any]):
        """GPU检测完成"""
        self._gpu_info = result
        self._check_worker = None
        
        self._gpu_progress.setRange(0, 100)
        
        if result.get("available"):
            self._gpu_status_label.setText("✅ 检测到NVIDIA显卡")
            self._show_gpu_details(result)
            
            if result.get("meets_requirements"):
                self._show_model_selection(result)
                self._choice_group.setVisible(True)
                self._confirm_button.setEnabled(True)
            else:
                self._show_insufficient_gpu(result)
        else:
            self._gpu_status_label.setText("❌ 未检测到NVIDIA显卡")
            self._show_no_gpu_message(result)
        
        self._refresh_button.setVisible(True)
    
    def _on_gpu_check_error(self, error: str):
        """GPU检测错误"""
        self._check_worker = None
        self._gpu_progress.setRange(0, 100)
        self._gpu_status_label.setText(f"❌ 检测失败: {error}")
        self._gpu_details.setText(f"错误详情:\n{error}")
        self._gpu_details.setVisible(True)
        self._refresh_button.setVisible(True)
    
    def _show_gpu_details(self, result: Dict[str, Any]):
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
    
    def _show_model_selection(self, result: Dict[str, Any]):
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
            
            # 检查是否已下载
            if model.is_downloaded:
                radio.setText(radio.text() + " [已下载]")
                radio.setStyleSheet("color: green;")
            
            # 设置推荐模型为默认选中
            if model.name == recommended:
                radio.setChecked(True)
                radio.setText(radio.text() + " [推荐]")
            
            self._model_buttons.addButton(radio)
            self._model_layout.addWidget(radio)
        
        self._model_group.setVisible(True)
    
    def _show_insufficient_gpu(self, result: Dict[str, Any]):
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
    
    def _show_no_gpu_message(self, result: Dict[str, Any]):
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
    
    def _on_confirm(self):
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
    
    def _on_cancel(self):
        """取消按钮点击"""
        self._user_choice = self.CHOICE_CANCEL
        self.reject()
    
    def _start_model_download(self, model_name: str):
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
    
    def _on_download_progress(self, percentage: int, message: str):
        """下载进度更新"""
        self._download_progress.setValue(percentage)
        self._download_status.setText(message)
    
    def _on_download_finished(self, success: bool, message: str):
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
    
    def closeEvent(self, event):
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
    parent=None,
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
