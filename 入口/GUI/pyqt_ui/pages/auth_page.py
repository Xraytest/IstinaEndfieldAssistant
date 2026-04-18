"""
认证管理页面
处理用户登录、注销和用户状态显示
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QGroupBox,
    QFrame,
    QSizePolicy,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

# 支持两种导入方式
try:
    from ..theme.theme_manager import ThemeManager
    from ..widgets.base_widgets import PrimaryButton, SecondaryButton, DangerButton, CardWidget
    from ..widgets.status_indicator import ConnectionStatusIndicator
except ImportError:
    from theme.theme_manager import ThemeManager
    from widgets.base_widgets import PrimaryButton, SecondaryButton, DangerButton, CardWidget
    from widgets.status_indicator import ConnectionStatusIndicator


class AuthPage(QWidget):
    """
    认证管理页面
    
    功能：
    - 登录表单（用户名、密码输入）
    - 登录/注销按钮
    - 用户状态显示
    - 记住密码选项
    - ArkPass文件选择
    
    信号：
    - login_requested(str, str): 登录请求信号（用户名，密码/文件路径）
    - logout_requested(): 注销请求信号
    - register_requested(str): 注册请求信号（用户名）
    """
    
    # 自定义信号
    login_requested = pyqtSignal(str, str)     # 登录请求信号（用户名，密码/文件路径）
    logout_requested = pyqtSignal()            # 注销请求信号
    register_requested = pyqtSignal(str)       # 注册请求信号（用户名）
    arkpass_selected = pyqtSignal(str)         # ArkPass文件选择信号
    
    # 登录状态常量
    STATUS_LOGGED_OUT = "logged_out"
    STATUS_LOGGED_IN = "logged_in"
    STATUS_LOGGING_IN = "logging_in"
    
    def __init__(
        self,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        初始化认证管理页面
        
        Args:
            parent: 父控件
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._login_status: str = self.STATUS_LOGGED_OUT
        self._user_id: Optional[str] = None
        self._user_info: Dict[str, Any] = {}
        
        self._setup_ui()
        self._setup_style()
        self._setup_connections()
    
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
        
        # === 登录状态区域 ===
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 登录状态指示器
        self._status_indicator = ConnectionStatusIndicator(
            connection_type="server"
        )
        status_layout.addWidget(self._status_indicator)
        
        status_layout.addStretch()
        
        main_layout.addWidget(status_frame)
        
        # === 登录表单区域 ===
        login_card = CardWidget()
        login_layout = QVBoxLayout(login_card)
        login_layout.setContentsMargins(
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md')
        )
        login_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 登录标题
        login_title = QLabel("账户认证")
        login_title.setProperty("variant", "header")
        login_layout.addWidget(login_title)
        
        # 用户名输入区域
        username_frame = QFrame()
        username_layout = QHBoxLayout(username_frame)
        username_layout.setContentsMargins(0, 0, 0, 0)
        username_layout.setSpacing(self._theme.get_spacing('sm'))
        
        username_label = QLabel("用户名:")
        username_label.setProperty("variant", "secondary")
        username_label.setFixedWidth(80)
        username_layout.addWidget(username_label)
        
        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("输入用户名")
        self._username_input.setFixedWidth(200)
        username_layout.addWidget(self._username_input)
        
        username_layout.addStretch()
        login_layout.addWidget(username_frame)
        
        # 密码输入区域（可选，用于传统登录）
        password_frame = QFrame()
        password_layout = QHBoxLayout(password_frame)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(self._theme.get_spacing('sm'))
        
        password_label = QLabel("密码:")
        password_label.setProperty("variant", "secondary")
        password_label.setFixedWidth(80)
        password_layout.addWidget(password_label)
        
        self._password_input = QLineEdit()
        self._password_input.setPlaceholderText("输入密码（可选）")
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setFixedWidth(200)
        password_layout.addWidget(self._password_input)
        
        password_layout.addStretch()
        login_layout.addWidget(password_frame)
        
        # 记住密码选项
        remember_frame = QFrame()
        remember_layout = QHBoxLayout(remember_frame)
        remember_layout.setContentsMargins(80, 0, 0, 0)  # 与输入框对齐
        
        self._remember_checkbox = QCheckBox("记住密码")
        remember_layout.addWidget(self._remember_checkbox)
        
        remember_layout.addStretch()
        login_layout.addWidget(remember_frame)
        
        # ArkPass文件选择区域
        arkpass_frame = QFrame()
        arkpass_layout = QHBoxLayout(arkpass_frame)
        arkpass_layout.setContentsMargins(0, 0, 0, 0)
        arkpass_layout.setSpacing(self._theme.get_spacing('sm'))
        
        arkpass_label = QLabel("ArkPass:")
        arkpass_label.setProperty("variant", "secondary")
        arkpass_label.setFixedWidth(80)
        arkpass_layout.addWidget(arkpass_label)
        
        self._arkpass_path_display = QLabel("未选择文件")
        self._arkpass_path_display.setProperty("variant", "muted")
        self._arkpass_path_display.setFixedWidth(200)
        arkpass_layout.addWidget(self._arkpass_path_display)
        
        self._select_arkpass_btn = SecondaryButton("选择文件")
        self._select_arkpass_btn.setFixedWidth(100)
        arkpass_layout.addWidget(self._select_arkpass_btn)
        
        arkpass_layout.addStretch()
        login_layout.addWidget(arkpass_frame)
        
        # 操作按钮区域
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(self._theme.get_spacing('md'))
        
        self._login_btn = PrimaryButton("登录")
        btn_layout.addWidget(self._login_btn)
        
        self._register_btn = SecondaryButton("注册")
        btn_layout.addWidget(self._register_btn)
        
        self._logout_btn = DangerButton("注销")
        self._logout_btn.setEnabled(False)
        btn_layout.addWidget(self._logout_btn)
        
        btn_layout.addStretch()
        login_layout.addWidget(btn_frame)
        
        # 提示信息
        tip_label = QLabel("提示：使用ArkPass文件登录可免输入密码")
        tip_label.setProperty("variant", "muted")
        tip_label.setWordWrap(True)
        login_layout.addWidget(tip_label)
        
        main_layout.addWidget(login_card)
        
        # === 用户信息区域 ===
        user_info_card = CardWidget()
        user_info_layout = QVBoxLayout(user_info_card)
        user_info_layout.setContentsMargins(
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md')
        )
        user_info_layout.setSpacing(self._theme.get_spacing('sm'))
        
        # 用户信息标题
        user_info_title = QLabel("用户信息")
        user_info_title.setProperty("variant", "header")
        user_info_layout.addWidget(user_info_title)
        
        # 用户名显示
        self._user_id_label = QLabel("用户名: 未登录")
        self._user_id_label.setProperty("variant", "secondary")
        user_info_layout.addWidget(self._user_id_label)
        
        # 用户层级显示
        self._user_tier_label = QLabel("用户层级: -")
        self._user_tier_label.setProperty("variant", "secondary")
        user_info_layout.addWidget(self._user_tier_label)
        
        # 登录时间显示
        self._login_time_label = QLabel("登录时间: -")
        self._login_time_label.setProperty("variant", "muted")
        user_info_layout.addWidget(self._login_time_label)
        
        main_layout.addWidget(user_info_card)
        
        main_layout.addStretch()
    
    def _setup_style(self) -> None:
        """设置样式"""
        # 页面样式通过QApplication全局应用，这里只设置特定控件样式
        
        # 设置输入框样式
        input_style = """
            QLineEdit {
                border: 1px solid #48484a;
                border-radius: 4px;
                background-color: #2c2c2e;
                color: #ffffff;
                padding: 8px;
            }
            QLineEdit:focus {
                border-color: #4361ee;
            }
            QLineEdit:disabled {
                background-color: #3a3a3c;
                color: #636366;
            }
        """
        
        self._username_input.setStyleSheet(input_style)
        self._password_input.setStyleSheet(input_style)
        
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
        
        self._remember_checkbox.setStyleSheet(checkbox_style)
    
    def _setup_connections(self) -> None:
        """设置信号连接"""
        # 按钮点击信号
        self._login_btn.clicked.connect(self._on_login_clicked)
        self._register_btn.clicked.connect(self._on_register_clicked)
        self._logout_btn.clicked.connect(self._on_logout_clicked)
        self._select_arkpass_btn.clicked.connect(self._on_select_arkpass_clicked)
        
        # 输入框回车信号
        self._username_input.returnPressed.connect(self._on_login_clicked)
        self._password_input.returnPressed.connect(self._on_login_clicked)
    
    # === 信号处理方法 ===
    
    def _on_login_clicked(self) -> None:
        """登录按钮点击"""
        # 检查是否有ArkPass文件
        arkpass_path = self._arkpass_path_display.text()
        if arkpass_path != "未选择文件" and arkpass_path:
            # 使用ArkPass文件登录
            self.arkpass_selected.emit(arkpass_path)
            return
        
        # 使用用户名密码登录
        username = self._username_input.text().strip()
        password = self._password_input.text()
        
        if not username:
            QMessageBox.warning(self, "警告", "请输入用户名")
            return
        
        if not password:
            QMessageBox.warning(self, "警告", "请输入密码或选择ArkPass文件")
            return
        
        self.login_requested.emit(username, password)
    
    def _on_register_clicked(self) -> None:
        """注册按钮点击"""
        username = self._username_input.text().strip()
        if not username:
            QMessageBox.warning(self, "警告", "请输入用户名进行注册")
            return
        
        self.register_requested.emit(username)
    
    def _on_logout_clicked(self) -> None:
        """注销按钮点击"""
        self.logout_requested.emit()
    
    def _on_select_arkpass_clicked(self) -> None:
        """选择ArkPass文件按钮点击"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择ArkPass文件",
            "",
            "ArkPass Files (*.arkpass);;All Files (*)"
        )
        
        if file_path:
            self._arkpass_path_display.setText(file_path)
            self._arkpass_path_display.setProperty("variant", "primary")
            self.arkpass_selected.emit(file_path)
    
    # === 公共方法 ===
    
    def set_login_status(self, is_logged_in: bool, user_info: Optional[Dict[str, Any]] = None) -> None:
        """
        设置登录状态
        
        Args:
            is_logged_in: 是否已登录
            user_info: 用户信息字典
        """
        self._login_status = self.STATUS_LOGGED_IN if is_logged_in else self.STATUS_LOGGED_OUT
        self._user_info = user_info or {}
        
        if is_logged_in:
            self._status_indicator.set_connected()
            self._logout_btn.setEnabled(True)
            self._login_btn.setEnabled(False)
            self._register_btn.setEnabled(False)
            
            # 禁用输入框
            self._username_input.setEnabled(False)
            self._password_input.setEnabled(False)
            self._select_arkpass_btn.setEnabled(False)
            
            # 更新用户信息显示
            self._user_id = user_info.get('user_id', 'Unknown') if user_info else 'Unknown'
            self._user_id_label.setText(f"用户名: {self._user_id}")
            
            if user_info:
                tier = user_info.get('tier', 'free')
                tier_names = {
                    'free': '免费用户',
                    'prime': 'Prime用户',
                    'plus': 'Plus用户',
                    'pro': '专业用户'
                }
                tier_text = tier_names.get(tier, tier)
                self._user_tier_label.setText(f"用户层级: {tier_text}")
                
                # 设置层级颜色
                tier_colors = {
                    'free': self._theme.get_color('text_secondary'),
                    'prime': self._theme.get_color('primary'),
                    'plus': self._theme.get_color('success'),
                    'pro': self._theme.get_color('warning'),
                }
                tier_color = tier_colors.get(tier, self._theme.get_color('text_primary'))
                self._user_tier_label.setStyleSheet(f"color: {tier_color};")
                
                # 登录时间
                login_time = user_info.get('login_time', '-')
                self._login_time_label.setText(f"登录时间: {login_time}")
        else:
            self._status_indicator.set_disconnected()
            self._logout_btn.setEnabled(False)
            self._login_btn.setEnabled(True)
            self._register_btn.setEnabled(True)
            
            # 启用输入框
            self._username_input.setEnabled(True)
            self._password_input.setEnabled(True)
            self._select_arkpass_btn.setEnabled(True)
            
            # 清空用户信息显示
            self._user_id = None
            self._user_id_label.setText("用户名: 未登录")
            self._user_tier_label.setText("用户层级: -")
            self._user_tier_label.setStyleSheet("")
            self._login_time_label.setText("登录时间: -")
    
    def set_logging_in(self) -> None:
        """设置为正在登录状态"""
        self._login_status = self.STATUS_LOGGING_IN
        self._status_indicator.set_connecting()
        self._login_btn.setEnabled(False)
        self._register_btn.setEnabled(False)
    
    def get_user_id(self) -> Optional[str]:
        """获取当前用户ID"""
        return self._user_id
    
    def get_user_info(self) -> Dict[str, Any]:
        """获取用户信息"""
        return self._user_info
    
    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        return self._login_status == self.STATUS_LOGGED_IN
    
    def clear_form(self) -> None:
        """清空登录表单"""
        self._username_input.clear()
        self._password_input.clear()
        self._arkpass_path_display.setText("未选择文件")
        self._arkpass_path_display.setProperty("variant", "muted")
        self._remember_checkbox.setChecked(False)
    
    def set_username(self, username: str) -> None:
        """设置用户名"""
        self._username_input.setText(username)
    
    def set_remember_password(self, remember: bool) -> None:
        """设置记住密码选项"""
        self._remember_checkbox.setChecked(remember)