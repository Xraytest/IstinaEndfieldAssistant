"""
认证管理页面
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
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.base_widgets import PrimaryButton, SecondaryButton, DangerButton, CardWidget
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.status_indicator import ConnectionStatusIndicator


class AuthPage(QWidget):
    """
    认证管理页面

    功能：
    - ArkPass文件认证登录
    - 自动加载缓存的ArkPass文件
    - 登录/注销按钮
    - 用户状态显示

    信号：
    - arkpass_selected(str): ArkPass文件选择信号（文件路径）
    - logout_requested(): 注销请求信号
    """

    # 自定义信号
    login_requested = pyqtSignal(str, str)     # 保留以兼容旧接口，但仅使用ArkPass路径
    logout_requested = pyqtSignal()            # 注销请求信号
    register_requested = pyqtSignal(str)       # 保留以兼容旧接口
    arkpass_selected = pyqtSignal(str)         # ArkPass文件选择信号
    auto_login_requested = pyqtSignal()        # 自动登录请求信号

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
        self._arkpass_path: str = ""

        self._setup_ui()
        self._setup_style()
        self._setup_connections()

    def _get_cache_dir(self) -> str:
        """获取缓存目录路径"""
        # 从当前文件路径推导: auth_page.py -> pages -> pyqt_ui -> GUI -> 入口 -> IstinaEndfieldAssistant
        current_dir = os.path.dirname(os.path.abspath(__file__))
        istina_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
        cache_dir = os.path.join(istina_root, "cache")
        return cache_dir

    def _get_cached_arkpass(self) -> Optional[str]:
        """获取缓存的ArkPass文件路径"""
        cache_dir = self._get_cache_dir()

        if not os.path.exists(cache_dir):
            return None

        # 查找所有 .arkpass 文件
        arkpass_files = glob.glob(os.path.join(cache_dir, "*.arkpass"))

        if not arkpass_files:
            return None

        # 返回最新修改的文件
        return max(arkpass_files, key=os.path.getmtime)

    def try_auto_login(self) -> bool:
        """
        尝试自动登录

        Returns:
            是否找到缓存文件并发起自动登录请求
        """
        cached_arkpass = self._get_cached_arkpass()

        if cached_arkpass and os.path.exists(cached_arkpass):
            # 更新UI显示缓存的文件路径
            self._arkpass_path_display.setText(cached_arkpass)
            self._arkpass_path_display.setProperty("variant", "primary")
            self._arkpass_path = cached_arkpass

            # 设置正在登录状态
            self.set_logging_in()

            # 发送自动登录请求信号
            self.arkpass_selected.emit(cached_arkpass)
            return True

        return False

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
        status_frame = QWidget()
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
        # 使用CardWidget的内部布局
        login_layout = login_card.get_content_layout()
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

        # ArkPass文件选择区域
        arkpass_frame = QWidget()
        arkpass_layout = QHBoxLayout(arkpass_frame)
        arkpass_layout.setContentsMargins(0, 0, 0, 0)
        arkpass_layout.setSpacing(self._theme.get_spacing('sm'))

        arkpass_label = QLabel("ArkPass:")
        arkpass_label.setProperty("variant", "secondary")
        arkpass_label.setFixedWidth(80)
        arkpass_layout.addWidget(arkpass_label)

        self._arkpass_path_display = QLabel("未选择文件")
        self._arkpass_path_display.setProperty("variant", "muted")
        self._arkpass_path_display.setFixedWidth(250)
        arkpass_layout.addWidget(self._arkpass_path_display)

        self._select_arkpass_btn = SecondaryButton("选择文件")
        self._select_arkpass_btn.setFixedWidth(100)
        arkpass_layout.addWidget(self._select_arkpass_btn)

        arkpass_layout.addStretch()
        login_layout.addWidget(arkpass_frame)

        # 操作按钮区域
        btn_frame = QWidget()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(self._theme.get_spacing('md'))

        self._login_btn = PrimaryButton("登录")
        btn_layout.addWidget(self._login_btn)

        btn_layout.addStretch()
        login_layout.addWidget(btn_frame)

        # 提示信息
        tip_label = QLabel("提示：请选择ArkPass认证文件进行登录")
        tip_label.setProperty("variant", "muted")
        tip_label.setWordWrap(True)
        login_layout.addWidget(tip_label)

        main_layout.addWidget(login_card)

        # === 用户信息区域 ===
        user_info_card = CardWidget()
        user_info_layout = user_info_card.get_content_layout()
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
        pass

    def _setup_connections(self) -> None:
        """设置信号连接"""
        # 按钮点击信号
        self._login_btn.clicked.connect(self._on_login_clicked)
        self._select_arkpass_btn.clicked.connect(self._on_select_arkpass_clicked)

    # === 信号处理方法 ===

    def _on_login_clicked(self) -> None:
        """登录按钮点击 - 仅支持ArkPass登录"""
        # 检查是否有ArkPass文件
        arkpass_path = self._arkpass_path_display.text()
        if arkpass_path == "未选择文件" or not arkpass_path:
            QMessageBox.warning(self, "警告", "请先选择ArkPass认证文件")
            return

        # 使用ArkPass文件登录
        self._arkpass_path = arkpass_path
        self.arkpass_selected.emit(arkpass_path)

    def _on_select_arkpass_clicked(self) -> None:
        """选择ArkPass文件按钮点击"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择ArkPass文件",
            "",
            "ArkPass Files (*.arkpass);;All Files (*.*)"
        )

        if file_path:
            self._arkpass_path_display.setText(file_path)
            self._arkpass_path_display.setProperty("variant", "primary")
            self._arkpass_path = file_path

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
            self._login_btn.setEnabled(False)

            # 禁用ArkPass选择
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
            self._login_btn.setEnabled(True)

            # 启用ArkPass选择
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
        self._arkpass_path_display.setText("未选择文件")
        self._arkpass_path_display.setProperty("variant", "muted")
        self._arkpass_path = ""

    def set_username(self, username: str) -> None:
        """设置用户名（保留方法，当前版本不使用）"""
        pass

    def set_remember_password(self, remember: bool) -> None:
        """设置记住密码选项（保留方法，当前版本不使用）"""
        pass
