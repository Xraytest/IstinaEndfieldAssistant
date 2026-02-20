"""ReAcrture 客户端GUI - 重构后的模块化版本"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import os
import sys
import json

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from adb_manager import ADBDeviceManager
from screen_capture import ScreenCapture
from touch_executor import TouchExecutor
from task_manager import TaskManager
from communicator import ClientCommunicator

# 导入新创建的模块化组件
from components.device_manager import DeviceManager
from components.task_queue_manager import TaskQueueManager
from components.auth_manager import AuthManager
from components.execution_manager import ExecutionManager
from components.log_manager import LogManager
from ui.device_ui import DeviceUI
from ui.task_queue_ui import TaskQueueUI

class ReAcrtureClientGUI:
    """ReAcrture客户端GUI主类（模块化版本）"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("ReAcrture - 分布式自动化客户端")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # 初始化核心组件
        self.adb_manager = None
        self.screen_capture = None
        self.touch_executor = None
        self.task_manager = None
        self.communicator = None
        
        # 加载配置
        self.config = self._load_config("config/client_config.json")
        
        # 创建UI样式
        self.setup_styles()
        
        # 初始化核心服务
        self.init_core_services()
        
        # 创建业务逻辑管理器
        self.device_manager = DeviceManager(self.adb_manager, self.config)
        self.task_queue_manager = TaskQueueManager(self.task_manager)
        self.auth_manager = AuthManager(self.communicator, self.config)
        
        # 创建UI
        self.setup_ui()
        
        # 创建日志管理器
        self.log_manager = LogManager(self.main_log_text, self.status_bar)
        
        # 为UI组件设置日志回调
        self.device_ui.log_callback = self.log_manager.log_message
        self.task_queue_ui.log_callback = self.log_manager.log_message
        
        # 创建执行管理器（需要log_manager）
        self.execution_manager = ExecutionManager(
            self.device_manager,
            self.screen_capture,
            self.touch_executor,
            self.task_queue_manager,
            self.communicator,
            self.auth_manager
        )
        
        # 检查登录状态
        self.auth_manager.check_login_status(self.root)
        
        # 加载任务队列
        self.task_queue_ui.update_queue_display()
        
    def setup_styles(self):
        """设置UI样式"""
        style = ttk.Style()
        style.configure('Action.TButton', font=('Arial', 10, 'bold'))
        style.configure('Security.TButton', font=('Arial', 10, 'bold'), foreground='green')
        style.configure('Stop.TButton', font=('Arial', 10, 'bold'), foreground='red')
        style.configure('Status.TLabel', font=('Arial', 9))
        style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        
    def setup_ui(self):
        """设置主UI"""
        # 主notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 页面框架
        self.execution_page_frame = ttk.Frame(self.notebook)
        self.log_page_frame = ttk.Frame(self.notebook)
        
        # 添加页面
        self.notebook.add(self.execution_page_frame, text='执行控制台')
        self.notebook.add(self.log_page_frame, text='执行日志')
        
        # 设置各页面
        self.setup_execution_page()
        self.setup_log_page()
        
        # 状态栏
        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def setup_execution_page(self):
        """设置执行控制台页面（包含设备管理和任务队列）"""
        frame = ttk.Frame(self.execution_page_frame, padding="10")
        frame.pack(fill='both', expand=True)
        
        # 上下分栏：设备管理在上，任务队列在下
        main_paned = ttk.PanedWindow(frame, orient=tk.VERTICAL)
        main_paned.pack(fill='both', expand=True)
        
        # 设备管理区域（上方）
        device_frame = ttk.Frame(main_paned)
        main_paned.add(device_frame, weight=1)
        
        # 创建设备UI
        self.device_ui = DeviceUI(
            device_frame,
            self.device_manager,
            self.screen_capture,
            None  # 暂时传入None，稍后设置
        )
        
        # 任务队列区域（下方）
        queue_frame = ttk.Frame(main_paned)
        main_paned.add(queue_frame, weight=1)
        
        # 创建任务队列UI
        self.task_queue_ui = TaskQueueUI(
            queue_frame,
            self.task_queue_manager,
            None  # 暂时传入None，稍后设置
        )
        
        # 执行控制按钮
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill='x', pady=(10, 0))
        
        self.llm_start_btn = ttk.Button(
            control_frame, 
            text="▶ 启动推理", 
            command=self.start_llm_execution, 
            style='Security.TButton'
        )
        self.llm_start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.llm_stop_btn = ttk.Button(
            control_frame, 
            text="■ 停止执行", 
            command=self.stop_llm_execution, 
            style='Stop.TButton'
        )
        self.llm_stop_btn.pack(side=tk.LEFT)
        self.llm_stop_btn.config(state='disabled')
        
        # 当前任务状态
        status_frame = ttk.Frame(frame)
        status_frame.pack(fill='x', pady=(10, 0))
        
        self.current_task_label = ttk.Label(status_frame, text="当前任务: 无", style='Status.TLabel')
        self.current_task_label.pack(side=tk.LEFT)
        
        self.progress_var = tk.StringVar(value="进度: 0/0")
        self.progress_label = ttk.Label(status_frame, textvariable=self.progress_var, style='Status.TLabel')
        self.progress_label.pack(side=tk.RIGHT)
        
    def setup_log_page(self):
        """设置执行日志页面"""
        frame = ttk.Frame(self.log_page_frame, padding="10")
        frame.pack(fill='both', expand=True)
        
        # 执行日志显示
        self.main_log_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=('Consolas', 9))
        self.main_log_text.pack(fill='both', expand=True)
        
    def _load_config(self, config_file):
        """加载配置文件"""
        config_path = os.path.join(os.path.dirname(__file__), config_file)
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "server": {"host": "127.0.0.1", "port": 9999},
                "adb": {"path": "3rd-part/ADB/adb.exe", "timeout": 10},
                "screen": {"quality": 80, "max_size": 1024},
                "security": {"press_duration_ms": 100, "press_jitter_px": 2},
                "communication": {"password": "default_password"}
            }
            
    def init_core_services(self):
        """初始化核心服务"""
        try:
            self.adb_manager = ADBDeviceManager(
                adb_path=self.config['adb']['path'],
                timeout=self.config['adb']['timeout']
            )
            self.screen_capture = ScreenCapture(
                adb_manager=self.adb_manager,
                quality=self.config['screen']['quality'],
                max_size=self.config['screen']['max_size']
            )
            self.touch_executor = TouchExecutor(
                adb_manager=self.adb_manager,
                press_duration_ms=self.config['security']['press_duration_ms'],
                press_jitter_px=self.config['security']['press_jitter_px']
            )
            self.task_manager = TaskManager(
                config_dir=os.path.join(os.path.dirname(__file__), "config"),
                data_dir=os.path.join(os.path.dirname(__file__), "data")
            )
            self.communicator = ClientCommunicator(
                host=self.config['server']['host'],
                port=self.config['server']['port'],
                password=self.config.get('communication', {}).get('password', 'default_password'),
                timeout=30
            )
            print("核心服务初始化成功")
        except Exception as e:
            print(f"核心服务初始化失败: {e}")
            messagebox.showerror("初始化错误", f"核心服务初始化失败: {e}")
            
    def start_llm_execution(self):
        """开始LLM执行"""
        success, message = self.execution_manager.start_execution(
            self.log_manager.log_message,
            self.update_ui_callback
        )
        
        if success:
            self.llm_start_btn.config(state='disabled')
            self.llm_stop_btn.config(state='normal')
        else:
            messagebox.showwarning("执行失败", message)
            
    def stop_llm_execution(self):
        """停止LLM执行"""
        self.execution_manager.stop_execution()
        self.llm_start_btn.config(state='normal')
        self.llm_stop_btn.config(state='disabled')
        self.log_manager.log_message("执行已停止", "execution", "INFO")
        
    def update_ui_callback(self, action, value):
        """UI更新回调函数"""
        if action == 'current_task':
            self.current_task_label.config(text=value)
        elif action == 'progress':
            self.progress_var.set(value)
        elif action == 'stop_execution':
            self.stop_llm_execution()
            
    def on_closing(self):
        """窗口关闭事件"""
        if self.execution_manager.is_running():
            if messagebox.askokcancel("确认", "执行正在进行中，确定要退出吗？"):
                self.stop_llm_execution()
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ReAcrtureClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()