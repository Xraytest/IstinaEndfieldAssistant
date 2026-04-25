"""
云服务页面
显示服务器连接状态、用户信息和配额使用情况
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QGroupBox,
    QFrame,
    QGridLayout,
    QSizePolicy,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from datetime import datetime

# 支持两种导入方式
try:
    from ..theme.theme_manager import ThemeManager
    from ..widgets.base_widgets import PrimaryButton, SecondaryButton, CardWidget
    from ..widgets.status_indicator import ConnectionStatusIndicator, DualStatusIndicator
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
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.base_widgets import PrimaryButton, SecondaryButton, CardWidget
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.status_indicator import ConnectionStatusIndicator, DualStatusIndicator


class CloudPage(QWidget):
    """
    云服务页面
    
    功能：
    - 服务器连接状态显示
    - 用户信息显示（用户名、层级）
    - 配额使用情况（每日、每周、每月）
    - Token用量统计
    - 高级权限到期时间
    - 同步操作按钮
    
    信号：
    - refresh_requested(): 刷新信息请求信号
    - sync_requested(): 同步请求信号
    """
    
    # 自定义信号
    refresh_requested = pyqtSignal()    # 刷新信息请求信号
    sync_requested = pyqtSignal()       # 同步请求信号
    
    # 服务状态常量
    STATUS_DISCONNECTED = "disconnected"
    STATUS_CONNECTED = "connected"
    STATUS_CONNECTING = "connecting"
    
    def __init__(
        self,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        初始化云服务页面
        
        Args:
            parent: 父控件
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._service_status: str = self.STATUS_DISCONNECTED
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
        
        # === 服务器状态区域 ===
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(self._theme.get_spacing('md'))
        
        # 服务器连接状态指示器
        self._server_status_indicator = ConnectionStatusIndicator(
            connection_type="server"
        )
        status_layout.addWidget(self._server_status_indicator)
        
        # 服务器地址显示
        server_label = QLabel("服务器地址:")
        server_label.setProperty("variant", "secondary")
        status_layout.addWidget(server_label)
        
        self._server_address_display = QLabel("-")
        self._server_address_display.setProperty("variant", "muted")
        status_layout.addWidget(self._server_address_display)
        
        status_layout.addStretch()
        
        main_layout.addWidget(status_frame)
        
        # === 用户信息区域 ===
        user_info_card = CardWidget()
        # 使用CardWidget的内部布局，而不是创建新布局覆盖它
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
        
        main_layout.addWidget(user_info_card)
        
        # === 配额使用区域 ===
        quota_card = CardWidget()
        # 使用CardWidget的内部布局，而不是创建新布局覆盖它
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
        
        main_layout.addWidget(quota_card)
        
        # === Token用量区域 ===
        token_card = CardWidget()
        # 使用CardWidget的内部布局，而不是创建新布局覆盖它
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
        
        main_layout.addWidget(token_card)
        
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
        main_layout.addWidget(btn_frame)
        
        main_layout.addStretch()
    
    def _setup_style(self) -> None:
        """设置样式"""
        # 页面样式通过QApplication全局应用，这里只设置特定控件样式
        
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
    
    def _setup_connections(self) -> None:
        """设置信号连接"""
        # 按钮点击信号
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)
        self._sync_btn.clicked.connect(self._on_sync_clicked)
    
    # === 信号处理方法 ===
    
    def _on_refresh_clicked(self) -> None:
        """刷新信息按钮点击"""
        self.refresh_requested.emit()
    
    def _on_sync_clicked(self) -> None:
        """同步数据按钮点击"""
        self.sync_requested.emit()
    
    # === 公共方法 ===
    
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
        elif status == self.STATUS_CONNECTING:
            self._server_status_indicator.set_connecting()
        else:
            self._server_status_indicator.set_disconnected()
        
        if address:
            self._server_address_display.setText(address)
    
    def update_user_info(self, user_info: Dict[str, Any]) -> None:
        """
        更新用户信息显示
        
        Args:
            user_info: 用户信息字典
        """
        self._user_info = user_info
        
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
    
    def clear_user_info(self) -> None:
        """清空用户信息显示"""
        self._user_info = {}
        
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
    
    def get_user_info(self) -> Dict[str, Any]:
        """获取用户信息"""
        return self._user_info
    
    def is_connected(self) -> bool:
        """检查服务器是否已连接"""
        return self._service_status == self.STATUS_CONNECTED
    
    def get_service_status(self) -> str:
        """获取服务状态"""
        return self._service_status