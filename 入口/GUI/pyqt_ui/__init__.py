"""
PyQt6 UI 模块
基于 Material Design 3 设计规范的 PyQt6 界面实现

提供：
- MainWindow: 主窗口组件
- ThemeManager: 主题管理器
- PyQt6Application: 应用管理类
- run_application(): 应用入口函数
- 页面组件: DevicePage, TaskPage, AuthPage, SettingsPage, CloudPage
- 对话框组件: MessageBox, ConfirmDialog, ProgressDialog
- 工具组件: 各种自定义控件
"""

# 支持两种导入方式：相对导入（包内使用）和绝对导入（测试使用）
try:
    from .theme.theme_manager import ThemeManager
    from .main_window import MainWindow
    from .app_main import (
        PyQt6Application,
        QtLogHandler,
        WorkerThread,
        run_application,
        run_demo_application,
    )
    from .pages import (
        DevicePage,
        TaskPage,
        AuthPage,
        SettingsPage,
        CloudPage,
    )
    from .dialogs import (
        MessageBox,
        ConfirmDialog,
        ProgressDialog,
        show_info,
        show_warning,
        show_error,
        show_success,
        ask_question,
        confirm_action,
        confirm_delete,
        confirm_exit,
    )
    from .widgets import (
        NavigationButton,
        PrimaryButton,
        SecondaryButton,
        DangerButton,
        CardWidget,
        DevicePreviewWidget,
        TaskListWidget,
        DragDropTaskList,
        LogDisplayWidget,
        ConnectionStatusIndicator,
        StatusIndicatorWidget,
    )
except ImportError:
    from theme.theme_manager import ThemeManager
    from main_window import MainWindow
    from app_main import (
        PyQt6Application,
        QtLogHandler,
        WorkerThread,
        run_application,
        run_demo_application,
    )
    from pages import (
        DevicePage,
        TaskPage,
        AuthPage,
        SettingsPage,
        CloudPage,
    )
    from dialogs import (
        MessageBox,
        ConfirmDialog,
        ProgressDialog,
        show_info,
        show_warning,
        show_error,
        show_success,
        ask_question,
        confirm_action,
        confirm_delete,
        confirm_exit,
    )
    from widgets import (
        NavigationButton,
        PrimaryButton,
        SecondaryButton,
        DangerButton,
        CardWidget,
        DevicePreviewWidget,
        TaskListWidget,
        DragDropTaskList,
        LogDisplayWidget,
        ConnectionStatusIndicator,
        StatusIndicatorWidget,
    )


__all__ = [
    # 核心组件
    'ThemeManager',
    'MainWindow',
    'PyQt6Application',
    
    # 工具类
    'QtLogHandler',
    'WorkerThread',
    
    # 入口函数
    'run_application',
    'run_demo_application',
    
    # 页面组件
    'DevicePage',
    'TaskPage',
    'AuthPage',
    'SettingsPage',
    'CloudPage',
    
    # 对话框组件
    'MessageBox',
    'ConfirmDialog',
    'ProgressDialog',
    
    # 对话框便捷函数
    'show_info',
    'show_warning',
    'show_error',
    'show_success',
    'ask_question',
    'confirm_action',
    'confirm_delete',
    'confirm_exit',
    
    # 基础控件
    'NavigationButton',
    'PrimaryButton',
    'SecondaryButton',
    'DangerButton',
    'CardWidget',
    
    # 功能控件
    'DevicePreviewWidget',
    'TaskListWidget',
    'DragDropTaskList',
    'LogDisplayWidget',
    'ConnectionStatusIndicator',
    'StatusIndicatorWidget',
]


def create_application(
    auth_manager=None,
    device_manager=None,
    execution_manager=None,
    task_queue_manager=None,
    communicator=None,
    config=None
):
    """
    创建应用实例
    
    这是创建PyQt6应用的便捷函数
    
    Args:
        auth_manager: 认证管理器
        device_manager: 设备管理器
        execution_manager: 执行管理器
        task_queue_manager: 任务队列管理器
        communicator: 通信器
        config: 配置字典
        
    Returns:
        PyQt6Application实例
    """
    return PyQt6Application(
        auth_manager=auth_manager,
        device_manager=device_manager,
        execution_manager=execution_manager,
        task_queue_manager=task_queue_manager,
        communicator=communicator,
        config=config
    )


def start_gui(
    auth_manager=None,
    device_manager=None,
    execution_manager=None,
    task_queue_manager=None,
    communicator=None,
    config=None
):
    """
    启动GUI应用
    
    这是启动PyQt6 GUI的主入口函数
    
    Args:
        auth_manager: 认证管理器
        device_manager: 设备管理器
        execution_manager: 执行管理器
        task_queue_manager: 任务队列管理器
        communicator: 通信器
        config: 配置字典
        
    Returns:
        应用退出代码
    """
    return run_application(
        auth_manager=auth_manager,
        device_manager=device_manager,
        execution_manager=execution_manager,
        task_queue_manager=task_queue_manager,
        communicator=communicator,
        config=config
    )