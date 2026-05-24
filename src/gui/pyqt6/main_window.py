"""
PyQt6 主窗口 - Endfield 终端工业风格
Hypergryph 终末地设计语言：左侧终端导航 + 右侧内容面板
"""

import os
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
from PyQt6.QtGui import QIcon, QFont

try:
    from .theme.theme_manager import ThemeManager
    from .widgets.base_widgets import NavigationButton, HorizontalSeparator
    from .pages import AuthPage, SettingsPage, CloudPage, AgentPage
    from .pages.agent_page import AgentPage as AgentPageDirect
    from .pages.model_manager_page import ModelManagerPage
except ImportError:
    import sys
    import os
    current_file = os.path.abspath(__file__)
    pyqt6_dir = os.path.dirname(current_file)
    gui_dir = os.path.dirname(pyqt6_dir)
    src_dir = os.path.dirname(gui_dir)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    from gui.pyqt6.theme.theme_manager import ThemeManager
    from gui.pyqt6.widgets.base_widgets import NavigationButton, HorizontalSeparator
    from gui.pyqt6.pages import AuthPage, SettingsPage, CloudPage, AgentPage
    from gui.pyqt6.pages.model_manager_page import ModelManagerPage


class NavigationBar(QWidget):
    """
    Endfield 终端风格导航栏
    固定左侧面板，终端青蓝指示条 + 命令行式导航
    """
    
    page_changed = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
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
        self._login_required = required
        self._is_logged_in = is_logged_in
        self._auth_page_id = auth_page_id
        self._update_nav_buttons_state()

    def _update_nav_buttons_state(self) -> None:
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
        if not self._login_required or self._is_logged_in:
            return True
        if self._auth_page_id and page_id == self._auth_page_id:
            return True
        return False
    
    def _setup_ui(self) -> None:
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        
        # 终端标题区域
        header_widget = QWidget()
        header_widget.setObjectName("navHeader")
        header_widget.setStyleSheet("""
            QWidget#navHeader {
                background-color: rgba(24, 209, 255, 0.04);
                border-bottom: 1px solid rgba(24, 209, 255, 0.10);
            }
        """)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 20, 20, 16)
        header_layout.setSpacing(4)
        
        self._title_label = QLabel("ISTINA//ENDFIELD")
        self._title_label.setStyleSheet("""
            QLabel {
                color: #18d1ff;
                font-size: 13px;
                font-family: Consolas;
                font-weight: bold;
                letter-spacing: 2px;
            }
        """)
        header_layout.addWidget(self._title_label)
        
        self._version_label = QLabel("v1.0.0")
        self._version_label.setStyleSheet("""
            QLabel {
                color: #606080;
                font-size: 11px;
                font-family: Consolas;
            }
        """)
        header_layout.addWidget(self._version_label)
        
        header_layout.addSpacing(8)
        
        # 分隔线
        term_line = QLabel("━━━━━━━━━━━━━━")
        term_line.setStyleSheet("color: rgba(24, 209, 255, 0.15); font-size: 10px;")
        header_layout.addWidget(term_line)
        
        self._main_layout.addWidget(header_widget)
        
        # 导航按钮区域
        nav_scroll = QWidget()
        self._nav_layout = QVBoxLayout(nav_scroll)
        self._nav_layout.setContentsMargins(0, 8, 0, 8)
        self._nav_layout.setSpacing(2)
        self._main_layout.addWidget(nav_scroll, 1)
        
        # 底部区域
        self._bottom_widget = QWidget()
        self._bottom_layout = QVBoxLayout(self._bottom_widget)
        self._bottom_layout.setContentsMargins(0, 8, 0, 8)
        self._bottom_layout.setSpacing(2)
        
        # 底部终端分隔线
        bottom_line = QLabel("━━━━━━━━━━━━━━")
        bottom_line.setStyleSheet("color: rgba(24, 209, 255, 0.15); font-size: 10px;")
        bottom_line.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._bottom_layout.addWidget(bottom_line)
        self._bottom_layout.addSpacing(4)
        
        self._main_layout.addWidget(self._bottom_widget)
    
    def _setup_style(self) -> None:
        self.setProperty("class", "navigationBar")
        self.setFixedWidth(220)
    
    def add_page(
        self,
        page_id: str,
        title: str,
        icon: Optional[str] = None,
        position: str = "top"
    ) -> None:
        # 终端风格前缀
        prefix = "◆ " if position == "top" else "▸ "
        display_title = f"{prefix}{title}"
        
        button = NavigationButton(display_title, self, icon)
        button.clicked.connect(lambda: self._on_nav_clicked(page_id))
        
        if position == "bottom":
            self._bottom_layout.addWidget(button)
        else:
            self._nav_layout.addWidget(button)
        
        self._nav_buttons[page_id] = button
        
        if self._current_page is None:
            self.set_current_page(page_id)
    
    def remove_page(self, page_id: str) -> None:
        if page_id in self._nav_buttons:
            button = self._nav_buttons.pop(page_id)
            button.deleteLater()
    
    def _on_nav_clicked(self, page_id: str) -> None:
        if not self.can_navigate_to(page_id):
            return
        self.set_current_page(page_id)
        self.page_changed.emit(page_id)
    
    def set_current_page(self, page_id: str) -> None:
        for pid, button in self._nav_buttons.items():
            button.set_selected(pid == page_id)
        self._current_page = page_id
    
    def get_current_page(self) -> Optional[str]:
        return self._current_page
    
    def set_version(self, version: str) -> None:
        self._version_label.setText(version)


class ContentArea(QWidget):
    """
    Endfield 内容区域
    QStackedWidget 页面容器
    """
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._pages: Dict[str, QWidget] = {}
        
        self._setup_ui()
        self._setup_style()
    
    def _setup_ui(self) -> None:
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        self._stacked_widget = QStackedWidget()
        self._main_layout.addWidget(self._stacked_widget)
    
    def _setup_style(self) -> None:
        self.setProperty("class", "contentArea")
    
    def add_page(self, page_id: str, page_widget: QWidget) -> None:
        self._pages[page_id] = page_widget
        self._stacked_widget.addWidget(page_widget)
    
    def remove_page(self, page_id: str) -> None:
        if page_id in self._pages:
            page_widget = self._pages.pop(page_id)
            self._stacked_widget.removeWidget(page_widget)
            page_widget.deleteLater()
    
    def show_page(self, page_id: str) -> None:
        if page_id in self._pages:
            self._stacked_widget.setCurrentWidget(self._pages[page_id])
    
    def get_page(self, page_id: str) -> Optional[QWidget]:
        return self._pages.get(page_id)
    
    def get_current_page_id(self) -> Optional[str]:
        current_widget = self._stacked_widget.currentWidget()
        for page_id, widget in self._pages.items():
            if widget == current_widget:
                return page_id
        return None


class MainWindow(QMainWindow):
    """
    Endfield 终端工业风格主窗口
    包含左侧导航栏、右侧内容区域和状态栏
    
    信号：
    - page_changed(str): 页面切换信号
    - window_closed(): 窗口关闭信号
    """
    
    page_changed = pyqtSignal(str)
    window_closed = pyqtSignal()
    device_connect_requested = pyqtSignal(str)
    device_disconnect_requested = pyqtSignal()
    device_scan_requested = pyqtSignal()
    screenshot_requested = pyqtSignal()
    task_start_requested = pyqtSignal()
    task_stop_requested = pyqtSignal()
    task_added = pyqtSignal(dict)
    task_deleted = pyqtSignal(str)
    login_requested = pyqtSignal(str, str)
    logout_requested = pyqtSignal()
    settings_changed = pyqtSignal(dict)
    check_update_requested = pyqtSignal()
    refresh_user_info_requested = pyqtSignal()
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Istina Endfield Assistant",
        min_width: int = 1280,
        min_height: int = 800,
        config: Optional[Dict[str, Any]] = None,
        auth_manager: Optional[Any] = None,
        device_manager: Optional[Any] = None,
        agent_executor: Optional[Any] = None,
        communicator: Optional[Any] = None,
        screen_capture: Optional[Any] = None
    ) -> None:
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._title = title
        self._min_width = min_width
        self._min_height = min_height
        self._config = config or {}
        
        self._auth_manager = auth_manager
        self._device_manager = device_manager
        self._agent_executor = agent_executor
        self._communicator = communicator
        self._screen_capture = screen_capture
        
        self._auth_page: Optional[AuthPage] = None
        self._settings_page: Optional[SettingsPage] = None
        self._cloud_page: Optional[Any] = None
        self._agent_page: Optional[AgentPage] = None
        self._model_manager_page: Optional[Any] = None
        
        self._is_logged_in: bool = False
        self._require_login: bool = True
        
        self._setup_window()
        self._setup_ui()
        self._setup_connections()
    
    def _setup_window(self) -> None:
        self.setWindowTitle(self._title)
        self.setMinimumSize(QSize(self._min_width, self._min_height))
    
    def _setup_ui(self) -> None:
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)
        
        self._main_layout = QHBoxLayout(self._central_widget)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        
        self._navigation_bar = NavigationBar()
        self._main_layout.addWidget(self._navigation_bar)
        
        self._content_area = ContentArea()
        self._main_layout.addWidget(self._content_area, stretch=1)
        
        # 状态栏 - 终端风格
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage(">>> SYSTEM READY")
        self._status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #07070b;
                color: #18d1ff;
                border-top: 1px solid rgba(24, 209, 255, 0.10);
                font-size: 11px;
                font-family: Consolas;
                padding: 2px 12px;
            }
        """)
        
        self._init_pages()
    
    def _init_pages(self) -> None:
        from gui.pyqt6.pages.auth_page import AuthPage
        self._auth_page = AuthPage()
        self.add_page("auth_cloud", "终端认证", self._auth_page)

        self._agent_page = AgentPage(agent_executor=self._agent_executor)
        self.add_page("agent", "Agent 控制台", self._agent_page)

        self._model_manager_page = ModelManagerPage(config=self._config)
        self.add_page("model_manager", "模型仓库", self._model_manager_page)
        
        from gui.pyqt6.pages.settings_page import SettingsPage
        self._settings_page = SettingsPage(config=self._config)
        self.add_page("settings", "系统设置", self._settings_page, position="bottom")

        self.show_page("auth_cloud")
        self._navigation_bar.set_login_state(True, False, "auth_cloud")
        
        self._auth_page_id = "auth_cloud"
    
    def _setup_connections(self) -> None:
        self._navigation_bar.page_changed.connect(self._content_area.show_page)
        self._navigation_bar.page_changed.connect(self.page_changed.emit)
        self.page_changed.connect(self._on_page_changed)

        if self._auth_page and self._auth_manager:
            self._auth_page.arkpass_selected.connect(self._on_arkpass_selected)
            self._auth_page.logout_requested.connect(self._on_logout_requested)
            self._auth_page.refresh_requested.connect(self._refresh_user_info)
        
        if self._settings_page:
            self._settings_page.settings_changed.connect(self.settings_changed.emit)
            self._settings_page.check_update_requested.connect(self.check_update_requested.emit)
            self._settings_page.local_inference_toggled.connect(self._on_local_inference_toggled)
            self._settings_page.refresh_gpu_status.connect(self._refresh_gpu_status)
        
        if self._model_manager_page:
            self._model_manager_page.model_selected.connect(self._on_model_changed)
            self._model_manager_page.model_download_requested.connect(self._on_model_download_requested)
            self._model_manager_page.model_remove_requested.connect(self._on_model_remove_requested)
            self._model_manager_page.refresh_requested.connect(self._refresh_model_manager)
    
    def _on_page_changed(self, page_id: str) -> None:
        page_names = {
            "agent": "Agent 控制台",
            "auth_cloud": "终端认证",
            "settings": "系统设置",
            "model_manager": "模型仓库"
        }
        page_name = page_names.get(page_id, page_id)
        self.set_status(f">>> 当前终端: {page_name}")

        if page_id == "auth_cloud" and self._auth_manager:
            self._refresh_auth_status()
    
    def _on_model_changed(self, model_name: str) -> None:
        if 'inference' not in self._config:
            self._config['inference'] = {}
        if 'local' not in self._config['inference']:
            self._config['inference']['local'] = {}
        
        self._config['inference']['local']['model_name'] = model_name
        self.append_log(f"模型已选择: {model_name}", "INFO")
        
    def _on_local_inference_toggled(self, enabled: bool):
        self.append_log(f"本地推理: {'ON' if enabled else 'OFF'}", "INFO")
        if 'inference' not in self._config:
            self._config['inference'] = {}
        if 'local' not in self._config['inference']:
            self._config['inference']['local'] = {}
        self._config['inference']['local']['enabled'] = enabled
        
        if enabled:
            self.show_page("model_manager")
        else:
            self.show_page("settings")
            
    def _refresh_gpu_status(self):
        if self._settings_page:
            self._settings_page._start_gpu_check()
            
    def _on_model_download_requested(self, model_name: str):
        self.append_log(f"模型下载: {model_name}", "INFO")
        QMessageBox.information(
            self,
            "模型下载",
            f"模型 '{model_name}' 下载功能尚未实现。\n"
            f"在实际使用中，这将从后台下载模型文件。"
        )
        
    def _on_model_remove_requested(self, model_name: str):
        self.append_log(f"模型删除请求: {model_name}", "INFO")
        QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除模型 '{model_name}' 吗？\n此操作将删除本地模型文件。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        self.append_log(f"模型已删除: {model_name}", "INFO")
        if self._model_manager_page:
            self._model_manager_page.refresh_requested.emit()
            
    def _refresh_model_manager(self):
        if self._model_manager_page:
            self._model_manager_page.refresh_requested.emit()
    
    def add_page(
        self,
        page_id: str,
        title: str,
        page_widget: QWidget,
        icon: Optional[str] = None,
        position: str = "top"
    ) -> None:
        self._navigation_bar.add_page(page_id, title, icon, position)
        self._content_area.add_page(page_id, page_widget)
    
    def remove_page(self, page_id: str) -> None:
        if page_id == "settings":
            return
        
        self._navigation_bar.remove_page(page_id)
        self._content_area.remove_page(page_id)
    
    def has_page(self, page_id: str) -> bool:
        return page_id in self._navigation_bar._nav_buttons and page_id in self._content_area._pages
    
    def show_page(self, page_id: str) -> None:
        if not self.has_page(page_id):
            return
        
        current_page_id = self._content_area.get_current_page_id()
        if current_page_id == page_id:
            return
        
        self._navigation_bar.set_current_page(page_id)
        self._content_area.show_page(page_id)
    
    def get_current_page_id(self) -> Optional[str]:
        return self._content_area.get_current_page_id()
    
    def get_page(self, page_id: str) -> Optional[QWidget]:
        return self._content_area.get_page(page_id)

    def get_auth_page(self) -> Optional[AuthPage]:
        return self._auth_page
    
    def get_settings_page(self) -> Optional[SettingsPage]:
        return self._settings_page
    
    def get_cloud_page(self) -> Optional[SettingsPage]:
        return self._auth_page

    def set_status(self, message: str) -> None:
        self._status_bar.showMessage(message)
    
    def set_version(self, version: str) -> None:
        self._navigation_bar.set_version(version)
    
    def append_log(self, message: str, level: str = "INFO") -> None:
        prefix = ">>>" if level == "INFO" else "!!!" if level == "ERROR" else ">>>"
        self.set_status(f"{prefix} {level}: {message[:50]}...")

    def set_agent_executor(self, agent_executor):
        if self._agent_page:
            self._agent_page.set_agent_executor(agent_executor)

    def update_device_status(self, status: str, connected: bool = False, device_info: Optional[Dict[str, Any]] = None) -> None:
        self.set_status(status)

    def update_screen_preview(self, image_data: bytes) -> None:
        pass
    
    def start_preview_refresh(self) -> None:
        pass
    
    def _on_screenshot_requested(self) -> None:
        self.screenshot_requested.emit()
    
    def stop_preview_refresh(self) -> None:
        pass
    
    def closeEvent(self, event) -> None:
        self.window_closed.emit()
        
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
            
    def _on_arkpass_selected(self, arkpass_path: str):
        if not self._auth_manager:
            self.append_log("错误：AuthManager 未初始化", "ERROR")
            QMessageBox.warning(self, "错误", "认证组件未初始化")
            return
            
        # 检查文件是否存在
        if not os.path.exists(arkpass_path):
            error_msg = f"访问凭证读取失败\n\n文件不存在或无法访问:\n{arkpass_path}"
            self.set_status(">>> AUTH FAILED: FILE NOT FOUND")
            self.append_log(f"认证失败：{error_msg}", "ERROR")
            QMessageBox.critical(self, "访问凭证读取失败", error_msg)
            return
        
        try:
            result = self._auth_manager.login_with_arkpass(arkpass_path)
            
            if isinstance(result, tuple):
                success = result[0]
                error_msg = result[1] if len(result) > 1 else "LOGIN FAILED"
            else:
                success = bool(result)
                error_msg = "LOGIN FAILED"
                
            if success:
                self.set_status(">>> AUTHENTICATION SUCCESS")
                self._is_logged_in = True
                self._navigation_bar.set_login_state(True, True, None)
                user_id = getattr(self._auth_manager, 'user_id', '')
                self.append_log(f"用户已认证：{user_id}", "INFO")
                QMessageBox.information(self, "认证成功", f"欢迎回来，{user_id or 'User'}")
            else:
                actual_error = error_msg if error_msg else (result[1] if isinstance(result, tuple) and len(result) > 1 else "未知错误")
                formatted_error = f"认证失败\n\n{actual_error}\n\n文件路径:\n{arkpass_path}"
                self.set_status(f">>> AUTH FAILED: {actual_error}")
                self.append_log(f"认证失败：{actual_error}", "ERROR")
                QMessageBox.warning(self, "认证失败", formatted_error)
        except FileNotFoundError as e:
            error_msg = f"访问凭证读取失败\n\n找不到文件:\n{arkpass_path}"
            self.set_status(">>> AUTH FAILED: FILE NOT FOUND")
            self.append_log(f"认证失败：{error_msg}", "ERROR")
            QMessageBox.critical(self, "访问凭证读取失败", error_msg)
        except PermissionError as e:
            error_msg = f"访问凭证读取失败\n\n权限不足，无法读取文件:\n{arkpass_path}"
            self.set_status(">>> AUTH FAILED: PERMISSION DENIED")
            self.append_log(f"认证失败：{error_msg}", "ERROR")
            QMessageBox.critical(self, "权限错误", error_msg)
        except Exception as e:
            error_msg = f"访问凭证读取失败\n\n{str(e)}"
            self.append_log(f"认证异常：{e}", "ERROR")
            self.set_status(">>> AUTH FAILED: EXCEPTION")
            QMessageBox.warning(self, "认证异常", error_msg)
            QMessageBox.critical(self, "错误", f"认证过程发生异常：{e}")
    
    def _on_logout_requested(self):
        if not self._auth_manager:
            return
            
        self._auth_manager.is_logged_in = False
        self._is_logged_in = False
        self._navigation_bar.set_login_state(True, False, "auth_cloud")
        self.append_log("用户已注销", "INFO")
        QMessageBox.information(self, "已注销", "您已成功登出终端")
        
    def _refresh_user_info(self):
        self._refresh_auth_status()
        
    def _refresh_auth_status(self):
        if not self._auth_manager or not self._auth_page:
            return
            
        is_logged_in = getattr(self._auth_manager, 'is_logged_in', False)
        if is_logged_in:
            user_id = getattr(self._auth_manager, 'user_id', '')
            self._auth_page.set_login_status(True, {"user_id": user_id})
            self._is_logged_in = True
            self._navigation_bar.set_login_state(True, True, None)
            self.set_status(f">>> 已认证: {user_id}")


def create_demo_main_window() -> MainWindow:
    window = MainWindow()
    
    try:
        from .widgets.base_widgets import CardWidget, PrimaryButton, SecondaryButton
    except ImportError:
        import sys
        import os
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
        
        from gui.pyqt6.widgets.base_widgets import CardWidget, PrimaryButton, SecondaryButton
    
    home_page = QWidget()
    home_layout = QVBoxLayout(home_page)
    home_layout.setContentsMargins(20, 20, 20, 20)
    home_layout.setSpacing(16)
    
    home_card = CardWidget(title="WELCOME TO ISTINA ENDFIELD")
    home_card.add_widget(QLabel("基于 Hypergryph 终末地工业科幻设计语言的 PyQt6 界面终端。"))
    home_card.add_widget(QLabel("左侧导航栏支持页面切换，右侧内容区域使用 QStackedWidget 实现页面堆叠。"))
    
    button_layout = QHBoxLayout()
    button_layout.addWidget(PrimaryButton("启动主操作"))
    button_layout.addWidget(SecondaryButton("辅助操作"))
    button_layout.addStretch()
    home_card.add_layout(button_layout)
    
    home_layout.addWidget(home_card)
    home_layout.addStretch()
    
    window.add_page("home", "首页", home_page)
    
    device_page = QWidget()
    device_layout = QVBoxLayout(device_page)
    device_layout.setContentsMargins(20, 20, 20, 20)
    device_layout.addWidget(QLabel("设备管理终端（待实现）"))
    device_layout.addStretch()
    window.add_page("device", "设备管理", device_page)
    
    task_page = QWidget()
    task_layout = QVBoxLayout(task_page)
    task_layout.setContentsMargins(20, 20, 20, 20)
    task_layout.addWidget(QLabel("任务管理终端（待实现）"))
    task_layout.addStretch()
    window.add_page("task", "任务管理", task_page)
    
    settings_page = QWidget()
    settings_layout = QVBoxLayout(settings_page)
    settings_layout.setContentsMargins(20, 20, 20, 20)
    settings_layout.addWidget(QLabel("系统设置终端（待实现）"))
    settings_layout.addStretch()
    window.add_page("settings", "系统设置", settings_page, position="bottom")
    
    return window


def run_demo() -> None:
    import sys
    
    app = QApplication(sys.argv)
    
    ThemeManager.get_instance().apply_theme(app)
    
    window = create_demo_main_window()
    window.show()
    
    sys.exit(app.exec())