"""Settings page - Endfield terminal style with local inference controls"""
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QPushButton, QGroupBox, QFormLayout
from PyQt6.QtCore import pyqtSignal, Qt
import sys
import os

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    src_dir = os.path.join(project_root, "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

try:
    from core.local_inference.gpu_checker import GPUChecker
except ImportError:
    GPUChecker = None


class SettingsPage(QWidget):
    settings_changed = pyqtSignal(dict)
    local_inference_toggled = pyqtSignal(bool)
    check_update_requested = pyqtSignal()
    refresh_gpu_status = pyqtSignal()

    def __init__(self, config: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self._config = config or {}
        self._gpu_checker = None
        self._gpu_info = None
        self._setup_ui()
        self._start_gpu_check()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 终端标题
        title = QLabel("// SYSTEM SETTINGS")
        title.setStyleSheet("""
            QLabel {
                color: #18d1ff;
                font-size: 14px;
                font-family: Consolas;
                font-weight: bold;
                letter-spacing: 1px;
                padding: 4px 0;
            }
        """)
        layout.addWidget(title)

        # ======== 本地推理面板 ========
        inference_group = QWidget()
        inference_group.setStyleSheet("""
            QWidget {
                background-color: rgba(16, 16, 26, 0.85);
                border: 1px solid rgba(24, 209, 255, 0.10);
                border-radius: 4px;
            }
        """)
        inference_layout = QVBoxLayout(inference_group)
        inference_layout.setContentsMargins(20, 16, 20, 16)
        inference_layout.setSpacing(12)

        infer_title = QLabel("LOCAL INFERENCE")
        infer_title.setStyleSheet("color: #e8e8ee; font-size: 14px; font-family: Consolas; font-weight: bold; letter-spacing: 1px;")
        inference_layout.addWidget(infer_title)

        # Enable checkbox
        self._enable_checkbox = QCheckBox("ENABLE LOCAL INFERENCE (NVIDIA GPU REQUIRED)")
        self._enable_checkbox.setStyleSheet("""
            QCheckBox {
                color: #e8e8ee;
                font-size: 12px;
                font-family: Consolas;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 2px;
                border: 1px solid rgba(24, 209, 255, 0.30);
                background-color: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #18d1ff;
                border-color: #18d1ff;
            }
            QCheckBox::indicator:hover {
                border-color: #18d1ff;
            }
        """)
        self._enable_checkbox.setToolTip("启用后将使用本地模型进行推理，否则使用云端服务")
        self._enable_checkbox.toggled.connect(self._on_local_inference_toggled)
        inference_layout.addWidget(self._enable_checkbox)

        # 标准推理设置 (large VLM)
        self._large_vlm_container = QWidget()
        self._large_vlm_container.setVisible(False)
        lvlm_layout = QVBoxLayout(self._large_vlm_container)
        lvlm_layout.setContentsMargins(0, 0, 0, 0)
        lvlm_layout.setSpacing(6)

        lvlm_sep = QLabel("─── Large VLM Settings ───")
        lvlm_sep.setStyleSheet("color: rgba(144, 144, 168, 0.30); font-size: 10px; font-family: Consolas;")
        lvlm_layout.addWidget(lvlm_sep)

        info_style = "color: #9090a8; font-size: 12px; font-family: Consolas; padding: 3px 0;"
        val_style = "color: #e8e8ee; font-size: 12px; font-family: Consolas; padding: 3px 0;"

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("GPU STATUS:"))
        row1.itemAt(0).widget().setStyleSheet(info_style)
        self._gpu_status_label = QLabel("SCANNING...")
        self._gpu_status_label.setStyleSheet(val_style)
        row1.addWidget(self._gpu_status_label)
        row1.addStretch()
        lvlm_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("VRAM:"))
        row2.itemAt(0).widget().setStyleSheet(info_style)
        self._vram_label = QLabel("UNKNOWN")
        self._vram_label.setStyleSheet(val_style)
        row2.addWidget(self._vram_label)
        row2.addStretch()
        lvlm_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("SYSTEM RAM:"))
        row3.itemAt(0).widget().setStyleSheet(info_style)
        self._ram_label = QLabel("UNKNOWN")
        self._ram_label.setStyleSheet(val_style)
        row3.addWidget(self._ram_label)
        row3.addStretch()
        lvlm_layout.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel("REQUIREMENTS:"))
        row4.itemAt(0).widget().setStyleSheet(info_style)
        self._requirements_label = QLabel("SCANNING...")
        self._requirements_label.setStyleSheet("color: #18d1ff; font-size: 12px; font-family: Consolas; padding: 3px 0;")
        row4.addWidget(self._requirements_label)
        row4.addStretch()
        lvlm_layout.addLayout(row4)

        row5 = QHBoxLayout()
        row5.addWidget(QLabel("RECOMMENDED:"))
        row5.itemAt(0).widget().setStyleSheet(info_style)
        self._model_label = QLabel("UNKNOWN")
        self._model_label.setStyleSheet(val_style)
        row5.addWidget(self._model_label)
        row5.addStretch()
        lvlm_layout.addLayout(row5)

        sep = QLabel("────────────────────────────────")
        sep.setStyleSheet("color: rgba(24, 209, 255, 0.08); font-size: 10px;")
        lvlm_layout.addWidget(sep)

        button_layout = QHBoxLayout()
        self._check_gpu_btn = QPushButton("RE-SCAN GPU")
        self._check_gpu_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #18d1ff;
                border: 1px solid rgba(24, 209, 255, 0.30);
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11px;
                font-family: Consolas;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: rgba(24, 209, 255, 0.10);
            }
        """)
        self._check_gpu_btn.clicked.connect(self._start_gpu_check)
        self._check_update_btn = QPushButton("CHECK UPDATE")
        self._check_update_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #9090a8;
                border: 1px solid rgba(144, 144, 168, 0.20);
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11px;
                font-family: Consolas;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: rgba(144, 144, 168, 0.10);
            }
        """)
        self._check_update_btn.clicked.connect(self.check_update_requested.emit)
        button_layout.addWidget(self._check_gpu_btn)
        button_layout.addStretch()
        button_layout.addWidget(self._check_update_btn)
        lvlm_layout.addLayout(button_layout)

        inference_layout.addWidget(self._large_vlm_container)
        layout.addWidget(inference_group)
        layout.addStretch()

        self._load_config()

    def _load_config(self):
        local_config = self._config.get("inference", {}).get("local", {})
        enabled = local_config.get("enabled", False)
        self._enable_checkbox.setEnabled(True)
        self._enable_checkbox.setChecked(enabled)
        self._large_vlm_container.setVisible(enabled)

    def _start_gpu_check(self):
        self._gpu_status_label.setText("SCANNING...")
        self._vram_label.setText("UNKNOWN")
        self._ram_label.setText("UNKNOWN")
        self._requirements_label.setText("SCANNING...")
        self._model_label.setText("UNKNOWN")
        self._enable_checkbox.setEnabled(False)
        self._check_gpu_btn.setEnabled(False)

        from PyQt6.QtCore import QThread, pyqtSignal

        class GpuCheckWorker(QThread):
            result = pyqtSignal(dict)
            error = pyqtSignal(str)

            def run(self):
                try:
                    if GPUChecker is None:
                        result = {
                            "available": False,
                            "error": "GPUChecker module not available"
                        }
                    else:
                        checker = GPUChecker()
                        result = checker.check_gpu_availability()
                    self.result.emit(result)
                except Exception as e:
                    self.error.emit(str(e))

        self._gpu_worker = GpuCheckWorker()
        self._gpu_worker.result.connect(self._update_gpu_status_ui)
        self._gpu_worker.error.connect(self._update_gpu_error_ui)
        self._gpu_worker.start()

    def _update_gpu_status_ui(self, gpu_info: dict):
        self._gpu_info = gpu_info
        red_style = "color: #ff3355; font-size: 12px; font-family: Consolas; padding: 3px 0;"
        green_style = "color: #00ffa2; font-size: 12px; font-family: Consolas; padding: 3px 0;"

        if not self._gpu_info:
            self._gpu_status_label.setStyleSheet(red_style)
            self._vram_label.setStyleSheet(red_style)
            self._ram_label.setStyleSheet(red_style)
            self._requirements_label.setStyleSheet(red_style)
            self._model_label.setStyleSheet(red_style)
            self._gpu_status_label.setText("ERROR")
            self._vram_label.setText("N/A")
            self._ram_label.setText("N/A")
            self._requirements_label.setText("ERROR")
            self._model_label.setText("N/A")
            self._enable_checkbox.setEnabled(False)
            self._check_gpu_btn.setEnabled(True)
            return

        if not self._gpu_info.get("available", False):
            self._gpu_status_label.setText("NO NVIDIA GPU DETECTED")
            self._vram_label.setText("N/A")
            self._ram_label.setText("N/A")
            self._requirements_label.setText("NOT MET (NO GPU)")
            self._model_label.setText("N/A")
            self._gpu_status_label.setStyleSheet(red_style)
            self._vram_label.setStyleSheet(red_style)
            self._ram_label.setStyleSheet(red_style)
            self._requirements_label.setStyleSheet(red_style)
            self._model_label.setStyleSheet(red_style)
            self._enable_checkbox.setEnabled(False)
            self._check_gpu_btn.setEnabled(True)
            return

        gpus = self._gpu_info.get("gpus", [])
        if gpus:
            gpu = gpus[0]
            self._gpu_status_label.setText("GPU DETECTED")
            self._vram_label.setText(f"{gpu.get('total_memory_gb', 0):.1f} GB")
            self._ram_label.setText("PENDING")

            meets_req = self._gpu_info.get("meets_requirements", False)
            self._requirements_label.setText("MET" if meets_req else "NOT MET")
            recommended = self._gpu_info.get("recommended_model")
            self._model_label.setText(recommended or "UNKNOWN")
            
            color = green_style if meets_req else red_style
            self._gpu_status_label.setStyleSheet(color)
            self._vram_label.setStyleSheet(color)
            self._ram_label.setStyleSheet(color)
            self._requirements_label.setStyleSheet(color)
            self._model_label.setStyleSheet(color)
            
            self._enable_checkbox.setEnabled(True)
        else:
            self._gpu_status_label.setText("GPU SCAN ERROR")
            self._vram_label.setText("N/A")
            self._ram_label.setText("N/A")
            self._requirements_label.setText("NOT MET")
            self._model_label.setText("N/A")
            self._gpu_status_label.setStyleSheet(red_style)
            self._vram_label.setStyleSheet(red_style)
            self._ram_label.setStyleSheet(red_style)
            self._requirements_label.setStyleSheet(red_style)
            self._model_label.setStyleSheet(red_style)

        self._check_gpu_btn.setEnabled(True)

    def _update_gpu_error_ui(self, error_msg: str):
        red_style = "color: #ff3355; font-size: 12px; font-family: Consolas; padding: 3px 0;"
        self._gpu_status_label.setText("SCAN FAILED")
        self._vram_label.setText("N/A")
        self._ram_label.setText("N/A")
        self._requirements_label.setText("ERROR")
        self._model_label.setText("N/A")
        self._gpu_status_label.setStyleSheet(red_style)
        self._vram_label.setStyleSheet(red_style)
        self._ram_label.setStyleSheet(red_style)
        self._requirements_label.setStyleSheet(red_style)
        self._model_label.setStyleSheet(red_style)
        self._enable_checkbox.setEnabled(False)
        self._check_gpu_btn.setEnabled(True)

    def _on_local_inference_toggled(self, checked: bool):
        if not self._gpu_info:
            self._enable_checkbox.setEnabled(False)
            self._gpu_status_label.setText("SCAN GPU FIRST...")
            self._start_gpu_check()
            self._enable_checkbox.setChecked(not checked)
            return

        if not self._gpu_info.get("available", False):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "无法启用本地推理",
                "未检测到可用的 NVIDIA GPU。请确保已安装 NVIDIA 驱动程序和 CUDA。"
            )
            self._enable_checkbox.setChecked(False)
            return

        if not self._gpu_info.get("meets_requirements", False):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "硬件不满足要求",
                f"当前硬件不满足本地推理的最低要求。\n"
                f"要求: VRAM >= 6GB 或 VRAM + RAM >= 48GB\n"
                f"当前状态: {self._gpu_info.get('gpus', [{}])[0].get('total_memory_gb', 0):.1f} GB VRAM"
            )
            self._enable_checkbox.setChecked(False)
            return

        self.local_inference_toggled.emit(checked)
        
        if 'inference' not in self._config:
            self._config['inference'] = {}
        if 'local' not in self._config['inference']:
            self._config['inference']['local'] = {}
        self._config['inference']['local']['enabled'] = checked
        self.settings_changed.emit(self._config)

        self._enable_checkbox.setChecked(checked)
        self._large_vlm_container.setVisible(checked)

    def get_config(self) -> Dict[str, Any]:
        return self._config

    def set_config(self, config: Dict[str, Any]):
        self._config = config or {}
        self._load_config()
        self._start_gpu_check()