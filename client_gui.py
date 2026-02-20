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
        
        # 创建UI（这会创建status_bar）
        self.setup_ui()
        
        # 创建日志管理器（使用任务队列UI中的日志控件）
        log_text_widget = self.task_queue_ui.get_log_text_widget()
        self.log_manager = LogManager(log_text_widget, self.status_bar)
        
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
        # 主notebook（重新引入以支持多页面）
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 页面框架
        self.execution_page_frame = ttk.Frame(self.notebook)
        self.cloud_service_frame = ttk.Frame(self.notebook)
        
        # 添加页面
        self.notebook.add(self.execution_page_frame, text='执行控制台')
        self.notebook.add(self.cloud_service_frame, text='云服务')
        
        # 添加页面切换事件监听
        self.notebook.bind('<<NotebookTabChanged>>', self.on_notebook_tab_changed)
        
        # 设置各页面
        self.setup_execution_page()
        self.setup_cloud_service_page()
        
        # 状态栏
        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def setup_execution_page(self):
        """设置执行控制台页面（包含设备管理和任务队列）"""
        frame = ttk.Frame(self.execution_page_frame, padding="10")
        frame.pack(fill='both', expand=True)
        
        # 左右分栏：任务队列在左，设备相关在右
        main_paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        main_paned.pack(fill='both', expand=True)
        
        # 任务队列区域（左侧）
        queue_frame = ttk.Frame(main_paned)
        main_paned.add(queue_frame, weight=1)
        
        # 创建任务队列UI
        self.task_queue_ui = TaskQueueUI(
            queue_frame,
            self.task_queue_manager,
            None  # 暂时传入None，稍后设置
        )
        
        # 设备相关区域（右侧）- 合并设备连接、可用设备和屏幕预览
        device_combined_frame = ttk.LabelFrame(main_paned, text="设备管理", padding="10")
        main_paned.add(device_combined_frame, weight=2)
        
        # 创建设备UI（现在所有设备相关内容都在一个框内）
        self.device_ui = DeviceUI(
            device_combined_frame,
            self.device_manager,
            self.screen_capture,
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
    def setup_cloud_service_page(self):
        """设置云服务页面"""
        frame = ttk.Frame(self.cloud_service_frame, padding="20")
        frame.pack(fill='both', expand=True)
        
        # 标题
        title_label = ttk.Label(frame, text="云服务账户信息", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 用户信息显示区域
        info_frame = ttk.LabelFrame(frame, text="账户详情", padding="15")
        info_frame.pack(fill='x', pady=(0, 20))
        
        # 用户名
        username_frame = ttk.Frame(info_frame)
        username_frame.pack(fill='x', pady=5)
        ttk.Label(username_frame, text="用户名:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.username_value = ttk.Label(username_frame, text="未登录", font=('Arial', 10))
        self.username_value.pack(side=tk.LEFT, padx=(10, 0))
        
        # 账号层级
        tier_frame = ttk.Frame(info_frame)
        tier_frame.pack(fill='x', pady=5)
        ttk.Label(tier_frame, text="账号层级:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.tier_value = ttk.Label(tier_frame, text="未知", font=('Arial', 10))
        self.tier_value.pack(side=tk.LEFT, padx=(10, 0))
        
        # Token (API Key)
        token_frame = ttk.Frame(info_frame)
        token_frame.pack(fill='x', pady=5)
        ttk.Label(token_frame, text="Token:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.token_value = ttk.Label(token_frame, text="未获取", font=('Arial', 10))
        self.token_value.pack(side=tk.LEFT, padx=(10, 0))
        
        # 请求用量
        usage_frame = ttk.Frame(info_frame)
        usage_frame.pack(fill='x', pady=5)
        ttk.Label(usage_frame, text="请求用量:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.usage_value = ttk.Label(usage_frame, text="0/0", font=('Arial', 10))
        self.usage_value.pack(side=tk.LEFT, padx=(10, 0))
        
        # 刷新按钮
        refresh_btn = ttk.Button(frame, text="🔄 刷新信息", command=self.refresh_cloud_service_info)
        refresh_btn.pack(pady=(10, 0))
        
        # 初始化显示
        self.refresh_cloud_service_info()
        
    def refresh_cloud_service_info(self):
        """刷新云服务信息"""
        if not self.auth_manager or not self.auth_manager.get_login_status():
            self.username_value.config(text="未登录")
            self.tier_value.config(text="未知")
            self.token_value.config(text="未获取")
            self.usage_value.config(text="0/0")
            return
            
        # 获取用户ID
        user_id = self.auth_manager.get_user_id()
        self.username_value.config(text=user_id)
        
        # 尝试获取用户信息
        user_info = self.auth_manager.get_user_info()
        if user_info:
            self.tier_value.config(text=user_info.get('tier', '未知'))
            self.token_value.config(text=str(user_info.get('total_tokens_used', 0)))
            self.usage_value.config(text=f"{user_info.get('quota_used', 0)}/{user_info.get('quota_daily', 0)}")
        else:
            self.tier_value.config(text="未知")
            self.usage_value.config(text="无法获取")
            
            
        if self.status_bar:
            self.status_bar.config(text="云服务信息已刷新")

    def on_notebook_tab_changed(self, event):
        """处理notebook页面切换事件"""
        current_tab = self.notebook.index(self.notebook.select())
        # 云服务页面是第二个页面（索引1）
        if current_tab == 1:
            self.refresh_cloud_service_info()
        
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