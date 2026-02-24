"""
ReAcrture 客户端GUI
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
import os
import json
import base64
from datetime import datetime
from PIL import Image, ImageTk
import io
import sys

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from logger import init_logger, get_logger, LogCategory, LogLevel
from adb_manager import ADBDeviceManager
from screen_capture import ScreenCapture
from touch_executor import TouchExecutor
from task_manager import TaskManager
from communicator import ClientCommunicator
from components.auth_manager import AuthManager
from components.device_manager import DeviceManager
from components.execution_manager import ExecutionManager
from components.task_queue_manager import TaskQueueManager
from managers.main_gui_manager import MainGUIManager
from managers.auth_manager_gui import AuthManagerGUI


class ReAcrtureClientGUI:
    """ReAcrture客户端GUI主类"""
    
    def __init__(self, root):
        self.root = root
        self.latest_version = None  # 存储最新版本号
        # 将gui_manager引用添加到root，便于其他组件访问
        self.root.gui_manager = None
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # 初始化日志系统
        log_config_path = os.path.join(os.path.dirname(__file__), "config/logging_config.json")
        init_logger(log_config_path)
        self.logger = get_logger()
        self.logger.info(LogCategory.MAIN, "程序启动",
                        working_dir=os.path.dirname(os.path.abspath(__file__)))
        
        # 状态变量
        self.client_running = False
        self.start_time = time.time()
        
        # 初始化组件
        self.adb_manager = None
        self.screen_capture = None
        self.touch_executor = None
        self.task_manager = None
        self.communicator = None
        self.auth_manager = None
        self.device_manager = None
        self.task_queue_manager = None
        self.execution_manager = None
        self.gui_manager = None
        
        # 加载配置
        self.config = self._load_config("config/client_config.json")
        self.logger.debug(LogCategory.MAIN, "配置文件加载完成")
        
        # 创建UI样式
        self.setup_styles()
        
        # 初始化核心组件
        self.init_components()
        
        # 检查登录状态
        self.check_login_status()
        
        # 启动时检查更新
        self.root.after(1000, self.check_for_updates_on_startup)
        
    def setup_styles(self):
        """设置UI样式"""
        style = ttk.Style()
        style.configure('Action.TButton', font=('Arial', 10, 'bold'))
        style.configure('Security.TButton', font=('Arial', 10, 'bold'), foreground='green')
        style.configure('Stop.TButton', font=('Arial', 10, 'bold'), foreground='red')
        style.configure('Status.TLabel', font=('Arial', 9))
        style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        
    def _load_config(self, config_file):
        """加载配置文件"""
        config_path = os.path.join(os.path.dirname(__file__), config_file)
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.logger.debug(LogCategory.MAIN, "配置文件加载", config_path=config_path)
                return json.load(f)
        else:
            self.logger.warning(LogCategory.MAIN, "配置文件不存在，使用默认配置", config_path=config_path)
            return {
                "server": {"host": "127.0.0.1", "port": 9999},
                "adb": {"path": "3rd-part/ADB/adb.exe", "timeout": 10},
                "git": {"path": "3rd-part/Git/bin/git.exe"},
                "screen": {"quality": 80, "max_size": 1024},
                "security": {"press_duration_ms": 100, "press_jitter_px": 2},
                "communication": {"password": "default_password"}
            }
            
    def init_components(self):
        """初始化所有组件"""
        self.logger.info(LogCategory.MAIN, "开始初始化组件")
        
        try:
            # 初始化核心功能模块
            script_dir = os.path.dirname(os.path.abspath(__file__))
            adb_path = os.path.join(script_dir, self.config['adb']['path'])
            
            if not os.path.exists(adb_path):
                self.logger.exception(LogCategory.MAIN, "ADB可执行文件不存在", adb_path=adb_path)
                raise FileNotFoundError(f"ADB executable not found at: {adb_path}")
            
            self.logger.debug(LogCategory.MAIN, "初始化ADB设备管理器", adb_path=adb_path)
            self.adb_manager = ADBDeviceManager(
                adb_path=adb_path,
                timeout=self.config['adb']['timeout']
            )
            
            self.logger.debug(LogCategory.MAIN, "初始化屏幕捕获模块")
            self.screen_capture = ScreenCapture(
                adb_manager=self.adb_manager,
                quality=self.config['screen']['quality'],
                max_size=self.config['screen']['max_size']
            )
            
            self.logger.debug(LogCategory.MAIN, "初始化触控执行模块")
            self.touch_executor = TouchExecutor(
                adb_manager=self.adb_manager,
                press_duration_ms=self.config['security']['press_duration_ms'],
                press_jitter_px=self.config['security']['press_jitter_px']
            )
            
            self.logger.debug(LogCategory.MAIN, "初始化任务管理模块")
            self.task_manager = TaskManager(
                config_dir=os.path.join(os.path.dirname(__file__), "config"),
                data_dir=os.path.join(os.path.dirname(__file__), "data")
            )
            
            self.logger.debug(LogCategory.MAIN, "初始化通信模块")
            self.communicator = ClientCommunicator(
                host=self.config['server']['host'],
                port=self.config['server']['port'],
                password=self.config.get('communication', {}).get('password', 'default_password'),
                timeout=300
            )
            
            # 初始化业务逻辑组件
            self.logger.debug(LogCategory.MAIN, "初始化认证管理模块")
            self.auth_manager = AuthManager(self.communicator, self.config)
            
            self.logger.debug(LogCategory.MAIN, "初始化设备管理模块")
            self.device_manager = DeviceManager(self.adb_manager, self.config)
            
            self.logger.debug(LogCategory.MAIN, "初始化任务队列管理模块")
            self.task_queue_manager = TaskQueueManager(self.task_manager)
            
            # 加载任务队列缓存
            self.load_task_queue()
            
            self.logger.debug(LogCategory.MAIN, "初始化执行管理模块")
            self.execution_manager = ExecutionManager(
                self.device_manager,
                self.screen_capture,
                self.touch_executor,
                self.task_queue_manager,
                self.communicator,
                self.auth_manager
            )
            
            # 初始化GUI管理器
            self.logger.debug(LogCategory.MAIN, "初始化GUI管理器")
            self.gui_manager = MainGUIManager(
                self.root,
                self.auth_manager,
                self.device_manager,
                self.execution_manager,
                self.task_queue_manager,
                self.config,
                self.log_message,
                self  # 传递自身引用以便更新标题
            )
            # 将gui_manager引用添加到root，便于其他组件访问
            self.root.gui_manager = self.gui_manager
            
            # 设置GUI日志处理器
            if hasattr(self.gui_manager, 'log_text'):
                get_logger().set_gui_handler(self.gui_manager.log_text)
            
            self.logger.info(LogCategory.MAIN, "所有组件初始化完成")
            self.log_message("所有组件初始化成功", "system", "INFO")
            
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "组件初始化异常", exc_info=True)
            self.log_message(f"组件初始化失败: {e}", "system", "ERROR")
            messagebox.showerror("初始化错误", f"组件初始化失败: {e}")
            
    def check_for_updates_on_startup(self):
        """启动时检查更新并显示提示"""
        self.logger.debug(LogCategory.MAIN, "启动时检查更新")
        try:
            current_version = self.load_local_version()
            self.update_window_title(current_version)
            # 这里会由SettingsManagerGUI自动处理更新检查
            self.logger.debug(LogCategory.MAIN, "版本检查完成", current_version=current_version)
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "启动时检查更新异常", exc_info=True)
            self.log_message(f"启动时检查更新失败: {e}", "version", "ERROR")
            
    def update_window_title(self, current_version=None):
        """更新窗口标题"""
        if current_version is None:
            current_version = self.load_local_version()
        
        title = f"IstinaEndfieldArknights - {current_version}"
        if self.latest_version and self.latest_version != current_version:
            title += f" <发现新版本：{self.latest_version}>"
        self.root.title(title)
        
    def set_latest_version(self, latest_version):
        """设置最新版本号并更新标题"""
        self.latest_version = latest_version
        current_version = self.load_local_version()
        self.update_window_title(current_version)
        
    def load_local_version(self):
        """加载本地版本信息"""
        try:
            ver_file = os.path.join(os.path.dirname(__file__), "data", "ver.json")
            if os.path.exists(ver_file):
                with open(ver_file, 'r', encoding='utf-8') as f:
                    ver_data = json.load(f)
                version = ver_data.get('version', 'unknown')
                self.logger.debug(LogCategory.MAIN, "本地版本加载完成", version=version)
                return version
            else:
                # 如果文件不存在，创建默认版本文件
                ver_data = {'version': 'alpha_0.0.1'}
                os.makedirs(os.path.dirname(ver_file), exist_ok=True)
                with open(ver_file, 'w', encoding='utf-8') as f:
                    json.dump(ver_data, f, indent=2)
                self.logger.debug(LogCategory.MAIN, "创建默认版本文件", version='alpha_0.0.1')
                return 'alpha_0.0.1'
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "加载本地版本异常", exc_info=True)
            self.log_message(f"加载本地版本失败: {e}", "version", "ERROR")
            return "unknown"
            
    def check_login_status(self):
        """检查登录状态"""
        self.logger.debug(LogCategory.MAIN, "检查登录状态")
        # 首先检查业务逻辑层的登录状态
        if self.auth_manager.check_login_status():
            # 如果已登录，直接更新UI
            self.logger.debug(LogCategory.MAIN, "已登录状态")
            self.on_login_success()
        else:
            # 如果未登录，显示登录对话框
            self.logger.debug(LogCategory.MAIN, "未登录状态，显示登录对话框")
            auth_gui = AuthManagerGUI(
                self.root,
                self.auth_manager,
                on_login_success=self.on_login_success
            )
            self.auth_gui = auth_gui
            self.auth_gui.show_login_or_register_dialog()
        
    def on_login_success(self):
        """登录成功回调"""
        self.logger.info(LogCategory.AUTHENTICATION, "登录成功")
        # 更新云服务页面的用户信息显示
        if hasattr(self.gui_manager, 'cloud_service_gui'):
            self.gui_manager.cloud_service_gui.update_user_info_display()
            
    def load_task_queue(self):
        """加载任务队列"""
        self.logger.debug(LogCategory.MAIN, "加载任务队列")
        # 从本地文件加载持久化的任务队列
        cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        task_queue_file = os.path.join(cache_dir, "task_queue.json")
        
        if os.path.exists(task_queue_file):
            try:
                with open(task_queue_file, 'r', encoding='utf-8') as f:
                    task_queue = json.load(f)
                    for task in task_queue:
                        self.task_queue_manager.add_task(task)
                self.logger.info(LogCategory.MAIN, "任务队列加载完成", task_count=len(task_queue))
                self.log_message("已从本地加载任务队列", "task", "INFO")
            except Exception as e:
                self.logger.exception(LogCategory.MAIN, "任务队列加载异常", exc_info=True)
                self.log_message(f"加载任务队列失败: {e}", "task", "ERROR")
        else:
            self.logger.debug(LogCategory.MAIN, "任务队列文件不存在", task_queue_file=task_queue_file)
                
    def log_message(self, message, category="general", level="INFO"):
        """记录日志消息（兼容旧接口）"""
        # 映射旧的category到新的LogCategory
        category_map = {
            "system": LogCategory.MAIN,
            "adb": LogCategory.ADB,
            "communication": LogCategory.COMMUNICATION,
            "execution": LogCategory.EXECUTION,
            "auth": LogCategory.AUTHENTICATION,
            "task": LogCategory.EXECUTION,
            "version": LogCategory.MAIN,
            "general": LogCategory.MAIN
        }
        
        # 映射旧的level到新的LogLevel
        level_map = {
            "DEBUG": LogLevel.DEBUG,
            "INFO": LogLevel.INFO,
            "WARNING": LogLevel.WARNING,
            "ERROR": LogLevel.EXCEPTION,
            "CRITICAL": LogLevel.CRITICAL
        }
        
        log_category = category_map.get(category, LogCategory.MAIN)
        log_level = level_map.get(level, LogLevel.INFO)
        
        # 使用新的日志系统
        self.logger.log(log_level, log_category, message)
        
        # 更新日志文本控件（如果GUI管理器已初始化）
        if self.gui_manager is not None:
            # 更新状态栏
            if hasattr(self.gui_manager, 'status_bar'):
                self.gui_manager.status_bar.config(text=message)
    
    def on_closing(self):
        """窗口关闭事件"""
        self.logger.info(LogCategory.MAIN, "程序关闭请求")
        
        # 保存任务队列到本地
        self.task_queue_manager.save_task_queue()
        self.logger.debug(LogCategory.MAIN, "任务队列已保存")
        
        # 准确检测实际执行状态
        execution_running = False
        if hasattr(self, 'execution_manager') and self.execution_manager:
            execution_running = self.execution_manager.is_running()
        
        if execution_running:
            self.logger.warning(LogCategory.MAIN, "执行正在进行中")
            if messagebox.askokcancel("确认", "执行正在进行中，确定要退出吗？"):
                # 停止执行
                self.execution_manager.stop_execution()
                self.logger.debug(LogCategory.MAIN, "执行已停止")
                
                # 等待执行线程完全结束（最多5秒）
                max_wait_time = 5.0
                wait_interval = 0.1
                total_waited = 0.0
                
                while total_waited < max_wait_time:
                    if not self.execution_manager.is_running():
                        break
                    time.sleep(wait_interval)
                    total_waited += wait_interval
                    
                if self.execution_manager.is_running():
                    self.logger.warning(LogCategory.MAIN, "执行线程未在预期时间内结束")
                    self.log_message("警告: 执行线程未在预期时间内结束", "system", "WARNING")
                    
                # 安全关闭
                run_duration = (time.time() - self.start_time) * 1000
                self.logger.info(LogCategory.MAIN, "程序关闭", run_duration_ms=round(run_duration, 3))
                self.root.destroy()
        else:
            run_duration = (time.time() - self.start_time) * 1000
            self.logger.info(LogCategory.MAIN, "程序关闭", run_duration_ms=round(run_duration, 3))
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ReAcrtureClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    try:
        root.mainloop()
    except Exception as e:
        if hasattr(app, 'logger'):
            app.logger.exception(LogCategory.MAIN, "程序异常", exc_info=True)
        raise