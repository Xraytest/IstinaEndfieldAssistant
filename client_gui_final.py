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

from adb_manager import ADBDeviceManager
from screen_capture import ScreenCapture
from touch_executor import TouchExecutor
from task_manager import TaskManager
from communicator import ClientCommunicator

class ReAcrtureClientGUI:
    """ReAcrture客户端GUI主类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("ReAcrture - 分布式自动化客户端")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # 状态变量
        self.current_device = None
        self.current_image = None
        self.image_scale_x = 1.0
        self.image_scale_y = 1.0
        self.client_running = False
        self.client_thread = None
        self.task_queue = []
        self.current_task_index = 0
        self.execution_count = 1
        self.is_logged_in = False
        self.user_id = ""
        self.session_id = ""
        
        # 初始化组件
        self.adb_manager = None
        self.screen_capture = None
        self.touch_executor = None
        self.task_manager = None
        self.communicator = None
        
        # 加载配置
        self.config = self._load_config("config/client_config.json")
        
        # 加载上次连接的设备
        self.last_connected_device = self._load_last_connected_device()
        
        # 创建UI
        self.setup_styles()
        self.setup_ui()
        
        # 初始化ADB
        self.init_adb()
        
        # 检查登录状态
        self.check_login_status()
        
        # 加载任务队列
        self.load_task_queue()
        
        # 启动时检查更新（仅在设置页面存在时）
        if hasattr(self, 'settings_page_frame'):
            self.root.after(1000, self.check_for_updates_on_startup)
        
    def check_for_updates_on_startup(self):
        """启动时检查更新并显示提示"""
        try:
            current_version = self.load_local_version()
            self.check_for_updates()
            
            # 等待几秒让检查完成，然后显示提示
            self.root.after(3000, lambda: self.show_update_notification_if_needed(current_version))
        except Exception as e:
            self.log_message(f"启动时检查更新失败: {e}", "version", "ERROR")
        
    def show_update_notification_if_needed(self, old_version):
        """如果需要，显示更新通知"""
        try:
            current_version = self.load_local_version()
            if (old_version != 'unknown' and
                current_version != 'unknown' and
                old_version != current_version):
                messagebox.showinfo("新版本可用", f"发现新版本！\n当前版本: {old_version}\n最新版本: {current_version}")
        except Exception as e:
            pass  # 忽略通知错误
        
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
        self.settings_page_frame = ttk.Frame(self.notebook)
        self.cloud_service_page_frame = ttk.Frame(self.notebook)
        
        # 添加页面
        self.notebook.add(self.execution_page_frame, text='执行控制台')
        self.notebook.add(self.settings_page_frame, text='设置')
        self.notebook.add(self.cloud_service_page_frame, text='云服务')
        
        # 状态栏（先创建状态栏，确保log_message可以访问）
        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 设置各页面
        self.setup_execution_page()
        self.setup_settings_page()
        self.setup_cloud_service_page()
        
    def setup_device_page(self):
        """设置设备管理页面"""
        frame = ttk.Frame(self.device_page_frame, padding="10")
        frame.pack(fill='both', expand=True)
        
        # 设备连接区域
        conn_frame = ttk.LabelFrame(frame, text="设备连接", padding="10")
        conn_frame.pack(fill='x', pady=(0, 10))
        
        # 扫描设备按钮
        scan_btn = ttk.Button(conn_frame, text="扫描设备", command=self.scan_devices)
        scan_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 连接状态
        self.device_status_label = ttk.Label(conn_frame, text="未连接设备", foreground='gray')
        self.device_status_label.pack(side=tk.LEFT)
        
        # 设备列表
        device_list_frame = ttk.LabelFrame(frame, text="可用设备", padding="10")
        device_list_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # 设备列表
        self.device_tree = ttk.Treeview(device_list_frame, columns=('serial', 'model', 'state'), show='headings', height=8)
        self.device_tree.heading('serial', text='设备序列号')
        self.device_tree.heading('model', text='设备型号')
        self.device_tree.heading('state', text='状态')
        self.device_tree.column('serial', width=200)
        self.device_tree.column('model', width=150)
        self.device_tree.column('state', width=100)
        self.device_tree.pack(side=tk.LEFT, fill='both', expand=True)
        
        # 滚动条
        device_scroll = ttk.Scrollbar(device_list_frame, orient=tk.VERTICAL, command=self.device_tree.yview)
        device_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.device_tree.configure(yscrollcommand=device_scroll.set)
        
        # 设备操作按钮
        device_btn_frame = ttk.Frame(frame)
        device_btn_frame.pack(fill='x')
        
        connect_device_btn = ttk.Button(device_btn_frame, text="连接选中设备", command=self.connect_selected_device)
        connect_device_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        disconnect_device_btn = ttk.Button(device_btn_frame, text="断开连接", command=self.disconnect_device)
        disconnect_device_btn.pack(side=tk.LEFT)
        
        # 屏幕预览
        preview_frame = ttk.LabelFrame(frame, text="屏幕预览", padding="10")
        preview_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        self.preview_canvas = tk.Canvas(preview_frame, bg='black', highlightthickness=0)
        self.preview_canvas.pack(fill='both', expand=True)
        
    def setup_execution_page(self):
        """设置执行控制台页面（包含设备管理和任务队列）"""
        frame = ttk.Frame(self.execution_page_frame, padding="10")
        frame.pack(fill='both', expand=True)
        
        # 左右分栏：任务队列在左，设备管理在右
        main_paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        main_paned.pack(fill='both', expand=True)
        
        # 左：任务队列区域
        queue_frame = ttk.Frame(main_paned)
        main_paned.add(queue_frame, weight=1)
        
        # 任务队列管理
        task_queue_frame = ttk.LabelFrame(queue_frame, text="任务队列", padding="10")
        task_queue_frame.pack(fill='both', expand=True)
        
        # 任务队列列表
        list_container = ttk.Frame(task_queue_frame)
        list_container.pack(fill='both', expand=True, pady=(0, 5))
        
        scrollbar = ttk.Scrollbar(list_container, orient="vertical")
        scrollbar.pack(side=tk.RIGHT, fill='y')
        
        self.task_queue_listbox = tk.Listbox(
            list_container,
            height=8,
            font=('Arial', 10),
            yscrollcommand=scrollbar.set
        )
        self.task_queue_listbox.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.config(command=self.task_queue_listbox.yview)
        
        # 队列信息显示
        self.queue_info_label = ttk.Label(task_queue_frame, text="队列: 0个任务", font=('Arial', 9))
        self.queue_info_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 任务队列操作按钮
        queue_btn_frame = ttk.Frame(queue_frame)
        queue_btn_frame.pack(fill='x', pady=(10, 0))
        
        add_task_btn = ttk.Button(queue_btn_frame, text="添加任务", command=self.show_add_task_dialog)
        add_task_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        edit_task_btn = ttk.Button(queue_btn_frame, text="设置选中", command=self.show_edit_task_dialog)
        edit_task_btn.pack(side=tk.LEFT)
        
        # 右：设备管理区域（合并设备连接、可用设备和屏幕预览）
        device_frame = ttk.Frame(main_paned)
        main_paned.add(device_frame, weight=2)
        
        # 设备管理主框
        device_main_frame = ttk.LabelFrame(device_frame, text="设备管理", padding="10")
        device_main_frame.pack(fill='both', expand=True)
        
        # 设备连接区域
        conn_frame = ttk.Frame(device_main_frame)
        conn_frame.pack(fill='x', pady=(0, 10))
        
        # 扫描设备按钮和手动输入
        scan_btn = ttk.Button(conn_frame, text="扫描设备", command=self.scan_devices)
        scan_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 手动输入设备
        manual_frame = ttk.Frame(conn_frame)
        manual_frame.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(manual_frame, text="手动输入:").pack(side=tk.LEFT)
        self.manual_device_var = tk.StringVar()
        manual_entry = ttk.Entry(manual_frame, textvariable=self.manual_device_var, width=20)
        manual_entry.pack(side=tk.LEFT, padx=(5, 5))
        manual_connect_btn = ttk.Button(manual_frame, text="连接", command=self.manual_connect_device)
        manual_connect_btn.pack(side=tk.LEFT)
        
        # 连接状态
        self.device_status_label = ttk.Label(conn_frame, text="未连接设备", foreground='gray')
        self.device_status_label.pack(side=tk.LEFT)
        
        # 设备列表
        device_list_frame = ttk.LabelFrame(device_main_frame, text="可用设备", padding="10")
        device_list_frame.pack(fill='x', pady=(0, 10))
        
        # 设备列表
        self.device_tree = ttk.Treeview(device_list_frame, columns=('serial', 'model', 'state'), show='headings', height=4)
        self.device_tree.heading('serial', text='设备序列号')
        self.device_tree.heading('model', text='设备型号')
        self.device_tree.heading('state', text='状态')
        self.device_tree.column('serial', width=200)
        self.device_tree.column('model', width=150)
        self.device_tree.column('state', width=100)
        self.device_tree.pack(side=tk.LEFT, fill='x', expand=True)
        
        # 滚动条
        device_scroll = ttk.Scrollbar(device_list_frame, orient=tk.VERTICAL, command=self.device_tree.yview)
        device_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.device_tree.configure(yscrollcommand=device_scroll.set)
        
        # 设备操作按钮
        device_btn_frame = ttk.Frame(device_main_frame)
        device_btn_frame.pack(fill='x', pady=(0, 10))
        
        connect_device_btn = ttk.Button(device_btn_frame, text="连接选中设备", command=self.connect_selected_device)
        connect_device_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        disconnect_device_btn = ttk.Button(device_btn_frame, text="断开连接", command=self.disconnect_device)
        disconnect_device_btn.pack(side=tk.LEFT)
        
        # 屏幕预览（缩小比例）
        preview_frame = ttk.LabelFrame(device_main_frame, text="屏幕预览", padding="10")
        preview_frame.pack(fill='both', expand=True)
        
        self.preview_canvas = tk.Canvas(preview_frame, bg='black', highlightthickness=0, height=200)
        self.preview_canvas.pack(fill='both', expand=True)
        
        # 执行控制
        exec_frame = ttk.LabelFrame(queue_frame, text="执行控制", padding="10")
        exec_frame.pack(fill='x', pady=(10, 0))
        
        self.llm_start_btn = ttk.Button(exec_frame, text="▶ 启动推理", command=self.start_llm_execution, style='Security.TButton')
        self.llm_start_btn.pack(fill='x', pady=(0, 5))
        
        self.llm_stop_btn = ttk.Button(exec_frame, text="■ 停止执行", command=self.stop_llm_execution, style='Stop.TButton')
        self.llm_stop_btn.pack(fill='x', pady=(5, 0))
        self.llm_stop_btn.config(state='disabled')
        
        # 执行次数设置
        count_frame = ttk.Frame(exec_frame)
        count_frame.pack(fill='x', pady=(5, 0))
        ttk.Label(count_frame, text="执行次数:", font=('Arial', 9)).pack(side=tk.LEFT)
        self.execution_count_var = tk.IntVar(value=self.execution_count)
        execution_count_spinbox = ttk.Spinbox(count_frame, from_=1, to=99, textvariable=self.execution_count_var, width=5)
        execution_count_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        execution_count_spinbox.bind('<Return>', lambda e: self.on_execution_count_changed())
        execution_count_spinbox.bind('<FocusOut>', lambda e: self.on_execution_count_changed())
        self.execution_count_entry = execution_count_spinbox
        
        # Content Notebook（保持在设备管理区域下方）
        content_frame = ttk.Frame(device_frame)
        content_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        # Content Notebook
        self.content_notebook = ttk.Notebook(content_frame)
        self.content_notebook.pack(fill='both', expand=True)
        
        # 执行日志（第一个标签页）
        log_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(log_frame, text='📋 执行日志')
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=('Consolas', 9))
        self.log_text.pack(fill='both', expand=True)
        
        # 设备视觉
        vision_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(vision_frame, text='📱 设备视觉')
        self.vision_canvas = tk.Canvas(vision_frame, bg='black', highlightthickness=0)
        self.vision_canvas.pack(fill='both', expand=True)
        
        # 完整上下文（最后一个标签页）
        full_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(full_frame, text='🧠 完整上下文')
        self.full_content_text = scrolledtext.ScrolledText(full_frame, wrap=tk.WORD, font=('Consolas', 9))
        self.full_content_text.pack(fill='both', expand=True)
        
        # 当前任务状态
        status_frame = ttk.Frame(frame)
        status_frame.pack(fill='x', pady=(10, 0))
        
        self.current_task_label = ttk.Label(status_frame, text="当前任务: 无", style='Status.TLabel')
        self.current_task_label.pack(side=tk.LEFT)
        
        self.progress_var = tk.StringVar(value="进度: 0/0")
        self.progress_label = ttk.Label(status_frame, textvariable=self.progress_var, style='Status.TLabel')
        self.progress_label.pack(side=tk.RIGHT)
        
        
    def setup_settings_page(self):
        """设置设置页面"""
        frame = ttk.Frame(self.settings_page_frame, padding="20")
        frame.pack(fill='both', expand=True)
        
        # 版本信息区域
        version_frame = ttk.LabelFrame(frame, text="版本信息", padding="15")
        version_frame.pack(fill='x', pady=(0, 20))
        
        # 当前版本
        current_version_frame = ttk.Frame(version_frame)
        current_version_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(current_version_frame, text="当前版本:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.current_version_label = ttk.Label(current_version_frame, text="加载中...", font=('Arial', 10))
        self.current_version_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 最新版本
        latest_version_frame = ttk.Frame(version_frame)
        latest_version_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(latest_version_frame, text="最新版本:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.latest_version_label = ttk.Label(latest_version_frame, text="检查中...", font=('Arial', 10))
        self.latest_version_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 更新状态
        self.update_status_label = ttk.Label(version_frame, text="", foreground='blue', font=('Arial', 9))
        self.update_status_label.pack(fill='x', pady=(5, 10))
        
        # 检查更新按钮
        check_update_btn = ttk.Button(version_frame, text="检查更新", command=self.check_for_updates)
        check_update_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 更新按钮
        self.update_btn = ttk.Button(version_frame, text="更新到最新版本", command=self.update_client, state='disabled')
        self.update_btn.pack(side=tk.LEFT)
        
        # 初始化版本信息
        self.load_local_version()
        self.check_for_updates()
         
    def setup_cloud_service_page(self):
        """设置云服务页面"""
        frame = ttk.Frame(self.cloud_service_page_frame, padding="20")
        frame.pack(fill='both', expand=True)
        
        # 用户信息区域
        user_info_frame = ttk.LabelFrame(frame, text="用户信息", padding="15")
        user_info_frame.pack(fill='x', pady=(0, 20))
        
        # 用户名
        self.username_label = ttk.Label(user_info_frame, text="用户名: 未登录", font=('Arial', 10, 'bold'))
        self.username_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 用户层级
        self.tier_label = ttk.Label(user_info_frame, text="用户层级: -", font=('Arial', 10))
        self.tier_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 配额使用情况 - 每日
        self.daily_quota_label = ttk.Label(user_info_frame, text="每日配额: -/-", font=('Arial', 10))
        self.daily_quota_label.pack(anchor=tk.W, pady=(0, 2))
        
        # 配额使用情况 - 每周
        self.weekly_quota_label = ttk.Label(user_info_frame, text="每周配额: -/-", font=('Arial', 10))
        self.weekly_quota_label.pack(anchor=tk.W, pady=(0, 2))
        
        # 配额使用情况 - 每月
        self.monthly_quota_label = ttk.Label(user_info_frame, text="每月配额: -/-", font=('Arial', 10))
        self.monthly_quota_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Token用量统计
        self.token_label = ttk.Label(user_info_frame, text="Token用量: -", font=('Arial', 10))
        self.token_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 到期时间（仅高层级用户显示）
        self.expiry_label = ttk.Label(user_info_frame, text="", font=('Arial', 10, 'bold'), foreground='red')
        self.expiry_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 刷新按钮
        refresh_btn = ttk.Button(user_info_frame, text="🔄 刷新信息", command=self.refresh_user_info)
        refresh_btn.pack(anchor=tk.W, pady=(10, 0))
        
        # 绑定notebook切换事件，实现自动刷新
        self.notebook.bind('<<NotebookTabChanged>>', self.on_notebook_tab_changed)
        
        # 初始化用户信息显示
        self.update_user_info_display()
         
    def on_notebook_tab_changed(self, event):
        """处理notebook标签页切换事件"""
        selected_tab = self.notebook.select()
        if selected_tab == str(self.cloud_service_page_frame):
            # 切换到云服务页面时自动刷新
            if self.is_logged_in:
                self.refresh_user_info()
        
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
            
    def _load_last_connected_device(self):
        """加载上次连接的设备"""
        cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        device_cache_file = os.path.join(cache_dir, "last_device.json")
        
        if os.path.exists(device_cache_file):
            try:
                with open(device_cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('last_device')
            except Exception as e:
                self.log_message(f"加载设备缓存失败: {e}", "device", "WARNING")
        return None
        
    def _save_last_connected_device(self, device_serial):
        """保存上次连接的设备"""
        cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        device_cache_file = os.path.join(cache_dir, "last_device.json")
        try:
            with open(device_cache_file, 'w', encoding='utf-8') as f:
                json.dump({'last_device': device_serial}, f)
        except Exception as e:
            self.log_message(f"保存设备缓存失败: {e}", "device", "WARNING")
            
    def load_local_version(self):
        """加载本地版本信息"""
        try:
            ver_file = os.path.join(os.path.dirname(__file__), "data", "ver.json")
            if os.path.exists(ver_file):
                with open(ver_file, 'r', encoding='utf-8') as f:
                    ver_data = json.load(f)
                version = ver_data.get('version', 'unknown')
                self.current_version_label.config(text=version)
                return version
            else:
                # 如果文件不存在，创建默认版本文件
                ver_data = {'version': 'alpha_0.0.1'}
                os.makedirs(os.path.dirname(ver_file), exist_ok=True)
                with open(ver_file, 'w', encoding='utf-8') as f:
                    json.dump(ver_data, f, indent=2)
                self.current_version_label.config(text='alpha_0.0.1')
                return 'alpha_0.0.1'
        except Exception as e:
            self.log_message(f"加载本地版本失败: {e}", "version", "ERROR")
            self.current_version_label.config(text="未知")
            return "unknown"
            
    def check_for_updates(self):
        """检查更新"""
        try:
            import urllib.request
            import urllib.error
            
            # 构建API URL
            server_host = self.config['server']['host']
            web_port = 8000  # Web服务器端口
            api_url = f"http://{server_host}:{web_port}/api/client/version"
            
            self.update_status_label.config(text="正在检查更新...", foreground='blue')
            self.root.update()
            
            # 发送HTTP请求
            req = urllib.request.Request(api_url)
            req.add_header('User-Agent', 'ReAcrture-Client/1.0')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    if data.get('status') == 'success':
                        latest_version = data.get('data', {}).get('version', 'unknown')
                        self.latest_version_label.config(text=latest_version)
                        
                        # 比较版本
                        current_version = self.load_local_version()
                        if current_version != 'unknown' and latest_version != 'unknown' and current_version != latest_version:
                            self.update_status_label.config(text="发现新版本！", foreground='green')
                            self.update_btn.config(state='normal')
                        else:
                            self.update_status_label.config(text="已是最新版本", foreground='gray')
                            self.update_btn.config(state='disabled')
                    else:
                        self.update_status_label.config(text=f"检查失败: {data.get('message', '未知错误')}", foreground='red')
                else:
                    self.update_status_label.config(text=f"检查失败: HTTP {response.status}", foreground='red')
                    
        except urllib.error.URLError as e:
            self.update_status_label.config(text=f"网络错误: {str(e)}", foreground='red')
            self.log_message(f"检查更新失败 - 网络错误: {e}", "version", "ERROR")
            # 网络错误时直接退出客户端
            messagebox.showerror("网络连接失败", "无法连接到更新服务器，请检查网络连接后重试。")
            self.root.quit()
        except Exception as e:
            self.update_status_label.config(text=f"检查失败: {str(e)}", foreground='red')
            self.log_message(f"检查更新失败: {e}", "version", "ERROR")
            
    def update_client(self):
        """更新客户端"""
        if messagebox.askyesno("确认更新", "确定要更新到最新版本吗？这将覆盖本地文件！"):
            try:
                import subprocess
                import shutil
                
                self.update_status_label.config(text="正在更新...", foreground='blue')
                self.update_btn.config(state='disabled')
                self.root.update()
                
                # 获取当前工作目录
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                
                # 备份当前版本（可选）
                backup_dir = os.path.join(current_dir, "backup_before_update")
                if os.path.exists(backup_dir):
                    shutil.rmtree(backup_dir)
                shutil.copytree(current_dir, backup_dir)
                
                # 执行git clone覆盖
                git_path = self.config.get('git', {}).get('path', 'git')
                if not os.path.exists(git_path):
                    git_path = 'git'  # 使用系统git
                
                # 克隆到临时目录
                temp_dir = os.path.join(current_dir, "temp_update")
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                
                cmd = [git_path, "clone", "https://github.com/Xraytest/IstinaEndfieldAssistant.git", temp_dir]
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=current_dir, timeout=300)
                
                if result.returncode == 0:
                    # 复制新文件覆盖旧文件（保留data目录和cache目录）
                    for item in os.listdir(temp_dir):
                        src_path = os.path.join(temp_dir, item)
                        dst_path = os.path.join(current_dir, item)
                        
                        # 跳过data和cache目录
                        if item in ['data', 'cache']:
                            continue
                            
                        if os.path.isdir(src_path):
                            if os.path.exists(dst_path):
                                shutil.rmtree(dst_path)
                            shutil.copytree(src_path, dst_path)
                        else:
                            if os.path.exists(dst_path):
                                os.remove(dst_path)
                            shutil.copy2(src_path, dst_path)
                    
                    # 清理临时目录
                    shutil.rmtree(temp_dir)
                    
                    # 更新版本文件
                    ver_file = os.path.join(os.path.dirname(__file__), "data", "ver.json")
                    latest_version = self.latest_version_label.cget("text")
                    if latest_version and latest_version != "检查中...":
                        with open(ver_file, 'w', encoding='utf-8') as f:
                            json.dump({'version': latest_version}, f, indent=2)
                        
                        self.update_status_label.config(text="更新成功！请重启客户端", foreground='green')
                        self.current_version_label.config(text=latest_version)
                        messagebox.showinfo("更新成功", "客户端已更新到最新版本！\n请重启客户端以应用更改。")
                    else:
                        self.update_status_label.config(text="更新完成，但版本信息未更新", foreground='orange')
                        messagebox.showinfo("更新完成", "客户端已更新！\n请重启客户端以应用更改。")
                        
                else:
                    # 恢复备份
                    if os.path.exists(backup_dir):
                        shutil.rmtree(current_dir)
                        shutil.move(backup_dir, current_dir)
                    
                    error_msg = result.stderr if result.stderr else result.stdout
                    self.update_status_label.config(text=f"更新失败: {error_msg}", foreground='red')
                    messagebox.showerror("更新失败", f"更新过程中发生错误:\n{error_msg}")
                    
            except Exception as e:
                self.update_status_label.config(text=f"更新失败: {str(e)}", foreground='red')
                self.log_message(f"更新失败: {e}", "version", "ERROR")
                messagebox.showerror("更新失败", f"更新过程中发生错误:\n{str(e)}")
                
    def init_adb(self):
        """初始化ADB"""
        try:
            # 使用绝对路径确保正确找到ADB可执行文件
            script_dir = os.path.dirname(os.path.abspath(__file__))
            adb_path = os.path.join(script_dir, self.config['adb']['path'])
            
            # 验证ADB文件是否存在
            if not os.path.exists(adb_path):
                raise FileNotFoundError(f"ADB executable not found at: {adb_path}")
                
            self.adb_manager = ADBDeviceManager(
                adb_path=adb_path,
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
                timeout=300
            )
            self.log_message("ADB初始化成功", "system", "INFO")
        except Exception as e:
            self.log_message(f"ADB初始化失败: {e}", "system", "ERROR")
            messagebox.showerror("初始化错误", f"ADB初始化失败: {e}")
            
    def check_login_status(self):
        """检查登录状态"""
        
        # 检查多个可能的arkpass文件位置
        possible_paths = []
        
        # 1. 客户端缓存目录
        cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        else:
            cache_files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith('.arkpass')]
            possible_paths.extend(cache_files)
        
        # 2. 项目根目录（相对于client目录的上一级）
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        root_files = [os.path.join(project_root, f) for f in os.listdir(project_root) if f.endswith('.arkpass')]
        possible_paths.extend(root_files)
        
        # 3. 当前工作目录
        current_files = [f for f in os.listdir('.') if f.endswith('.arkpass')]
        possible_paths.extend(current_files)
        
        # 去重并按优先级排序（缓存目录优先）
        unique_paths = []
        seen = set()
        for path in possible_paths:
            if path not in seen and os.path.exists(path):
                unique_paths.append(path)
                seen.add(path)
        
        
        # 尝试每个arkpass文件
        last_error = None
        for arkpass_path in unique_paths:
            result = self.auto_login_with_arkpass(arkpass_path)
            if isinstance(result, tuple):
                success, error_msg = result
                if success:
                    return
                else:
                    last_error = error_msg
            elif result:
                return
                
        # 如果有arkpass文件但登录失败，检查是否为网络错误
        if unique_paths:
            if last_error:
                # 检查是否为网络错误
                if "网络连接异常" in last_error or "网络错误" in last_error:
                    messagebox.showerror("网络连接失败", "无法连接到服务器，请检查网络连接后重试。")
                    # 网络错误时直接退出客户端
                    self.root.quit()
                    return
                else:
                    messagebox.showerror("自动登录失败", f"自动登录失败: {last_error}")
            else:
                messagebox.showerror("自动登录失败", "找到ArkPass文件但自动登录失败，请检查文件格式或网络连接。")
            # 凭证无效时，直接转到登录注册流程
            self.show_login_or_register_dialog()
        else:
            # 未找到arkpass文件，显示登录对话框
            self.show_login_or_register_dialog()
        
    def show_login_or_register_dialog(self):
        """显示登录或注册选择对话框 - 不登录则退出"""
        dialog = tk.Toplevel(self.root)
        dialog.title("账户认证")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="请选择操作:", font=('Arial', 12, 'bold')).pack(pady=20)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        def on_register():
            dialog.destroy()
            self.show_register_dialog()
            
        def on_login():
            dialog.destroy()
            self.show_login_dialog()
            
        def on_cancel():
            # 不登录注册，直接退出客户端
            dialog.destroy()
            self.root.quit()
            
        ttk.Button(btn_frame, text="注册", command=on_register, style='Action.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="登入", command=on_login, style='Action.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
    def show_register_dialog(self):
        """显示注册对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("注册")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="请输入用户名:", font=('Arial', 10)).pack(pady=10)
        
        username_var = tk.StringVar()
        username_entry = ttk.Entry(dialog, textvariable=username_var, width=30)
        username_entry.pack(pady=5)
        username_entry.focus()
        
        def on_submit():
            username = username_var.get().strip()
            if not username:
                messagebox.showwarning("警告", "请输入有效的用户名")
                return
                
            success, error_msg = self.register_user(username)
            if success:
                dialog.destroy()
                messagebox.showinfo("注册成功", f"{username}注册成功！登入凭证已缓存于本地")
            else:
                # 检查是否为网络错误
                if error_msg and ("网络连接异常" in error_msg or "网络错误" in error_msg):
                    messagebox.showerror("网络连接失败", "无法连接到服务器，请检查网络连接后重试。")
                    # 网络错误时直接退出客户端
                    dialog.destroy()
                    self.root.quit()
                    return
                else:
                    error_display = error_msg if error_msg else "注册失败，请重试。"
                    messagebox.showerror("注册失败", f"注册失败: {error_display}")
                
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="注册", command=on_submit, style='Action.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # 绑定回车键
        username_entry.bind('<Return>', lambda e: on_submit())
        
    def show_login_dialog(self):
        """显示登录对话框"""
        def on_select_file():
            file_path = filedialog.askopenfilename(
                title="选择ArkPass文件",
                filetypes=[("ArkPass Files", "*.arkpass"), ("All Files", "*.*")]
            )
            if file_path:
                result = self.login_with_arkpass(file_path)
                if isinstance(result, tuple):
                    success, error_msg = result[:2]
                    if success:
                        messagebox.showinfo("登录成功", "登录成功！")
                    else:
                        # 检查是否为网络错误
                        if "网络连接异常" in error_msg or "网络错误" in error_msg:
                            messagebox.showerror("网络连接失败", "无法连接到服务器，请检查网络连接后重试。")
                            # 网络错误时直接退出客户端
                            self.root.quit()
                            return
                        # 如果是用户不存在或密钥错误，删除文件
                        if len(result) > 2 and result[2] in ['user_not_found', 'invalid_api_key']:
                            try:
                                os.remove(file_path)
                                self.log_message(f"已删除无效的ArkPass文件: {file_path}", "auth", "INFO")
                            except Exception as e:
                                self.log_message(f"删除ArkPass文件失败: {e}", "auth", "ERROR")
                        messagebox.showerror("登录失败", f"登录失败: {error_msg}")
                elif result:
                    messagebox.showinfo("登录成功", "登录成功！")
                else:
                    messagebox.showerror("登录失败", "ArkPass文件无效或登录失败。")
                    
        on_select_file()
        
    def register_user(self, username):
        """注册用户"""
        try:
            if self.communicator is None:
                return False, "通信器未初始化"
            # 调用服务端注册接口
            response = self.communicator.send_request("register", {"user_id": username})
            if response is None:
                return False, "网络连接异常，请检查网络连接"
            elif response and response.get('status') == 'success':
                api_key = response.get('key')
                if api_key:
                    # 保存arkpass文件
                    arkpass_data = {
                        "user_id": username,
                        "api_key": api_key,
                        "server_host": self.config['server']['host'],
                        "server_port": self.config['server']['port']
                    }
                    
                    cache_dir = os.path.join(os.path.dirname(__file__), "cache")
                    if not os.path.exists(cache_dir):
                        os.makedirs(cache_dir)
                        
                    arkpass_path = os.path.join(cache_dir, f"{username}.arkpass")
                    try:
                        with open(arkpass_path, 'w', encoding='utf-8') as f:
                            json.dump(arkpass_data, f, indent=2)
                    except Exception as e:
                        return False
                        
                    # 更新UI状态
                    self.is_logged_in = True
                    self.user_id = username
                    if hasattr(self, 'auth_status_label'):
                        self.auth_status_label.config(text="已登录", foreground='green')
                    if hasattr(self, 'user_info_text'):
                        self.user_info_text.delete(1.0, tk.END)
                        self.user_info_text.insert(tk.END, f"用户: {username}\n状态: 已连接\nAPI密钥: {api_key[:8]}...")
                    
                    # 更新云服务页面的用户信息显示
                    self.update_user_info_display()
                    
                    return True, None
                else:
                    return False, "服务器响应中缺少API密钥"
            else:
                error_msg = response.get('message', '未知错误')
                return False, error_msg
                    
        except Exception as e:
            import traceback
            self.log_message(f"注册失败: {e}", "auth", "ERROR")
            return False, str(e)
            
        return False
        
    def login_with_arkpass(self, file_path):
        """使用arkpass文件登录"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 尝试解析JSON格式
            if content.startswith('{') and content.endswith('}'):
                arkpass_data = json.loads(content)
                user_id = arkpass_data.get('user_id')
                api_key = arkpass_data.get('api_key')
                is_json_format = True
            else:
                # 尝试解析旧格式 username:api_key
                parts = content.split(':', 1)
                if len(parts) == 2:
                    user_id = parts[0].strip()
                    api_key = parts[1].strip()
                    is_json_format = False
                    # 为legacy格式创建JSON数据用于缓存
                    arkpass_data = {
                        'user_id': user_id,
                        'api_key': api_key
                    }
                else:
                    return False, "ArkPass文件格式无效"
            
            if not user_id or not api_key:
                return False, "ArkPass文件缺少必要信息"
                
            # 调用服务端登录接口
            response = self.communicator.send_request("login", {
                "user_id": user_id,
                "key": api_key
            })
            
            if response is None:
                return False, "网络连接异常，请检查网络连接"
                
            if response.get('status') == 'success':
                session_id = response.get('session_id')
                if session_id:
                    # 缓存arkpass文件到本地
                    cache_dir = os.path.join(os.path.dirname(__file__), "cache")
                    if not os.path.exists(cache_dir):
                        os.makedirs(cache_dir)
                        
                    filename = os.path.basename(file_path)
                    cache_path = os.path.join(cache_dir, filename)
                    with open(cache_path, 'w', encoding='utf-8') as f:
                        json.dump(arkpass_data, f, indent=2)
                        
                    # 更新UI状态
                    self.is_logged_in = True
                    self.user_id = user_id
                    self.session_id = session_id
                    if hasattr(self, 'auth_status_label'):
                        self.auth_status_label.config(text="已登录", foreground='green')
                    if hasattr(self, 'user_info_text'):
                        self.user_info_text.delete(1.0, tk.END)
                        self.user_info_text.insert(tk.END, f"用户: {user_id}\n状态: 已连接\n会话ID: {session_id[:8]}...")
                     
                    # 更新云服务页面的用户信息显示
                    self.update_user_info_display()
                    
                    return True, None
                    
            else:
                # 处理不同的错误类型
                error_type = response.get('error_type', 'unknown')
                error_message = response.get('message', '未知错误')
                
                if error_type in ['user_not_found', 'invalid_api_key']:
                    # 用户不存在或密钥错误，应该删除缓存的arkpass文件
                    return False, error_message, error_type
                else:
                    # 其他错误类型（如封禁等）
                    return False, error_message, error_type
                    
        except Exception as e:
            self.log_message(f"登录失败: {e}", "auth", "ERROR")
            return False, f"登录过程发生异常: {str(e)}"
            
        return False, "未知错误"
        
    def auto_login_with_arkpass(self, arkpass_path):
        """自动使用arkpass文件登录"""
        result = self.login_with_arkpass(arkpass_path)
        if isinstance(result, tuple):
            success, error_msg, *error_type = result
            if not success and len(error_type) > 0:
                error_type_val = error_type[0]
                # 如果是用户不存在或密钥错误，删除缓存的arkpass文件
                if error_type_val in ['user_not_found', 'invalid_api_key']:
                    try:
                        os.remove(arkpass_path)
                        self.log_message(f"已删除无效的ArkPass文件: {arkpass_path}", "auth", "INFO")
                    except Exception as e:
                        self.log_message(f"删除ArkPass文件失败: {e}", "auth", "ERROR")
            return success, error_msg
        return result
        
    def refresh_user_info(self):
        """刷新用户信息"""
        if not self.is_logged_in:
            messagebox.showwarning("未登录", "请先登录后再查看云服务信息")
            return
            
        try:
            # 使用auth_manager获取用户信息（如果存在）
            if hasattr(self, 'auth_manager') and self.auth_manager:
                user_info = self.auth_manager.get_user_info()
            else:
                # 直接调用服务器API
                if self.communicator:
                    response = self.communicator.send_request("get_user_info", {
                        "user_id": self.user_id,
                        "session_id": self.session_id
                    })
                    if response and response.get('status') == 'success':
                        user_info = response.get('user_info')
                    else:
                        user_info = None
                else:
                    user_info = None
                    
            if user_info:
                self.update_user_info_display(user_info)
                self.log_message("用户信息已刷新", "cloud", "INFO")
            else:
                self.log_message("无法获取用户信息", "cloud", "ERROR")
                messagebox.showerror("错误", "无法获取用户信息，请检查网络连接")
                
        except Exception as e:
            self.log_message(f"刷新用户信息失败: {e}", "cloud", "ERROR")
            messagebox.showerror("错误", f"刷新用户信息失败: {str(e)}")
            
    def update_user_info_display(self, user_info=None):
        """更新用户信息显示"""
        if not self.is_logged_in:
            self.username_label.config(text="用户名: 未登录")
            self.tier_label.config(text="用户层级: -")
            self.daily_quota_label.config(text="每日配额: -/-")
            self.weekly_quota_label.config(text="每周配额: -/-")
            self.monthly_quota_label.config(text="每月配额: -/-")
            self.token_label.config(text="Token用量: -")
            self.expiry_label.config(text="")
            return
             
        if user_info is None:
            # 显示基本登录信息
            self.username_label.config(text=f"用户名: {self.user_id}")
            self.tier_label.config(text="用户层级: 加载中...")
            self.daily_quota_label.config(text="每日配额: 加载中...")
            self.weekly_quota_label.config(text="每周配额: 加载中...")
            self.monthly_quota_label.config(text="每月配额: 加载中...")
            self.token_label.config(text="Token用量: 加载中...")
            self.expiry_label.config(text="")
            return
             
        # 更新用户名
        self.username_label.config(text=f"用户名: {user_info.get('user_id', '未知')}")
         
        # 更新用户层级
        tier = user_info.get('tier', 'free')
        tier_names = {
            'free': '免费用户',
            'prime': 'Prime用户',
            'plus': 'Plus用户',
            'pro': '专业用户'
        }
        tier_display = tier_names.get(tier, tier)
        self.tier_label.config(text=f"用户层级: {tier_display}")
         
        # 更新每日配额使用情况
        quota_used = user_info.get('quota_used', 0)
        quota_daily = user_info.get('quota_daily', 1000)  # 使用正确的默认值1000
        self.daily_quota_label.config(text=f"每日配额: {quota_used}/{quota_daily}")
        
        # 更新每周配额使用情况（目前服务器不跟踪周/月使用量，只显示配额上限）
        quota_weekly = user_info.get('quota_weekly', 6000)
        self.weekly_quota_label.config(text=f"每周配额: 0/{quota_weekly}")
        
        # 更新每月配额使用情况
        quota_monthly = user_info.get('quota_monthly', 15000)
        self.monthly_quota_label.config(text=f"每月配额: 0/{quota_monthly}")
         
        # 更新Token用量
        total_tokens = user_info.get('total_tokens_used', 0)
        self.token_label.config(text=f"Token用量: {total_tokens}")
         
        # 更新到期时间（仅高层级用户）
        premium_until = user_info.get('premium_until', 0)
        if premium_until > 0:
            from datetime import datetime
            expiry_date = datetime.fromtimestamp(premium_until)
            self.expiry_label.config(text=f"高级权限到期: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.expiry_label.config(text="")
         
    def load_task_queue(self):
        """加载任务队列"""
        # 从本地文件加载持久化的任务队列
        cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        task_queue_file = os.path.join(cache_dir, "task_queue.json")
        
        if os.path.exists(task_queue_file):
            try:
                with open(task_queue_file, 'r', encoding='utf-8') as f:
                    self.task_queue = json.load(f)
                self.log_message("已从本地加载任务队列", "task", "INFO")
            except Exception as e:
                self.log_message(f"加载任务队列失败: {e}", "task", "ERROR")
                self.task_queue = []
        else:
            self.task_queue = []
            
        self.update_queue_display()
        
    def save_task_queue(self):
        """保存任务队列到本地"""
        cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        task_queue_file = os.path.join(cache_dir, "task_queue.json")
        try:
            with open(task_queue_file, 'w', encoding='utf-8') as f:
                json.dump(self.task_queue, f, ensure_ascii=False, indent=2)
            self.log_message("任务队列已保存到本地", "task", "INFO")
        except Exception as e:
            self.log_message(f"保存任务队列失败: {e}", "task", "ERROR")
        
    def update_queue_display(self):
        """更新任务队列显示"""
        self.task_queue_listbox.delete(0, tk.END)
        for task in self.task_queue:
            self.task_queue_listbox.insert(tk.END, f"{task.get('name', 'Unknown')}")
        self.queue_info_label.config(text=f"队列: {len(self.task_queue)}个任务")
        
    def scan_devices(self):
        """扫描设备"""
        if not self.adb_manager:
            self.log_message("ADB未初始化", "device", "ERROR")
            return
            
        self.log_message("正在扫描设备...", "device", "INFO")
        devices = self.adb_manager.get_devices(force_refresh=True)
        
        # 清空设备列表
        for item in self.device_tree.get_children():
            self.device_tree.delete(item)
            
        # 添加设备到列表
        last_device_selected = False
        for device in devices:
            item_id = self.device_tree.insert('', 'end', values=(
                device['serial'],
                device['model'] or 'Unknown',
                device['state']
            ))
            # 如果这是上次连接的设备，自动选中它
            if self.last_connected_device and device['serial'] == self.last_connected_device:
                self.device_tree.selection_set(item_id)
                last_device_selected = True
                
        if not last_device_selected and self.last_connected_device:
            # 如果上次连接的设备不在列表中，清空缓存
            self.last_connected_device = None
            
        self.log_message(f"发现 {len(devices)} 个设备", "device", "INFO")
        
    def connect_selected_device(self):
        """连接选中的设备"""
        selection = self.device_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个设备")
            return
            
        item = self.device_tree.item(selection[0])
        device_serial = item['values'][0]
        
        if self.adb_manager and self.adb_manager.connect_device(device_serial):
            self.current_device = device_serial
            self.device_status_label.config(text=f"已连接: {device_serial}", foreground='green')
            if self.touch_executor:
                self.touch_executor.set_current_device(device_serial)
            self.log_message(f"成功连接到设备: {device_serial}", "device", "INFO")
            
            # 保存设备信息
            self._save_last_connected_device(device_serial)
            
            # 更新屏幕预览
            self.update_screen_preview()
        else:
            messagebox.showerror("连接失败", "无法连接到选中的设备")
            self.log_message(f"连接设备失败: {device_serial}", "device", "ERROR")
            
    def manual_connect_device(self):
        """手动连接设备"""
        device_serial = self.manual_device_var.get().strip()
        if not device_serial:
            messagebox.showwarning("警告", "请输入设备序列号")
            return
            
        if self.adb_manager and self.adb_manager.connect_device_manual(device_serial):
            self.current_device = device_serial
            self.device_status_label.config(text=f"已连接: {device_serial}", foreground='green')
            if self.touch_executor:
                self.touch_executor.set_current_device(device_serial)
            self.log_message(f"成功连接到设备: {device_serial}", "device", "INFO")
            
            # 更新屏幕预览
            self.update_screen_preview()
        else:
            messagebox.showerror("连接失败", f"无法连接到设备: {device_serial}")
            self.log_message(f"连接设备失败: {device_serial}", "device", "ERROR")
            
    def disconnect_device(self):
        """断开设备连接"""
        if self.current_device:
            self.current_device = None
            self.device_status_label.config(text="未连接设备", foreground='gray')
            self.log_message("设备连接已断开", "device", "INFO")
            
    def update_screen_preview(self):
        """更新屏幕预览"""
        if not self.current_device or not self.screen_capture:
            return
            
        try:
            screen_data = self.screen_capture.capture_screen(self.current_device)
            if screen_data:
                # 解码Base64图像
                image_data = base64.b64decode(screen_data)
                image = Image.open(io.BytesIO(image_data))
                
                # 调整图像大小以适应预览区域
                canvas_width = self.preview_canvas.winfo_width()
                canvas_height = self.preview_canvas.winfo_height()
                
                if canvas_width > 1 and canvas_height > 1:
                    img_width, img_height = image.size
                    scale_x = canvas_width / img_width
                    scale_y = canvas_height / img_height
                    scale = min(scale_x, scale_y)
                    
                    new_width = int(img_width * scale)
                    new_height = int(img_height * scale)
                    
                    resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    self.current_image = ImageTk.PhotoImage(resized_image)
                    
                    self.preview_canvas.delete("all")
                    x = (canvas_width - new_width) // 2
                    y = (canvas_height - new_height) // 2
                    self.preview_canvas.create_image(x, y, anchor=tk.NW, image=self.current_image)
                    
        except Exception as e:
            self.log_message(f"屏幕预览更新失败: {e}", "device", "ERROR")
            
    def get_available_tasks_from_server(self):
        """从服务器获取可用任务列表"""
        if not self.is_logged_in:
            messagebox.showwarning("未登录", "请先登录后再获取任务列表")
            return []
            
        if not self.communicator:
            self.log_message("通信模块未初始化", "task", "ERROR")
            return []
            
        try:
            # 发送请求获取默认任务（可用任务）
            response = self.communicator.send_request("get_default_tasks", {})
            if response and response.get('status') == 'success':
                tasks = response.get('tasks', [])
                # 过滤掉不可见的任务
                visible_tasks = [task for task in tasks if task.get('visible', True)]
                self.log_message(f"成功从服务器获取 {len(visible_tasks)} 个可用任务", "task", "INFO")
                return visible_tasks
            else:
                error_msg = response.get('message', '未知错误') if response else '无响应'
                self.log_message(f"获取可用任务失败: {error_msg}", "task", "ERROR")
                return []
        except Exception as e:
            self.log_message(f"获取可用任务异常: {e}", "task", "ERROR")
            return []
            
    def show_add_task_dialog(self):
        """显示添加任务对话框"""
        if not self.is_logged_in:
            messagebox.showwarning("未登录", "请先登录后再添加任务")
            return
            
        # 从服务器获取可用任务
        available_tasks = self.get_available_tasks_from_server()
        if not available_tasks:
            messagebox.showinfo("提示", "暂无可用任务")
            return
            
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("添加任务")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 任务列表
        ttk.Label(dialog, text="选择要添加的任务:", font=('Arial', 10, 'bold')).pack(pady=10)
        
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        scrollbar.pack(side=tk.RIGHT, fill='y')
        
        task_listbox = tk.Listbox(
            list_frame,
            font=('Arial', 10),
            yscrollcommand=scrollbar.set
        )
        task_listbox.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.config(command=task_listbox.yview)
        
        # 填充任务列表
        for task in available_tasks:
            task_listbox.insert(tk.END, f"{task.get('name', '未知任务')} - {task.get('description', '')}")
            
        def on_add():
            selection = task_listbox.curselection()
            if not selection:
                messagebox.showwarning("警告", "请选择一个任务")
                return
                
            selected_task = available_tasks[selection[0]]
            self.add_task_to_queue(selected_task)
            dialog.destroy()
            
        def on_cancel():
            dialog.destroy()
            
        # 按钮
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="添加", command=on_add, style='Action.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
    def show_edit_task_dialog(self):
        """显示编辑任务对话框"""
        selection = self.task_queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个任务")
            return
            
        task_index = selection[0]
        task = self.task_queue[task_index]
        
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("设置任务")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 任务名称
        ttk.Label(dialog, text="任务名称:", font=('Arial', 10, 'bold')).pack(pady=(10, 5))
        name_var = tk.StringVar(value=task.get('custom_name', task.get('name', '')))
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.pack(pady=5)
        
        # 任务变量
        ttk.Label(dialog, text="任务变量:", font=('Arial', 10, 'bold')).pack(pady=(10, 5))
        
        variables_frame = ttk.Frame(dialog)
        variables_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        variables = task.get('variables', [])
        variable_entries = {}
        
        for var_def in variables:
            var_name = var_def.get('name', '')
            var_type = var_def.get('type', 'string')
            var_default = var_def.get('default', '')
            var_desc = var_def.get('desc', '')
            
            # 获取当前值（如果有）
            current_value = task.get('custom_variables', {}).get(var_name, var_default)
            
            var_frame = ttk.Frame(variables_frame)
            var_frame.pack(fill='x', pady=2)
            
            ttk.Label(var_frame, text=f"{var_name} ({var_type}):").pack(side=tk.LEFT)
            
            if var_type == 'bool':
                var_var = tk.BooleanVar(value=bool(current_value))
                var_entry = ttk.Checkbutton(var_frame, variable=var_var)
                var_entry.pack(side=tk.RIGHT)
            elif var_type == 'int':
                var_var = tk.StringVar(value=str(current_value))
                var_entry = ttk.Entry(var_frame, textvariable=var_var, width=10)
                var_entry.pack(side=tk.RIGHT)
            else:  # string or other types
                var_var = tk.StringVar(value=str(current_value))
                var_entry = ttk.Entry(var_frame, textvariable=var_var, width=20)
                var_entry.pack(side=tk.RIGHT)
                
            variable_entries[var_name] = (var_var, var_type)
            
            if var_desc:
                ttk.Label(var_frame, text=f" - {var_desc}", font=('Arial', 8)).pack(side=tk.LEFT, padx=(5, 0))
        
        def on_save():
            # 更新任务名称
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showwarning("警告", "任务名称不能为空")
                return
                
            task['custom_name'] = new_name
            task['name'] = new_name
            
            # 更新任务变量
            custom_vars = {}
            for var_name, (var_var, var_type) in variable_entries.items():
                value = var_var.get()
                if var_type == 'int':
                    try:
                        custom_vars[var_name] = int(value)
                    except ValueError:
                        custom_vars[var_name] = 0
                elif var_type == 'bool':
                    custom_vars[var_name] = bool(value)
                else:
                    custom_vars[var_name] = str(value)
                    
            task['custom_variables'] = custom_vars
            
            # 保存到本地持久化存储
            self.save_task_queue()
            
            self.update_queue_display()
            self.log_message(f"任务 '{new_name}' 已更新", "task", "INFO")
            dialog.destroy()
            
        def on_cancel():
            dialog.destroy()
            
        # 按钮
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="保存", command=on_save, style='Action.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
    def add_task_to_queue(self, task_template=None):
        """添加任务到队列"""
        if task_template is None:
            # 如果没有提供任务模板，使用默认任务
            if not self.task_manager:
                self.log_message("任务管理器未初始化", "execution", "ERROR")
                return
                
            tasks = self.task_manager.get_default_task_chain()
            if not tasks:
                self.log_message("未找到默认任务", "execution", "WARNING")
                return
                
            for task in tasks:
                self.task_queue.append(task)
            self.update_queue_display()
            self.log_message(f"已添加 {len(tasks)} 个默认任务到队列", "execution", "INFO")
            # 保存到本地持久化存储
            self.save_task_queue()
        else:
            # 添加指定的任务模板
            import time
            # 创建新的任务实例，使用不同的ID但相同的模板
            new_task = task_template.copy()
            new_task['id'] = f"{task_template['id']}_{int(time.time())}"
            new_task['name'] = task_template.get('name', '新任务')
            new_task['custom_name'] = new_task['name']  # 用于自定义名称
            self.task_queue.append(new_task)
            self.update_queue_display()
            self.log_message(f"已添加任务 '{new_task['name']}' 到队列", "task", "INFO")
            # 保存到本地持久化存储
            self.save_task_queue()
        
    def remove_task_from_queue(self):
        """从队列中移除任务"""
        selection = self.task_queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个任务")
            return
            
        index = selection[0]
        task_name = self.task_queue[index]['name']
        del self.task_queue[index]
        self.update_queue_display()
        self.log_message(f"任务 '{task_name}' 已从队列中移除", "execution", "INFO")
        # 保存到本地持久化存储
        self.save_task_queue()
        
    def clear_task_queue(self):
        """清空任务队列"""
        if messagebox.askyesno("确认", "确定要清空任务队列吗？"):
            self.task_queue = []
            self.update_queue_display()
            self.log_message("任务队列已清空", "execution", "INFO")
            # 保存到本地持久化存储
            self.save_task_queue()
            
    def on_execution_count_changed(self):
        """执行次数改变时的处理"""
        try:
            self.execution_count = self.execution_count_var.get()
            self.log_message(f"执行次数设置为: {self.execution_count}", "execution", "INFO")
        except tk.TclError:
            pass
            
    def start_llm_execution(self):
        """开始LLM执行"""
        if not self.is_logged_in:
            messagebox.showwarning("未登录", "请先登录后再执行任务")
            return
            
        if not self.current_device:
            messagebox.showwarning("警告", "请先连接设备")
            return
            
        if not self.task_queue:
            # 自动加载默认任务
            self.add_task_to_queue()
            if not self.task_queue:
                messagebox.showwarning("警告", "任务队列为空")
                return
            
        if self.client_running:
            messagebox.showwarning("警告", "执行已在进行中")
            return
            
        self.client_running = True
        self.llm_start_btn.config(state='disabled')
        self.llm_stop_btn.config(state='normal')
        
        self.client_thread = threading.Thread(target=self.run_automation, daemon=True)
        self.client_thread.start()
        
    def stop_llm_execution(self):
        """停止LLM执行"""
        self.client_running = False
        self.llm_start_btn.config(state='normal')
        self.llm_stop_btn.config(state='disabled')
        self.log_message("执行已停止", "execution", "INFO")
        
    def run_automation(self):
        """运行自动化流程"""
        self.log_message("开始自动化执行...", "execution", "INFO")
        
        total_executions = self.execution_count
        for execution in range(total_executions):
            if not self.client_running:
                break
                
            self.log_message(f"执行第 {execution + 1}/{total_executions} 次", "execution", "INFO")
            
            current_task_index = 0
            total_tasks = len(self.task_queue)
            
            while current_task_index < total_tasks and self.client_running:
                current_task = self.task_queue[current_task_index]
                task_id = current_task['id']
                
                self.root.after(0, lambda t=current_task: self.current_task_label.config(text=f"当前任务: {t['name']}"))
                self.root.after(0, lambda i=current_task_index, t=total_tasks: self.progress_var.set(f"进度: {i+1}/{t}"))
                
                self.log_message(f"执行任务: {current_task['name']}", "execution", "INFO")
                
                # 获取任务变量（包括自定义变量）
                task_variables = {}
                if 'custom_variables' in current_task:
                    task_variables.update(current_task['custom_variables'])
                elif self.task_manager:
                    task_variables.update(self.task_manager.get_task_variables(task_id))
                
                # 捕获屏幕
                if self.screen_capture and self.current_device:
                    screen_data = self.screen_capture.capture_screen(self.current_device)
                    if not screen_data:
                        self.log_message("屏幕捕获失败", "execution", "ERROR")
                        break
                else:
                    self.log_message("屏幕捕获模块未初始化或设备未连接", "execution", "ERROR")
                    break
                    
                # 获取设备信息
                if self.screen_capture and self.current_device:
                    device_info = self.screen_capture.get_device_info(self.current_device)
                else:
                    device_info = {'resolution': [1080, 1920], 'model': 'Unknown'}
                
                # 构建请求数据
                request_data = {
                    "user_id": self.user_id,
                    "session_id": self.session_id,
                    "device_image": screen_data.decode('utf-8') if screen_data else "",
                    "current_task": task_id,
                    "task_variables": task_variables,
                    "device_info": device_info
                }
                
                # 添加system_prompt字段（任务变量的JSON字符串）
                if task_variables:
                    import json as json_lib
                    request_data["system_prompt"] = json_lib.dumps(task_variables, ensure_ascii=False)
                
                # 发送请求到服务端
                if self.communicator:
                    response = self.communicator.send_request("process_image", request_data)
                else:
                    self.log_message("通信模块未初始化", "execution", "ERROR")
                    break
                
                if not response:
                    self.log_message("服务端处理失败: 无响应", "execution", "ERROR")
                    break
                    
                if response.get('status') != 'success':
                    error_message = response.get('message', '未知错误')
                    self.log_message(f"服务端处理失败: {error_message}", "execution", "ERROR")
                    break
                    
                # 执行触控动作
                touch_actions = response.get('data', {}).get('touch_actions', [])
                if touch_actions and self.touch_executor and self.current_device:
                    success = self.touch_executor.execute_touch_actions(self.current_device, touch_actions)
                    if not success:
                        self.log_message("触控执行失败", "execution", "ERROR")
                        break
                        
                # 检查任务是否完成
                task_completed = response.get('data', {}).get('task_completed', False)
                if task_completed:
                    self.log_message(f"任务 '{current_task['name']}' 完成", "execution", "INFO")
                    current_task_index += 1
                else:
                    # 任务未完成，继续当前任务
                    time.sleep(1)
                    
            if not self.client_running:
                break
                
        self.log_message("自动化执行结束", "execution", "INFO")
        self.root.after(0, lambda: self.stop_llm_execution())
        
            
    def log_message(self, message, category="general", level="INFO"):
        """记录日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{category.upper()}] {level}: {message}"
        self.log_text.insert(tk.END, log_entry + "\n")
        self.log_text.see(tk.END)
        self.status_bar.config(text=message)
        
    def on_closing(self):
        """窗口关闭事件"""
        # 保存任务队列到本地
        self.save_task_queue()
        
        if self.client_running:
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