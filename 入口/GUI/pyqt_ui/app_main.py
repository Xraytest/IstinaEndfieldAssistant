"""
PyQt6 应用入口
整合所有组件，实现与业务逻辑层的连接
"""

import sys
import os
import logging
import time
import json
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
    from .dialogs.local_inference_dialog import LocalInferenceDialog, show_local_inference_dialog
except ImportError:
    from main_window import MainWindow
    from theme.theme_manager import ThemeManager
    from widgets.log_display import LogDisplayWidget
    from dialogs.message_box import MessageBox
    from dialogs.confirm_dialog import ConfirmDialog
    from dialogs.local_inference_dialog import LocalInferenceDialog, show_local_inference_dialog

# 导入本地推理模块
try:
    from .....安卓相关.core.local_inference.inference_manager import InferenceManager
    from .....安卓相关.core.local_inference.gpu_checker import GPUChecker
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
    
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.inference_manager import InferenceManager
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.gpu_checker import GPUChecker


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
        self._is_shutting_down = False
        
    def emit(self, record: logging.LogRecord) -> None:
        """发送日志记录"""
        try:
            # 如果正在关闭，跳过日志处理
            if self._is_shutting_down:
                return
                
            # 检查QObject是否仍然有效
            if not self.isValid():
                return
                
            # 格式化日志消息
            message = self.format(record)
            level = record.levelname
            
            # 通过Qt信号发送（确保在主线程中处理）
            self.log_signal.emit(message, level)
        except Exception:
            self.handleError(record)
    
    def isValid(self) -> bool:
        """检查handler是否仍然有效"""
        try:
            # 尝试访问QObject的属性来验证对象是否有效
            _ = self.signalsBlocked()
            return not self._is_shutting_down
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            return False
    
    def shutdown(self) -> None:
        """关闭handler，标记为正在关闭状态"""
        self._is_shutting_down = True
        try:
            # 断开所有信号连接
            self.log_signal.disconnect()
        except (TypeError, RuntimeError):
            # 可能没有连接或已经断开
            pass


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
    # 线程安全的屏幕预览更新信号
    _preview_update_signal = pyqtSignal(bytes)
    
    def __init__(
        self,
        auth_manager: Optional[Any] = None,
        device_manager: Optional[Any] = None,
        execution_manager: Optional[Any] = None,
        task_queue_manager: Optional[Any] = None,
        communicator: Optional[Any] = None,
        screen_capture: Optional[Any] = None,
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
            screen_capture: 屏幕捕获器
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
        self._screen_capture = screen_capture
        self._config = config or {}
        
        # 本地推理管理器
        self._inference_manager: Optional[InferenceManager] = None
        
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

        # 连接内部预览更新信号到主窗口的更新方法（确保在主线程执行）
        self._preview_update_signal.connect(self._update_screen_preview)

        # === IEA页面信号连接（整合设备连接和任务链推理） ===
        iea_page = self._main_window.get_iea_page()
        if iea_page:
            # 设备相关信号
            iea_page.connect_requested.connect(self._on_device_connect_requested)
            iea_page.disconnect_requested.connect(self._on_device_disconnect_requested)
            iea_page.scan_requested.connect(self._on_device_scan_requested)
            iea_page.device_selected.connect(self._on_device_selected)
            # 截图请求信号
            self._main_window.screenshot_requested.connect(self._on_screenshot_requested)
            # 任务链相关信号
            iea_page.task_started.connect(self._on_task_started)
            iea_page.task_stopped.connect(self._on_task_stopped)
            iea_page.task_added.connect(self._on_task_added)
            iea_page.task_deleted.connect(self._on_task_deleted)
            iea_page.task_reordered.connect(self._on_task_reordered)
            iea_page.start_execution_requested.connect(self._on_start_execution)
            iea_page.stop_execution_requested.connect(self._on_stop_execution)

        # === 认证页面信号连接 ===
        auth_page = self._main_window.get_auth_page()
        if auth_page:
            # 认证请求 -> 业务逻辑
            auth_page.login_requested.connect(self._on_login_requested)

            auth_page.register_requested.connect(self._on_register_requested)
            auth_page.arkpass_selected.connect(self._on_arkpass_login_requested)
        
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
                    # [AutoFix 2026-04-18] 更新设备状态并启动预览自动刷新
                    # 构建设备信息字典
                    device_info = {
                        'serial': device_serial,
                        'method': 'android'  # 默认Android模式
                    }
                    # 尝试获取更多信息
                    if hasattr(self._device_manager, 'get_device_info'):
                        try:
                            info = self._device_manager.get_device_info(device_serial)
                            if info:
                                device_info.update(info)
                        except:
                            pass
                    
                    self._main_window.update_device_status(
                        f"已连接: {device_serial}", connected=True, device_info=device_info
                    )
                    self._main_window.append_log(
                        f"成功连接设备: {device_serial}", "INFO"
                    )
                    # [AutoFix 2026-04-18] 移除重复启动自动刷新调用
                    # 自动刷新已在 update_device_status -> set_connected -> set_device_status 内部启动
                    # self._main_window.start_preview_refresh()
                    # self._main_window.append_log("设备预览自动刷新已启动", "INFO")
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
                # [AutoFix 2026-04-18] 停止预览自动刷新
                self._main_window.stop_preview_refresh()
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
        # 转换为字典列表格式
        device_list = [{'serial': d} if isinstance(d, str) else d for d in devices]
        self._main_window.update_device_list(device_list)
        self._main_window.append_log(f"发现 {len(devices)} 个设备", "INFO")
        
        # 清理完成的线程
        self._cleanup_finished_threads()
    
    def _on_device_selected(self, device_serial: str) -> None:
        """处理设备选择"""
        self._main_window.append_log(f"选择设备: {device_serial}", "INFO")
    
    def _on_screenshot_requested(self) -> None:
        """处理截图请求 [AutoFix 2026-04-18]"""
        # 在工作线程中执行截图，避免阻塞UI
        try:
            if not self._device_manager:
                return
            
            current_device = self._device_manager.get_current_device()
            if not current_device:
                return
            
            # 使用screen_capture获取截图
            if self._screen_capture:
                # 在新线程中执行截图
                import threading
                import logging
                logger = logging.getLogger(__name__)
                
                def capture_and_update():
                    try:
                        image_data = self._screen_capture.capture_screen(current_device)
                        if image_data:
                            # 通过信号在主线程更新UI
                            self._preview_update_signal.emit(image_data)
                    except Exception as e:
                        logger.error(f"截图失败: {e}")
                
                thread = threading.Thread(target=capture_and_update, daemon=True)
                thread.start()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"截图请求处理失败: {e}")
    
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
    
    def _update_screen_preview(self, image_data: bytes) -> None:
        """
        在主线程中更新屏幕预览
        
        Args:
            image_data: 图像数据
        """
        if self._main_window:
            self._main_window.update_screen_preview(image_data)
    
    def _on_start_execution(self) -> None:
        """处理启动执行请求"""
        try:
            if self._execution_manager:
                # 定义回调函数
                def log_callback(message, category, level):
                    self._main_window.append_log(message, level)
                
                def update_ui_callback(key, value):
                    # 更新UI状态
                    pass
                
                def preview_update_callback(image_data):
                    # 通过信号机制在主线程中更新屏幕预览
                    # 这确保UI更新在主线程执行，避免线程安全问题
                    self._preview_update_signal.emit(image_data)
                
                success, message = self._execution_manager.start_execution(
                    log_callback=log_callback,
                    update_ui_callback=update_ui_callback,
                    preview_update_callback=preview_update_callback
                )
                
                if success:
                    self._main_window.append_log(message, "INFO")
                    self._main_window.set_status("正在执行...")
                else:
                    self._main_window.append_log(message, "ERROR")
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
        """处理登录请求（保留以兼容旧接口）"""
        # 当前版本仅支持ArkPass登录，此方法保留以兼容
        self._main_window.append_log("请使用ArkPass文件进行登录", "WARNING")

    def _on_arkpass_login_requested(self, arkpass_path: str) -> None:
        """处理ArkPass登录请求"""
        try:
            if self._auth_manager:
                # 检查auth_manager是否支持ArkPass登录
                if hasattr(self._auth_manager, 'login_with_arkpass'):
                    result = self._auth_manager.login_with_arkpass(arkpass_path)
                    # 处理返回结果（可能是布尔值或元组）
                    if isinstance(result, tuple):
                        success = result[0]
                        error_msg = result[1] if len(result) > 1 else "登录失败"
                        error_type = result[2] if len(result) > 2 else None
                    else:
                        success = result
                        error_msg = "登录失败"
                        error_type = None
                elif hasattr(self._auth_manager, 'login'):
                    # 回退到普通登录，传入文件路径作为密码
                    success = self._auth_manager.login(arkpass_path, arkpass_path)
                    error_msg = "登录失败"
                    error_type = None
                else:
                    self._main_window.append_log("认证管理器未配置", "ERROR")
                    return

                if success:
                    user_info = self._auth_manager.get_user_info()
                    self._main_window.update_auth_status(True, user_info)
                    self._main_window.append_log(f"ArkPass登录成功", "INFO")
                else:
                    self._main_window.update_auth_status(False)
                    self._main_window.append_log(f"ArkPass登录失败: {error_msg}", "ERROR")

                    # 如果是无效凭证错误，删除缓存文件
                    if error_type in ['user_not_found', 'invalid_api_key']:
                        try:
                            import os
                            if os.path.exists(arkpass_path):
                                os.remove(arkpass_path)
                                self._main_window.append_log(f"已删除无效的ArkPass缓存文件", "WARNING")
                        except Exception as e:
                            self._main_window.append_log(f"删除缓存文件失败: {e}", "WARNING")
            else:
                self._main_window.append_log("认证管理器未初始化", "ERROR")
                self._main_window.update_auth_status(False)
        except Exception as e:
            self._main_window.append_log(f"登录异常: {str(e)}", "ERROR")
            self._main_window.update_auth_status(False)
    
    def _on_logout_requested(self) -> None:
        """处理注销请求（已禁用）"""
        pass  # 注销功能已禁用

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
        # 首先关闭日志处理器（防止后续代码产生日志时访问已删除的对象）
        if self._log_handler:
            try:
                # 标记为关闭状态并断开信号
                self._log_handler.shutdown()
                # 从root logger中移除
                root_logger = logging.getLogger()
                root_logger.removeHandler(self._log_handler)
            except Exception:
                pass
            finally:
                self._log_handler = None
        
        # 停止所有工作线程
        for thread in self._worker_threads:
            if thread.isRunning():
                thread.cancel()
                thread.wait(1000)  # 等待最多1秒
        
        # 清理线程列表
        self._worker_threads.clear()
        
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
            try:
                if not self._is_setup:
                    if not self.setup():
                        return 1
                
                # 显示主窗口
                if self._main_window:
                    self._main_window.show()
                
                self._is_running = True
                self.application_ready.emit()
    
                # 尝试自动登录（使用缓存的ArkPass文件）
                self._try_auto_login()
    
                # 尝试自动连接上次连接的设备
                self._try_auto_connect_device()
                
                # 尝试注册客户端并获取/选择模型
                self._try_register_client_and_select_model()
                
                # 尝试初始化本地推理（在客户端注册完成后）
                self._try_initialize_local_inference()
    
                # 运行事件循环
                return self._app.exec()
            except Exception as e:
                error_msg = f"应用运行异常: {str(e)}"
                if self._main_window:
                    self._main_window.append_log(error_msg, "ERROR")
                else:
                    print(error_msg)
                return 1
    
    def _try_auto_login(self) -> None:
        """尝试使用缓存的ArkPass文件自动登录"""
        try:
            if self._auth_manager and self._main_window:
                # 通过auth_page尝试自动登录
                auth_page = self._main_window.get_auth_page()
                if auth_page:
                    # 尝试自动登录
                    auto_login_initiated = auth_page.try_auto_login()
                    if auto_login_initiated:
                        self._main_window.append_log("正在使用缓存的ArkPass文件自动登录...", "INFO")
                    else:
                        self._main_window.append_log("未找到缓存的ArkPass文件，请手动选择文件登录", "INFO")
        except Exception as e:
            if self._main_window:
                self._main_window.append_log(f"自动登录检查异常: {str(e)}", "WARNING")

    def _try_auto_connect_device(self) -> None:
        """尝试自动连接上次连接的设备"""
        try:
            if self._device_manager and self._main_window:
                # 获取上次连接的设备
                last_device = None
                if hasattr(self._device_manager, 'get_last_connected_device'):
                    last_device = self._device_manager.get_last_connected_device()

                if last_device:
                    self._main_window.append_log(
                        f"尝试自动连接上次设备: {last_device}", "INFO"
                    )

                    # 先扫描设备列表
                    devices = []
                    if hasattr(self._device_manager, 'scan_devices'):
                        devices = self._device_manager.scan_devices()

                    # 更新设备列表显示
                    self._main_window.update_device_list(devices)

                    # 检查上次连接的设备是否在列表中
                    device_serials = [d.get('serial') for d in devices if isinstance(d, dict)]

                    if last_device in device_serials:
                        self._main_window.append_log(
                            f"设备 {last_device} 在列表中，尝试连接...", "INFO"
                        )
                    else:
                        self._main_window.append_log(
                            f"设备 {last_device} 不在当前设备列表中，但仍尝试连接...", "INFO"
                        )

                    # 不管设备是否在列表中，都尝试连接
                    success = self._device_manager.connect_device(last_device)
                    if success:
                        # [AutoFix 2026-04-18] 统一自动连接和手动连接逻辑：获取完整设备信息
                        device_info = {
                            'serial': last_device,
                            'method': 'android'
                        }
                        # 尝试获取更多信息（与手动连接保持一致）
                        if hasattr(self._device_manager, 'get_device_info'):
                            try:
                                info = self._device_manager.get_device_info(last_device)
                                if info:
                                    device_info.update(info)
                            except:
                                pass
                        self._main_window.update_device_status(
                            f"已连接: {last_device}", connected=True, device_info=device_info
                        )
                        self._main_window.append_log(
                            f"自动连接成功: {last_device}", "INFO"
                        )
                    else:
                        self._main_window.append_log(
                            f"自动连接失败: {last_device}", "WARNING"
                        )
                else:
                    # 没有上次连接的设备，仅扫描并显示设备列表
                    self._main_window.append_log("扫描可用设备...", "INFO")
                    if hasattr(self._device_manager, 'scan_devices'):
                        devices = self._device_manager.scan_devices()
                        self._main_window.update_device_list(devices)
                        self._main_window.append_log(
                            f"发现 {len(devices)} 个设备", "INFO"
                        )
            elif self._main_window:
                # 无设备管理器，跳过自动连接
                self._main_window.append_log(
                    "自动连接已跳过 (无设备管理器)", "INFO"
                )
        except Exception as e:
            if self._main_window:
                self._main_window.append_log(f"自动连接设备异常: {str(e)}", "ERROR")
    
    def _try_register_client_and_select_model(self) -> None:
        """尝试注册客户端并获取/选择模型"""
        try:
            if self._communicator and self._main_window:
                # 获取客户端配置
                client_config = self._config.get('client', {})
                model_config = self._config.get('model', {})
                
                client_name = client_config.get('client_name', 'IEA_Client')
                preferred_model = model_config.get('selected_model', '')
                auto_select = model_config.get('auto_select', True)
                
                # 1. 注册客户端
                self._main_window.append_log("正在注册客户端到服务器...", "INFO")
                register_response = self._communicator.register_client(
                    client_name=client_name,
                    preferred_model=preferred_model if not auto_select else None
                )
                
                if register_response and register_response.get('status') == 'success':
                    client_id = register_response.get('client_id')
                    assigned_model = register_response.get('assigned_model', '')
                    
                    # 更新配置
                    self._config['client']['client_id'] = client_id
                    self._config['client']['registered'] = True
                    
                    self._main_window.append_log(
                        f"客户端注册成功，ID: {client_id[:8]}...", "INFO"
                    )
                    
                    # 2. 获取可用模型列表
                    self._main_window.append_log("正在获取可用模型列表...", "INFO")
                    models_response = self._communicator.get_available_models(
                        session_id=client_id
                    )
                    
                    if models_response and models_response.get('status') == 'success':
                        models = models_response.get('models', [])
                        default_model = models_response.get('default_model', '')
                        
                        # 更新设置页面的模型列表
                        settings_page = self._main_window.get_settings_page()
                        if settings_page:
                            settings_page.update_available_models(models, default_model)
                        
                        # 3. 选择模型
                        selected_model = ""
                        if auto_select:
                            # 自动选择：优先使用服务器分配的模型，其次是服务器默认模型
                            if assigned_model:
                                selected_model = assigned_model
                                self._main_window.append_log(
                                    f"自动选择服务器分配的模型: {selected_model}", "INFO"
                                )
                            elif default_model:
                                selected_model = default_model
                                self._main_window.append_log(
                                    f"自动选择服务器默认模型: {selected_model}", "INFO"
                                )
                            elif models:
                                # 选择第一个可用模型
                                selected_model = models[0].get('name', '')
                                self._main_window.append_log(
                                    f"自动选择第一个可用模型: {selected_model}", "INFO"
                                )
                        else:
                            # 手动选择：使用用户配置的模型
                            if preferred_model:
                                # 检查配置的模型是否在可用列表中
                                available_model_names = [m.get('name') for m in models]
                                if preferred_model in available_model_names:
                                    selected_model = preferred_model
                                    self._main_window.append_log(
                                        f"使用配置的模型: {selected_model}", "INFO"
                                    )
                                else:
                                    self._main_window.append_log(
                                        f"配置的模型 {preferred_model} 不可用，将自动选择", "WARNING"
                                    )
                                    if default_model:
                                        selected_model = default_model
                                    elif models:
                                        selected_model = models[0].get('name', '')
                            else:
                                # 没有配置模型，使用默认
                                if default_model:
                                    selected_model = default_model
                                elif models:
                                    selected_model = models[0].get('name', '')
                        
                        # 更新配置
                        if selected_model:
                            self._config['model']['selected_model'] = selected_model
                            self._config['model']['available_models'] = models
                            self._config['model']['last_updated'] = int(time.time())
                            
                            # 更新设置页面显示
                            if settings_page:
                                settings_page.set_auto_select(auto_select)
                                if not auto_select:
                                    settings_page._current_model_display.setText(selected_model)
                                else:
                                    settings_page._current_model_display.setText(
                                        f"自动选择 ({selected_model})"
                                    )
                            
                            self._main_window.append_log(
                                f"模型选择完成: {selected_model}", "INFO"
                            )
                        else:
                            self._main_window.append_log(
                                "没有可用的模型，请检查服务器配置", "WARNING"
                            )
                    else:
                        error_msg = models_response.get('message', '未知错误') if models_response else '无响应'
                        self._main_window.append_log(
                            f"获取模型列表失败: {error_msg}", "WARNING"
                        )
                else:
                    error_msg = register_response.get('message', '未知错误') if register_response else '无响应'
                    self._main_window.append_log(
                        f"客户端注册失败: {error_msg}", "WARNING"
                    )
            elif self._main_window:
                self._main_window.append_log(
                    "跳过客户端注册 (无通信器)", "INFO"
                )
        except Exception as e:
            if self._main_window:
                self._main_window.append_log(f"客户端注册/模型选择异常: {str(e)}", "ERROR")
    
    def _try_initialize_local_inference(self) -> None:
            """尝试初始化本地推理"""
            try:
                if not self._main_window:
                    return
                
                self._main_window.append_log("正在检查本地推理支持...", "INFO")
                
                # 创建推理管理器
                self._inference_manager = InferenceManager(
                    config=self._config,
                    communicator=self._communicator
                )
                
                # 检查是否需要显示首次询问对话框
                first_run_config = self._config.get("first_run", {})
                prompt_shown = first_run_config.get("local_inference_prompt_shown", False)
                
                if not prompt_shown:
                    # 首次运行，显示询问对话框
                    if self._inference_manager.should_prompt_for_local_inference():
                        self._main_window.append_log("显示本地推理配置对话框...", "INFO")
                        
                        try:
                            user_choice, gpu_info, selected_model = show_local_inference_dialog(
                                parent=self._main_window,
                                config=self._config
                            )
                        except Exception as dialog_error:
                            self._main_window.append_log(f"本地推理对话框异常: {str(dialog_error)}", "ERROR")
                            user_choice = None
                            gpu_info = None
                            selected_model = None
                        
                        if user_choice == "cancel":
                            self._main_window.append_log("用户取消了本地推理配置，继续使用云端推理", "INFO")
                            # 标记首次运行完成，避免重复提示
                            self._config["first_run"]["local_inference_prompt_shown"] = True
                            self._save_config()
                            # 继续执行，不返回
                        elif user_choice and gpu_info:
                            # 保存GPU信息
                            self._config["gpu"] = {
                                "checked": True,
                                "cuda_available": gpu_info.get("cuda_available", False),
                                "cuda_version": gpu_info.get("cuda_version", ""),
                                "driver_version": gpu_info.get("driver_version", ""),
                                "gpu_count": gpu_info.get("gpu_count", 0),
                                "gpus": gpu_info.get("gpus", []),
                                "meets_requirements": gpu_info.get("meets_requirements", False),
                                "recommended_model": gpu_info.get("recommended_model")
                            }
                            
                            # 标记首次运行完成
                            self._config["first_run"]["local_inference_prompt_shown"] = True
                            self._config["first_run"]["user_choice"] = user_choice
                            
                            # 保存配置到文件
                            self._save_config()
                            
                            if user_choice == "local" and selected_model:
                                self._config["inference"]["local"]["enabled"] = True
                                self._config["inference"]["local"]["model_name"] = selected_model
                                self._main_window.append_log(
                                    f"用户选择本地推理，模型: {selected_model}", "INFO"
                                )
                            else:
                                self._config["inference"]["local"]["enabled"] = False
                                self._main_window.append_log("用户选择云端推理", "INFO")
                            
                            # 重新加载配置到推理管理器
                            self._inference_manager = InferenceManager(
                                config=self._config,
                                communicator=self._communicator
                            )
                
                # 初始化推理管理器
                if self._inference_manager.initialize():
                    stats = self._inference_manager.get_stats()
                    mode = stats.get("effective_mode", "unknown")
                    
                    if mode == "local":
                        self._main_window.append_log(
                            f"本地推理已启用，模型: {stats.get('config', {}).get('model_name', 'unknown')}",
                            "INFO"
                        )
                    else:
                        self._main_window.append_log("使用云端推理模式", "INFO")
                else:
                    self._main_window.append_log("本地推理初始化失败，将使用云端推理", "WARNING")
                    
            except Exception as e:
                error_msg = f"本地推理初始化异常: {str(e)}"
                if self._main_window:
                    self._main_window.append_log(error_msg, "ERROR")
                else:
                    print(error_msg)
    
    def _save_config(self) -> None:
            """保存配置到文件"""
            try:
                config_path = os.path.join(
                    os.path.dirname(__file__), "..", "..", "config", "client_config.json"
                )
                config_path = os.path.abspath(config_path)
                
                # 确保配置目录存在
                config_dir = os.path.dirname(config_path)
                if not os.path.exists(config_dir):
                    os.makedirs(config_dir, exist_ok=True)
                    if self._main_window:
                        self._main_window.append_log(f"创建配置目录: {config_dir}", "DEBUG")
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(self._config, f, indent=2, ensure_ascii=False)
                
                if self._main_window:
                    self._main_window.append_log("配置已保存", "DEBUG")
            except Exception as e:
                error_msg = f"保存配置失败: {str(e)}"
                if self._main_window:
                    self._main_window.append_log(error_msg, "WARNING")
                else:
                    print(error_msg)
    
    def get_inference_manager(self) -> Optional[InferenceManager]:
        """获取推理管理器"""
        return self._inference_manager
    
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
    screen_capture: Optional[Any] = None,
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
        screen_capture: 屏幕捕获器
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
        screen_capture=screen_capture,
        config=config
    )
    
    # 运行应用
    return app.run()


if __name__ == "__main__":
    # 直接运行此文件时需要传入业务逻辑组件
    # 示例：sys.exit(run_application(auth_manager=..., device_manager=...))
    print("请通过 client_main_pyqt6.py 启动应用，或传入业务逻辑组件")
    sys.exit(1)