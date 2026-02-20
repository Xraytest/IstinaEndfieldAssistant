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
    """ReAcrture客户端GUI主类（最终版）"""
    
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
        
        # 状态栏
        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
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
        
        # 上下分栏：设备管理在上，任务队列在下
        main_paned = ttk.PanedWindow(frame, orient=tk.VERTICAL)
        main_paned.pack(fill='both', expand=True)
        
        # 设备管理区域（上方）
        device_frame = ttk.Frame(main_paned)
        main_paned.add(device_frame, weight=1)
        
        # 设备连接区域
        conn_frame = ttk.LabelFrame(device_frame, text="设备连接", padding="10")
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
        device_list_frame = ttk.LabelFrame(device_frame, text="可用设备", padding="10")
        device_list_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # 设备列表
        self.device_tree = ttk.Treeview(device_list_frame, columns=('serial', 'model', 'state'), show='headings', height=6)
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
        device_btn_frame = ttk.Frame(device_frame)
        device_btn_frame.pack(fill='x')
        
        connect_device_btn = ttk.Button(device_btn_frame, text="连接选中设备", command=self.connect_selected_device)
        connect_device_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        disconnect_device_btn = ttk.Button(device_btn_frame, text="断开连接", command=self.disconnect_device)
        disconnect_device_btn.pack(side=tk.LEFT)
        
        # 屏幕预览
        preview_frame = ttk.LabelFrame(device_frame, text="屏幕预览", padding="10")
        preview_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        self.preview_canvas = tk.Canvas(preview_frame, bg='black', highlightthickness=0)
        self.preview_canvas.pack(fill='both', expand=True)
        
        # 任务队列区域（下方）
        queue_frame = ttk.Frame(main_paned)
        main_paned.add(queue_frame, weight=1)
        
        # 左右分栏
        paned = ttk.PanedWindow(queue_frame, orient=tk.HORIZONTAL)
        paned.pack(fill='both', expand=True)
        
        # 左：控制面板
        control_frame = ttk.Frame(paned)
        paned.add(control_frame, weight=1)
        
        # 任务队列管理（只显示，不编辑）
        task_queue_frame = ttk.LabelFrame(control_frame, text="任务队列", padding="10")
        task_queue_frame.pack(fill='x')
        
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
        
        # 执行控制
        exec_frame = ttk.LabelFrame(control_frame, text="执行控制", padding="10")
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
        
        # 右：Content Window
        content_frame = ttk.Frame(paned)
        paned.add(content_frame, weight=2)
        
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
        
    def setup_log_page(self):
        """设置执行日志页面"""
        frame = ttk.Frame(self.log_page_frame, padding="10")
        frame.pack(fill='both', expand=True)
        
        # 执行日志显示
        self.main_log_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=('Consolas', 9))
        self.main_log_text.pack(fill='both', expand=True)
        
        # 将log_text指向main_log_text以保持兼容性
        self.log_text = self.main_log_text
        
        
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
            
    def init_adb(self):
        """初始化ADB"""
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
            self.log_message("ADB初始化成功", "system", "INFO")
        except Exception as e:
            self.log_message(f"ADB初始化失败: {e}", "system", "ERROR")
            messagebox.showerror("初始化错误", f"ADB初始化失败: {e}")
            
    def check_login_status(self):
        """检查登录状态"""
        print("[DEBUG] 检查登录状态...")
        
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
        
        print(f"[DEBUG] 找到可能的arkpass文件: {unique_paths}")
        
        # 尝试每个arkpass文件
        for arkpass_path in unique_paths:
            print(f"[DEBUG] 尝试使用arkpass文件: {arkpass_path}")
            if self.auto_login_with_arkpass(arkpass_path):
                print("[DEBUG] 自动登录成功")
                return
                
        print("[DEBUG] 未找到有效的登录信息或自动登录失败")
        # 如果有arkpass文件但登录失败，显示错误提示
        if unique_paths:
            messagebox.showerror("自动登录失败", "找到ArkPass文件但自动登录失败，请检查文件格式或网络连接。")
            print("[DEBUG] 自动登录失败，显示错误提示")
        else:
            # 未找到arkpass文件，显示登录对话框
            print("[DEBUG] 未找到ArkPass文件，显示登录对话框")
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
                if self.login_with_arkpass(file_path):
                    messagebox.showinfo("登录成功", "登录成功！")
                else:
                    messagebox.showerror("登录失败", "ArkPass文件无效或登录失败。")
                    
        on_select_file()
        
    def register_user(self, username):
        """注册用户"""
        try:
            print(f"[DEBUG] 尝试注册用户: {username}")
            print(f"[DEBUG] Communicator对象: {self.communicator}")
            if self.communicator is None:
                print("[DEBUG] 错误: Communicator未初始化")
                return False, "通信器未初始化"
            # 调用服务端注册接口
            response = self.communicator.send_request("register", {"user_id": username})
            print(f"[DEBUG] 注册响应: {response}")
            if response and response.get('status') == 'success':
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
                    print(f"[DEBUG] 缓存目录: {cache_dir}")
                    if not os.path.exists(cache_dir):
                        os.makedirs(cache_dir)
                        print(f"[DEBUG] 创建缓存目录")
                        
                    arkpass_path = os.path.join(cache_dir, f"{username}.arkpass")
                    print(f"[DEBUG] ArkPass文件路径: {arkpass_path}")
                    try:
                        with open(arkpass_path, 'w', encoding='utf-8') as f:
                            json.dump(arkpass_data, f, indent=2)
                        print(f"[DEBUG] ArkPass文件保存成功")
                    except Exception as e:
                        print(f"[DEBUG] ArkPass文件保存失败: {e}")
                        return False
                        
                    # 更新UI状态
                    self.is_logged_in = True
                    self.user_id = username
                    if hasattr(self, 'auth_status_label'):
                        self.auth_status_label.config(text="已登录", foreground='green')
                    if hasattr(self, 'user_info_text'):
                        self.user_info_text.delete(1.0, tk.END)
                        self.user_info_text.insert(tk.END, f"用户: {username}\n状态: 已连接\nAPI密钥: {api_key[:8]}...")
                    
                    print(f"[DEBUG] 用户 {username} 注册成功")
                    return True, None
                else:
                    print("[DEBUG] 响应中缺少API密钥")
                    return False, "服务器响应中缺少API密钥"
            else:
                error_msg = response.get('message', '未知错误')
                print(f"[DEBUG] 注册失败，响应状态不正确: {response}")
                print(f"[DEBUG] 错误信息: {error_msg}")
                return False, error_msg
                    
        except Exception as e:
            import traceback
            print(f"[DEBUG] 注册异常: {e}")
            print(f"[DEBUG] 异常详情: {traceback.format_exc()}")
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
                    return False
            
            if not user_id or not api_key:
                return False
                
            # 调用服务端登录接口
            response = self.communicator.send_request("login", {
                "user_id": user_id,
                "key": api_key
            })
            
            if response and response.get('status') == 'success':
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
                    
                    return True
                    
        except Exception as e:
            self.log_message(f"登录失败: {e}", "auth", "ERROR")
            
        return False
        
    def auto_login_with_arkpass(self, arkpass_path):
        """自动使用arkpass文件登录"""
        return self.login_with_arkpass(arkpass_path)
        
    def load_task_queue(self):
        """加载任务队列"""
        self.update_queue_display()
        
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
            
        if self.adb_manager and self.adb_manager.connect_device(device_serial):
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
            
    def add_task_to_queue(self):
        """添加任务到队列（从服务端获取默认任务）"""
        if not self.is_logged_in:
            messagebox.showwarning("未登录", "请先登录后再执行任务")
            return
            
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
        
    def clear_task_queue(self):
        """清空任务队列"""
        if messagebox.askyesno("确认", "确定要清空任务队列吗？"):
            self.task_queue = []
            self.update_queue_display()
            self.log_message("任务队列已清空", "execution", "INFO")
            
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
                
                # 获取任务变量
                if self.task_manager:
                    task_variables = self.task_manager.get_task_variables(task_id)
                else:
                    task_variables = {}
                
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