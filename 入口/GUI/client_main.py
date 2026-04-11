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

# 添加安卓相关目录到Python路径
import sys
import os
istina_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
安卓相关_dir = os.path.join(istina_root, "安卓相关")
入口_dir = os.path.join(istina_root, "入口")
if 安卓相关_dir not in sys.path:
    sys.path.insert(0, 安卓相关_dir)
if 入口_dir not in sys.path:
    sys.path.insert(0, 入口_dir)

from core.logger import init_logger, get_logger, LogCategory, LogLevel
from 控制.adb_manager import ADBDeviceManager
from 图像传递.screen_capture import ScreenCapture
from 控制.touch import TouchManager, TouchDeviceType
from 控制.touch.maafw_touch_adapter import MaaFwTouchExecutor, MaaFwTouchConfig
from 控制.touch.maafw_win32_adapter import MaaFwWin32Executor, MaaFwWin32Config
from core.cloud.task_manager import TaskManager
from core.communication.communicator import ClientCommunicator
from core.cloud.managers.auth_manager import AuthManager
from core.cloud.managers.device_manager import DeviceManager
from core.cloud.managers.execution_manager import ExecutionManager
from core.cloud.managers.task_queue_manager import TaskQueueManager
from GUI.ui.theme import setup_ttk_styles, configure_tk_root, COLORS
from GUI.ui.managers.main_gui_manager import MainGUIManager
from GUI.ui.managers.auth_manager_gui import AuthManagerGUI


class IstinaEndfieldClientGUI:
    """IstinaEndfield客户端GUI主类"""
    
    def __init__(self, root):
        self.root = root
        self.latest_version = None  # 存储最新版本号
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
        # 配置根窗口背景
        configure_tk_root(self.root)

        # 设置 ttk 样式
        style = setup_ttk_styles()

        # 配置窗口标题栏颜色（Windows 特定）
        try:
            import ctypes
            from ctypes import wintypes

            # 获取窗口句柄
            hwnd = ctypes.windll.user32.GetForegroundWindow()

            # 启用深色标题栏（Windows 10/11）
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(ctypes.c_int(1)),
                ctypes.sizeof(ctypes.c_int)
            )
        except (ImportError, AttributeError, OSError):
            # 在非 Windows 系统或旧版本 Windows 上忽略
            pass
        
    def _load_config(self, config_file):
        """加载配置文件"""
        # 配置文件位于 IstinaEndfieldAssistant/config/ 目录，需要向上两级
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), config_file)
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
                "touch": {
                    "touch_method": "maatouch",
                    "maa_style": {
                        "enabled": True,
                        "press_duration_ms": 50,
                        "press_jitter_px": 2,
                        "swipe_delay_min_ms": 100,
                        "swipe_delay_max_ms": 300,
                        "use_normalized_coords": True
                    },
                    "swipe_duration_ms": 300,
                    "long_press_duration_ms": 500,
                    "minitouch": {
                        "enabled": False,
                        "binary_path": "device_control_system/minitouch_resources/armeabi-v7a/minitouch"
                    },
                    "maatouch": {
                        "enabled": False,
                        "binary_path": "device_control_system/minitouch_resources/maatouch/minitouch"
                    }
                },
                "security": {"enable_safe_press": True, "enable_jitter": True},
                "communication": {"password": "default_password"}
            }
            
    def init_components(self):
        """初始化所有组件"""
        self.logger.info(LogCategory.MAIN, "开始初始化组件")
        
        try:
            # 初始化核心功能模块
            # ADB路径相对于IstinaEndfieldAssistant根目录
            istina_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            adb_path = os.path.join(istina_root, self.config['adb']['path'])
            
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
                adb_manager=self.adb_manager
            )
            
            self.logger.debug(LogCategory.MAIN, "初始化触控管理器")
            
            touch_config = self.config.get('touch', {})
            touch_method = touch_config.get('touch_method', 'maatouch')
            maa_style_config = touch_config.get('maa_style', {})

            # 获取失败处理选项（强制启用）
            fail_on_error = True

            # 创建统一触控管理器
            self.touch_executor = TouchManager()
            
            self.logger.info(LogCategory.MAIN, "触控管理器初始化完成",
                           touch_method=touch_method,
                           fail_on_error=fail_on_error)
            
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
                self.auth_manager,
                self.config  # 传递配置以支持PC模式判断
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
            self.root.gui_manager = self.gui_manager
            
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
        is_logged_in, error_msg = self.auth_manager.check_login_status()
        
        if is_logged_in:
            self.logger.debug(LogCategory.MAIN, "已登录状态")
            self.on_login_success()
        elif error_msg and ("网络连接异常" in error_msg or "网络错误" in error_msg):
            # 如果是网络错误，弹出网络环境异常提示并退出
            self.logger.warning(LogCategory.MAIN, "网络连接异常", error_msg=error_msg)
            messagebox.showerror("网络环境异常", "无法连接到服务器，请检查网络连接后重试。")
            self.root.quit()
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
        cache_dir = "cache"
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
            self.logger.debug(LogCategory.MAIN, "任务队列文件不存在，创建推荐日常任务链")
            # 创建推荐的日常任务链
            recommended_task_chain = [
                {
                    'id': 'task_visit_friends',
                    'name': '访问好友',
                    'variables': {
                        '优先偷菜': '是',
                        '访问数量': '全部',
                        '交换线索': '是'
                    }
                },
                {
                    'id': 'task_dijiang_rewards',
                    'name': '帝江号奖励',
                    'variables': {
                        '自动开始交换': '否',
                        '无控制中枢生产助力': '否',
                        '线索设置': '是',
                        '线索发送数量': '3',
                        '线索库存上限': '3',
                        '培养目标': '任意',
                        '自动提取种子': '否'
                    }
                },
                {
                    'id': 'task_credit_shopping',
                    'name': '积分购物',
                    'variables': {
                        '优先购买': '嵌晶玉|武库配额',
                        '自动领取积分': '是',
                        '折扣要求': '不限',
                        '购买黑名单物品': '否',
                        '黑名单': '',
                        '保留积分': '否'
                    }
                },
                {
                    'id': 'task_sell_product',
                    'name': '出售产品',
                    'variables': {
                        '出售地区': '四号谷地',
                        '保留数量': '0'
                    }
                },
                {
                    'id': 'task_daily_rewards',
                    'name': '每日奖励领取',
                    'variables': {
                        '领取邮件奖励': '是',
                        '领取任务奖励': '是',
                        '领取送货奖励': '是',
                        '领取活动奖励': '是',
                        '领取协议通行证奖励': '是'
                    }
                }
            ]
            
            for task in recommended_task_chain:
                self.task_queue_manager.add_task(task)
            self.logger.info(LogCategory.MAIN, "推荐日常任务链创建完成", task_count=len(recommended_task_chain))
            self.log_message("已创建推荐日常任务链", "task", "INFO")

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
        
        self.task_queue_manager.save_task_queue()
        self.logger.debug(LogCategory.MAIN, "任务队列已保存")
        
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
                    
                run_duration = (time.time() - self.start_time) * 1000
                self.logger.info(LogCategory.MAIN, "程序关闭", run_duration_ms=round(run_duration, 3))
                self.root.destroy()
        else:
            run_duration = (time.time() - self.start_time) * 1000
            self.logger.info(LogCategory.MAIN, "程序关闭", run_duration_ms=round(run_duration, 3))
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = IstinaEndfieldClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    try:
        root.mainloop()
    except Exception as e:
        if hasattr(app, 'logger'):
            app.logger.exception(LogCategory.MAIN, "程序异常", exc_info=True)
        raise