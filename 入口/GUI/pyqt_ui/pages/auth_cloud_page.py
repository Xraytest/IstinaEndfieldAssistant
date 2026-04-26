"""
认证与云服务合并页面
整合用户认证和云服务功能到一个页面中
使用QTabWidget分隔两个功能区域
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
    QProgressBar,
    QFrame,
    QTabWidget,
    QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from datetime import datetime

# 支持两种导入方式
try:
    from ..theme.theme_manager import ThemeManager
    from ..widgets.base_widgets import PrimaryButton, SecondaryButton, CardWidget, DangerButton
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
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.base_widgets import PrimaryButton, SecondaryButton, CardWidget, DangerButton
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.status_indicator import ConnectionStatusIndicator


class AuthCloudPage(QWidget):
    """
    认证与云服务合并页面
    
    功能：
    - ArkPass文件认证登录（标签页1）
    - 服务器连接状态显示（标签页2）
    - 用户信息和配额使用（标签页2）
    - Token用量统计（标签页2）
    
    信号：
    - arkpass_selected(str): ArkPass文件选择信号
    - logout_requested(): 注销请求信号
    - refresh_requested(): 刷新信息请求信号
    - sync_requested(): 同步请求信号
    """
    
    # 自定义信号
    arkpass_selected = pyqtSignal(str)  # ArkPass文件选择信号
    logout_requested = pyqtSignal()      # 注销请求信号
    refresh_requested = pyqtSignal()     # 刷新信息请求信号
    sync_requested = pyqtSignal()        # 同步请求信号
    
    # 服务状态常量
    STATUS_DISCONNECTED = "disconnected"
    STATUS_CONNECTED = "connected"
    STATUS_CONNECTING = "connecting"
    
    # 登录状态常量
    STATUS_LOGGED_OUT = "logged_out"
    STATUS_LOGGED_IN = "logged_in"
    STATUS_LOGGING_IN = "logging_in"
    
    def __init__(
        self,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        初始化认证与云服务页面
        
        Args:
            parent: 父控件
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._service_status: str = self.STATUS_DISCONNECTED
        self._user_info: Dict[str, Any] = {}
        self._login_status: str = self.STATUS_LOGGED_OUT
        self._arkpass_path: str = ""
        
        self._setup_ui()
        self._setup_style()
        self._setup_connections()
        
        # 尝试自动登录
        self._try_auto_login()
    
    def _get_cache_dir(self) -> str:
        """获取缓存目录路径"""
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

    def _try_auto_login(self) -> bool:
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
        
        # === 页面标题 ===
        title_label = QLabel("🔐 账户与云服务")
        title_label.setProperty("variant", "header")
        title_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {self._theme.get_color('text_primary')};")
        main_layout.addWidget(title_label)
        
        # === 创建标签页 ===
        self._tab_widget = QTabWidget()
        self._tab_widget.setDocumentMode(True)
        
        # 标签页1: 认证
        self._auth_tab = self._create_auth_tab()
        self._tab_widget.addTab(self._auth_tab, "🔐 账户认证")
        
        # 标签页2: 云服务
        self._cloud_tab = self._create_cloud_tab()
        self._tab_widget.addTab(self._cloud_tab, "☁️ 云服务")
        
        main_layout.addWidget(self._tab_widget)
    
    def _create_auth_tab(self) -> QWidget:
        """创建认证标签页"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        tab_widget = QWidget()
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md')
        )
        tab_layout.setSpacing(self._theme.get_spacing('md'))
        
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
        tab_layout.addWidget(status_frame)
        
        # === 认证卡片 ===
        auth_card = CardWidget()
        auth_layout = auth_card.get_content_layout()
        auth_layout.setContentsMargins(
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md')
        )
        auth_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 认证标题
        auth_title = QLabel("ArkPass 认证")
        auth_title.setProperty("variant", "header")
        auth_layout.addWidget(auth_title)
        
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
        auth_layout.addWidget(arkpass_frame)
        
        # 操作按钮区域
        btn_frame = QWidget()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(self._theme.get_spacing('md'))
        
        self._login_btn = PrimaryButton("登录")
        btn_layout.addWidget(self._login_btn)
        
        self._logout_btn = DangerButton("注销")
        self._logout_btn.setVisible(False)  # 初始隐藏
        btn_layout.addWidget(self._logout_btn)
        
        btn_layout.addStretch()
        auth_layout.addWidget(btn_frame)
        
        # 提示信息
        tip_label = QLabel("提示：请选择ArkPass认证文件进行登录")
        tip_label.setProperty("variant", "muted")
        tip_label.setWordWrap(True)
        auth_layout.addWidget(tip_label)
        
        tab_layout.addWidget(auth_card)
        
        # === 用户信息卡片 ===
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
        
        tab_layout.addWidget(user_info_card)
        tab_layout.addStretch()
        
        scroll_area.setWidget(tab_widget)
        return scroll_area
    
    def _create_cloud_tab(self) -> QWidget:
        """创建云服务标签页"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        tab_widget = QWidget()
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md')
        )
        tab_layout.setSpacing(self._theme.get_spacing('md'))
        
        # === 服务器状态卡片 ===
        status_card = CardWidget()
        status_layout = status_card.get_content_layout()
        status_layout.setContentsMargins(
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md')
        )
        status_layout.setSpacing(self._theme.get_spacing('md'))
        
        status_header = QFrame()
        status_header_layout = QHBoxLayout(status_header)
        status_header_layout.setContentsMargins(0, 0, 0, 0)
        status_header_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 服务器连接状态指示器
        self._server_status_indicator = ConnectionStatusIndicator(
            connection_type="server"
        )
        status_header_layout.addWidget(self._server_status_indicator)
        
        # 服务器地址显示
        server_label = QLabel("服务器地址:")
        server_label.setProperty("variant", "secondary")
        status_header_layout.addWidget(server_label)
        
        self._server_address_display = QLabel("-")
        self._server_address_display.setProperty("variant", "muted")
        status_header_layout.addWidget(self._server_address_display)
        
        status_header_layout.addStretch()
        status_layout.addWidget(status_header)
        
        tab_layout.addWidget(status_card)
        
        # === 用户信息区域 ===
        user_info_card = CardWidget()
        user_info_layout = user_info_card.get_content_layout()
        user_info_layout.setContentsMargins(
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md')
        )
        user_info_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 用户信息标题
        user_title = QLabel("用户信息")
        user_title.setProperty("variant", "header")
        user_info_layout.addWidget(user_title)
        
        # 用户名
        username_frame = QFrame()
        username_layout = QHBoxLayout(username_frame)
        username_layout.setContentsMargins(0, 0, 0, 0)
        username_layout.setSpacing(self._theme.get_spacing('sm'))
        
        username_label = QLabel("用户名:")
        username_label.setProperty("variant", "secondary")
        username_label.setFixedWidth(100)
        username_layout.addWidget(username_label)
        
        self._username_display = QLabel("未登录")
        self._username_display.setProperty("variant", "primary")
        username_layout.addWidget(self._username_display)
        
        username_layout.addStretch()
        user_info_layout.addWidget(username_frame)
        
        # 用户层级
        tier_frame = QFrame()
        tier_layout = QHBoxLayout(tier_frame)
        tier_layout.setContentsMargins(0, 0, 0, 0)
        tier_layout.setSpacing(self._theme.get_spacing('sm'))
        
        tier_label = QLabel("用户层级:")
        tier_label.setProperty("variant", "secondary")
        tier_label.setFixedWidth(100)
        tier_layout.addWidget(tier_label)
        
        self._tier_display = QLabel("-")
        self._tier_display.setProperty("variant", "primary")
        tier_layout.addWidget(self._tier_display)
        
        tier_layout.addStretch()
        user_info_layout.addWidget(tier_frame)
        
        # 高级权限到期时间
        expiry_frame = QFrame()
        expiry_layout = QHBoxLayout(expiry_frame)
        expiry_layout.setContentsMargins(0, 0, 0, 0)
        expiry_layout.setSpacing(self._theme.get_spacing('sm'))
        
        expiry_label = QLabel("到期时间:")
        expiry_label.setProperty("variant", "secondary")
        expiry_label.setFixedWidth(100)
        expiry_layout.addWidget(expiry_label)
        
        self._expiry_display = QLabel("-")
        self._expiry_display.setProperty("variant", "muted")
        expiry_layout.addWidget(self._expiry_display)
        
        expiry_layout.addStretch()
        user_info_layout.addWidget(expiry_frame)
        
        tab_layout.addWidget(user_info_card)
        
        # === 配额使用区域 ===
        quota_card = CardWidget()
        quota_layout = quota_card.get_content_layout()
        quota_layout.setContentsMargins(
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md')
        )
        quota_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 配额标题
        quota_title = QLabel("配额使用情况")
        quota_title.setProperty("variant", "header")
        quota_layout.addWidget(quota_title)
        
        # 每日配额
        daily_frame = QFrame()
        daily_layout = QVBoxLayout(daily_frame)
        daily_layout.setContentsMargins(0, 0, 0, 0)
        daily_layout.setSpacing(self._theme.get_spacing('xs'))
        
        daily_label_frame = QFrame()
        daily_label_layout = QHBoxLayout(daily_label_frame)
        daily_label_layout.setContentsMargins(0, 0, 0, 0)
        
        daily_label = QLabel("每日配额:")
        daily_label.setProperty("variant", "secondary")
        daily_label_layout.addWidget(daily_label)
        
        self._daily_quota_text = QLabel("0/1000")
        self._daily_quota_text.setProperty("variant", "primary")
        daily_label_layout.addWidget(self._daily_quota_text)
        
        daily_label_layout.addStretch()
        daily_layout.addWidget(daily_label_frame)
        
        self._daily_progress = QProgressBar()
        self._daily_progress.setMinimum(0)
        self._daily_progress.setMaximum(1000)
        self._daily_progress.setValue(0)
        self._daily_progress.setTextVisible(False)
        daily_layout.addWidget(self._daily_progress)
        
        quota_layout.addWidget(daily_frame)
        
        # 每周配额
        weekly_frame = QFrame()
        weekly_layout = QVBoxLayout(weekly_frame)
        weekly_layout.setContentsMargins(0, 0, 0, 0)
        weekly_layout.setSpacing(self._theme.get_spacing('xs'))
        
        weekly_label_frame = QFrame()
        weekly_label_layout = QHBoxLayout(weekly_label_frame)
        weekly_label_layout.setContentsMargins(0, 0, 0, 0)
        
        weekly_label = QLabel("每周配额:")
        weekly_label.setProperty("variant", "secondary")
        weekly_label_layout.addWidget(weekly_label)
        
        self._weekly_quota_text = QLabel("0/6000")
        self._weekly_quota_text.setProperty("variant", "primary")
        weekly_label_layout.addWidget(self._weekly_quota_text)
        
        weekly_label_layout.addStretch()
        weekly_layout.addWidget(weekly_label_frame)
        
        self._weekly_progress = QProgressBar()
        self._weekly_progress.setMinimum(0)
        self._weekly_progress.setMaximum(6000)
        self._weekly_progress.setValue(0)
        self._weekly_progress.setTextVisible(False)
        weekly_layout.addWidget(self._weekly_progress)
        
        quota_layout.addWidget(weekly_frame)
        
        # 每月配额
        monthly_frame = QFrame()
        monthly_layout = QVBoxLayout(monthly_frame)
        monthly_layout.setContentsMargins(0, 0, 0, 0)
        monthly_layout.setSpacing(self._theme.get_spacing('xs'))
        
        monthly_label_frame = QFrame()
        monthly_label_layout = QHBoxLayout(monthly_label_frame)
        monthly_label_layout.setContentsMargins(0, 0, 0, 0)
        
        monthly_label = QLabel("每月配额:")
        monthly_label.setProperty("variant", "secondary")
        monthly_label_layout.addWidget(monthly_label)
        
        self._monthly_quota_text = QLabel("0/15000")
        self._monthly_quota_text.setProperty("variant", "primary")
        monthly_label_layout.addWidget(self._monthly_quota_text)
        
        monthly_label_layout.addStretch()
        monthly_layout.addWidget(monthly_label_frame)
        
        self._monthly_progress = QProgressBar()
        self._monthly_progress.setMinimum(0)
        self._monthly_progress.setMaximum(15000)
        self._monthly_progress.setValue(0)
        self._monthly_progress.setTextVisible(False)
        monthly_layout.addWidget(self._monthly_progress)
        
        quota_layout.addWidget(monthly_frame)
        
        tab_layout.addWidget(quota_card)
        
        # === Token用量区域 ===
        token_card = CardWidget()
        token_layout = token_card.get_content_layout()
        token_layout.setContentsMargins(
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_md')
        )
        token_layout.setSpacing(self._theme.get_spacing('sm'))
        
        # Token标题
        token_title = QLabel("Token用量统计")
        token_title.setProperty("variant", "header")
        token_layout.addWidget(token_title)
        
        # Token用量显示
        token_frame = QFrame()
        token_frame_layout = QHBoxLayout(token_frame)
        token_frame_layout.setContentsMargins(0, 0, 0, 0)
        token_frame_layout.setSpacing(self._theme.get_spacing('sm'))
        
        token_label = QLabel("累计用量:")
        token_label.setProperty("variant", "secondary")
        token_label.setFixedWidth(100)
        token_frame_layout.addWidget(token_label)
        
        self._token_display = QLabel("0")
        self._token_display.setProperty("variant", "primary")
        token_frame_layout.addWidget(self._token_display)
        
        token_frame_layout.addStretch()
        token_layout.addWidget(token_frame)
        
        tab_layout.addWidget(token_card)
        
        # === 操作按钮区域 ===
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(self._theme.get_spacing('md'))
        
        self._refresh_btn = PrimaryButton("刷新信息")
        btn_layout.addWidget(self._refresh_btn)
        
        self._sync_btn = SecondaryButton("同步数据")
        btn_layout.addWidget(self._sync_btn)
        
        btn_layout.addStretch()
        tab_layout.addWidget(btn_frame)
        
        tab_layout.addStretch()
        
        scroll_area.setWidget(tab_widget)
        return scroll_area
    
    def _setup_style(self) -> None:
        """设置样式"""
        # 设置进度条样式
        progress_style = """
            QProgressBar {
                border: 1px solid #48484a;
                border-radius: 4px;
                background-color: #2c2c2e;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #4361ee;
                border-radius: 3px;
            }
        """
        
        self._daily_progress.setStyleSheet(progress_style)
        self._weekly_progress.setStyleSheet(progress_style)
        self._monthly_progress.setStyleSheet(progress_style)
        
        # 设置标签页样式
        tab_style = f"""
            QTabWidget::pane {{
                border: 1px solid {self._theme.get_color('border')};
                border-radius: 8px;
                background-color: {self._theme.get_color('surface')};
            }}
            QTabBar::tab {{
                background-color: {self._theme.get_color('surface_variant')};
                color: {self._theme.get_color('text_secondary')};
                padding: 10px 20px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {self._theme.get_color('primary')};
                color: {self._theme.get_color('on_primary')};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {self._theme.get_color('surface')};
            }}
        """
        self._tab_widget.setStyleSheet(tab_style)
    
    def _setup_connections(self) -> None:
        """设置信号连接"""
        # 认证按钮
        self._login_btn.clicked.connect(self._on_login_clicked)
        self._logout_btn.clicked.connect(self._on_logout_clicked)
        self._select_arkpass_btn.clicked.connect(self._on_select_arkpass_clicked)
        
        # 云服务按钮
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)
        self._sync_btn.clicked.connect(self._on_sync_clicked)
    
    def _on_login_clicked(self) -> None:
        """登录按钮点击"""
        arkpass_path = self._arkpass_path_display.text()
        if arkpass_path == "未选择文件" or not arkpass_path:
            QMessageBox.warning(self, "警告", "请先选择ArkPass认证文件")
            return
        
        self._arkpass_path = arkpass_path
        self.arkpass_selected.emit(arkpass_path)
    
    def _on_logout_clicked(self) -> None:
        """注销按钮点击"""
        self.logout_requested.emit()
    
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
    
    def _on_refresh_clicked(self) -> None:
        """刷新信息按钮点击"""
        self.refresh_requested.emit()
    
    def _on_sync_clicked(self) -> None:
        """同步数据按钮点击"""
        self.sync_requested.emit()
    
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
            self._server_status_indicator.set_connected()
            self._service_status = self.STATUS_CONNECTED
            
            # 更新按钮状态
            self._login_btn.setEnabled(False)
            self._login_btn.setVisible(False)
            self._logout_btn.setVisible(True)
            self._select_arkpass_btn.setEnabled(False)
            
            # 更新认证标签页用户信息
            self._update_auth_tab_user_info(user_info)
            
            # 更新云服务标签页信息
            self.update_user_info(user_info)
            
            # 切换到云服务标签页
            self._tab_widget.setCurrentIndex(1)
        else:
            self._status_indicator.set_disconnected()
            self._server_status_indicator.set_disconnected()
            self._service_status = self.STATUS_DISCONNECTED
            
            # 更新按钮状态
            self._login_btn.setEnabled(True)
            self._login_btn.setVisible(True)
            self._logout_btn.setVisible(False)
            self._select_arkpass_btn.setEnabled(True)
            
            # 清空用户信息
            self._clear_user_info()
    
    def _update_auth_tab_user_info(self, user_info: Optional[Dict[str, Any]]) -> None:
        """更新认证标签页的用户信息"""
        if user_info:
            user_id = user_info.get('user_id', 'Unknown')
            self._user_id_label.setText(f"用户名: {user_id}")
            
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
            
            login_time = user_info.get('login_time', '-')
            self._login_time_label.setText(f"登录时间: {login_time}")
    
    def set_logging_in(self) -> None:
        """设置为正在登录状态"""
        self._login_status = self.STATUS_LOGGING_IN
        self._status_indicator.set_connecting()
        self._server_status_indicator.set_connecting()
        self._login_btn.setEnabled(False)
        self._select_arkpass_btn.setEnabled(False)
    
    def update_user_info(self, user_info: Dict[str, Any]) -> None:
        """
        更新用户信息显示
        
        Args:
            user_info: 用户信息字典
        """
        self._user_info = user_info
        
        # 同时更新认证标签页
        self._update_auth_tab_user_info(user_info)
        
        # 用户名
        user_id = user_info.get('user_id', '未知')
        self._username_display.setText(user_id)
        
        # 用户层级
        tier = user_info.get('tier', 'free')
        tier_names = {
            'free': '免费用户',
            'prime': 'Prime用户',
            'plus': 'Plus用户',
            'pro': '专业用户'
        }
        tier_text = tier_names.get(tier, tier)
        self._tier_display.setText(tier_text)
        
        # 设置层级颜色
        tier_colors = {
            'free': self._theme.get_color('text_secondary'),
            'prime': self._theme.get_color('primary'),
            'plus': self._theme.get_color('success'),
            'pro': self._theme.get_color('warning'),
        }
        tier_color = tier_colors.get(tier, self._theme.get_color('text_primary'))
        self._tier_display.setStyleSheet(f"color: {tier_color};")
        
        # 每日配额
        quota_used = user_info.get('quota_used', 0)
        quota_daily = user_info.get('quota_daily', 1000)
        self._daily_quota_text.setText(f"{quota_used}/{quota_daily}")
        self._daily_progress.setMaximum(quota_daily)
        self._daily_progress.setValue(quota_used)
        
        # 根据使用量设置进度条颜色
        daily_usage_ratio = quota_used / quota_daily if quota_daily > 0 else 0
        if daily_usage_ratio >= 0.9:
            self._daily_progress.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #e74c3c;
                    border-radius: 3px;
                }
            """)
        elif daily_usage_ratio >= 0.7:
            self._daily_progress.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #f39c12;
                    border-radius: 3px;
                }
            """)
        else:
            self._daily_progress.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #4361ee;
                    border-radius: 3px;
                }
            """)
        
        # 每周配额
        quota_weekly = user_info.get('quota_weekly', 6000)
        self._weekly_quota_text.setText(f"0/{quota_weekly}")
        self._weekly_progress.setMaximum(quota_weekly)
        self._weekly_progress.setValue(0)
        
        # 每月配额
        quota_monthly = user_info.get('quota_monthly', 15000)
        self._monthly_quota_text.setText(f"0/{quota_monthly}")
        self._monthly_progress.setMaximum(quota_monthly)
        self._monthly_progress.setValue(0)
        
        # Token用量
        total_tokens = user_info.get('total_tokens_used', 0)
        self._token_display.setText(str(total_tokens))
        
        # 高级权限到期时间
        premium_until = user_info.get('premium_until', 0)
        if premium_until > 0:
            expiry_date = datetime.fromtimestamp(premium_until)
            self._expiry_display.setText(expiry_date.strftime('%Y-%m-%d %H:%M:%S'))
            
            # 如果即将到期，显示警告颜色
            now = datetime.now()
            days_remaining = (expiry_date - now).days
            if days_remaining <= 7:
                self._expiry_display.setStyleSheet(f"color: {self._theme.get_color('danger')};")
            elif days_remaining <= 30:
                self._expiry_display.setStyleSheet(f"color: {self._theme.get_color('warning')};")
            else:
                self._expiry_display.setStyleSheet("")
        else:
            self._expiry_display.setText("-")
            self._expiry_display.setStyleSheet("")
    
    def _clear_user_info(self) -> None:
        """清空用户信息显示"""
        self._user_info = {}
        
        # 认证标签页
        self._user_id_label.setText("用户名: 未登录")
        self._user_tier_label.setText("用户层级: -")
        self._user_tier_label.setStyleSheet("")
        self._login_time_label.setText("登录时间: -")
        
        # 云服务标签页
        self._username_display.setText("未登录")
        self._tier_display.setText("-")
        self._tier_display.setStyleSheet("")
        
        self._daily_quota_text.setText("0/1000")
        self._daily_progress.setValue(0)
        
        self._weekly_quota_text.setText("0/6000")
        self._weekly_progress.setValue(0)
        
        self._monthly_quota_text.setText("0/15000")
        self._monthly_progress.setValue(0)
        
        self._token_display.setText("0")
        
        self._expiry_display.setText("-")
        self._expiry_display.setStyleSheet("")
    
    def set_server_status(self, status: str, address: Optional[str] = None) -> None:
        """
        设置服务器连接状态
        
        Args:
            status: 服务状态 (connected, disconnected, connecting)
            address: 服务器地址
        """
        self._service_status = status
        
        if status == self.STATUS_CONNECTED:
            self._server_status_indicator.set_connected()
            self._status_indicator.set_connected()
        elif status == self.STATUS_CONNECTING:
            self._server_status_indicator.set_connecting()
            self._status_indicator.set_connecting()
        else:
            self._server_status_indicator.set_disconnected()
            self._status_indicator.set_disconnected()
        
        if address:
            self._server_address_display.setText(address)
    
    def get_user_info(self) -> Dict[str, Any]:
        """获取用户信息"""
        return self._user_info
    
    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        return self._login_status == self.STATUS_LOGGED_IN
    
    def is_connected(self) -> bool:
        """检查服务器是否已连接"""
        return self._service_status == self.STATUS_CONNECTED
    
    def get_service_status(self) -> str:
        """获取服务状态"""
        return self._service_status
    
    def clear_form(self) -> None:
        """清空登录表单"""
        self._arkpass_path_display.setText("未选择文件")
        self._arkpass_path_display.setProperty("variant", "muted")
        self._arkpass_path = ""
