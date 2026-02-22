"""主GUI管理器 - 协调所有GUI组件"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import os
import sys

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from managers.auth_manager_gui import AuthManagerGUI
from managers.device_manager_gui import DeviceManagerGUI
from managers.task_manager_gui import TaskManagerGUI
from managers.settings_manager_gui import SettingsManagerGUI
from managers.cloud_service_manager_gui import CloudServiceManagerGUI


class MainGUIManager:
    """主GUI管理器类"""
    
    def __init__(self, root, auth_manager, device_manager, execution_manager, 
                 task_queue_manager, config, log_callback):
        self.root = root
        self.auth_manager = auth_manager
        self.device_manager = device_manager
        self.execution_manager = execution_manager
        self.task_queue_manager = task_queue_manager
        self.config = config
        self.log_callback = log_callback
        
        # UI组件引用
        self.notebook = None
        self.execution_page_frame = None
        self.settings_page_frame = None
        self.cloud_service_page_frame = None
        self.status_bar = None
        self.content_notebook = None
        self.log_text = None
        self.vision_canvas = None
        self.full_content_text = None
        self.current_task_label = None
        self.progress_label = None
        self.progress_var = None
        
        # GUI管理器实例
        self.auth_gui = None
        self.device_gui = None
        self.task_gui = None
        self.settings_gui = None
        self.cloud_service_gui = None
        
        self.setup_main_ui()
        
    def setup_main_ui(self):
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
        
        # 状态栏
        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 设置各页面
        self.setup_execution_page()
        self.setup_settings_page()
        self.setup_cloud_service_page()
        
        # 启动后自动扫描设备
        self.root.after(100, self.auto_scan_and_connect_devices)
        
        # 绑定notebook切换事件
        self.notebook.bind('<<NotebookTabChanged>>', self.on_notebook_tab_changed)
        
    def setup_execution_page(self):
        """设置执行控制台页面"""
        frame = ttk.Frame(self.execution_page_frame, padding="10")
        frame.pack(fill='both', expand=True)
        
        # 左右分栏：任务队列在左，设备管理在右
        main_paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        main_paned.pack(fill='both', expand=True)
        
        # 左：任务队列区域
        queue_frame = ttk.Frame(main_paned)
        main_paned.add(queue_frame, weight=1)
        
        # 右：设备管理区域
        device_frame = ttk.Frame(main_paned)
        main_paned.add(device_frame, weight=2)
        
        # 创建任务管理GUI
        self.task_gui = TaskManagerGUI(
            queue_frame, 
            self.task_queue_manager, 
            self.execution_manager,
            self.log_callback
        )
        
        # 创建设备管理GUI
        self.device_gui = DeviceManagerGUI(
            device_frame,
            self.device_manager,
            self.execution_manager.screen_capture,
            self.log_callback
        )
        
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
        self.settings_gui = SettingsManagerGUI(
            self.settings_page_frame,
            self.config,
            self.log_callback
        )
        
    def setup_cloud_service_page(self):
        """设置云服务页面"""
        self.cloud_service_gui = CloudServiceManagerGUI(
            self.cloud_service_page_frame,
            self.auth_manager,
            self.log_callback
        )
        
    def on_notebook_tab_changed(self, event):
        """处理notebook标签页切换事件"""
        selected_tab = self.notebook.select()
        if selected_tab == str(self.cloud_service_page_frame):
            # 切换到云服务页面时自动刷新
            if self.auth_manager.get_login_status():
                self.cloud_service_gui.refresh_user_info()
                
    def get_log_text_widget(self):
        """获取日志文本控件"""
        return self.log_text
        
    def get_full_content_text_widget(self):
        """获取完整上下文文本控件"""
        return self.full_content_text
        
    def get_vision_canvas(self):
        """获取设备视觉画布"""
        return self.vision_canvas
        
    def update_current_task_display(self, task_name):
        """更新当前任务显示"""
        self.current_task_label.config(text=f"当前任务: {task_name}")
        
    def update_progress_display(self, current, total):
        """更新进度显示"""
        self.progress_var.set(f"进度: {current}/{total}")
        
    def auto_scan_and_connect_devices(self):
       """自动扫描设备并尝试连接上次的设备"""
       try:
           # 首先扫描设备
           if self.device_gui:
               self.device_gui.scan_devices()
               
           # 获取上次连接的设备
           last_device = self.device_manager.get_last_connected_device()
           if not last_device:
               self.log_callback("没有上次连接的设备记录，跳过自动连接", "device", "INFO")
               return
               
           # 检查设备是否在当前列表中
           current_device = self.device_manager.get_current_device()
           if current_device:
               self.log_callback(f"已有设备连接: {current_device}，跳过自动连接", "device", "INFO")
               return
               
           # 检查上次的设备是否可用
           devices = self.device_manager.scan_devices()
           available_devices = [d['serial'] for d in devices]
           self.log_callback(f"扫描到 {len(available_devices)} 个可用设备", "device", "INFO")
           
           if last_device in available_devices:
               # 自动连接设备
               if self.device_manager.connect_device(last_device):
                   # 更新GUI状态
                   if self.device_gui:
                       self.device_gui.update_device_status(f"已连接: {last_device}", 'green')
                       self.device_gui.update_screen_preview()
                   self.log_callback(f"自动连接到上次的设备: {last_device}", "device", "INFO")
               else:
                   self.log_callback(f"连接上次设备 {last_device} 失败", "device", "ERROR")
           else:
               self.log_callback(f"上次连接的设备 {last_device} 不在可用设备列表中", "device", "WARNING")
               # 清除无效的设备缓存
               self.device_manager.clear_last_connected_device()
                   
       except Exception as e:
           self.log_callback(f"自动扫描和连接设备时出错: {e}", "device", "ERROR")
   
    def stop_execution_ui(self):
       """停止执行的UI更新"""
       if self.task_gui:
           self.task_gui.llm_start_btn.config(state='normal')
           self.task_gui.llm_stop_btn.config(state='disabled')