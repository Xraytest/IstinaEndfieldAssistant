"""
认证管理页面 - Endfield 终端风格
处理用户登录、注销和用户状态显示
"""

import os
import glob
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QFileDialog,
    QDialog,
    QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from module.utils.paths import get_project_root

try:
    from ..theme.theme_manager import ThemeManager
    from ..widgets.base_widgets import PrimaryButton, SecondaryButton, DangerButton, CardWidget
    from ..widgets.status_indicator import ConnectionStatusIndicator
except ImportError:
    import sys
    import os
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
    
    from gui.pyqt6.theme.theme_manager import ThemeManager
    from gui.pyqt6.widgets.base_widgets import PrimaryButton, SecondaryButton, DangerButton, CardWidget
    from gui.pyqt6.widgets.status_indicator import ConnectionStatusIndicator


class RegistrationDialog(QDialog):
    """注册对话框——提示用户输入用户名"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户注册")
        self.setFixedSize(360, 200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        prompt = QLabel("未检测到登录凭证，请输入用户名进行注册：")
        prompt.setStyleSheet("color: #e8e8ee; font-size: 13px; font-family: Consolas;")
        prompt.setWordWrap(True)
        layout.addWidget(prompt)

        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("输入用户名（至少2个字符）")
        self._username_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(10, 10, 15, 0.90);
                color: #e0e0e8;
                border: 1px solid rgba(24, 209, 255, 0.30);
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
                font-family: Consolas;
            }
            QLineEdit:focus {
                border-color: #18d1ff;
            }
        """)
        layout.addWidget(self._username_input)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self._confirm_btn = QPushButton("注册")
        self._confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(24, 209, 255, 0.15);
                color: #18d1ff;
                border: 1px solid rgba(24, 209, 255, 0.30);
                border-radius: 4px;
                padding: 8px 24px;
                font-size: 12px;
                font-family: Consolas;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(24, 209, 255, 0.25);
            }
        """)
        self._confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(self._confirm_btn)

        self._skip_btn = QPushButton("稍后注册")
        self._skip_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #606080;
                border: 1px solid rgba(144, 144, 168, 0.20);
                border-radius: 4px;
                padding: 8px 24px;
                font-size: 12px;
                font-family: Consolas;
            }
            QPushButton:hover {
                color: #9090a8;
                border-color: rgba(144, 144, 168, 0.40);
            }
        """)
        self._skip_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._skip_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setStyleSheet("background-color: #0c0c14;")

    def _on_confirm(self):
        username = self._username_input.text().strip()
        if not username:
            QMessageBox.warning(self, "警告", "请输入用户名")
            return
        if len(username) < 2:
            QMessageBox.warning(self, "警告", "用户名至少需要 2 个字符")
            return
        self.accept()

    def get_username(self) -> str:
        return self._username_input.text().strip()


class AuthPage(QWidget):
    """
    认证管理页面 - Endfield 终端风格

    功能：
    - ArkPass文件认证登录
    - 自动加载缓存的ArkPass文件
    - 登录/注销按钮
    - 用户状态显示

    信号：
    - arkpass_selected(str): ArkPass文件选择信号
    - logout_requested(): 注销请求信号
    """

    login_requested = pyqtSignal(str, str)
    logout_requested = pyqtSignal()
    register_requested = pyqtSignal(str)
    arkpass_selected = pyqtSignal(str)
    auto_login_requested = pyqtSignal()
    refresh_requested = pyqtSignal()

    STATUS_LOGGED_OUT = "logged_out"
    STATUS_LOGGED_IN = "logged_in"
    STATUS_LOGGING_IN = "logging_in"

    def __init__(
        self,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._login_status: str = self.STATUS_LOGGED_OUT
        self._user_id: Optional[str] = None
        self._user_info: Dict[str, Any] = {}
        self._arkpass_path: str = ""

        self._setup_ui()
        self._setup_style()
        self._setup_connections()

    def _get_cache_dir(self) -> str:
        istina_root = get_project_root()
        cache_dir = os.path.join(istina_root, "cache")
        return cache_dir

    def _get_cached_arkpass(self) -> Optional[str]:
        cache_dir = self._get_cache_dir()
        if not os.path.exists(cache_dir):
            return None
        arkpass_files = glob.glob(os.path.join(cache_dir, "*.arkpass"))
        if not arkpass_files:
            return None
        return max(arkpass_files, key=os.path.getmtime)

    def try_auto_login(self) -> bool:
        """Try auto login, show registration prompt if no cached credentials"""
        cached_arkpass = self._get_cached_arkpass()
        if cached_arkpass and os.path.exists(cached_arkpass):
            try:
                with open(cached_arkpass, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if not content:
                    import logging
                    logging.getLogger(__name__).warning(f"Cached ArkPass empty: {cached_arkpass}")
                    # 自动登录场景下不显示注册对话框，静默失败
                    return False
                self._arkpass_path_display.setText(cached_arkpass)
                self._arkpass_path_display.setProperty("variant", "primary")
                self._arkpass_path = cached_arkpass
                self.set_logging_in()
                self.arkpass_selected.emit(cached_arkpass)
                return True
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to read cached credentials: {e}", exc_info=True)
                self._arkpass_path_display.setText("Read failed")
                self._arkpass_path_display.setStyleSheet("color: #ff3355; font-size: 11px; font-family: Consolas; padding: 8px 0;")
                # 自动登录场景下不显示注册对话框，静默失败
                return False
        else:
            # 自动登录场景下无缓存凭证时静默失败，不显示对话框
            return False

    def _show_registration_prompt(self):
        """弹出注册对话框，提示用户输入用户名"""
        dialog = RegistrationDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            username = dialog.get_username()
            if username:
                self._username_input.setText(username)
                self._on_register_clicked()
                return
        QMessageBox.information(
            self,
            "提示",
            "请先注册或选择已有的 ArkPass 认证文件以继续使用。"
        )

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # 终端标题
        title = QLabel("// 认证终端")
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
        main_layout.addWidget(title)

        # 登录状态指示器
        status_frame = QWidget()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(12)

        self._status_indicator = ConnectionStatusIndicator(connection_type="server")
        status_layout.addWidget(self._status_indicator)
        status_layout.addStretch()

        main_layout.addWidget(status_frame)

        # ======== 登录终端面板 ========
        login_card = CardWidget()
        login_layout = login_card.get_content_layout()
        login_layout.setContentsMargins(20, 20, 20, 20)
        login_layout.setSpacing(16)

        login_title = QLabel("ARKPASS 认证")
        login_title.setStyleSheet("""
            QLabel {
                color: #e8e8ee;
                font-size: 16px;
                font-family: Consolas;
                font-weight: bold;
                letter-spacing: 1px;
            }
        """)
        login_layout.addWidget(login_title)

        # ArkPass 文件选择
        arkpass_frame = QWidget()
        arkpass_layout = QHBoxLayout(arkpass_frame)
        arkpass_layout.setContentsMargins(0, 0, 0, 0)
        arkpass_layout.setSpacing(12)

        arkpass_label = QLabel("ARKPASS:")
        arkpass_label.setStyleSheet("color: #18d1ff; font-size: 12px; font-family: Consolas; font-weight: bold;")
        arkpass_label.setFixedWidth(80)
        arkpass_layout.addWidget(arkpass_label)

        self._arkpass_path_display = QLabel("NULL")
        self._arkpass_path_display.setStyleSheet("color: #606080; font-size: 12px; font-family: Consolas; padding: 8px 0;")
        arkpass_layout.addWidget(self._arkpass_path_display, 1)

        self._select_arkpass_btn = SecondaryButton("浏览")
        self._select_arkpass_btn.setFixedWidth(100)
        arkpass_layout.addWidget(self._select_arkpass_btn)

        arkpass_layout.addStretch()
        login_layout.addWidget(arkpass_frame)

        # 注册区域（新用户）
        register_line = QLabel("────────────────  新用户注册  ────────────────")
        register_line.setStyleSheet("color: rgba(144, 144, 168, 0.30); font-size: 10px; font-family: Consolas;")
        login_layout.addWidget(register_line)

        reg_frame = QWidget()
        reg_layout = QHBoxLayout(reg_frame)
        reg_layout.setContentsMargins(0, 0, 0, 0)
        reg_layout.setSpacing(12)

        reg_label = QLabel("用户名:")
        reg_label.setStyleSheet("color: #18d1ff; font-size: 12px; font-family: Consolas; font-weight: bold;")
        reg_label.setFixedWidth(80)
        reg_layout.addWidget(reg_label)

        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("输入用户名进行注册...")
        self._username_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(10, 10, 15, 0.90);
                color: #e0e0e8;
                border: 1px solid rgba(24, 209, 255, 0.15);
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 12px;
                font-family: Consolas;
            }
            QLineEdit:focus {
                border-color: rgba(24, 209, 255, 0.40);
            }
        """)
        reg_layout.addWidget(self._username_input, 1)

        self._register_btn = SecondaryButton("注册")
        self._register_btn.setFixedWidth(100)
        self._register_btn.setToolTip("注册新账户，将生成 ArkPass 认证文件")
        reg_layout.addWidget(self._register_btn)

        reg_layout.addStretch()
        login_layout.addWidget(reg_frame)

        # 操作按钮
        btn_frame = QWidget()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)

        self._login_btn = PrimaryButton("认证登录")
        btn_layout.addWidget(self._login_btn)
        btn_layout.addStretch()

        login_layout.addWidget(btn_frame)

        # 提示
        tip_label = QLabel("// 选择 ArkPass 认证文件以访问终端")
        tip_label.setStyleSheet("color: #404058; font-size: 11px; font-family: Consolas; font-style: italic;")
        tip_label.setWordWrap(True)
        login_layout.addWidget(tip_label)

        main_layout.addWidget(login_card)

        # ======== 用户信息面板 ========
        user_info_card = CardWidget()
        user_info_layout = user_info_card.get_content_layout()
        user_info_layout.setContentsMargins(20, 20, 20, 20)
        user_info_layout.setSpacing(12)

        user_info_title = QLabel("// 用户信息")
        user_info_title.setStyleSheet("""
            QLabel {
                color: #e8e8ee;
                font-size: 16px;
                font-family: Consolas;
                font-weight: bold;
                letter-spacing: 1px;
            }
        """)
        user_info_layout.addWidget(user_info_title)

        # 用户信息以终端键值对显示
        info_style = "color: #9090a8; font-size: 12px; font-family: Consolas; padding: 4px 0;"
        value_style = "color: #e8e8ee; font-size: 12px; font-family: Consolas; padding: 4px 0;"

        user_row1 = QHBoxLayout()
        user_row1.addWidget(QLabel("用户ID:"))
        user_row1.itemAt(0).widget().setStyleSheet(info_style)
        self._user_id_label = QLabel("NULL")
        self._user_id_label.setStyleSheet(value_style)
        user_row1.addWidget(self._user_id_label)
        user_row1.addStretch()
        user_info_layout.addLayout(user_row1)

        user_row2 = QHBoxLayout()
        user_row2.addWidget(QLabel("等级:"))
        user_row2.itemAt(0).widget().setStyleSheet(info_style)
        self._user_tier_label = QLabel("NULL")
        self._user_tier_label.setStyleSheet(value_style)
        user_row2.addWidget(self._user_tier_label)
        user_row2.addStretch()
        user_info_layout.addLayout(user_row2)

        user_row3 = QHBoxLayout()
        user_row3.addWidget(QLabel('登录:'))
        user_row3.itemAt(0).widget().setStyleSheet(info_style)
        self._login_time_label = QLabel("NULL")
        self._login_time_label.setStyleSheet("color: #606080; font-size: 12px; font-family: Consolas; padding: 4px 0;")
        user_row3.addWidget(self._login_time_label)
        user_row3.addStretch()
        user_info_layout.addLayout(user_row3)

        # 分隔线
        sep = QLabel("──────────────────────────────")
        sep.setStyleSheet("color: rgba(24, 209, 255, 0.10); font-size: 10px;")
        user_info_layout.addWidget(sep)

        # 注销
        self._logout_btn = DangerButton("注销")
        self._logout_btn.setVisible(False)
        user_info_layout.addWidget(self._logout_btn)

        main_layout.addWidget(user_info_card)
        main_layout.addStretch()

    def _setup_style(self) -> None:
        pass

    def _setup_connections(self) -> None:
        self._login_btn.clicked.connect(self._on_login_clicked)
        self._select_arkpass_btn.clicked.connect(self._on_select_arkpass_clicked)
        self._logout_btn.clicked.connect(self.logout_requested.emit)
        self._register_btn.clicked.connect(self._on_register_clicked)

    def _on_login_clicked(self) -> None:
        arkpass_path = self._arkpass_path_display.text()
        if arkpass_path == "NULL" or not arkpass_path:
            QMessageBox.warning(self, "警告", "请先选择 ArkPass 认证文件")
            return
        self._arkpass_path = arkpass_path
        self.arkpass_selected.emit(arkpass_path)

    def _on_register_clicked(self) -> None:
        """点击注册按钮——emit register_requested 信号给 main_window 处理"""
        username = self._username_input.text().strip()
        if not username:
            QMessageBox.warning(self, "警告", "请输入用户名以注册新账户")
            return
        if len(username) < 2:
            QMessageBox.warning(self, "警告", "用户名至少需要 2 个字符")
            return
        self._register_btn.setEnabled(False)
        self._username_input.setEnabled(False)
        self.register_requested.emit(username)

    def _on_select_arkpass_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 ArkPass 文件",
            "",
            "ArkPass Files (*.arkpass);;All Files (*.*)"
        )
        if file_path:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                QMessageBox.critical(
                    self,
                    "错误",
                    f"访问凭证读取失败\n\n文件不存在或无法访问:\n{file_path}"
                )
                return
            
            # 检查文件是否可读
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not content or len(content.strip()) == 0:
                    QMessageBox.warning(
                        self,
                        "警告",
                        f"ArkPass 文件为空或无效:\n{file_path}\n\n请选择有效的认证文件。"
                    )
                    return
            except PermissionError:
                QMessageBox.critical(
                    self,
                    "权限错误",
                    f"无法读取文件，请检查文件权限:\n{file_path}"
                )
                return
            except UnicodeDecodeError:
                QMessageBox.warning(
                    self,
                    "文件格式错误",
                    f"ArkPass 文件格式不正确 (应为 UTF-8):\n{file_path}"
                )
                return
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "读取失败",
                    f"访问凭证读取失败:\n{str(e)}\n\n文件路径:\n{file_path}"
                )
                return
            
            # 文件验证通过，更新 UI
            self._arkpass_path_display.setText(file_path)
            self._arkpass_path_display.setStyleSheet("color: #18d1ff; font-size: 12px; font-family: Consolas; padding: 8px 0;")
            self._arkpass_path = file_path

    def set_login_status(self, is_logged_in: bool, user_info: Optional[Dict[str, Any]] = None) -> None:
        self._login_status = self.STATUS_LOGGED_IN if is_logged_in else self.STATUS_LOGGED_OUT
        self._user_info = user_info or {}

        if is_logged_in:
            self._status_indicator.set_connected()
            self._login_btn.setEnabled(False)
            self._select_arkpass_btn.setEnabled(False)

            self._user_id = user_info.get('user_id', 'Unknown') if user_info else 'Unknown'
            self._user_id_label.setText(self._user_id)
            self._user_id_label.setStyleSheet("color: #18d1ff; font-size: 12px; font-family: Consolas; padding: 4px 0;")

            if user_info:
                tier = user_info.get('tier', 'free')
                tier_names = {
                    'free': 'FREE',
                    'prime': 'PRIME',
                    'plus': 'PLUS',
                    'pro': 'PRO'
                }
                tier_text = tier_names.get(tier, tier.upper())
                self._user_tier_label.setText(tier_text)

                tier_colors = {
                    'free': '#606080',
                    'prime': '#18d1ff',
                    'plus': '#fffa00',
                    'pro': '#ff1aac',
                }
                tier_color = tier_colors.get(tier, '#e8e8ee')
                self._user_tier_label.setStyleSheet(f"color: {tier_color}; font-size: 12px; font-family: Consolas; padding: 4px 0;")

                login_time = user_info.get('login_time', '-')
                self._login_time_label.setText(login_time)
            
            self._logout_btn.setVisible(True)
        else:
            self._status_indicator.set_disconnected()
            self._login_btn.setEnabled(True)
            self._select_arkpass_btn.setEnabled(True)

            self._user_id = None
            self._user_id_label.setText("NULL")
            self._user_id_label.setStyleSheet("color: #e8e8ee; font-size: 12px; font-family: Consolas; padding: 4px 0;")
            self._user_tier_label.setText("NULL")
            self._user_tier_label.setStyleSheet("color: #e8e8ee; font-size: 12px; font-family: Consolas; padding: 4px 0;")
            self._login_time_label.setText("NULL")
            
            self._logout_btn.setVisible(False)

    def set_logging_in(self) -> None:
        self._login_status = self.STATUS_LOGGING_IN
        self._status_indicator.set_connecting()
        self._login_btn.setEnabled(False)

    def on_register_complete(self, success: bool, arkpass_path: str = "") -> None:
        """注册完成后恢复 UI 状态"""
        self._register_btn.setEnabled(True)
        self._username_input.setEnabled(True)
        if success:
            self._username_input.clear()
            if arkpass_path:
                self._arkpass_path_display.setText(arkpass_path)
                self._arkpass_path_display.setStyleSheet("color: #18d1ff; font-size: 12px; font-family: Consolas; padding: 8px 0;")
                self._arkpass_path = arkpass_path
            QMessageBox.information(self, "注册成功", f"账户注册成功！\nArkPass 文件已保存至:\n{arkpass_path}")
        else:
            QMessageBox.warning(self, "注册失败", "注册失败，请检查网络连接或尝试其他用户名")

    def get_user_id(self) -> Optional[str]:
        return self._user_id

    def get_user_info(self) -> Dict[str, Any]:
        return self._user_info

    def is_logged_in(self) -> bool:
        return self._login_status == self.STATUS_LOGGED_IN

    def clear_form(self) -> None:
        self._arkpass_path_display.setText("NULL")
        self._arkpass_path_display.setStyleSheet("color: #606080; font-size: 12px; font-family: Consolas; padding: 8px 0;")
        self._arkpass_path = ""

    def set_username(self, username: str) -> None:
        pass

    def set_remember_password(self, remember: bool) -> None:
        pass