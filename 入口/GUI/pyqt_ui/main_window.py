"""
PyQt6 主窗口
Material Design 3 风格的主窗口框架，包含左侧导航栏和右侧内容区
"""

from typing import Optional, Dict, List, Any
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QLabel,
    QFrame,
    QSplitter,
    QStatusBar,
    QScrollArea,
    QApplication,
    QTabWidget,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon

# 支持两种导入方式：相对导入（包内使用）和绝对导入（测试使用）
try:
    from .theme.theme_manager import ThemeManager
    from .widgets.base_widgets import NavigationButton, HorizontalSeparator
    from .widgets.log_display import LogDisplayWidget
    from .pages import AuthPage, SettingsPage, CloudPage, IEAPage, ModelManagerPage
except ImportError:
    import sys
    import os
    # 计算项目根目录路径
    current_file = os.path.abspath(__file__)
    pyqt_ui_dir = os.path.dirname(current_file)
    gui_dir = os.path.dirname(pyqt_ui_dir)
    entry_dir = os.path.dirname(gui_dir)
    istina_dir = os.path.dirname(entry_dir)
    project_root = os.path.dirname(istina_dir)
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if istina_dir not in sys.path:
        sys.path.insert(0, istina_dir)
    
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.theme.theme_manager import ThemeManager
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.base_widgets import NavigationButton, HorizontalSeparator
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.log_display import LogDisplayWidget
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.pages import AuthPage, SettingsPage, CloudPage, IEAPage, ModelManagerPage


class NavigationBar(QWidget):
    """
    Material Design 3 导航栏
    
    提供左侧导航菜单，支持页面切换
    """
    
    page_changed = pyqtSignal(str)  # 页面切换信号
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化导航栏"""
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._nav_buttons: Dict[str, NavigationButton] = {}
        self._current_page: Optional[str] = None
        self._login_required: bool = False
        self._auth_page_id: Optional[str] = None
        self._is_logged_in: bool = False

        self._setup_ui()
        self._setup_style()

    def set_login_state(self, required: bool, is_logged_in: bool, auth_page_id: Optional[str] = None) -> None:
        """设置登录状态"""
        self._login_required = required
        self._is_logged_in = is_logged_in
        self._auth_page_id = auth_page_id
        self._update_nav_buttons_state()

    def _update_nav_buttons_state(self) -> None:
        """更新导航按钮状态"""
        if not self._login_required or self._is_logged_in:
            for button in self._nav_buttons.values():
                button.setEnabled(True)
            return
        for page_id, button in self._nav_buttons.items():
            if self._auth_page_id and page_id == self._auth_page_id:
                button.setEnabled(True)
            else:
                button.setEnabled(False)

    def can_navigate_to(self, page_id: str) -> bool:
        """检查是否可以导航到指定页面"""
        if not self._login_required or self._is_logged_in:
            return True
        if self._auth_page_id and page_id == self._auth_page_id:
            return True
        return False
    
    def _setup_ui(self) -> None:
        """设置导航栏UI结构"""
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_md'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_md')
        )
        self._main_layout.setSpacing(self._theme.get_spacing('xs'))
        
        # 标题区域
        self._title_label = QLabel("Istina Endfield")
        self._title_label.setProperty("variant", "title")
        self._title_label.style().unpolish(self._title_label)
        self._title_label.style().polish(self._title_label)
        self._main_layout.addWidget(self._title_label)
        
        # 版本标签
        self._version_label = QLabel("v1.0.0")
        self._version_label.setProperty("variant", "muted")
        self._version_label.style().unpolish(self._version_label)
        self._version_label.style().polish(self._version_label)
        self._main_layout.addWidget(self._version_label)
        
        # 分割线
        self._main_layout.addSpacing(self._theme.get_spacing('md'))
        separator = HorizontalSeparator(self)
        self._main_layout.addWidget(separator)
        self._main_layout.addSpacing(self._theme.get_spacing('md'))
        
        # 导航按钮区域
        self._nav_widget = QWidget()
        self._nav_layout = QVBoxLayout(self._nav_widget)
        self._nav_layout.setContentsMargins(0, 0, 0, 0)
        self._nav_layout.setSpacing(self._theme.get_spacing('xs'))
        self._main_layout.addWidget(self._nav_widget)
        
        # 弹性空间，将底部内容推到底部
        self._main_layout.addStretch()
        
        # 底部区域（设置等）
        self._bottom_widget = QWidget()
        self._bottom_layout = QVBoxLayout(self._bottom_widget)
        self._bottom_layout.setContentsMargins(0, 0, 0, 0)
        self._bottom_layout.setSpacing(self._theme.get_spacing('xs'))
        self._main_layout.addWidget(self._bottom_widget)
    
    def _setup_style(self) -> None:
        """设置导航栏样式"""
        self.setProperty("class", "navigationBar")
        self.style().unpolish(self)
        self.style().polish(self)
        
        # 设置固定宽度
        self.setFixedWidth(200)
    
    def add_page(
        self,
        page_id: str,
        title: str,
        icon: Optional[str] = None,
        position: str = "top"
    ) -> None:
        """
        添加导航页面
        
        Args:
            page_id: 页面唯一标识
            title: 页面标题
            icon: 图标名称（可选）
            position: 位置 ("top" 或 "bottom")
        """
        button = NavigationButton(title, self, icon)
        button.clicked.connect(lambda: self._on_nav_clicked(page_id))
        
        if position == "bottom":
            self._bottom_layout.addWidget(button)
        else:
            self._nav_layout.addWidget(button)
        
        self._nav_buttons[page_id] = button
        
        # 如果是第一个页面，默认选中
        if self._current_page is None:
            self.set_current_page(page_id)
    
    def remove_page(self, page_id: str) -> None:
        """
        移除导航页面
        
        Args:
            page_id: 页面唯一标识
        """
        if page_id in self._nav_buttons:
            button = self._nav_buttons.pop(page_id)
            button.deleteLater()
    
    def _on_nav_clicked(self, page_id: str) -> None:
        """
        导航按钮点击处理
        
        Args:
            page_id: 点击的页面标识
        """
        if not self.can_navigate_to(page_id):
            return
        self.set_current_page(page_id)
        self.page_changed.emit(page_id)
    
    def set_current_page(self, page_id: str) -> None:
        """
        设置当前页面
        
        Args:
            page_id: 页面唯一标识
        """
        # 更新按钮选中状态
        for pid, button in self._nav_buttons.items():
            button.set_selected(pid == page_id)
        
        self._current_page = page_id
    
    def get_current_page(self) -> Optional[str]:
        """获取当前页面标识"""
        return self._current_page
    
    def set_version(self, version: str) -> None:
        """
        设置版本显示
        
        Args:
            version: 版本字符串
        """
        self._version_label.setText(version)


class ContentArea(QWidget):
    """
    Material Design 3 内容区域
    
    使用 QStackedWidget 实现页面切换
    """
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化内容区域"""
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._pages: Dict[str, QWidget] = {}
        
        self._setup_ui()
        self._setup_style()
    
    def _setup_ui(self) -> None:
        """设置内容区域UI结构"""
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        
        # 页面堆叠控件
        self._stacked_widget = QStackedWidget()
        self._main_layout.addWidget(self._stacked_widget)
    
    def _setup_style(self) -> None:
        """设置内容区域样式"""
        self.setProperty("class", "contentArea")
        self.style().unpolish(self)
        self.style().polish(self)
    
    def add_page(self, page_id: str, page_widget: QWidget) -> None:
        """
        添加页面
        
        Args:
            page_id: 页面唯一标识
            page_widget: 页面控件
        """
        self._pages[page_id] = page_widget
        self._stacked_widget.addWidget(page_widget)
    
    def remove_page(self, page_id: str) -> None:
        """
        移除页面
        
        Args:
            page_id: 页面唯一标识
        """
        if page_id in self._pages:
            page_widget = self._pages.pop(page_id)
            self._stacked_widget.removeWidget(page_widget)
            page_widget.deleteLater()
    
    def show_page(self, page_id: str) -> None:
        """
        显示指定页面
        
        Args:
            page_id: 页面唯一标识
        """
        if page_id in self._pages:
            self._stacked_widget.setCurrentWidget(self._pages[page_id])
    
    def get_page(self, page_id: str) -> Optional[QWidget]:
        """
        获取页面控件
        
        Args:
            page_id: 页面唯一标识
            
        Returns:
            页面控件，如果不存在返回 None
        """
        return self._pages.get(page_id)
    
    def get_current_page_id(self) -> Optional[str]:
        """获取当前显示的页面标识"""
        current_widget = self._stacked_widget.currentWidget()
        for page_id, widget in self._pages.items():
            if widget == current_widget:
                return page_id
        return None


class MainWindow(QMainWindow):
    """
    Material Design 3 主窗口
    
    包含左侧导航栏、右侧内容区域和状态栏
    支持页面切换机制
    集成所有业务页面组件
    
    信号：
    - page_changed(str): 页面切换信号
    - window_closed(): 窗口关闭信号
    - device_connect_requested(str): 设备连接请求信号
    - device_disconnect_requested(): 设备断开请求信号
    - task_start_requested(): 任务启动请求信号
    - task_stop_requested(): 任务停止请求信号
    - login_requested(str, str): 登录请求信号
    - logout_requested(): 注销请求信号
    """
    
    # 信号定义
    page_changed = pyqtSignal(str)  # 页面切换信号
    window_closed = pyqtSignal()    # 窗口关闭信号
    
    # 设备相关信号
    device_connect_requested = pyqtSignal(str)  # 设备连接请求
    device_disconnect_requested = pyqtSignal()  # 设备断开请求
    device_scan_requested = pyqtSignal()        # 设备扫描请求
    screenshot_requested = pyqtSignal()         # [AutoFix 2026-04-18] 截图请求信号
    
    # 任务相关信号
    task_start_requested = pyqtSignal()         # 任务启动请求
    task_stop_requested = pyqtSignal()          # 任务停止请求
    task_added = pyqtSignal(dict)               # 任务添加信号
    task_deleted = pyqtSignal(str)              # 任务删除信号
    
    # 认证相关信号
    login_requested = pyqtSignal(str, str)      # 登录请求（用户名，密码）
    logout_requested = pyqtSignal()             # 注销请求
    
    # 设置相关信号
    settings_changed = pyqtSignal(dict)         # 设置变更信号
    check_update_requested = pyqtSignal()       # 检查更新请求
    
    # 云服务相关信号
    refresh_user_info_requested = pyqtSignal()  # 刷新用户信息请求
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Istina Endfield Assistant",
        min_width: int = 1200,
        min_height: int = 800,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        初始化主窗口
        
        Args:
            parent: 父控件
            title: 窗口标题
            min_width: 最小宽度
            min_height: 最小高度
            config: 配置字典
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._title = title
        self._min_width = min_width
        self._min_height = min_height
        self._config = config or {}
        
        # 页面组件引用
        self._auth_page: Optional[AuthPage] = None
        self._settings_page: Optional[SettingsPage] = None
        self._cloud_page: Optional[CloudPage] = None
        self._iea_page: Optional[IEAPage] = None
        self._model_manager_page: Optional[ModelManagerPage] = None
        self._log_display: Optional[LogDisplayWidget] = None
        self._is_logged_in: bool = False
        self._require_login: bool = True
        
        self._setup_window()
        self._setup_ui()
        self._setup_connections()
    
    def _setup_window(self) -> None:
        """设置窗口属性"""
        self.setWindowTitle(self._title)
        self.setMinimumSize(QSize(self._min_width, self._min_height))
        
        # 设置窗口图标（如果有）
        # self.setWindowIcon(QIcon("path/to/icon.png"))
    
    def _setup_ui(self) -> None:
        """设置主窗口UI结构"""
        # 创建中心控件
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)
        
        # 主布局
        self._main_layout = QHBoxLayout(self._central_widget)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        
        # 导航栏
        self._navigation_bar = NavigationBar()
        self._main_layout.addWidget(self._navigation_bar)
        
        # 内容区域
        self._content_area = ContentArea()
        self._main_layout.addWidget(self._content_area, stretch=1)
        
        # 状态栏
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("就绪")
        
        # 初始化页面组件
        self._init_pages()
    
    def _init_pages(self) -> None:
        """初始化所有页面组件"""
        # 获取触控模式配置并映射到IEAPage的连接模式
        touch_config = self._config.get('touch', {})
        touch_method = touch_config.get('touch_method', 'maatouch')

        # 映射touch_method到连接模式
        # touch_method: 'maatouch'/'adb' -> MODE_ANDROID
        # touch_method: 'pc' -> MODE_PC
        if touch_method == 'pc':
            connection_mode = IEAPage.MODE_PC
        else:
            connection_mode = IEAPage.MODE_ANDROID

        # IEA任务链推理页面（整合设备连接和任务链推理）
        self._iea_page = IEAPage(connection_mode=connection_mode)
        self.add_page("iea", "开始推理", self._iea_page)

        # 认证页面
        self._auth_page = AuthPage()
        self.add_page("auth", "认证", self._auth_page)

        # 云服务页面
        self._cloud_page = CloudPage()
        self.add_page("cloud", "云服务", self._cloud_page)

        # 模型管理页面（仅在本地推理启用时显示）
        local_inference_enabled = self._config.get('inference', {}).get('local_inference_enabled', False)
        if local_inference_enabled:
            self._model_manager_page = ModelManagerPage(config=self._config)
            self.add_page("models", "模型管理", self._model_manager_page)
        else:
            self._model_manager_page = None

        # 设置页面（底部导航）
        self._settings_page = SettingsPage(config=self._config)
        self.add_page("settings", "设置", self._settings_page, position="bottom")

        # 默认显示认证页面（需要登录）
        self.show_page("auth")
        self._navigation_bar.set_login_state(True, False, "auth")
    
    def _setup_connections(self) -> None:
        """设置信号连接"""
        # 导航栏页面切换 -> 内容区域显示页面
        self._navigation_bar.page_changed.connect(self._content_area.show_page)
        
        # 导航栏页面切换 -> 外部信号
        self._navigation_bar.page_changed.connect(self.page_changed.emit)
        
        # 页面切换 -> 状态栏更新
        self.page_changed.connect(self._on_page_changed)

        # 连接IEA页面信号（整合设备连接和任务链推理）
        if self._iea_page:
            # 设备相关信号
            self._iea_page.connect_requested.connect(self.device_connect_requested.emit)
            self._iea_page.disconnect_requested.connect(self.device_disconnect_requested.emit)
            self._iea_page.scan_requested.connect(self.device_scan_requested.emit)
            self._iea_page.screenshot_requested.connect(self._on_screenshot_requested)
            # 任务链相关信号
            self._iea_page.start_execution_requested.connect(self.task_start_requested.emit)
            self._iea_page.stop_execution_requested.connect(self.task_stop_requested.emit)
            self._iea_page.task_added.connect(self.task_added.emit)
            self._iea_page.task_deleted.connect(self.task_deleted.emit)
        
        # 连接认证页面信号
        if self._auth_page:
            self._auth_page.login_requested.connect(self.login_requested.emit)
            self._auth_page.logout_requested.connect(self.logout_requested.emit)
        
        # 连接设置页面信号
        if self._settings_page:
            self._settings_page.settings_changed.connect(self.settings_changed.emit)
            self._settings_page.check_update_requested.connect(self.check_update_requested.emit)
        
        # 连接模型管理页面信号
        if self._model_manager_page:
            self._model_manager_page.model_changed.connect(self._on_model_changed)
            self._model_manager_page.settings_changed.connect(self.settings_changed.emit)
        
        # 连接云服务页面信号
        if self._cloud_page:
            self._cloud_page.refresh_requested.connect(self.refresh_user_info_requested.emit)
    
    def _on_page_changed(self, page_id: str) -> None:
        """
        页面切换处理

        Args:
            page_id: 页面标识
        """
        # 更新状态栏
        page_names = {
            "iea": "开始推理",
            "auth": "认证",
            "cloud": "云服务",
            "settings": "设置",
            "models": "模型管理"
        }
        page_name = page_names.get(page_id, page_id)
        self.set_status(f"当前页面: {page_name}")

        # 切换到云服务页面时自动刷新用户信息
        if page_id == "cloud" and self._cloud_page:
            self._cloud_page.refresh_requested.emit()
    
    def _on_model_changed(self, model_name: str) -> None:
        """
        模型选择变更处理
        
        Args:
            model_name: 模型名称
        """
        # 更新配置
        if 'inference' not in self._config:
            self._config['inference'] = {}
        if 'local' not in self._config['inference']:
            self._config['inference']['local'] = {}
        
        self._config['inference']['local']['model_name'] = model_name
        self.append_log(f"已选择模型: {model_name}", "INFO")
    
    def add_page(
        self,
        page_id: str,
        title: str,
        page_widget: QWidget,
        icon: Optional[str] = None,
        position: str = "top"
    ) -> None:
        """
        添加页面
        
        Args:
            page_id: 页面唯一标识
            title: 页面标题
            page_widget: 页面控件
            icon: 图标名称（可选）
            position: 导航位置 ("top" 或 "bottom")
        """
        # 添加到导航栏
        self._navigation_bar.add_page(page_id, title, icon, position)
        
        # 添加到内容区域
        self._content_area.add_page(page_id, page_widget)
    
    def remove_page(self, page_id: str) -> None:
        """
        移除页面
        
        Args:
            page_id: 页面唯一标识
        """
        self._navigation_bar.remove_page(page_id)
        self._content_area.remove_page(page_id)
    
    def show_page(self, page_id: str) -> None:
        """
        显示指定页面
        
        Args:
            page_id: 页面唯一标识
        """
        self._navigation_bar.set_current_page(page_id)
        self._content_area.show_page(page_id)
    
    def get_current_page_id(self) -> Optional[str]:
        """获取当前显示的页面标识"""
        return self._content_area.get_current_page_id()
    
    def get_page(self, page_id: str) -> Optional[QWidget]:
        """
        获取页面控件
        
        Args:
            page_id: 页面唯一标识
            
        Returns:
            页面控件，如果不存在返回 None
        """
        return self._content_area.get_page(page_id)

    def get_auth_page(self) -> Optional[AuthPage]:
        """获取认证页面"""
        return self._auth_page
    
    def get_settings_page(self) -> Optional[SettingsPage]:
        """获取设置页面"""
        return self._settings_page
    
    def get_cloud_page(self) -> Optional[CloudPage]:
        """获取云服务页面"""
        return self._cloud_page

    def get_iea_page(self) -> Optional[IEAPage]:
        """获取开始推理页面"""
        return self._iea_page
    
    def get_model_manager_page(self) -> Optional[ModelManagerPage]:
        """获取模型管理页面"""
        return self._model_manager_page
    
    def set_status(self, message: str) -> None:
        """
        设置状态栏消息
        
        Args:
            message: 状态消息
        """
        self._status_bar.showMessage(message)
    
    def set_version(self, version: str) -> None:
        """
        设置版本显示
        
        Args:
            version: 版本字符串
        """
        self._navigation_bar.set_version(version)
    
    def append_log(self, message: str, level: str = "INFO") -> None:
        """
        添加日志消息

        Args:
            message: 日志消息
            level: 日志级别
        """
        # 如果有日志显示组件，添加日志
        if self._log_display:
            self._log_display.append_log(message, level)
        # 同时添加日志到IEA页面
        if self._iea_page:
            self._iea_page.append_log(message, level)
        else:
            # 在状态栏显示简要日志
            self.set_status(f"[{level}] {message[:50]}...")
    
    def update_device_status(self, status: str, connected: bool = False, device_info: Optional[Dict[str, Any]] = None) -> None:
        """
        更新设备连接状态

        Args:
            status: 状态消息
            connected: 是否已连接
            device_info: 设备信息字典（可选）
        """
        if self._iea_page:
            self._iea_page.set_connected(connected, device_info)
        self.set_status(status)
    
    def update_task_status(self, task_name: str, is_running: bool = False) -> None:
        """
        更新任务执行状态

        Args:
            task_name: 当前任务名称
            is_running: 是否正在运行
        """
        if self._iea_page:
            self._iea_page.set_execution_running(is_running)
        if is_running:
            self.set_status(f"正在执行: {task_name}")
        else:
            self.set_status(f"任务完成: {task_name}")
    
    def update_user_info(self, user_info: Dict[str, Any]) -> None:
        """
        更新用户信息
        
        Args:
            user_info: 用户信息字典
        """
        if self._auth_page:
            self._auth_page.update_user_info(user_info)
        if self._cloud_page:
            self._cloud_page.update_user_info(user_info)
    
    def update_login_status(self, logged_in: bool, user_info: Optional[Dict[str, Any]] = None) -> None:
        """
        更新登录状态
        
        Args:
            logged_in: 是否已登录
            user_info: 用户信息字典
        """
        self._is_logged_in = logged_in
        
        if self._auth_page:
            self._auth_page.set_login_status(logged_in, user_info)
        if self._cloud_page:
            self._cloud_page.set_server_status(
                "connected" if logged_in else "disconnected"
            )
        
        # 更新导航栏状态
        self._navigation_bar.set_login_state(self._require_login, logged_in, "auth")

        # 登录成功跳转到IEA页面
        if logged_in:
            self.show_page("iea")
    
    def update_auth_status(self, logged_in: bool, user_info: Optional[Dict[str, Any]] = None) -> None:
        """更新认证状态（兼容方法）"""
        self.update_login_status(logged_in, user_info)
    
    def update_device_list(self, devices: List[Dict[str, Any]]) -> None:
        """
        更新设备列表

        Args:
            devices: 设备列表
        """
        if self._iea_page:
            self._iea_page.update_device_list(devices)
    
    def update_task_list(self, tasks: List[Dict[str, Any]]) -> None:
        """
        更新任务列表（IEA页面使用add_task逐个添加，不使用此方法）

        Args:
            tasks: 任务列表
        """
        pass
    
    def update_screen_preview(self, image_data: bytes) -> None:
        """
        更新屏幕预览

        Args:
            image_data: 图像数据
        """
        if self._iea_page:
            self._iea_page.update_preview(image_data)
    
    def start_preview_refresh(self) -> None:
        """启动预览自动刷新"""
        if self._iea_page:
            self._iea_page.start_preview_refresh()
    
    def _on_screenshot_requested(self) -> None:
        """截图请求处理 [AutoFix 2026-04-18]"""
        # 转发截图请求信号到外部
        self.screenshot_requested.emit()
    
    def stop_preview_refresh(self) -> None:
        """停止预览自动刷新"""
        if self._iea_page:
            self._iea_page.stop_preview_refresh()
    
    def closeEvent(self, event) -> None:
        """
        窗口关闭事件处理
        
        Args:
            event: 关闭事件
        """
        # 发射窗口关闭信号
        self.window_closed.emit()
        
        # 显示确认对话框
        reply = QMessageBox.question(
            self,
            '确认退出',
            '确定要退出 Istina Endfield Assistant 吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()


def create_demo_main_window() -> MainWindow:
    """
    创建演示主窗口
    
    用于测试和验证 PyQt6 界面框架
    
    Returns:
        配置好的主窗口实例
    """
    window = MainWindow()
    
    # 添加演示页面 - 支持两种导入方式
    try:
        from .widgets.base_widgets import CardWidget, PrimaryButton, SecondaryButton
    except ImportError:
        import sys
        import os
        # 计算项目根目录路径
        current_file = os.path.abspath(__file__)
        pyqt_ui_dir = os.path.dirname(current_file)
        gui_dir = os.path.dirname(pyqt_ui_dir)
        entry_dir = os.path.dirname(gui_dir)
        istina_dir = os.path.dirname(entry_dir)
        project_root = os.path.dirname(istina_dir)
        
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        if istina_dir not in sys.path:
            sys.path.insert(0, istina_dir)
        
        from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.widgets.base_widgets import CardWidget, PrimaryButton, SecondaryButton
    
    # 首页
    home_page = QWidget()
    home_layout = QVBoxLayout(home_page)
    home_layout.setContentsMargins(16, 16, 16, 16)
    home_layout.setSpacing(12)
    
    home_card = CardWidget(title="欢迎使用 Istina Endfield Assistant")
    home_card.add_widget(QLabel("这是一个基于 Material Design 3 设计规范的 PyQt6 界面框架。"))
    home_card.add_widget(QLabel("左侧导航栏支持页面切换，右侧内容区域使用 QStackedWidget 实现页面堆叠。"))
    
    button_layout = QHBoxLayout()
    button_layout.addWidget(PrimaryButton("主要操作"))
    button_layout.addWidget(SecondaryButton("次要操作"))
    button_layout.addStretch()
    home_card.add_layout(button_layout)
    
    home_layout.addWidget(home_card)
    home_layout.addStretch()
    
    window.add_page("home", "首页", home_page)
    
    # 设备页面
    device_page = QWidget()
    device_layout = QVBoxLayout(device_page)
    device_layout.setContentsMargins(16, 16, 16, 16)
    device_layout.addWidget(QLabel("设备管理页面（待实现）"))
    device_layout.addStretch()
    window.add_page("device", "设备管理", device_page)
    
    # 任务页面
    task_page = QWidget()
    task_layout = QVBoxLayout(task_page)
    task_layout.setContentsMargins(16, 16, 16, 16)
    task_layout.addWidget(QLabel("任务管理页面（待实现）"))
    task_layout.addStretch()
    window.add_page("task", "任务管理", task_page)
    
    # 设置页面（底部）
    settings_page = QWidget()
    settings_layout = QVBoxLayout(settings_page)
    settings_layout.setContentsMargins(16, 16, 16, 16)
    settings_layout.addWidget(QLabel("设置页面（待实现）"))
    settings_layout.addStretch()
    window.add_page("settings", "设置", settings_page, position="bottom")
    
    return window


def run_demo() -> None:
    """
    运行演示应用
    
    用于测试 PyQt6 界面框架
    """
    import sys
    
    app = QApplication(sys.argv)
    
    # 应用主题
    ThemeManager.get_instance().apply_theme(app)
    
    # 创建并显示主窗口
    window = create_demo_main_window()
    window.show()
    
    # 运行应用
    sys.exit(app.exec())