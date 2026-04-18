"""
设置页面
处理配置选项、版本信息和更新功能
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QGroupBox,
    QTreeWidget,
    QTreeWidgetItem,
    QFrame,
    QSplitter,
    QSizePolicy,
    QMessageBox,
    QProgressBar,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

# 支持两种导入方式
try:
    from ..theme.theme_manager import ThemeManager
    from ..widgets.base_widgets import PrimaryButton, SecondaryButton, DangerButton, CardWidget
except ImportError:
    from theme.theme_manager import ThemeManager
    from widgets.base_widgets import PrimaryButton, SecondaryButton, DangerButton, CardWidget


class SettingsPage(QWidget):
    """
    设置页面
    
    功能：
    - 配置选项列表（使用QTreeWidget）
    - 配置编辑区域
    - 保存/重置按钮
    - 触控设置
    - 版本信息和更新功能
    - 日志级别设置
    
    信号：
    - settings_changed(dict): 设置变更信号
    - check_update_requested(): 检查更新请求信号
    - update_requested(): 更新请求信号
    """
    
    # 自定义信号
    settings_changed = pyqtSignal(dict)            # 设置变更信号
    check_update_requested = pyqtSignal()          # 检查更新请求信号
    update_requested = pyqtSignal()                # 更新请求信号
    touch_method_changed = pyqtSignal(str)         # 触控方式变更信号
    
    # 日志级别常量
    LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    # 触控方式常量
    TOUCH_METHODS = ["maatouch", "pc_foreground"]
    
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
        self._theme = ThemeManager.get_instance()
        self._config = config or {}
        self._current_version: str = "未知"
        self._latest_version: str = "未知"
        self._has_update: bool = False
        
        self._setup_ui()
        self._setup_style()
        self._setup_connections()
        
        # 加载当前配置到UI
        self._load_config_to_ui()
    
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
        
        # === 触控设置区域 ===
        touch_card = CardWidget()
        touch_layout = QVBoxLayout(touch_card)
        touch_layout.setContentsMargins(
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md')
        )
        touch_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 触控设置标题
        touch_title = QLabel("触控设置")
        touch_title.setProperty("variant", "header")
        touch_layout.addWidget(touch_title)
        
        # 触控方式选择
        method_frame = QFrame()
        method_layout = QHBoxLayout(method_frame)
        method_layout.setContentsMargins(0, 0, 0, 0)
        method_layout.setSpacing(self._theme.get_spacing('sm'))
        
        method_label = QLabel("触控方式:")
        method_label.setProperty("variant", "secondary")
        method_label.setFixedWidth(100)
        method_layout.addWidget(method_label)
        
        self._touch_method_combo = QComboBox()
        self._touch_method_combo.addItems(["maatouch (Android)", "pc_foreground (PC前台)"])
        self._touch_method_combo.setFixedWidth(200)
        method_layout.addWidget(self._touch_method_combo)
        
        # 触控方式说明
        method_tip = QLabel("maatouch: 通过ADB控制Android设备 | pc_foreground: 直接控制PC窗口")
        method_tip.setProperty("variant", "muted")
        method_tip.setWordWrap(True)
        method_layout.addWidget(method_tip)
        
        method_layout.addStretch()
        touch_layout.addWidget(method_frame)
        
        # 失败时停止执行（隐藏，强制启用）
        self._fail_on_error_checkbox = QCheckBox("失败时停止执行")
        self._fail_on_error_checkbox.setChecked(True)
        self._fail_on_error_checkbox.setVisible(False)  # 隐藏，但保持逻辑
        touch_layout.addWidget(self._fail_on_error_checkbox)
        
        # 保存按钮
        save_frame = QFrame()
        save_layout = QHBoxLayout(save_frame)
        save_layout.setContentsMargins(0, 0, 0, 0)
        save_layout.setSpacing(self._theme.get_spacing('md'))
        
        self._save_touch_btn = PrimaryButton("保存设置")
        save_layout.addWidget(self._save_touch_btn)
        
        self._reset_touch_btn = SecondaryButton("重置")
        save_layout.addWidget(self._reset_touch_btn)
        
        save_layout.addStretch()
        touch_layout.addWidget(save_frame)
        
        main_layout.addWidget(touch_card)
        
        # === 日志设置区域 ===
        log_card = CardWidget()
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md')
        )
        log_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 日志设置标题
        log_title = QLabel("日志设置")
        log_title.setProperty("variant", "header")
        log_layout.addWidget(log_title)
        
        # 日志级别选择
        level_frame = QFrame()
        level_layout = QHBoxLayout(level_frame)
        level_layout.setContentsMargins(0, 0, 0, 0)
        level_layout.setSpacing(self._theme.get_spacing('sm'))
        
        level_label = QLabel("日志级别:")
        level_label.setProperty("variant", "secondary")
        level_label.setFixedWidth(100)
        level_layout.addWidget(level_label)
        
        self._log_level_combo = QComboBox()
        self._log_level_combo.addItems(self.LOG_LEVELS)
        self._log_level_combo.setCurrentText("INFO")
        self._log_level_combo.setFixedWidth(150)
        level_layout.addWidget(self._log_level_combo)
        
        level_layout.addStretch()
        log_layout.addWidget(level_frame)
        
        # 日志文件路径显示
        path_frame = QFrame()
        path_layout = QHBoxLayout(path_frame)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(self._theme.get_spacing('sm'))
        
        path_label = QLabel("日志路径:")
        path_label.setProperty("variant", "secondary")
        path_label.setFixedWidth(100)
        path_layout.addWidget(path_label)
        
        self._log_path_display = QLabel("logs/")
        self._log_path_display.setProperty("variant", "muted")
        path_layout.addWidget(self._log_path_display)
        
        path_layout.addStretch()
        log_layout.addWidget(path_frame)
        
        main_layout.addWidget(log_card)
        
        # === 版本信息区域 ===
        version_card = CardWidget()
        version_layout = QVBoxLayout(version_card)
        version_layout.setContentsMargins(
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md')
        )
        version_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 版本信息标题
        version_title = QLabel("版本信息")
        version_title.setProperty("variant", "header")
        version_layout.addWidget(version_title)
        
        # 当前版本
        current_frame = QFrame()
        current_layout = QHBoxLayout(current_frame)
        current_layout.setContentsMargins(0, 0, 0, 0)
        current_layout.setSpacing(self._theme.get_spacing('sm'))
        
        current_label = QLabel("当前版本:")
        current_label.setProperty("variant", "secondary")
        current_label.setFixedWidth(100)
        current_layout.addWidget(current_label)
        
        self._current_version_display = QLabel("加载中...")
        self._current_version_display.setProperty("variant", "primary")
        current_layout.addWidget(self._current_version_display)
        
        current_layout.addStretch()
        version_layout.addWidget(current_frame)
        
        # 最新版本
        latest_frame = QFrame()
        latest_layout = QHBoxLayout(latest_frame)
        latest_layout.setContentsMargins(0, 0, 0, 0)
        latest_layout.setSpacing(self._theme.get_spacing('sm'))
        
        latest_label = QLabel("最新版本:")
        latest_label.setProperty("variant", "secondary")
        latest_label.setFixedWidth(100)
        latest_layout.addWidget(latest_label)
        
        self._latest_version_display = QLabel("检查中...")
        self._latest_version_display.setProperty("variant", "muted")
        latest_layout.addWidget(self._latest_version_display)
        
        latest_layout.addStretch()
        version_layout.addWidget(latest_frame)
        
        # 更新状态
        self._update_status_display = QLabel("")
        self._update_status_display.setProperty("variant", "muted")
        version_layout.addWidget(self._update_status_display)
        
        # 更新进度条
        self._update_progress = QProgressBar()
        self._update_progress.setMinimum(0)
        self._update_progress.setMaximum(100)
        self._update_progress.setValue(0)
        self._update_progress.setTextVisible(True)
        self._update_progress.setVisible(False)
        version_layout.addWidget(self._update_progress)
        
        # 版本操作按钮
        version_btn_frame = QFrame()
        version_btn_layout = QHBoxLayout(version_btn_frame)
        version_btn_layout.setContentsMargins(0, 0, 0, 0)
        version_btn_layout.setSpacing(self._theme.get_spacing('md'))
        
        self._check_update_btn = SecondaryButton("检查更新")
        version_btn_layout.addWidget(self._check_update_btn)
        
        self._update_btn = PrimaryButton("更新到最新版本")
        self._update_btn.setEnabled(False)
        version_btn_layout.addWidget(self._update_btn)
        
        version_btn_layout.addStretch()
        version_layout.addWidget(version_btn_frame)
        
        main_layout.addWidget(version_card)
        
        main_layout.addStretch()
    
    def _setup_style(self) -> None:
        """设置样式"""
        # 页面样式通过QApplication全局应用，这里只设置特定控件样式
        
        # 设置ComboBox样式
        combo_style = """
            QComboBox {
                border: 1px solid #48484a;
                border-radius: 4px;
                background-color: #2c2c2e;
                color: #ffffff;
                padding: 8px;
            }
            QComboBox:focus {
                border-color: #4361ee;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #48484a;
                background-color: #2c2c2e;
                color: #ffffff;
                selection-background-color: #4361ee;
            }
        """
        
        self._touch_method_combo.setStyleSheet(combo_style)
        self._log_level_combo.setStyleSheet(combo_style)
        
        # 设置CheckBox样式
        checkbox_style = """
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
        """
        
        self._fail_on_error_checkbox.setStyleSheet(checkbox_style)
        
        # 设置进度条样式
        self._update_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #48484a;
                border-radius: 4px;
                background-color: #2c2c2e;
                height: 20px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4361ee;
                border-radius: 3px;
            }
        """)
    
    def _setup_connections(self) -> None:
        """设置信号连接"""
        # 触控设置按钮
        self._save_touch_btn.clicked.connect(self._on_save_touch_clicked)
        self._reset_touch_btn.clicked.connect(self._on_reset_touch_clicked)
        self._touch_method_combo.currentIndexChanged.connect(self._on_touch_method_changed)
        
        # 日志级别变更
        self._log_level_combo.currentIndexChanged.connect(self._on_log_level_changed)
        
        # 版本操作按钮
        self._check_update_btn.clicked.connect(self._on_check_update_clicked)
        self._update_btn.clicked.connect(self._on_update_clicked)
    
    def _load_config_to_ui(self) -> None:
        """加载当前配置到UI"""
        # 触控方式
        touch_method = self._config.get('touch', {}).get('touch_method', 'maatouch')
        if touch_method == 'pc_foreground':
            self._touch_method_combo.setCurrentIndex(1)
        else:
            self._touch_method_combo.setCurrentIndex(0)
        
        # 日志级别
        log_level = self._config.get('logging', {}).get('level', 'INFO')
        self._log_level_combo.setCurrentText(log_level)
    
    # === 信号处理方法 ===
    
    def _on_save_touch_clicked(self) -> None:
        """保存触控设置按钮点击"""
        touch_method = self.TOUCH_METHODS[self._touch_method_combo.currentIndex()]
        
        settings = {
            'touch': {
                'touch_method': touch_method,
                'fail_on_error': self._fail_on_error_checkbox.isChecked()
            }
        }
        
        self.settings_changed.emit(settings)
        QMessageBox.information(self, "成功", "触控设置已保存")
    
    def _on_reset_touch_clicked(self) -> None:
        """重置触控设置按钮点击"""
        self._touch_method_combo.setCurrentIndex(0)  # 默认maatouch
        self._fail_on_error_checkbox.setChecked(True)
    
    def _on_touch_method_changed(self, index: int) -> None:
        """触控方式变更"""
        touch_method = self.TOUCH_METHODS[index]
        self.touch_method_changed.emit(touch_method)
    
    def _on_log_level_changed(self, index: int) -> None:
        """日志级别变更"""
        log_level = self.LOG_LEVELS[index]
        settings = {
            'logging': {
                'level': log_level
            }
        }
        self.settings_changed.emit(settings)
    
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
    
    # === 公共方法 ===
    
    def set_current_version(self, version: str) -> None:
        """
        设置当前版本
        
        Args:
            version: 当前版本字符串
        """
        self._current_version = version
        self._current_version_display.setText(version)
    
    def set_latest_version(self, version: str, has_update: bool = False) -> None:
        """
        设置最新版本
        
        Args:
            version: 最新版本字符串
            has_update: 是否有更新可用
        """
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
        """
        设置更新错误状态
        
        Args:
            error_msg: 错误信息
        """
        self._update_status_display.setText(f"检查失败: {error_msg}")
        self._update_status_display.setStyleSheet(f"color: {self._theme.get_color('danger')};")
        self._update_btn.setEnabled(False)
    
    def set_update_progress(self, progress: int) -> None:
        """
        设置更新进度
        
        Args:
            progress: 进度值 (0-100)
        """
        self._update_progress.setValue(progress)
    
    def set_update_complete(self, success: bool) -> None:
        """
        设置更新完成状态
        
        Args:
            success: 是否成功
        """
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
    
    def get_touch_method(self) -> str:
        """获取当前触控方式"""
        return self.TOUCH_METHODS[self._touch_method_combo.currentIndex()]
    
    def set_touch_method(self, method: str) -> None:
        """
        设置触控方式
        
        Args:
            method: 触控方式字符串
        """
        if method in self.TOUCH_METHODS:
            self._touch_method_combo.setCurrentIndex(self.TOUCH_METHODS.index(method))
    
    def get_log_level(self) -> str:
        """获取当前日志级别"""
        return self._log_level_combo.currentText()
    
    def set_log_level(self, level: str) -> None:
        """
        设置日志级别
        
        Args:
            level: 日志级别字符串
        """
        if level in self.LOG_LEVELS:
            self._log_level_combo.setCurrentText(level)
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return {
            'touch': {
                'touch_method': self.get_touch_method(),
                'fail_on_error': self._fail_on_error_checkbox.isChecked()
            },
            'logging': {
                'level': self.get_log_level()
            }
        }
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """
        更新配置
        
        Args:
            config: 新配置字典
        """
        self._config = config
        self._load_config_to_ui()