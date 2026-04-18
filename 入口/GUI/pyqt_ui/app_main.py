"""
PyQt6 应用入口
整合所有组件，实现与业务逻辑层的连接
"""

import sys
import os
import logging
from typing import Optional, Dict, Any, Callable
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer, Qt
from PyQt6.QtGui import QFont

# 支持两种导入方式
try:
    from .main_window import MainWindow
    from .theme.theme_manager import ThemeManager
    from .widgets.log_display import LogDisplayWidget
    from .dialogs.message_box import MessageBox
    from .dialogs.confirm_dialog import ConfirmDialog
except ImportError:
    from main_window import MainWindow
    from theme.theme_manager import ThemeManager
    from widgets.log_display import LogDisplayWidget
    from dialogs.message_box import MessageBox
    from dialogs.confirm_dialog import ConfirmDialog


class QtLogHandler(logging.Handler, QObject):
    """
    Qt日志处理器
    将Python logging输出转发到Qt信号，用于UI显示
    
    使用方法：
    1. 创建实例并添加到logger
    2. 连接log_signal到UI组件的日志显示方法
    """
    
    # 日志信号
    log_signal = pyqtSignal(str, str)  # (message, level)
    
    def __init__(self, level: int = logging.NOTSET) -> None:
        """初始化日志处理器"""
        # 注意：多重继承时需要先调用QObject的初始化
        QObject.__init__(self)
        logging.Handler.__init__(self, level)
        
    def emit(self, record: logging.LogRecord) -> None:
        """发送日志记录"""
        try:
            # 格式化日志消息
            message = self.format(record)
            level = record.levelname
            
            # 通过Qt信号发送（确保在主线程中处理）
            self.log_signal.emit(message, level)
        except Exception:
            self.handleError(record)


class WorkerThread(QThread):
    """
    工作线程基类
    用于在后台执行任务，避免阻塞UI
    
    使用方法：
    1. 继承此类并实现run()方法
    2. 使用finished信号判断任务完成
    3. 使用error_signal处理错误
    """
    
    # 信号定义
    finished_signal = pyqtSignal(object)  # 任务完成信号，携带结果
    error_signal = pyqtSignal(str)         # 错误信号
    progress_signal = pyqtSignal(int, str) # 进度信号 (百分比, 消息)
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """初始化工作线程"""
        super().__init__(parent)
        self._is_cancelled: bool = False
        
    def cancel(self) -> None:
        """取消任务"""
        self._is_cancelled = True
        
    def is_cancelled(self) -> bool:
        """检查是否已取消"""
        return self._is_cancelled


class DeviceScanWorker(WorkerThread):
    """设备扫描工作线程"""
    
    def __init__(
        self,
        device_manager: Any,
        parent: Optional[QObject] = None
    ) -> None:
        """初始化设备扫描线程"""
        super().__init__(parent)
        self._device_manager = device_manager
        
    def run(self) -> None:
        """执行设备扫描"""
        try:
            self.progress_signal.emit(0, "开始扫描设备...")
            
            # 调用设备管理器的扫描方法
            if hasattr(self._device_manager, 'scan_devices'):
                devices = self._device_manager.scan_devices()
            else:
                devices = []
            
            self.progress_signal.emit(50, "扫描完成")
            
            if not self.is_cancelled():
                self.finished_signal.emit(devices)
                
        except Exception as e:
            self.error_signal.emit(f"设备扫描失败: {str(e)}")


class TaskSyncWorker(WorkerThread):
    """任务同步工作线程"""
    
    def __init__(
        self,
        task_manager: Any,
        communicator: Any,
        parent: Optional[QObject] = None
    ) -> None:
        """初始化任务同步线程"""
        super().__init__(parent)
        self._task_manager = task_manager
        self._communicator = communicator
        
    def run(self) -> None:
        """执行任务同步"""
        try:
            self.progress_signal.emit(0, "开始同步任务...")
            
            # 同步任务定义
            if hasattr(self._communicator, 'get_task_definitions'):
                tasks = self._communicator.get_task_definitions()
                if hasattr(self._task_manager, 'update_task_definitions'):
                    self._task_manager.update_task_definitions(tasks)
            
            self.progress_signal.emit(100, "同步完成")
            
            if not self.is_cancelled():
                self.finished_signal.emit(tasks)
                
        except Exception as e:
            self.error_signal.emit(f"任务同步失败: {str(e)}")


class PyQt6Application(QObject):
    """
    PyQt6应用管理类
    
    整合所有组件，实现：
    - Communicator通信器连接
    - DeviceStateManager设备状态管理
    - TaskManager任务管理
    - 信号槽连接（页面信号→业务逻辑，业务逻辑信号→页面更新）
    - 日志系统适配
    
    使用方法：
    1. 创建实例，传入业务逻辑组件
    2. 调用setup()初始化连接
    3. 调用run()启动应用
    """
    
    # 信号定义
    application_ready = pyqtSignal()
    application_error = pyqtSignal(str)
    
    def __init__(
        self,
        auth_manager: Optional[Any] = None,
        device_manager: Optional[Any] = None,
        execution_manager: Optional[Any] = None,
        task_queue_manager: Optional[Any] = None,
        communicator: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        parent: Optional[QObject] = None
    ) -> None:
        """
        初始化应用
        
        Args:
            auth_manager: 认证管理器
            device_manager: 设备管理器
            execution_manager: 执行管理器
            task_queue_manager: 任务队列管理器
            communicator: 通信器
            config: 配置字典
            parent: 父对象
        """
        super().__init__(parent)
        
        # 业务逻辑组件
        self._auth_manager = auth_manager
        self._device_manager = device_manager
        self._execution_manager = execution_manager
        self._task_queue_manager = task_queue_manager
        self._communicator = communicator
        self._config = config or {}
        
        # Qt组件
        self._app: Optional[QApplication] = None
        self._main_window: Optional[MainWindow] = None
        self._log_handler: Optional[QtLogHandler] = None
        
        # 工作线程
        self._worker_threads: list = []
        
        # 状态
        self._is_setup: bool = False
        self._is_running: bool = False
        
    def setup(self) -> bool:
        """
        设置应用
        
        Returns:
            是否成功设置
        """
        try:
            # 创建QApplication实例
            if QApplication.instance() is None:
                self._app = QApplication(sys.argv)
            else:
                self._app = QApplication.instance()
            
            # 设置应用属性
            self._app.setApplicationName("Istina Endfield Assistant")
            self._app.setApplicationVersion("1.0.0")
            self._app.setOrganizationName("IstinaStudio")
            
            # 启用高DPI支持
            # PyQt6默认启用高DPI
            
            # 应用主题
            theme = ThemeManager.get_instance()
            theme.apply_theme(self._app)
            
            # 创建主窗口
            self._main_window = MainWindow(config=self._config)
            
            # 设置日志处理器
            self._setup_log_handler()
            
            # 连接信号槽
            self._setup_connections()
            
            self._is_setup = True
            return True
            
        except Exception as e:
            self.application_error.emit(f"应用设置失败: {str(e)}")
            return False
    
    def _setup_log_handler(self) -> None:
        """设置日志处理器"""
        # 创建Qt日志处理器
        self._log_handler = QtLogHandler(level=logging.INFO)
        
        # 连接到主窗口的日志显示
        if self._main_window:
            self._log_handler.log_signal.connect(
                lambda msg, level: self._main_window.append_log(msg, level)
            )
        
        # 添加到根logger
        root_logger = logging.getLogger()
        root_logger.addHandler(self._log_handler)
        
    def _setup_connections(self) -> None:
        """设置信号槽连接"""
        if not self._main_window:
            return
        
        # === 设备页面信号连接 ===
        device_page = self._main_window.get_device_page()
        if device_page:
            # 设备连接请求 -> 业务逻辑
            device_page.connect_requested.connect(self._on_device_connect_requested)
            device_page.disconnect_requested.connect(self._on_device_disconnect_requested)
            device_page.scan_requested.connect(self._on_device_scan_requested)
            device_page.device_selected.connect(self._on_device_selected)
        
        # === 任务页面信号连接 ===
        task_page = self._main_window.get_task_page()
        if task_page:
            # 任务操作请求 -> 业务逻辑
            task_page.task_started.connect(self._on_task_started)
            task_page.task_stopped.connect(self._on_task_stopped)
            task_page.task_added.connect(self._on_task_added)
            task_page.task_deleted.connect(self._on_task_deleted)
            task_page.task_reordered.connect(self._on_task_reordered)
            task_page.start_execution_requested.connect(self._on_start_execution)
            task_page.stop_execution_requested.connect(self._on_stop_execution)
        
        # === 认证页面信号连接 ===
        auth_page = self._main_window.get_auth_page()
        if auth_page:
            # 认证请求 -> 业务逻辑
            auth_page.login_requested.connect(self._on_login_requested)
            auth_page.logout_requested.connect(self._on_logout_requested)
            auth_page.register_requested.connect(self._on_register_requested)
        
        # === 设置页面信号连接 ===
        settings_page = self._main_window.get_settings_page()
        if settings_page:
            # 设置变更 -> 业务逻辑
            settings_page.settings_changed.connect(self._on_settings_changed)
            settings_page.check_update_requested.connect(self._on_check_update)
            settings_page.touch_method_changed.connect(self._on_touch_method_changed)
        
        # === 云服务页面信号连接 ===
        cloud_page = self._main_window.get_cloud_page()
        if cloud_page:
            # 云服务请求 -> 业务逻辑
            cloud_page.refresh_requested.connect(self._on_refresh_cloud_info)
            cloud_page.sync_requested.connect(self._on_sync_requested)
        
        # === 主窗口信号连接 ===
        self._main_window.window_closed.connect(self._on_window_closed)
        
    def _on_device_connect_requested(self, device_serial: str) -> None:
        """处理设备连接请求"""
        try:
            if self._device_manager:
                success = self._device_manager.connect_device(device_serial)
                if success:
                    self._main_window.update_device_status(
                        f"已连接: {device_serial}", connected=True
                    )
                    self._main_window.append_log(
                        f"成功连接设备: {device_serial}", "INFO"
                    )
                else:
                    self._main_window.update_device_status(
                        "连接失败", connected=False
                    )
                    self._main_window.append_log(
                        f"连接设备失败: {device_serial}", "ERROR"
                    )
        except Exception as e:
            self._main_window.append_log(f"设备连接异常: {str(e)}", "ERROR")
    
    def _on_device_disconnect_requested(self) -> None:
        """处理设备断开请求"""
        try:
            if self._device_manager:
                self._device_manager.disconnect_device()
                self._main_window.update_device_status("未连接", connected=False)
                self._main_window.append_log("设备已断开", "INFO")
        except Exception as e:
            self._main_window.append_log(f"设备断开异常: {str(e)}", "ERROR")
    
    def _on_device_scan_requested(self) -> None:
        """处理设备扫描请求"""
        # 创建扫描工作线程
        worker = DeviceScanWorker(self._device_manager, self)
        worker.finished_signal.connect(self._on_device_scan_finished)
        worker.error_signal.connect(
            lambda err: self._main_window.append_log(err, "ERROR")
        )
        worker.progress_signal.connect(
            lambda pct, msg: self._main_window.append_log(msg, "INFO")
        )
        
        # 添加到线程列表并启动
        self._worker_threads.append(worker)
        worker.start()
    
    def _on_device_scan_finished(self, devices: list) -> None:
        """处理设备扫描完成"""
        self._main_window.update_devices(devices)
        self._main_window.append_log(f"发现 {len(devices)} 个设备", "INFO")
        
        # 清理完成的线程
        self._cleanup_finished_threads()
    
    def _on_device_selected(self, device_serial: str) -> None:
        """处理设备选择"""
        self._main_window.append_log(f"选择设备: {device_serial}", "INFO")
    
    def _on_task_started(self, task_id: str) -> None:
        """处理任务启动"""
        try:
            if self._execution_manager:
                self._execution_manager.start_task(task_id)
                self._main_window.update_task_status(task_id, is_running=True)
                self._main_window.append_log(f"启动任务: {task_id}", "INFO")
        except Exception as e:
            self._main_window.append_log(f"任务启动异常: {str(e)}", "ERROR")
    
    def _on_task_stopped(self, task_id: str) -> None:
        """处理任务停止"""
        try:
            if self._execution_manager:
                self._execution_manager.stop_task(task_id)
                self._main_window.update_task_status(task_id, is_running=False)
                self._main_window.append_log(f"停止任务: {task_id}", "INFO")
        except Exception as e:
            self._main_window.append_log(f"任务停止异常: {str(e)}", "ERROR")
    
    def _on_task_added(self, task_data: dict) -> None:
        """处理任务添加"""
        try:
            if self._task_queue_manager:
                self._task_queue_manager.add_task(task_data)
                self._main_window.append_log(f"添加任务: {task_data.get('name', '未知')}", "INFO")
        except Exception as e:
            self._main_window.append_log(f"任务添加异常: {str(e)}", "ERROR")
    
    def _on_task_deleted(self, task_id: str) -> None:
        """处理任务删除"""
        try:
            if self._task_queue_manager:
                self._task_queue_manager.remove_task(task_id)
                self._main_window.append_log(f"删除任务: {task_id}", "INFO")
        except Exception as e:
            self._main_window.append_log(f"任务删除异常: {str(e)}", "ERROR")
    
    def _on_task_reordered(self, task_ids: list) -> None:
        """处理任务重排序"""
        try:
            if self._task_queue_manager:
                self._task_queue_manager.reorder_tasks(task_ids)
                self._main_window.append_log("任务已重新排序", "INFO")
        except Exception as e:
            self._main_window.append_log(f"任务排序异常: {str(e)}", "ERROR")
    
    def _on_start_execution(self) -> None:
        """处理启动执行请求"""
        try:
            if self._execution_manager:
                self._execution_manager.start_execution()
                self._main_window.append_log("开始执行任务队列", "INFO")
                self._main_window.set_status("正在执行...")
        except Exception as e:
            self._main_window.append_log(f"启动执行异常: {str(e)}", "ERROR")
    
    def _on_stop_execution(self) -> None:
        """处理停止执行请求"""
        try:
            if self._execution_manager:
                self._execution_manager.stop_execution()
                self._main_window.append_log("停止执行", "INFO")
                self._main_window.set_status("就绪")
        except Exception as e:
            self._main_window.append_log(f"停止执行异常: {str(e)}", "ERROR")
    
    def _on_login_requested(self, username: str, password: str) -> None:
        """处理登录请求"""
        try:
            if self._auth_manager:
                success = self._auth_manager.login(username, password)
                if success:
                    user_info = self._auth_manager.get_user_info()
                    self._main_window.update_auth_status(True, user_info)
                    self._main_window.append_log(f"登录成功: {username}", "INFO")
                else:
                    self._main_window.update_auth_status(False)
                    self._main_window.append_log("登录失败", "ERROR")
        except Exception as e:
            self._main_window.append_log(f"登录异常: {str(e)}", "ERROR")
    
    def _on_logout_requested(self) -> None:
        """处理注销请求"""
        try:
            if self._auth_manager:
                self._auth_manager.logout()
                self._main_window.update_auth_status(False)
                self._main_window.append_log("已注销", "INFO")
        except Exception as e:
            self._main_window.append_log(f"注销异常: {str(e)}", "ERROR")
    
    def _on_register_requested(self, username: str) -> None:
        """处理注册请求"""
        try:
            if self._auth_manager:
                # 注册逻辑通常需要更多信息，这里只是示例
                self._main_window.append_log(f"注册请求: {username}", "INFO")
        except Exception as e:
            self._main_window.append_log(f"注册异常: {str(e)}", "ERROR")
    
    def _on_settings_changed(self, settings: dict) -> None:
        """处理设置变更"""
        try:
            # 更新配置
            if self._config:
                self._config.update(settings)
            self._main_window.append_log("设置已更新", "INFO")
        except Exception as e:
            self._main_window.append_log(f"设置变更异常: {str(e)}", "ERROR")
    
    def _on_check_update(self) -> None:
        """处理检查更新请求"""
        try:
            self._main_window.append_log("检查更新...", "INFO")
            # 实际的更新检查逻辑需要实现
        except Exception as e:
            self._main_window.append_log(f"检查更新异常: {str(e)}", "ERROR")
    
    def _on_touch_method_changed(self, method: str) -> None:
        """处理触控方式变更"""
        try:
            if self._config:
                touch_config = self._config.get('touch', {})
                touch_config['touch_method'] = method
                self._config['touch'] = touch_config
            self._main_window.append_log(f"触控方式已切换为: {method}", "INFO")
        except Exception as e:
            self._main_window.append_log(f"触控方式变更异常: {str(e)}", "ERROR")
    
    def _on_refresh_cloud_info(self) -> None:
        """处理刷新云服务信息请求"""
        try:
            if self._auth_manager and self._auth_manager.get_login_status():
                user_info = self._auth_manager.get_user_info()
                self._main_window.update_auth_status(True, user_info)
                self._main_window.append_log("用户信息已刷新", "INFO")
        except Exception as e:
            self._main_window.append_log(f"刷新信息异常: {str(e)}", "ERROR")
    
    def _on_sync_requested(self) -> None:
        """处理同步请求"""
        # 创建同步工作线程
        worker = TaskSyncWorker(self._task_queue_manager, self._communicator, self)
        worker.finished_signal.connect(self._on_sync_finished)
        worker.error_signal.connect(
            lambda err: self._main_window.append_log(err, "ERROR")
        )
        worker.progress_signal.connect(
            lambda pct, msg: self._main_window.append_log(msg, "INFO")
        )
        
        self._worker_threads.append(worker)
        worker.start()
    
    def _on_sync_finished(self, tasks: list) -> None:
        """处理同步完成"""
        self._main_window.update_tasks(tasks)
        self._main_window.append_log(f"同步完成，共 {len(tasks)} 个任务", "INFO")
        self._cleanup_finished_threads()
    
    def _on_window_closed(self) -> None:
        """处理窗口关闭"""
        self._cleanup()
    
    def _cleanup_finished_threads(self) -> None:
        """清理已完成的工作线程"""
        finished_threads = [
            t for t in self._worker_threads if t.isFinished()
        ]
        for thread in finished_threads:
            self._worker_threads.remove(thread)
            thread.deleteLater()
    
    def _cleanup(self) -> None:
        """清理资源"""
        # 停止所有工作线程
        for thread in self._worker_threads:
            if thread.isRunning():
                thread.cancel()
                thread.wait(1000)  # 等待最多1秒
        
        # 清理线程列表
        self._worker_threads.clear()
        
        # 移除日志处理器
        if self._log_handler:
            root_logger = logging.getLogger()
            root_logger.removeHandler(self._log_handler)
        
        # 断开连接
        if self._communicator:
            try:
                self._communicator.close()
            except Exception:
                pass
    
    def run(self) -> int:
        """
        运行应用
        
        Returns:
            应用退出代码
        """
        if not self._is_setup:
            if not self.setup():
                return 1
        
        # 显示主窗口
        if self._main_window:
            self._main_window.show()
        
        self._is_running = True
        self.application_ready.emit()
        
        # 运行事件循环
        return self._app.exec()
    
    def quit(self) -> None:
        """退出应用"""
        self._cleanup()
        if self._app:
            self._app.quit()
    
    def get_main_window(self) -> Optional[MainWindow]:
        """获取主窗口"""
        return self._main_window
    
    def get_app(self) -> Optional[QApplication]:
        """获取QApplication实例"""
        return self._app


def run_application(
    auth_manager: Optional[Any] = None,
    device_manager: Optional[Any] = None,
    execution_manager: Optional[Any] = None,
    task_queue_manager: Optional[Any] = None,
    communicator: Optional[Any] = None,
    config: Optional[Dict[str, Any]] = None
) -> int:
    """
    运行PyQt6应用
    
    这是应用的主入口函数，用于启动GUI
    
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
    # 创建应用实例
    app = PyQt6Application(
        auth_manager=auth_manager,
        device_manager=device_manager,
        execution_manager=execution_manager,
        task_queue_manager=task_queue_manager,
        communicator=communicator,
        config=config
    )
    
    # 运行应用
    return app.run()


def run_demo_application() -> int:
    """
    运行演示应用
    
    用于测试PyQt6界面框架，不连接业务逻辑
    """
    # 创建演示配置
    demo_config = {
        'touch': {
            'touch_method': 'maatouch'
        },
        'server': {
            'host': 'localhost',
            'port': 8080
        }
    }
    
    # 运行应用（不传入业务逻辑组件）
    return run_application(config=demo_config)


if __name__ == "__main__":
    # 直接运行此文件时启动演示应用
    sys.exit(run_demo_application())