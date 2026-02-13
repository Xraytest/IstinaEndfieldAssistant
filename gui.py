#gui.py

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog, filedialog
import threading
import time
import os
import json
import base64
import requests
import traceback
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from PIL import Image, ImageTk
import io
import random
import sys
import subprocess
import shutil

# 导入android_control模块
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
try:
    from android_control import (
        find_adb_device_list,
        connect_adb_device,
        click,  # 仅紧急回退
        swipe,
        input_text,
        click_key,
        screencap,
        get_current_datetime,
        KeyCode,
        add_network_device,
        disconnect_device,
        check_network_device_status,
        list_network_devices,
        get_device_resolution  # <--- 添加这一行
    )
    IMPORT_SUCCESS = True
except ImportError as e:
    # 使用临时列表存储导入错误
    _temp_log = []
    _temp_log.append(f"导入错误: {e}")
    IMPORT_SUCCESS = False

# 导入VLM客户端
# 先定义为None
llm_requests = None
try:
    from utils.vlm_transportation.to_llama_server import llm_requests
    VLM_AVAILABLE = True
except ImportError as e:
    _temp_log.append(f"VLM导入错误: {e}")
    VLM_AVAILABLE = False

# 导入云服务客户端
try:
    from utils.tcp_client import CloudClient
    CLOUD_AVAILABLE = True
except ImportError as e:
    _temp_log.append(f"云服务导入错误: {e}")
    CLOUD_AVAILABLE = False


class LLMTaskAutomationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LLM Task Automation v2.3 - 任务队列支持")
        self.root.geometry("1600x950")
        self.root.minsize(1400, 900)

        # 处理导入错误的临时日志
        if globals().get('_temp_log'):
            for msg in globals()['_temp_log']:
                self.log_message(f"模块导入: {msg}", "system", "Error")

        if not IMPORT_SUCCESS:
            messagebox.showerror("导入错误", "无法导入android_control模块，请检查utils目录")
            self.root.destroy()
            return

        if not VLM_AVAILABLE:
            messagebox.showwarning("VLM警告", "VLM服务器客户端不可用，将使用模拟模式")

        if not CLOUD_AVAILABLE:
            messagebox.showwarning("云服务警告", "云服务客户端不可用，云功能将被禁用")

        # 状态变量
        self.controller_id = None
        self.current_device = None
        self.current_image = None
        self.image_scale_x = 1.0
        self.image_scale_y = 1.0
        
        # LLM任务管理
        self.task_templates = self.load_default_templates()
        self.current_task_group = self.load_current_task_group()
        self.current_subtasks = []
        self.knowledge_base = self.load_knowledge_base()

        # 添加UI助手函数
        self.create_btn = self._create_btn
        self.create_label = self._create_label

        # 安全参数
        self.press_duration_ms = 100  # 默认按压时长
        self.press_jitter_px = 2      # 随机抖动范围

        # 设备缓存
        self.device_cache = self.load_device_cache()
        # 添加：上次成功设备
        self.last_successful_device = self.load_last_successful_device()

        # 添加分辨率缓存
        self.cached_resolution = None  # 缓存的设备分辨率 (width, height)
        self.resolution_verified = False  # 分辨率是否已验证

        # 执行状态
        self.llm_running = False
        self.llm_stop_flag = False
        self.llm_thread = None

        # 任务队列 - 新增
        self.task_queue = []  # 每个元素格式:
        # {
        #     "template_id": str,           # 任务模板ID
        #     "template_copy": dict,        # 模板的深拷贝（独立修改）
        #     "task_settings": dict,        # 任务特定设置
        #     "variables_override": dict,   # 变量覆盖值
        #     "enabled": bool,             # 任务是否启用
        #     "order": int                 # 显示顺序
        # }
        self.current_task_index = 0  # 当前执行的任务索引

        # 执行次数设置
        self.execution_count = 1  # 默认执行次数
        self.load_execution_count()  # 启动时读取

        # VLM工具定义（OpenAI格式）
        self.tools = self.define_vlm_tools()
        
        # 创建UI
        self.setup_styles()
        self.setup_ui()
        
        # 初始化
        self.scan_devices()
        self.update_time()
        # 加载任务队列
        self.task_queue = self.load_task_queue()

        # --- 自动检测并部署模型 ---
        self._check_and_deploy_vlm_model()

        # --- 自动检测并登录云服务 ---
        self.root.after(1000, self.auto_check_and_login_cloud)

    def _create_btn(self, parent, text, cmd=None, style=None, side=tk.LEFT, **kwargs):
        """创建按钮的辅助函数"""
        # 分离 pack 参数和按钮参数
        pack_params = {}
        button_params = {}

        # 定义 pack 方法接受的参数
        pack_options = {'after', 'anchor', 'before', 'expand', 'fill', 'in', 'ipadx', 'ipady', 'padx', 'pady', 'side'}

        # 分离参数
        for key, value in kwargs.items():
            if key in pack_options:
                pack_params[key] = value
            else:
                button_params[key] = value

        # 设置默认的 pack 参数
        default_pack_params = {'side': side, 'padx': 5, 'pady': 2}
        default_pack_params.update(pack_params)

        # 创建按钮并应用按钮参数
        btn = ttk.Button(parent, text=text, command=cmd, style=style, **button_params)
        btn.pack(**default_pack_params)
        return btn

    def _create_label(self, parent, text, style=None, side=tk.LEFT, **kwargs):
        """创建标签的辅助函数"""
        # 分离 pack 参数和标签参数
        pack_params = {}
        label_params = {}

        # 定义 pack 方法接受的参数
        pack_options = {'after', 'anchor', 'before', 'expand', 'fill', 'in', 'ipadx', 'ipady', 'padx', 'pady', 'side'}

        # 分离参数
        for key, value in kwargs.items():
            if key in pack_options:
                pack_params[key] = value
            else:
                label_params[key] = value

        # 设置默认的 pack 参数
        default_pack_params = {'side': side, 'padx': 5, 'pady': 2}
        default_pack_params.update(pack_params)

        # 创建标签并应用标签参数
        label = ttk.Label(parent, text=text, style=style, **label_params)
        label.pack(**default_pack_params)
        return label

    def define_vlm_tools(self) -> List[Dict]:
        """从配置文件加载VLM工具定义"""
        try:
            config_path = "config/tools_config.json"
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                self.log_message("已删除开发用Mock和尾部冗余代码", "all", "INFO")
                return self._get_default_tools()
        except Exception as e:
            self.log_message(f"加载工具配置失败: {str(e)}，使用默认工具集", "llm", "ERROR")
            return self._get_default_tools()

    def _get_default_tools(self) -> List[Dict]:
        """返回默认的VLM工具集（OpenAI格式）"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "safe_press",
                    "description": "安全按压模拟（通过滑动模拟点击）。必须使用比例坐标(0.0-1.0)，左上角(0,0)，右下角(1,1)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "x": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "目标x坐标（比例，0.0-1.0）"
                            },
                            "y": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "目标y坐标（比例，0.0-1.0）"
                            },
                            "duration_ms": {
                                "type": "integer",
                                "description": "按压时长（毫秒），默认100",
                                "default": 100
                            },
                            "purpose": {
                                "type": "string",
                                "description": "操作目的描述（必须说明为什么点击此处）"
                            }
                        },
                        "required": ["x", "y", "purpose"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "safe_swipe",
                    "description": "安全滑动操作，用于页面滚动或拖拽元素",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_x": {"type": "integer", "description": "起始x坐标"},
                            "start_y": {"type": "integer", "description": "起始y坐标"},
                            "end_x": {"type": "integer", "description": "结束x坐标"},
                            "end_y": {"type": "integer", "description": "结束y坐标"},
                            "duration_ms": {"type": "integer", "description": "滑动时长（毫秒），默认300", "default": 300},
                            "purpose": {"type": "string", "description": "滑动目的描述"}
                        },
                        "required": ["start_x", "start_y", "end_x", "end_y", "purpose"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "wait",
                    "description": "等待指定时间，用于界面加载或动画播放",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "duration_ms": {"type": "integer", "description": "等待时长（毫秒）", "minimum": 100, "maximum": 5000},
                            "purpose": {"type": "string", "description": "等待原因"}
                        },
                        "required": ["duration_ms", "purpose"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "input_text",
                    "description": "向设备输入文本（如聊天、搜索框）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "要输入的文本"},
                            "purpose": {"type": "string", "description": "输入目的"}
                        },
                        "required": ["text", "purpose"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "press_key",
                    "description": "模拟物理按键（BACK/HOME）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string", "enum": ["BACK", "HOME"], "description": "按键类型"},
                            "purpose": {"type": "string", "description": "按键目的"}
                        },
                        "required": ["key", "purpose"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_subtask",
                    "description": "创建新的子任务（动态任务分解）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "desc": {"type": "string", "description": "子任务描述"},
                            "parent_id": {"type": "string", "description": "父任务ID（可选，用于嵌套）"}
                        },
                        "required": ["desc"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_subtask_status",
                    "description": "更新子任务状态（pending/in_progress/completed）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "子任务ID"},
                            "status": {"type": "string", "enum": ["pending", "in_progress", "completed"], "description": "新状态"},
                            "notes": {"type": "string", "description": "状态更新备注"}
                        },
                        "required": ["task_id", "status"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_knowledge_entry",
                    "description": "向持久化知识库添加新词条（图文结合）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["button", "enemy", "ally", "resource", "ui_element"], "description": "词条类型"},
                            "content": {"type": "string", "description": "描述文本"},
                            "x_ratio": {"type": "number", "minimum": 0.0, "maximum": 1.0, "description": "中心点x坐标比例（0.0-1.0）"},
                            "y_ratio": {"type": "number", "minimum": 0.0, "maximum": 1.0, "description": "中心点y坐标比例（0.0-1.0）"},
                            "width_ratio": {"type": "number", "minimum": 0.01, "maximum": 1.0, "description": "宽度比例"},
                            "height_ratio": {"type": "number", "minimum": 0.01, "maximum": 1.0, "description": "高度比例"},
                            "purpose": {"type": "string", "description": "添加此知识的目的"}
                        },
                        "required": ["type", "content", "x_ratio", "y_ratio", "width_ratio", "height_ratio", "purpose"]
                    }
                }
            }
        ]

    def setup_styles(self):
        """配置UI样式"""
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except tk.TclError:
            # 如果clam主题不可用，忽略并使用默认主题
            pass
        
        # 按钮样式
        style.configure('Action.TButton', padding=6)
        style.configure('Accent.TButton', background='#2196F3', foreground='white')
        style.map('Accent.TButton', background=[('active', '#1976D2')])
        style.configure('Stop.TButton', background='#f44336', foreground='white')
        style.map('Stop.TButton', background=[('active', '#d32f2f')])
        style.configure('Security.TButton', background='#9C27B0', foreground='white')
        style.map('Security.TButton', background=[('active', '#7B1FA2')])
        
        # 状态标签
        style.configure('Status.Ready.TLabel', foreground='#4CAF50', font=('Arial', 10, 'bold'))
        style.configure('Status.Running.TLabel', foreground='#ff9800', font=('Arial', 10, 'bold'))
        style.configure('Status.Error.TLabel', foreground='#f44336', font=('Arial', 10, 'bold'))
        style.configure('Status.Complete.TLabel', foreground='#2196F3', font=('Arial', 10, 'bold'))
        style.configure('Status.Security.TLabel', foreground='#9C27B0', font=('Arial', 10, 'bold'))

        # 子任务状态颜色
        style.configure('Subtask.Pending.TLabel', foreground='#9e9e9e', font=('Arial', 9))
        style.configure('Subtask.InProgress.TLabel', foreground='#ff9800', font=('Arial', 9, 'bold'))
        style.configure('Subtask.Completed.TLabel', foreground='#4CAF50', font=('Arial', 9))
    
    def setup_ui(self):
        """设置主UI - 三页面设计，LLM控制台在最前"""
        # 顶部状态栏
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))

        # 添加分辨率显示
        self.resolution_status = ttk.Label(self.status_bar, text="分辨率: 未知", width=25)
        self.resolution_status.pack(side=tk.LEFT, padx=5)

        self.device_status = ttk.Label(self.status_bar, text="设备: 未连接", width=30)
        self.device_status.pack(side=tk.LEFT, padx=5)
        self.network_status = ttk.Label(self.status_bar, text="网络: 未连接", width=20)
        self.network_status.pack(side=tk.LEFT, padx=5)
        # VLM状态标记（已移除显示，但仍保留占位符）
        self.vlm_status = ttk.Label(self.status_bar, text="", width=0)
        self.vlm_status.pack(side=tk.LEFT, padx=5)
        self.app_status = ttk.Label(self.status_bar, text="就绪", width=20)
        self.app_status.pack(side=tk.LEFT, padx=5)
        self.time_label = ttk.Label(self.status_bar, text="", font=('Arial', 9))
        self.time_label.pack(side=tk.RIGHT, padx=5)

        # 主Notebook - 修改：LLM控制台在最前
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)

        # 页面框架 - 修改顺序：LLM控制台最前
        self.llm_page_frame = ttk.Frame(self.notebook)
        self.test_page_frame = ttk.Frame(self.notebook)
        self.designer_page_frame = ttk.Frame(self.notebook)
        self.cloud_page_frame = ttk.Frame(self.notebook)

        # 添加页面 - 修改顺序，云服务移至第二位
        self.notebook.add(self.llm_page_frame, text='开始代理')
        self.notebook.add(self.cloud_page_frame, text='云服务')
        self.notebook.add(self.test_page_frame, text='基础测试')
        self.notebook.add(self.designer_page_frame, text='LLM任务设计器')

        # 设置页面
        self.setup_llm_page()  # 先设置LLM页面
        self.setup_test_page()
        self.setup_designer_page()
        self.setup_cloud_page()

        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def update_time(self):
        """更新时间显示"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.time_label.config(text=f"🕒 {current_time}")
        except (AttributeError, tk.TclError):
            # 忽略时间更新错误（可能GUI还未完全初始化）
            pass
        self.root.after(1000, self.update_time)
    
    def log_message(self, message: str, page: str = "all", level: str = "INFO"):
        """
        线程安全的日志记录：使用 after() 将 UI 更新派发回主线程
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {message}\n"

        # ERROR级别消息同时输出到控制台 - 使用标准error输出
        if level == "ERROR":
            pass

        def _update():
            # 这部分代码最终会在主线程执行
            targets = {
                "test": getattr(self, 'test_log_text', None),
                "designer": getattr(self, 'designer_log_text', None),
                "llm": getattr(self, 'llm_log_text', None)
            }
            for p in ([page] if page != "all" else ["test", "designer", "llm"]):
               if p in targets and targets[p]:
                   targets[p].insert(tk.END, formatted)
                   targets[p].see(tk.END)

        # 0毫秒后立即在主线程执行 _update
        self.root.after(0, _update)
    
    def load_device_cache(self) -> List[str]:
        """加载缓存的设备列表"""
        try:
            cache_path = "config/device_cache.json"
            if os.path.exists(cache_path):
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (OSError, json.JSONDecodeError):
            # 文件不存在、权限问题或JSON格式错误时返回空列表
            pass
        return []

    def load_last_successful_device(self) -> Optional[str]:
        """加载上次成功连接的设备"""
        try:
            cache_path = "config/last_device.json"
            if os.path.exists(cache_path):
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('device_id')
        except (OSError, json.JSONDecodeError):
            # 文件不存在、权限问题或JSON格式错误时返回None
            pass
        return None

    def load_device_address(self) -> Optional[str]:
        """加载上次成功连接的设备地址"""
        return self.load_last_successful_device()

    def connect_device_by_address(self, device_address: str) -> bool:
        """通过地址连接设备"""
        try:
            # 使用connect_adb_device方法连接设备
            controller_id = connect_adb_device(device_address)
            if controller_id:
                self.controller_id = controller_id
                self.current_device = device_address
                self.save_last_successful_device(device_address)
                return True
            return False
        except Exception as e:
            self.log_message(f"连接设备失败: {str(e)}", "llm", "ERROR")
            return False

    def save_last_successful_device(self, device_id: str):
        """保存上次成功连接的设备"""
        try:
            os.makedirs("config", exist_ok=True)
            with open("config/last_device.json", 'w', encoding='utf-8') as f:
                json.dump({'device_id': device_id, 'timestamp': datetime.now().isoformat()},
                         f, ensure_ascii=False, indent=2)
        except (OSError, json.JSONEncodeError) as e:
            if hasattr(self, 'log_message'):
                self.log_message(f"保存设备配置失败: {str(e)}", "system", "ERROR")

    def save_device_cache(self):
        """保存设备缓存"""
        try:
            os.makedirs("config", exist_ok=True)
            with open("config/device_cache.json", 'w', encoding='utf-8') as f:
                json.dump(self.device_cache, f, ensure_ascii=False, indent=2)
        except (OSError, json.JSONEncodeError) as e:
            if hasattr(self, 'log_message'):
                self.log_message(f"保存设备缓存失败: {str(e)}", "system", "ERROR")

    def load_execution_count(self):
        """加载执行次数配置"""
        try:
            config_path = "config/config.json"
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.execution_count = config.get('execution_count', 1)
        except (OSError, json.JSONDecodeError):
            # 文件不存在、权限问题或JSON格式错误时使用默认值
            self.execution_count = 1

    def save_execution_count(self):
        """保存执行次数配置"""
        try:
            config_path = "config/config.json"
            config = {}

            # 读取现有配置
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            # 更新执行次数
            config['execution_count'] = self.execution_count

            # 保存配置
            os.makedirs("config", exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

        except (OSError, json.JSONEncodeError) as e:
            if hasattr(self, 'log_message'):
                self.log_message(f"保存执行次数配置失败: {str(e)}", "system", "ERROR")

    def on_execution_count_changed(self):
        """执行次数变化时的回调"""
        new_count = self.execution_count_var.get()
        if new_count != self.execution_count:
            self.execution_count = new_count
            self.save_execution_count()

    def on_continuous_loop_changed(self):
        """当持续循环选项改变时处理"""
        if self.continuous_loop_var.get():
            # 如果选中持续循环，禁用执行次数输入
            self.execution_count_entry.config(state='disabled')
            self.log_message("已启用持续循环模式", "system")
        else:
            # 如果取消持续循环，启用执行次数输入
            self.execution_count_entry.config(state='normal')
            self.log_message("已取消持续循环模式", "system")

    def manual_input_device(self, page: str):
        """手动输入设备ID"""
        dialog = tk.Toplevel(self.root)
        dialog.title("手动输入设备")
        dialog.geometry("600x250")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="手动输入设备地址", font=('Arial', 11, 'bold')).pack(pady=10)

        # 设备地址输入
        addr_frame = ttk.Frame(dialog)
        addr_frame.pack(fill='x', padx=20, pady=10)
        ttk.Label(addr_frame, text="设备地址:").pack(side=tk.LEFT)
        addr_var = tk.StringVar()
        ttk.Entry(addr_frame, textvariable=addr_var, width=30).pack(side=tk.LEFT, padx=5)

        # 说明（简化）
        ttk.Label(dialog, text="支持格式:", font=('Arial', 9, 'bold')).pack(anchor=tk.W, padx=20, pady=(5,0))
        ttk.Label(dialog, text="• USB设备: device_serial", font=('Arial', 9)).pack(anchor=tk.W, padx=40)
        ttk.Label(dialog, text="• 网络设备: IP:端口 (自动尝试两种连接方式)", font=('Arial', 9)).pack(anchor=tk.W, padx=40)

        def save_device():
            device_id = addr_var.get().strip()
            if not device_id:
                messagebox.showwarning("警告", "请输入设备地址")
                return

            # 更新对应页面的下拉框
            combo_map = {
                "test": self.test_device_combo,
                "designer": self.designer_device_combo,
            }

            # 只有当llm_device_combo存在时才添加到映射中
            if hasattr(self, 'llm_device_combo'):
                combo_map["llm"] = self.llm_device_combo

            combo = combo_map.get(page)
            if combo:
                combo.set(device_id)

                # 添加到缓存
                if device_id not in self.device_cache:
                    self.device_cache.append(device_id)
                    self.save_device_cache()
                    self.log_message(f"手动添加设备到缓存: {device_id}", page)

                    # 更新所有下拉框的值
                    self.update_device_list([])

                # 自动尝试连接
                dialog.destroy()
                self.connect_device(page)

        # 按钮框架
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="保存并连接",
                  command=save_device, style='Security.TButton').pack(side=tk.LEFT, padx=5)
        self.create_btn(btn_frame, "取消", dialog.destroy)

    def clear_device_cache(self):
        """清除设备缓存"""
        if messagebox.askyesno("确认", "确定清除所有缓存的设备？"):
            self.device_cache = []
            self.save_device_cache()
            self.update_device_list([])
            self.log_message("设备缓存已清除", "all")

    # ==================== 设备管理 ====================
    def scan_devices(self):
        """扫描ADB设备（包括网络设备）"""
        self.log_message("正在扫描ADB设备...", "all")

        def scan_thread():
            try:
                # 获取USB设备
                devices = find_adb_device_list()
                if not isinstance(devices, (list, tuple)):
                    if isinstance(devices, str) and ("error:" in devices.lower() or "device" in devices.lower()):
                        raise RuntimeError(f"ADB命令失败: {devices.strip()[:200]}")
                    raise TypeError(f"find_adb_device_list() 应返回列表，但得到 {type(devices).__name__}")

                # 获取网络设备
                try:
                    network_devices = list_network_devices()
                    if network_devices:
                        devices.extend(network_devices)
                except Exception as e:
                    # 网络设备列表获取失败，忽略具体错误
                    self.log_message(f"网络设备扫描失败，继续本地设备扫描: {str(e)}", "all", "INFO")
                    pass

                normalized_devices = []
                for dev in devices:
                    dev_id = None
                    if isinstance(dev, dict):
                        for key in ['id', 'serial', 'device_id', 'model']:
                            if key in dev and isinstance(dev[key], str) and dev[key].strip():
                                dev_id = dev[key].strip()
                                break
                    elif isinstance(dev, str) and dev.strip():
                        dev_id = dev.strip()
                    if dev_id and dev_id not in ['?', 'unknown', 'offline', 'unauthorized']:
                        normalized_devices.append(dev_id)

                normalized_devices = list(dict.fromkeys(normalized_devices))
                self.root.after(0, self.update_device_list, normalized_devices)
            except Exception as e:
                error_msg = f"设备扫描失败: {str(e)}"
                self.root.after(0, self.log_message, error_msg, "all", "ERROR")
                self.root.after(0, self.update_device_list, [])

        threading.Thread(target=scan_thread, daemon=True).start()
    
    def update_device_list(self, devices: List[str]):
        """更新设备列表，合并扫描结果和缓存，优先显示上次成功设备"""
        # 合并扫描到的设备和缓存设备，去重
        all_devices = list(dict.fromkeys(devices + self.device_cache))

        # 如果存在上次成功设备，将其移到列表前面
        if self.last_successful_device and self.last_successful_device in all_devices:
            all_devices.remove(self.last_successful_device)
            all_devices.insert(0, self.last_successful_device)

        # 更新所有页面的设备下拉框
        combos = []
        if hasattr(self, 'test_device_combo'):
            combos.append(self.test_device_combo)
        if hasattr(self, 'designer_device_combo'):
            combos.append(self.designer_device_combo)
        if hasattr(self, 'llm_device_combo'):
            combos.append(self.llm_device_combo)

        for combo in combos:
            # 设置下拉列表值
            combo['values'] = all_devices if all_devices else ["未检测到设备"]
            # 如果上次成功设备存在，则默认选择它
            if self.last_successful_device and self.last_successful_device in all_devices:
                combo.set(self.last_successful_device)

        # 更新状态栏
        if all_devices:
            display = ', '.join(all_devices[:3])
            if len(all_devices) > 3:
                display += f" ... (+{len(all_devices)-3}个)"
            self.device_status.config(text=f"{all_devices[0]}", style='Status.Ready.TLabel')
            self.log_message(f"找到 {len(all_devices)} 个设备: {display}", "all")
        else:
            self.device_status.config(text="无设备", style='Status.Error.TLabel')
            self.log_message("未找到可用设备", "all")
    
    def connect_device(self, page: str = "test"):
        """连接设备，先尝试USB连接，失败则尝试网络连接"""
        device_map = {
            "test": "test_device_combo",
            "designer": "designer_device_combo"
        }

        # 只有当llm_device_combo存在时才添加到映射中
        if hasattr(self, 'llm_device_combo'):
            device_map["llm"] = "llm_device_combo"
        combo_attr = device_map.get(page)
        if not combo_attr or not hasattr(self, combo_attr):
            return

        device_id = getattr(self, combo_attr).get().strip()

        if not device_id or device_id in ["未检测到设备", "未连接", ""]:
            messagebox.showwarning("警告", "请输入或选择有效设备ID")
            return

        # 记录当前尝试连接的设备
        self.log_message(f"正在连接设备: {device_id}", page)
        self.app_status.config(text="连接中...", style='Status.Running.TLabel')

        # 首先尝试直接连接（USB方式）
        self.log_message("  1. 尝试USB连接...", page)

        def connect_thread():
            try:
                # 第一步：尝试USB连接
                controller_id = connect_adb_device(device_id)

                if controller_id and controller_id.strip():
                    # USB连接成功
                    self.root.after(0, self.on_connect_success, controller_id, device_id, page, "USB")
                    return

                # USB连接失败，检查是否为网络设备格式
                is_network_format = ':' in device_id and '.' in device_id.split(':')[0]

                if is_network_format:
                    # 第二步：尝试网络连接
                    self.root.after(0, self.log_message, "  2. USB连接失败，尝试网络连接...", page)

                    try:
                        # 解析IP和端口
                        ip, port = device_id.split(':')

                        # 添加网络设备
                        self.root.after(0, self.log_message, f"   -> 添加网络设备 {ip}:{port}", page)
                        success = add_network_device(ip, port)

                        if success:
                            # 等待设备出现
                            time.sleep(2)

                            # 重新尝试连接
                            controller_id = connect_adb_device(device_id)

                            if controller_id and controller_id.strip():
                                # 网络连接成功
                                self.root.after(0, self.on_connect_success, controller_id, device_id, page, "网络")
                                return

                        # 网络连接也失败
                        error_msg = f"网络设备连接失败: {device_id}"
                        self.root.after(0, self.on_connect_failed, device_id, error_msg, page)

                    except Exception as net_e:
                        error_msg = f"网络连接失败: {str(net_e)}"
                        self.root.after(0, self.on_connect_failed, device_id, error_msg, page)
                else:
                    # 不是网络格式，直接失败
                    error_msg = "USB连接失败，设备ID不是网络格式"
                    self.root.after(0, self.on_connect_failed, device_id, error_msg, page)

            except Exception as e:
                error_msg = f"连接过程异常: {str(e)}"
                self.root.after(0, self.on_connect_failed, device_id, error_msg, page)

        threading.Thread(target=connect_thread, daemon=True).start()

    def continue_connect_device(self, device_id: str, page: str):
        """继续连接网络设备"""
        self.log_message(f"🔌 继续连接网络设备: {device_id}", page)

        def connect_thread():
            try:
                controller_id = connect_adb_device(device_id)
                if controller_id and controller_id.strip():
                    self.root.after(0, self.on_connect_success, controller_id, device_id, page, "网络")
                else:
                    raise RuntimeError("网络设备连接返回空ID")
            except Exception as e:
                self.root.after(0, self.on_connect_failed, device_id, str(e), page)

        threading.Thread(target=connect_thread, daemon=True).start()
    
    def on_connect_success(self, controller_id: str, device_id: str, page: str, connection_type: str = "USB"):
        """连接成功"""
        def _update():
            self.controller_id = controller_id
            self.current_device = device_id

            # 保存为上次成功设备
            self.last_successful_device = device_id
            self.save_last_successful_device(device_id)

            # 添加到缓存（如果不存在）
            if device_id not in self.device_cache:
                self.device_cache.append(device_id)
                self.save_device_cache()

            self.device_status.config(text=f"{device_id}", style='Status.Ready.TLabel')

            # 更新网络状态显示
            if connection_type == "网络":
                self.network_status.config(text=f"{device_id}", style='Status.Ready.TLabel')
            else:
                self.network_status.config(text="USB设备", style='Status.Ready.TLabel')

            self.app_status.config(text="就绪", style='Status.Ready.TLabel')
            self.log_message(f"连接成功 ({connection_type}): {device_id}", page)

        self.root.after(0, _update)

        # 立即获取设备分辨率
        def get_resolution_after_connect():
            try:
                width, height = self.get_device_resolution()
                self.log_message(f"设备分辨率: {width}x{height}", page)

                # 更新UI显示分辨率
                self.update_resolution_display(width, height, page)

            except Exception as e:
                error_msg = f"连接后获取分辨率失败: {str(e)}"
                self.log_message(error_msg, page, "ERROR")
                # 移除冗余的控制台输出，log_message已经处理了ERROR级别的输出

        # 在新线程中获取分辨率
        threading.Thread(target=get_resolution_after_connect, daemon=True).start()

        if page == "test":
            # 延迟一点再截图，确保设备稳定
            self.root.after(1000, self.take_screenshot)
    
    def on_connect_failed(self, device_id: str, error: str, page: str):
        """连接失败"""
        def _update():
            self.app_status.config(text="连接失败", style='Status.Error.TLabel')
            self.log_message(f"连接失败 {device_id}: {error}", page)
            messagebox.showerror("连接错误", f"无法连接设备 {device_id}:\n{error}\n请确保:\n• 设备已解锁屏幕\n• USB调试已授权\n• ADB驱动已安装")

        self.root.after(0, _update)
    
    def disconnect_device(self):
        """断开设备"""
        if self.controller_id:
            # 调用android_control的disconnect_device函数
            try:
                success = disconnect_device(self.controller_id)
                if success:
                    self.log_message(f"设备已断开连接", "all")
            except Exception as e:
                self.log_message(f"断开设备时出错: {str(e)}", "all")

            self.controller_id = None
            self.current_device = None
            self.device_status.config(text="无设备", style='Status.Error.TLabel')
            self.app_status.config(text="已断开", style='Status.Error.TLabel')
            self.log_message("设备状态已清除", "all")

    # ==================== 基础测试页 ====================
    def setup_test_page(self):
        """设置基础测试页面 - 调试点击带明确安全警告"""
        frame = ttk.Frame(self.test_page_frame, padding="10")
        frame.pack(fill='both', expand=True)
        
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill='both', expand=True)
        
        left_panel = ttk.Frame(paned)
        paned.add(left_panel, weight=1)
        right_panel = ttk.Frame(paned)
        paned.add(right_panel, weight=2)
        
        # 左侧面板：设备控制
        device_frame = ttk.LabelFrame(left_panel, text="设备控制", padding="10")
        device_frame.pack(fill='x', pady=(0, 10))

        # 设备选择和输入
        device_input_frame = ttk.Frame(device_frame)
        device_input_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(device_input_frame, text="设备:").pack(side=tk.LEFT)
        self.test_device_combo = ttk.Combobox(device_input_frame, width=30)
        self.test_device_combo.pack(side=tk.LEFT, padx=(5, 5), fill='x', expand=True)
        self.test_device_combo['values'] = ["未检测到设备"] if not self.device_cache else self.device_cache
        self.test_device_combo.config(state='normal')

        # 手动输入按钮
        self.create_btn(device_input_frame, "手动输入", lambda: self.manual_input_device("test"), width=10)

        # 连接测试按钮
        self.create_btn(device_input_frame, "连接测试", lambda: self.connect_device("test"), 'Action.TButton', width=10)

        # 按钮框架
        btn_frame = ttk.Frame(device_frame)
        btn_frame.pack(fill='x')
        self.create_btn(btn_frame, "刷新", self.scan_devices, 'Action.TButton', tk.LEFT, padx=(0, 5))
        self.create_btn(btn_frame, "连接", lambda: self.connect_device("test"), 'Action.TButton', tk.LEFT, padx=5)
        self.create_btn(btn_frame, "断开", self.disconnect_device, 'Action.TButton', tk.LEFT, padx=(5, 0))
        self.create_btn(btn_frame, "清除缓存", self.clear_device_cache, 'Action.TButton', tk.LEFT, padx=5)

        # 添加网络设备连接按钮
        network_btn_frame = ttk.Frame(device_frame)
        network_btn_frame.pack(fill='x', pady=(5, 0))
        
        # 操作控制（仅调试用）
        control_frame = ttk.LabelFrame(left_panel, text="调试操作（仅开发）", padding="10")
        control_frame.pack(fill='x', pady=(0, 10))
        btn_grid = ttk.Frame(control_frame)
        btn_grid.pack(fill='x')
        actions = [
            ("截图", self.take_screenshot),
            ("返回", lambda: self.perform_action("key", "BACK")),
            ("Home", lambda: self.perform_action("key", "HOME")),
        ]
        for i, (text, cmd) in enumerate(actions):
            ttk.Button(btn_grid, text=text, command=cmd, width=12,
                       style='Action.TButton').grid(row=0, column=i, padx=3, pady=3)
        
        # 日志
        log_frame = ttk.LabelFrame(left_panel, text="操作日志", padding="10")
        log_frame.pack(fill='both', expand=True)
        self.test_log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD)
        self.test_log_text.pack(fill='both', expand=True)
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill='x', pady=(5, 0))
        self.create_btn(log_btn_frame, "清空", lambda: self.clear_log("test"), None, tk.LEFT, padx=(0, 5))
        self.create_btn(log_btn_frame, "保存", lambda: self.save_log("test"), None, tk.LEFT)
        
        # 右侧面板：截图显示
        image_frame = ttk.LabelFrame(right_panel, text="屏幕截图", padding="10")
        image_frame.pack(fill='both', expand=True)
        canvas_frame = ttk.Frame(image_frame)
        canvas_frame.pack(fill='both', expand=True)
        self.test_canvas = tk.Canvas(canvas_frame, bg='black', highlightthickness=0)
        self.test_canvas.pack(fill='both', expand=True)
        self.test_coord_label = ttk.Label(right_panel, text="坐标: (0, 0)", font=('Arial', 9, 'bold'))
        self.test_coord_label.pack(pady=(5, 0))
        self.test_canvas.bind("<Motion>", self.on_canvas_motion)
        self.test_canvas.bind("<Button-1>", self.on_canvas_click_debug)
    
    def on_canvas_motion(self, event):
        """显示坐标"""
        if not self.current_image:
            return
        canvas_x = self.test_canvas.canvasx(event.x)
        canvas_y = self.test_canvas.canvasy(event.y)
        actual_x = int(canvas_x * self.image_scale_x)
        actual_y = int(canvas_y * self.image_scale_y)
        self.test_coord_label.config(text=f"坐标: ({actual_x}, {actual_y})")
    
    def on_canvas_click_debug(self, event):
        """点击测试页面的点击事件"""
        if not self.controller_id or not self.current_image:
            return
        canvas_x = self.test_canvas.canvasx(event.x)
        canvas_y = self.test_canvas.canvasy(event.y)
        actual_x = int(canvas_x * self.image_scale_x)
        actual_y = int(canvas_y * self.image_scale_y)

        self.log_message(f"调试点击 ({actual_x}, {actual_y})", "test", "INFO")
        threading.Thread(target=lambda: click(self.controller_id, actual_x, actual_y, 50), daemon=True).start()

        self.test_canvas.create_oval(
            canvas_x-8, canvas_y-8, canvas_x+8, canvas_y+8,
            outline="red", width=3, tags="debug_click"
        )
    
    def take_screenshot(self):
        """获取设备屏幕截图"""
        if not self.controller_id:
            messagebox.showwarning("警告", "请先连接设备")
            return
        self.log_message("正在截图...", "test")
        
        def capture():
            try:
                image_obj = screencap(self.controller_id)
                if not image_obj or not hasattr(image_obj, 'data'):
                    raise RuntimeError("截图返回空数据")
                data_url = image_obj.data
                b64_data = data_url.split(',', 1)[1] if ',' in data_url else data_url
                image_data = base64.b64decode(b64_data)
                image = Image.open(io.BytesIO(image_data))
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                screenshot_path = os.path.join("screenshots", f"screen_{timestamp}.jpg")
                os.makedirs("screenshots", exist_ok=True)
                image.save(screenshot_path, "JPEG", quality=85)
                self.root.after(0, self.display_screenshot, image, screenshot_path)
            except Exception as e:
                self.root.after(0, self.log_message, f"截图失败: {str(e)}", "test")
                self.root.after(0, self.log_message, f"   详细: {traceback.format_exc()[:200]}", "test")
        
        threading.Thread(target=capture, daemon=True).start()
    
    def display_screenshot(self, image: Image.Image, path: str):
        """显示截图"""
        def _update():
            try:
                self.current_image = image
                img_width, img_height = image.size
                canvas_width = self.test_canvas.winfo_width() or 640
                canvas_height = self.test_canvas.winfo_height() or 480
                scale = min(canvas_width / img_width, canvas_height / img_height, 1.0)
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                self.image_scale_x = img_width / new_width if new_width > 0 else 1.0
                self.image_scale_y = img_height / new_height if new_height > 0 else 1.0
                display_img = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(display_img)
                self.test_canvas.delete("all")
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                self.test_canvas.create_image(x, y, anchor=tk.NW, image=photo)
                self.test_canvas.image = photo
                self.log_message(f"截图已显示 ({img_width}x{img_height} → {new_width}x{new_height})", "test")
            except Exception as e:
                self.log_message(f"显示截图失败: {str(e)}", "test")

        self.root.after(0, _update)
    
    def perform_action(self, action_type: str, *args):
        """执行基础操作（仅用于调试）"""
        if not self.controller_id:
            messagebox.showwarning("警告", "请先连接设备")
            return
        
        def do_action():
            try:
                if action_type == "key" and args:
                    key_map = {"BACK": KeyCode.BACK, "HOME": KeyCode.HOME}
                    key_code = key_map.get(args[0], KeyCode.BACK)
                    success = click_key(self.controller_id, key_code)
                    msg = f"按键 {args[0]}" if success else f"按键 {args[0]} 失败"
                    self.root.after(0, self.log_message, msg, "test")
                    if success:
                        time.sleep(0.5)
                        self.root.after(0, self.take_screenshot)
            except Exception as e:
                self.root.after(0, self.log_message, f"操作错误: {str(e)}", "test")
        
        threading.Thread(target=do_action, daemon=True).start()
    
    # ==================== LLM任务设计器 ====================
    def setup_designer_page(self):
        """LLM任务设计器 - 移除所有硬编码操作，专注高层目标"""
        frame = ttk.Frame(self.designer_page_frame, padding="10")
        frame.pack(fill='both', expand=True)
        
        # 上下分栏：设计器 | 预览/知识库
        paned = ttk.PanedWindow(frame, orient=tk.VERTICAL)
        paned.pack(fill='both', expand=True)
        
        # 上：设计器
        designer_panel = ttk.Frame(paned)
        paned.add(designer_panel, weight=3)
        
        # 下：预览/知识库
        preview_panel = ttk.Frame(paned)
        paned.add(preview_panel, weight=1)
        
        # ----- 任务设计器 -----
        # 左右分栏：模板库 | 编辑器
        designer_paned = ttk.PanedWindow(designer_panel, orient=tk.HORIZONTAL)
        designer_paned.pack(fill='both', expand=True)
        
        # 左：模板库
        lib_frame = ttk.LabelFrame(designer_paned, text="任务模板库", padding="10")
        designer_paned.add(lib_frame, weight=1)

        # 创建带有滚动条的模板列表
        template_list_frame = ttk.Frame(lib_frame)
        template_list_frame.pack(fill='both', expand=True, pady=(0, 5))

        self.template_listbox = tk.Listbox(template_list_frame, height=15, font=('Arial', 10))
        template_listbox_scrollbar = ttk.Scrollbar(template_list_frame, orient="vertical", command=self.template_listbox.yview)
        self.template_listbox.configure(yscrollcommand=template_listbox_scrollbar.set)

        self.template_listbox.pack(side="left", fill="both", expand=True)
        template_listbox_scrollbar.pack(side="right", fill="y")

        # 添加鼠标滚轮支持
        def _on_template_mousewheel(event):
            if sys.platform.startswith('win') or sys.platform.startswith('darwin'):
                delta = -1 * (event.delta // 120) if event.delta else 0
                self.template_listbox.yview_scroll(delta, "units")
            else:
                if event.num == 4:
                    self.template_listbox.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.template_listbox.yview_scroll(1, "units")

        self.template_listbox.bind("<MouseWheel>", _on_template_mousewheel)
        self.template_listbox.bind("<Button-4>", _on_template_mousewheel)
        self.template_listbox.bind("<Button-5>", _on_template_mousewheel)
        # 模板列表初始化（修改后）
        self.template_listbox.delete(0, tk.END)
        if self.task_templates:
            for template in self.task_templates:
                self.template_listbox.insert(tk.END, f"{template['name']} - {template['description'][:40]}...")
        else:
            self.template_listbox.insert(tk.END, "无任务模板，请点击'新建任务'创建")
        
        lib_btn_frame = ttk.Frame(lib_frame)
        lib_btn_frame.pack(fill='x')
        self.create_btn(lib_btn_frame, "新建任务", self.create_new_task_template).pack(side=tk.LEFT, fill='x', expand=True, padx=(0, 5))
        self.create_btn(lib_btn_frame, "编辑选中", self.edit_selected_template).pack(side=tk.LEFT, fill='x', expand=True)

        # 添加示例按钮
        self.create_btn(lib_btn_frame, "重新加载文件", self.reload_templates_from_file).pack(side=tk.LEFT, fill='x', expand=True, padx=(0, 5))
        self.create_btn(lib_btn_frame, "创建示例", self.create_example_template_ui).pack(side=tk.LEFT, fill='x', expand=True)
        
        # 右：任务编辑器（关键：添加滚动容器）
        editor_frame = ttk.LabelFrame(designer_paned, text="LLM任务编辑器", padding="5")
        designer_paned.add(editor_frame, weight=2)
        
        # === 创建可滚动容器（修复背景色问题）===
        try:
            bg_color = ttk.Style().lookup('TFrame', 'background') or '#f0f0f0'
        except (tk.TclError, AttributeError):
            # 主题样式获取失败时使用默认背景色
            bg_color = '#f0f0f0'
        
        canvas = tk.Canvas(editor_frame, highlightthickness=0, bg=bg_color)
        scrollbar = ttk.Scrollbar(editor_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding="10")
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def on_editor_resize(event):
            available_width = event.width - scrollbar.winfo_width() - 10
            if available_width > 0:
                canvas.itemconfig(canvas_window, width=available_width)
        editor_frame.bind("<Configure>", on_editor_resize)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # === 鼠标滚轮支持 ===
        def _on_mousewheel(event):
            if sys.platform.startswith('win') or sys.platform.startswith('darwin'):
                delta = -1 * (event.delta // 120) if event.delta else 0
                canvas.yview_scroll(delta, "units")
            else:
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")

        # 修复：为整个编辑器框架的子组件都绑定滚轮事件
        def _bind_mousewheel_to_widget(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            widget.bind("<Button-4>", _on_mousewheel)
            widget.bind("<Button-5>", _on_mousewheel)
            for child in widget.winfo_children():
                _bind_mousewheel_to_widget(child)

        # 为canvas绑定滚轮事件
        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", _on_mousewheel)
        canvas.bind("<Button-5>", _on_mousewheel)

        # 为scrollable_frame及其所有子组件绑定滚轮事件
        _bind_mousewheel_to_widget(scrollable_frame)
        
        # === 任务基本信息 ===
        basic_frame = ttk.Frame(scrollable_frame)
        basic_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(basic_frame, text="任务ID:").grid(row=0, column=0, sticky=tk.W)
        self.task_id_var = tk.StringVar(value="llm_task_001")
        ttk.Entry(basic_frame, textvariable=self.task_id_var, width=30).grid(row=0, column=1, sticky='ew', padx=5)
        ttk.Label(basic_frame, text="任务名称:").grid(row=1, column=0, sticky=tk.W, pady=(5,0))
        self.task_name_var = tk.StringVar(value="LLM自动化任务")
        ttk.Entry(basic_frame, textvariable=self.task_name_var, width=30).grid(row=1, column=1, sticky='ew', padx=5, pady=(5,0))
        ttk.Label(basic_frame, text="全局目标:").grid(row=2, column=0, sticky=tk.W, pady=(5,0))
        self.task_desc_text = scrolledtext.ScrolledText(basic_frame, height=3, width=40, wrap=tk.WORD)
        self.task_desc_text.grid(row=2, column=1, sticky='ew', padx=5, pady=(5,0))
        self.task_desc_text.insert(1.0, "定义LLM需要达成的总体目标，例如：完成日常任务并收集所有资源")
        basic_frame.columnconfigure(1, weight=1)
        
        # === 任务变量定义 ===
        var_frame = ttk.LabelFrame(scrollable_frame, text="任务变量", padding="10")
        var_frame.pack(fill='x', pady=(0, 10))
        self.var_tree = ttk.Treeview(var_frame, columns=('name', 'type', 'default', 'desc'), show='headings', height=6)
        self.var_tree.heading('name', text='变量名')
        self.var_tree.heading('type', text='类型')
        self.var_tree.heading('default', text='默认值')
        self.var_tree.heading('desc', text='描述')
        self.var_tree.column('name', width=100)
        self.var_tree.column('type', width=80)
        self.var_tree.column('default', width=100)
        self.var_tree.column('desc', width=200)
        self.var_tree.pack(fill='x', pady=(0, 5))
        var_btn_frame = ttk.Frame(var_frame)
        var_btn_frame.pack(fill='x')
        self.create_btn(var_btn_frame, "添加变量", self.add_task_variable).pack(side=tk.LEFT, padx=(0,5))
        self.create_btn(var_btn_frame, "编辑", self.edit_task_variable).pack(side=tk.LEFT, padx=5)
        self.create_btn(var_btn_frame, "删除", self.remove_task_variable).pack(side=tk.LEFT)
        
        # === 任务步骤描述（替代操作序列）===
        steps_frame = ttk.LabelFrame(scrollable_frame, text="任务步骤描述", padding="10")
        steps_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(steps_frame, text="详细步骤（供LLM参考）:", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
        self.task_steps_text = scrolledtext.ScrolledText(steps_frame, height=8, width=60, wrap=tk.WORD)
        self.task_steps_text.pack(fill='both', expand=True, pady=(5, 0))
        self.task_steps_text.insert(1.0, """1. 启动游戏并登录
2. 完成所有日常任务（战术演习、信用商店等）
3. 收集所有区域的无人机产出物
4. 检查资源库存并补充消耗品
5. 安全退出游戏""")
        
                
        # === 保存按钮区域 ===
        save_frame = ttk.Frame(scrollable_frame)
        save_frame.pack(fill='x', pady=(10, 0), side=tk.BOTTOM)
        self.create_btn(save_frame, "保存任务模板", self.save_task_template, 'Security.TButton').pack(side=tk.RIGHT, padx=(5,0))
        self.create_btn(save_frame, "预览JSON", self.preview_task_json).pack(side=tk.LEFT)
        
        # ----- 预览/知识库面板 -----
        preview_notebook = ttk.Notebook(preview_panel)
        preview_notebook.pack(fill='both', expand=True)
        
        # LLM Content Window 预览
        content_frame = ttk.Frame(preview_notebook)
        preview_notebook.add(content_frame, text='LLM Content Window')
        self.content_preview = scrolledtext.ScrolledText(content_frame, height=10, wrap=tk.WORD, font=('Consolas', 9))
        self.content_preview.pack(fill='both', expand=True)
        self.content_preview.insert(1.0, "LLM将接收的完整上下文预览...\n包含: device_vision, global_goal, task_list, splited_task, markdown, function")
        
        # 知识库管理
        kb_frame = ttk.Frame(preview_notebook)
        preview_notebook.add(kb_frame, text='知识库')
        self.kb_tree = ttk.Treeview(kb_frame, columns=('type', 'content', 'timestamp'), show='headings', height=8)
        self.kb_tree.heading('type', text='类型')
        self.kb_tree.heading('content', text='内容摘要')
        self.kb_tree.heading('timestamp', text='时间')
        self.kb_tree.column('type', width=80)
        self.kb_tree.column('content', width=300)
        self.kb_tree.column('timestamp', width=150)
        self.kb_tree.pack(fill='both', expand=True, pady=(0, 5))
        kb_btn_frame = ttk.Frame(kb_frame)
        kb_btn_frame.pack(fill='x')
        self.create_btn(kb_btn_frame, "添加词条", self.add_knowledge_entry).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(kb_btn_frame, text="清空知识库", command=self.clear_knowledge_base).pack(side=tk.LEFT)
        
        # 设备连接
        device_frame = ttk.LabelFrame(preview_panel, text="测试设备", padding="10")
        device_frame.pack(fill='x', pady=(5, 10))

        # 设备选择输入框架
        device_input_frame = ttk.Frame(device_frame)
        device_input_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(device_input_frame, text="设备:").pack(side=tk.LEFT)
        self.designer_device_combo = ttk.Combobox(device_input_frame, width=20)
        self.designer_device_combo.pack(side=tk.LEFT, padx=5, fill='x', expand=True)
        self.designer_device_combo['values'] = ["未检测到设备"] if not self.device_cache else self.device_cache
        self.designer_device_combo.config(state='normal')

        # 手动输入按钮
        self.create_btn(device_input_frame, "手动输入", lambda: self.manual_input_device("designer"), None, tk.LEFT, padx=5, width=10)

        # 按钮框架
        device_btn_frame = ttk.Frame(device_frame)
        device_btn_frame.pack(fill='x')

        # 连接按钮
        self.create_btn(device_btn_frame, "刷新", self.scan_devices, 'Action.TButton', tk.LEFT, padx=(0, 5))
        self.create_btn(device_btn_frame, "连接", lambda: self.connect_device("designer"), 'Action.TButton', tk.LEFT, padx=5)
        self.create_btn(device_btn_frame, "清除缓存", self.clear_device_cache, 'Action.TButton', tk.LEFT, padx=5)

        self.create_btn(device_btn_frame, "测试LLM执行", self.test_llm_execution, 'Security.TButton', tk.RIGHT)

        # ----- 日志面板添加到预览页面 -----
        log_frame = ttk.LabelFrame(preview_panel, text="运行日志", padding="10")
        log_frame.pack(fill='both', expand=True, pady=(5, 0))
        self.designer_log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD, font=('Consolas', 9))
        self.designer_log_text.pack(fill='both', expand=True)
    
    # ==================== 任务模板管理（安全增强）====================
    def load_task_templates(self) -> List[Dict]:
        """从文件加载LLM任务模板，如果文件不存在则返回空列表"""
        try:
            template_path = "tasks/llm_task_templates.json"
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    templates = json.load(f)
                    # 验证模板格式
                    if isinstance(templates, list):
                        self.log_message(f"从文件加载了 {len(templates)} 个任务模板", "designer")
                        return templates
                    else:
                        self.log_message("任务模板文件格式错误，将使用空列表", "designer", "WARNING")
                        return []
            else:
                self.log_message("任务模板文件不存在，将创建空模板列表", "designer", "INFO")
                return []
        except json.JSONDecodeError as e:
            self.log_message(f"任务模板文件解析失败: {str(e)}", "designer", "ERROR")
            return []
        except Exception as e:
            self.log_message(f"加载任务模板失败: {str(e)}", "designer", "WARNING")
            return []

    def load_default_templates(self) -> List[Dict]:
        """加载默认LLM任务模板"""
        return self.load_task_templates()

    def create_example_template(self) -> Dict:
        """创建一个示例模板（仅用于演示）"""
        return {
            "id": f"example_{int(time.time())}",
            "name": "示例任务",
            "description": "这是一个示例任务，请根据实际需求修改",
            "variables": [],
            "task_steps": [
                "1. 启动应用",
                "2. 执行主要操作",
                "3. 完成并退出"
            ],
            "success_indicators": ["任务完成"],
            "security_params": {
                "press_duration_ms": 100,
                "press_jitter_px": 2
            }
        }
    
    def create_new_task_template(self):
        """创建新LLM任务模板"""
        self.task_id_var.set(f"llm_task_{int(time.time())}")
        self.task_name_var.set("新LLM任务")
        self.task_desc_text.delete(1.0, tk.END)
        self.task_desc_text.insert(1.0, "定义LLM需要达成的总体目标...")
        self.var_tree.delete(*self.var_tree.get_children())
        self.task_steps_text.delete(1.0, tk.END)
        self.task_steps_text.insert(1.0, "1. 步骤一描述...\n2. 步骤二描述...\n3. ...")
        self.log_message("已创建新LLM任务模板", "designer")

    def reload_templates_from_file(self):
        """从文件重新加载任务模板"""
        if messagebox.askyesno("确认", "重新加载将放弃所有未保存的修改，确定继续吗？"):
            try:
                # 重新从文件加载
                self.task_templates = self.load_task_templates()

                # 刷新UI
                self.template_listbox.delete(0, tk.END)
                if self.task_templates:
                    for template in self.task_templates:
                        self.template_listbox.insert(tk.END, f"{template['name']} - {template['description'][:40]}...")
                    self.log_message(f"从文件重新加载了 {len(self.task_templates)} 个任务模板", "designer")
                else:
                    self.template_listbox.insert(tk.END, "无任务模板，请点击'新建任务'创建")
                    self.log_message("任务模板文件为空", "designer", "INFO")

            except Exception as e:
                self.log_message(f"重新加载失败: {str(e)}", "designer", "ERROR")

    def create_example_template_ui(self):
        """创建示例模板UI"""
        timestamp = int(time.time())
        random_suffix = random.randint(1000, 9999)

        example_template = self.create_example_template()
        self.task_id_var.set(f"example_{timestamp}_{random_suffix}")
        self.task_name_var.set(example_template["name"])
        self.task_desc_text.delete(1.0, tk.END)
        self.task_desc_text.insert(1.0, example_template["description"])
        self.var_tree.delete(*self.var_tree.get_children())
        self.task_steps_text.delete(1.0, tk.END)
        self.task_steps_text.insert(1.0, "\n".join(example_template["task_steps"]))
        self.log_message("已创建示例任务模板", "designer")
    
    def edit_selected_template(self):
        """编辑选中的模板"""
        selection = self.template_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先在任务库中选择一个任务模板")
            return
        template = self.task_templates[selection[0]]
        
        self.task_id_var.set(template.get("id", ""))
        self.task_name_var.set(template.get("name", ""))
        self.task_desc_text.delete(1.0, tk.END)
        self.task_desc_text.insert(1.0, template.get("description", ""))
        
        self.var_tree.delete(*self.var_tree.get_children())
        for var in template.get("variables", []):
            range_str = f"{var.get('min', '')}~{var.get('max', '')}" if "min" in var else var.get("default", "")
            self.var_tree.insert("", "end", values=(
                var["name"],
                var["type"],
                var["default"],
                var.get("desc", "")
            ), tags=(json.dumps(var),))
        
        self.task_steps_text.delete(1.0, tk.END)
        steps = template.get("task_steps", [])
        self.task_steps_text.insert(1.0, "\n".join(steps) if steps else "1. 步骤描述...")
        
        self.log_message(f"已加载模板 '{template['name']}' 进行编辑", "designer")

    def add_task_variable(self):
        """添加新任务变量"""
        try:
            # 创建变量设置对话框
            dialog = tk.Toplevel(self.root)
            dialog.title("添加任务变量")
            dialog.geometry("500x500")
            dialog.resizable(True, True)
            dialog.transient(self.root)
            dialog.grab_set()

            # 使用 notebooks 组织不同的设置
            notebook = ttk.Notebook(dialog)
            notebook.pack(fill='both', expand=True, padx=10, pady=10)

            # 基本设置页面
            basic_frame = ttk.Frame(notebook, padding="10")
            notebook.add(basic_frame, text='基本设置')

            # 输入字段
            ttk.Label(basic_frame, text="变量名:").grid(row=0, column=0, sticky=tk.W, pady=5)
            name_var = tk.StringVar()
            name_entry = ttk.Entry(basic_frame, textvariable=name_var, width=30)
            name_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=5)

            ttk.Label(basic_frame, text="变量类型:").grid(row=1, column=0, sticky=tk.W, pady=5)
            type_var = tk.StringVar(value="string")
            type_combo = ttk.Combobox(basic_frame, textvariable=type_var, width=27, state='readonly')
            type_combo['values'] = ('string', 'int', 'bool', 'float', 'select')
            type_combo.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
            type_combo.bind('<<ComboboxSelected>>', lambda e: self.update_multi_select_ui(select_frame, type_var.get()))

            ttk.Label(basic_frame, text="默认值:").grid(row=2, column=0, sticky=tk.W, pady=5)
            default_var = tk.StringVar()
            default_entry = ttk.Entry(basic_frame, textvariable=default_var, width=30)
            default_entry.grid(row=2, column=1, sticky='ew', padx=5, pady=5)

            ttk.Label(basic_frame, text="变量描述:").grid(row=3, column=0, sticky=tk.W, pady=5)
            desc_var = tk.StringVar()
            desc_entry = ttk.Entry(basic_frame, textvariable=desc_var, width=30)
            desc_entry.grid(row=3, column=1, sticky='ew', padx=5, pady=5)

            basic_frame.grid_columnconfigure(1, weight=1)

            # 多选值设置页面
            select_frame = ttk.Frame(notebook, padding="10")
            notebook.add(select_frame, text='多选值设置')

            ttk.Label(select_frame, text="可选值列表:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)

            # 可选值管理界面
            values_frame = ttk.Frame(select_frame)
            values_frame.pack(fill='both', expand=True, pady=5)

            # 左侧：可选值列表
            list_frame = ttk.Frame(values_frame)
            list_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=(0, 5))

            self.multi_select_values = tk.Listbox(list_frame, height=12)
            scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.multi_select_values.yview)
            self.multi_select_values.configure(yscrollcommand=scrollbar.set)
            self.multi_select_values.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            # 右侧：操作按钮
            btn_frame = ttk.Frame(values_frame)
            btn_frame.pack(side=tk.RIGHT, fill='y')

            value_entry_var = tk.StringVar()
            ttk.Label(btn_frame, text="添加值:").pack(anchor=tk.W)
            value_entry = ttk.Entry(btn_frame, textvariable=value_entry_var, width=20)
            value_entry.pack(fill='x', pady=2)

            def add_value():
                value = value_entry_var.get().strip()
                if value and value not in self.multi_select_values.get(0, tk.END):
                    self.multi_select_values.insert(tk.END, value)
                    value_entry_var.set("")

            def remove_value():
                selection = self.multi_select_values.curselection()
                if selection:
                    self.multi_select_values.delete(selection[0])

            ttk.Button(btn_frame, text="添加", command=add_value).pack(fill='x', pady=2)
            ttk.Button(btn_frame, text="删除", command=remove_value).pack(fill='x', pady=2)
            ttk.Button(btn_frame, text="清空", command=lambda: self.multi_select_values.delete(0, tk.END)).pack(fill='x', pady=2)

            # 预设值
            ttk.Label(btn_frame, text="预设值:").pack(anchor=tk.W, pady=(10, 2))

            def add_preset_values(values_list):
                for value in values_list:
                    if value and value not in self.multi_select_values.get(0, tk.END):
                        self.multi_select_values.insert(tk.END, value)

            ttk.Button(btn_frame, text="常用选项",
                      command=lambda: add_preset_values(['选项1', '选项2', '选项3'])).pack(fill='x', pady=1)
            ttk.Button(btn_frame, text="数字序列",
                      command=lambda: add_preset_values([str(i) for i in range(1, 11)])).pack(fill='x', pady=1)
            ttk.Button(btn_frame, text="True/False",
                      command=lambda: add_preset_values(['true', 'false'])).pack(fill='x', pady=1)

            # 初始状态隐藏多选值界面
            self.update_multi_select_ui(select_frame, type_var.get())

            # 对话框按钮
            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill='x', padx=10, pady=10)

            def save_variable():
                name = name_var.get().strip()
                if not name:
                    messagebox.showwarning("警告", "请输入变量名")
                    return

                # 收集多选值
                multi_values = list(self.multi_select_values.get(0, tk.END))

                # 获取当前默认值并验证
                current_default = default_var.get().strip()

                var_def = {
                    "name": name,
                    "type": type_var.get(),
                    "default": current_default,
                    "desc": desc_var.get().strip(),
                    "multi_values": multi_values if multi_values else []
                }

                # 更新默认值选择（类型为select时）
                if type_var.get() == 'select' and multi_values:
                    # 确保默认值在可选值中
                    if current_default not in multi_values:
                        if multi_values:
                            var_def['default'] = multi_values[0]  # 默认选择第一个
                        else:
                            var_def['default'] = ''

                # 添加到树形列表
                display_default = var_def['default']
                if var_def['type'] == 'select' and var_def['multi_values']:
                    display_default = f"{var_def['default']} (可选: {', '.join(var_def['multi_values'])})"

                self.var_tree.insert("", "end", values=(
                    var_def["name"],
                    var_def["type"],
                    display_default,
                    var_def["desc"]
                ), tags=(json.dumps(var_def),))

                self.log_message(f"已添加任务变量: {var_def['name']}", "designer")
                dialog.destroy()

            ttk.Button(button_frame, text="保存", command=save_variable).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT)

            name_entry.focus()

        except Exception as e:
            self.log_message(f"添加变量失败: {str(e)}", "designer")
            messagebox.showerror("错误", f"添加变量失败:\n{str(e)}")

    def update_multi_select_ui(self, frame, var_type):
        """根据变量类型更新多选值界面"""
        # 查找并启用/禁用多选值相关的控件
        for widget in frame.winfo_children():
            if isinstance(widget, ttk.Frame):
                # 递归处理子控件
                for child in widget.winfo_children():
                    try:
                        if var_type == 'select':
                            # 大多数控件支持state选项
                            if isinstance(child, (ttk.Button, ttk.Entry, ttk.Label, ttk.Scrollbar)):
                                child.configure(state='normal')
                            elif isinstance(child, tk.Listbox):
                                child.configure(state='normal')
                        else:
                            if isinstance(child, (ttk.Button, ttk.Entry, ttk.Label, ttk.Scrollbar)):
                                child.configure(state='disabled')
                            elif isinstance(child, tk.Listbox):
                                child.configure(state='disabled')
                    except tk.TclError:
                        pass  # 某些控件不支持state配置，忽略错误

    def edit_task_variable(self):
        """编辑选中的任务变量"""
        selection = self.var_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个变量")
            return

        try:
            item_id = selection[0]
            values = self.var_tree.item(item_id, 'values')
            tags = self.var_tree.item(item_id, 'tags')

            var_def = {}
            if tags:
                try:
                    var_def = json.loads(tags[0])
                except (json.JSONDecodeError, TypeError):
                    # JSON解析失败时使用空字典
                    var_def = {}

            # 创建变量编辑对话框
            dialog = tk.Toplevel(self.root)
            dialog.title("编辑任务变量")
            dialog.geometry("500x500")
            dialog.resizable(True, True)
            dialog.transient(self.root)
            dialog.grab_set()

            # 使用 notebooks 组织不同的设置
            notebook = ttk.Notebook(dialog)
            notebook.pack(fill='both', expand=True, padx=10, pady=10)

            # 基本设置页面
            basic_frame = ttk.Frame(notebook, padding="10")
            notebook.add(basic_frame, text='基本设置')

            # 输入字段
            ttk.Label(basic_frame, text="变量名:").grid(row=0, column=0, sticky=tk.W, pady=5)
            name_var = tk.StringVar(value=values[0] if values else "")
            name_entry = ttk.Entry(basic_frame, textvariable=name_var, width=30)
            name_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=5)

            ttk.Label(basic_frame, text="变量类型:").grid(row=1, column=0, sticky=tk.W, pady=5)
            type_var = tk.StringVar(value=var_def.get('type', values[1] if len(values) > 1 else "string"))
            type_combo = ttk.Combobox(basic_frame, textvariable=type_var, width=27, state='readonly')
            type_combo['values'] = ('string', 'int', 'bool', 'float', 'select')
            type_combo.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
            type_combo.bind('<<ComboboxSelected>>', lambda e: self.update_multi_select_ui(select_frame, type_var.get()))

            ttk.Label(basic_frame, text="默认值:").grid(row=2, column=0, sticky=tk.W, pady=5)
            default_var = tk.StringVar(value=var_def.get('default', values[2] if len(values) > 2 else ""))
            default_entry = ttk.Entry(basic_frame, textvariable=default_var, width=30)
            default_entry.grid(row=2, column=1, sticky='ew', padx=5, pady=5)

            ttk.Label(basic_frame, text="变量描述:").grid(row=3, column=0, sticky=tk.W, pady=5)
            desc_var = tk.StringVar(value=var_def.get('desc', values[3] if len(values) > 3 else ""))
            desc_entry = ttk.Entry(basic_frame, textvariable=desc_var, width=30)
            desc_entry.grid(row=3, column=1, sticky='ew', padx=5, pady=5)

            basic_frame.grid_columnconfigure(1, weight=1)

            # 多选值设置页面
            select_frame = ttk.Frame(notebook, padding="10")
            notebook.add(select_frame, text='多选值设置')

            ttk.Label(select_frame, text="可选值列表:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)

            # 可选值管理界面
            values_frame = ttk.Frame(select_frame)
            values_frame.pack(fill='both', expand=True, pady=5)

            # 左侧：可选值列表
            list_frame = ttk.Frame(values_frame)
            list_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=(0, 5))

            self.multi_select_values = tk.Listbox(list_frame, height=12)
            scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.multi_select_values.yview)
            self.multi_select_values.configure(yscrollcommand=scrollbar.set)
            self.multi_select_values.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            # 加载现有的多选值
            existing_values = var_def.get('multi_values', [])
            for value in existing_values:
                self.multi_select_values.insert(tk.END, value)

            # 右侧：操作按钮
            btn_frame = ttk.Frame(values_frame)
            btn_frame.pack(side=tk.RIGHT, fill='y')

            value_entry_var = tk.StringVar()
            ttk.Label(btn_frame, text="添加值:").pack(anchor=tk.W)
            value_entry = ttk.Entry(btn_frame, textvariable=value_entry_var, width=20)
            value_entry.pack(fill='x', pady=2)

            def add_value():
                value = value_entry_var.get().strip()
                if value and value not in self.multi_select_values.get(0, tk.END):
                    self.multi_select_values.insert(tk.END, value)
                    value_entry_var.set("")

            def remove_value():
                selection = self.multi_select_values.curselection()
                if selection:
                    self.multi_select_values.delete(selection[0])

            ttk.Button(btn_frame, text="添加", command=add_value).pack(fill='x', pady=2)
            ttk.Button(btn_frame, text="删除", command=remove_value).pack(fill='x', pady=2)
            ttk.Button(btn_frame, text="清空", command=lambda: self.multi_select_values.delete(0, tk.END)).pack(fill='x', pady=2)

            # 预设值
            ttk.Label(btn_frame, text="预设值:").pack(anchor=tk.W, pady=(10, 2))

            def add_preset_values(values_list):
                for value in values_list:
                    if value and value not in self.multi_select_values.get(0, tk.END):
                        self.multi_select_values.insert(tk.END, value)

            ttk.Button(btn_frame, text="常用选项",
                      command=lambda: add_preset_values(['选项1', '选项2', '选项3'])).pack(fill='x', pady=1)
            ttk.Button(btn_frame, text="数字序列",
                      command=lambda: add_preset_values([str(i) for i in range(1, 11)])).pack(fill='x', pady=1)
            ttk.Button(btn_frame, text="True/False",
                      command=lambda: add_preset_values(['true', 'false'])).pack(fill='x', pady=1)

            # 初始状态隐藏多选值界面
            self.update_multi_select_ui(select_frame, type_var.get())

            # 对话框按钮
            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill='x', padx=10, pady=10)

            def save_variable():
                name = name_var.get().strip()
                if not name:
                    messagebox.showwarning("警告", "请输入变量名")
                    return

                # 收集多选值
                multi_values = list(self.multi_select_values.get(0, tk.END))

                # 获取当前默认值并验证
                current_default = default_var.get().strip()

                var_def = {
                    "name": name,
                    "type": type_var.get(),
                    "default": current_default,
                    "desc": desc_var.get().strip(),
                    "multi_values": multi_values if multi_values else []
                }

                # 更新默认值选择（类型为select时）
                if type_var.get() == 'select' and multi_values:
                    # 确保默认值在可选值中
                    if current_default not in multi_values:
                        if multi_values:
                            var_def['default'] = multi_values[0]  # 默认选择第一个
                        else:
                            var_def['default'] = ''

                # 更新树形列表显示
                display_default = var_def['default']
                if var_def['type'] == 'select' and var_def['multi_values']:
                    display_default = f"{var_def['default']} (可选: {', '.join(var_def['multi_values'])})"

                self.var_tree.item(item_id, values=(
                    var_def["name"],
                    var_def["type"],
                    display_default,
                    var_def["desc"]
                ), tags=(json.dumps(var_def),))

                self.log_message(f"已更新任务变量: {var_def['name']}", "designer")
                dialog.destroy()

            ttk.Button(button_frame, text="保存", command=save_variable).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT)

            name_entry.focus()

        except Exception as e:
            self.log_message(f"编辑变量失败: {str(e)}", "designer")
            messagebox.showerror("错误", f"编辑变量失败:\n{str(e)}")

    def remove_task_variable(self):
        """删除选中的任务变量"""
        selection = self.var_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个变量")
            return

        if not messagebox.askyesno("确认删除", "确定删除选中的变量？"):
            return

        try:
            item_id = selection[0]
            values = self.var_tree.item(item_id, 'values')
            var_name = values[0] if values else "未知变量"
            self.var_tree.delete(item_id)
            self.log_message(f"已删除任务变量: {var_name}", "designer")

        except Exception as e:
            self.log_message(f"删除变量失败: {str(e)}", "designer")
            messagebox.showerror("错误", f"删除变量失败:\n{str(e)}")

    def save_task_template(self):
        """保存LLM任务模板到文件"""
        try:
            # 构建当前任务定义
            task_def = {
                "id": self.task_id_var.get().strip(),
                "name": self.task_name_var.get().strip(),
                "description": self.task_desc_text.get(1.0, tk.END).strip(),
                "variables": [],
                "task_steps": [line.strip() for line in self.task_steps_text.get(1.0, tk.END).strip().split('\n') if line.strip()],
                "success_indicators": ["任务目标达成"],
                "security_params": {
                    "press_duration_ms": 100,
                    "press_jitter_px": 2
                },
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            # 收集变量
            for item_id in self.var_tree.get_children():
                tags = self.var_tree.item(item_id, 'tags')
                if tags:
                    try:
                        var_def = json.loads(tags[0])
                        task_def["variables"].append(var_def)
                    except (json.JSONDecodeError, TypeError):
                        # JSON解析失败时回退到手动构建变量定义
                        values = self.var_tree.item(item_id, 'values')
                        if values:
                            name, var_type, default_val, desc = values
                            task_def["variables"].append({
                                "name": name,
                                "type": var_type,
                                "default": default_val,
                                "desc": desc
                            })

            # 检查是否已存在相同ID的任务
            exists = False
            for i, tmpl in enumerate(self.task_templates):
                if tmpl['id'] == task_def['id']:
                    # 更新现有任务
                    task_def['created_at'] = tmpl.get('created_at', datetime.now().isoformat())
                    self.task_templates[i] = task_def
                    exists = True
                    self.log_message(f"📝 更新现有任务模板: {task_def['name']}", "designer")
                    break

            if not exists:
                # 添加新任务
                self.task_templates.append(task_def)
                self.log_message(f"添加新任务模板: {task_def['name']}", "designer")

            # 保存到文件
            self.save_task_templates()

            # 刷新UI
            self.template_listbox.delete(0, tk.END)
            for template in self.task_templates:
                self.template_listbox.insert(tk.END, f"{template['name']} - {template['description'][:40]}...")

            # 保存成功消息
            self.log_message(f"💾 任务模板已保存到文件: {task_def['name']}", "designer")
            messagebox.showinfo("成功", f"任务模板 '{task_def['name']}' 已保存")

        except Exception as e:
            self.log_message(f"保存失败: {str(e)}", "designer", "ERROR")
            messagebox.showerror("错误", f"保存任务模板失败:\n{str(e)}")
    
    def save_task_templates(self):
        """保存任务模板到文件（仅保存，不重置）"""
        try:
            os.makedirs("tasks", exist_ok=True)
            template_path = "tasks/llm_task_templates.json"

            # 备份现有文件（如果存在）
            if os.path.exists(template_path):
                backup_path = f"{template_path}.backup_{int(time.time())}"
                shutil.copy2(template_path, backup_path)
                self.log_message(f"📦 已创建备份: {backup_path}", "designer", "INFO")

            # 保存当前模板
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(self.task_templates, f, ensure_ascii=False, indent=2)

            self.log_message(f"💾 已保存 {len(self.task_templates)} 个任务模板到文件", "designer")

        except Exception as e:
            self.log_message(f"模板保存失败: {str(e)}", "designer", "ERROR")
            # 不显示错误对话框，避免干扰用户
    
    def preview_task_json(self):
        """预览LLM任务JSON（包含完整content_window结构）"""
        try:
            # 构建模拟content_window
            content_window = {
                "device_vision": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "screenshot_path": "screenshots/screen_20240601_123456_789.jpg",
                    "resolution": "1080x1920"
                },
                "global_goal": self.task_desc_text.get(1.0, tk.END).strip(),
                "task_list": [line.strip() for line in self.task_steps_text.get(1.0, tk.END).strip().split('\n') if line.strip()],
                "splited_task": [
                    {"id": "t1", "desc": "进入游戏主界面", "status": "completed", "subtasks": []},
                    {"id": "t2", "desc": "完成战术演习", "status": "in_progress", "subtasks": [
                        {"id": "t2.1", "desc": "进入战术终端", "status": "completed"},
                        {"id": "t2.2", "desc": "选择LS-5关卡", "status": "pending"}
                    ]},
                    {"id": "t3", "desc": "收集无人机资源", "status": "pending", "subtasks": []}
                ],
                "markdown": [
                    {
                        "type": "button",
                        "content": "战术终端入口",
                        "coordinates": {"x_ratio": 0.88, "y_ratio": 0.94, "width_ratio": 0.1, "height_ratio": 0.06},
                        "image_path": "knowledge/tactical_terminal_btn.jpg",
                        "timestamp": "2024-06-01T12:30:45Z"
                    }
                ],
                "function": [
                    {"timestamp": "2024-06-01T12:30:40Z", "action": "safe_press", "params": {"x": 950, "y": 1800}, "purpose": "进入战术终端"},
                    {"timestamp": "2024-06-01T12:30:42Z", "action": "wait", "params": {"duration": 1200}, "purpose": "等待界面加载"}
                ]
            }
            
            self.content_preview.delete(1.0, tk.END)
            self.content_preview.insert(1.0, json.dumps(content_window, ensure_ascii=False, indent=2))
        except Exception as e:
            self.content_preview.delete(1.0, tk.END)
            self.content_preview.insert(1.0, f"预览错误: {str(e)}")
    
    # ==================== 核心安全实现：点击转滑动模拟 ====================
    def _convert_coordinates(self, x_param: float, y_param: float) -> tuple:
        """
        将坐标转换为设备像素坐标
        支持两种输入格式：
        1. 比例坐标 (0.0-1.0)
        2. 像素坐标

        返回: (actual_x, actual_y) 或抛出异常
        """
        try:
            # 获取实际设备分辨率
            device_width, device_height = self.get_device_resolution()

            # 验证分辨率有效性
            if device_width <= 0 or device_height <= 0:
                error_msg = f"无效的设备分辨率: {device_width}x{device_height}"
                self.log_message(error_msg, "all", "ERROR")
                # 移除冗余的控制台输出，log_message已经处理了ERROR级别的输出
                raise ValueError(error_msg)

            self.log_message(f"📐 使用分辨率: {device_width}x{device_height} 进行坐标转换", "llm")

            # 判断输入类型
            if isinstance(x_param, (int, float)) and isinstance(y_param, (int, float)):
                # 判断是否为比例坐标 (通常比例坐标在0-1之间)
                is_ratio_x = 0.0 <= x_param <= 1.0 or (x_param < 0 and x_param >= -1.0)
                is_ratio_y = 0.0 <= y_param <= 1.0 or (y_param < 0 and y_param >= -1.0)

                if is_ratio_x or is_ratio_y:
                    # 按比例坐标处理
                    # 确保坐标在有效范围内
                    x_ratio = max(0.0, min(1.0, x_param))
                    y_ratio = max(0.0, min(1.0, y_param))

                    # 转换为像素坐标
                    actual_x = int(x_ratio * device_width)
                    actual_y = int(y_ratio * device_height)

                    # 验证转换结果
                    if not (0 <= actual_x < device_width and 0 <= actual_y < device_height):
                        error_msg = f"转换后坐标超出范围: ({actual_x}, {actual_y}) 范围: 0-{device_width-1}, 0-{device_height-1}"
                        self.log_message(error_msg, "llm", "ERROR")
                        # 移除冗余的控制台输出，log_message已经处理了ERROR级别的输出

                        # 强制修正到范围内
                        actual_x = max(0, min(device_width - 1, actual_x))
                        actual_y = max(0, min(device_height - 1, actual_y))
                        self.log_message(f"坐标已修正为: ({actual_x}, {actual_y})", "llm", "WARNING")

                    self.log_message(f"📏 比例坐标→像素: ({x_ratio:.3f}, {y_ratio:.3f}) → ({actual_x}, {actual_y})", "llm")
                    return actual_x, actual_y

            # 如果已经是像素坐标，直接返回（确保是整数）
            actual_x = int(x_param)
            actual_y = int(y_param)

            # 验证像素坐标范围
            if not (0 <= actual_x < device_width and 0 <= actual_y < device_height):
                error_msg = f"像素坐标超出范围: ({actual_x}, {actual_y}) 设备范围: 0-{device_width-1}, 0-{device_height-1}"
                self.log_message(error_msg, "llm", "ERROR")
                # 移除冗余的控制台输出，log_message已经处理了ERROR级别的输出

                # 强制修正到范围内
                actual_x = max(0, min(device_width - 1, actual_x))
                actual_y = max(0, min(device_height - 1, actual_y))
                self.log_message(f"坐标已修正为: ({actual_x}, {actual_y})", "llm", "WARNING")

            return actual_x, actual_y

        except ValueError as e:
            # 重新抛出ValueError
            raise
        except Exception as e:
            error_msg = f"坐标转换发生未知错误: {str(e)}"
            self.log_message(error_msg, "all", "ERROR")
            # 移除冗余的控制台输出，log_message已经处理了ERROR级别的输出

            # 返回安全默认值（屏幕中心）
            device_width, device_height = self.get_device_resolution()
            return device_width // 2, device_height // 2

    def get_device_resolution(self) -> tuple:
        """获取设备分辨率 - 优先使用缓存"""
        if hasattr(self, 'cached_resolution') and self.cached_resolution:
            return self.cached_resolution

        if not self.controller_id:
            return (1080, 1920)

        try:
            # [修复] 直接使用顶部导入的函数，注意函数名冲突
            from android_control import get_device_resolution as adb_get_resolution
            width, height = adb_get_resolution(self.current_device)

            if width and height:
                self.cached_resolution = (width, height)
                self.log_message(f"获取分辨率成功: {width}x{height}", "all")
                return (width, height)
            else:
                self.log_message("获取分辨率失败，使用默认值", "all", "ERROR")
                return (1080, 1920)

        except Exception as e:
            error_msg = f"获取设备分辨率时发生错误: {str(e)}"
            self.log_message(error_msg, "all", "ERROR")
            # 移除冗余的控制台输出，log_message已经处理了ERROR级别的输出

            # 根据设备名称猜测分辨率
            return self.guess_resolution_by_device_name()


    def guess_resolution_by_device_name(self) -> tuple:
        """根据设备名称猜测分辨率"""
        if not self.current_device:
            return (1080, 1920)

        device_lower = self.current_device.lower()

        # 常见设备分辨率映射
        resolution_map = {
            # 三星
            'sm-': (1440, 2560),  # 三星高端机
            'samsung': (1080, 1920),
            'galaxy': (1080, 1920),

            # 谷歌
            'pixel': (1080, 1920),
            'nexus': (1440, 2560),

            # 小米
            'mi ': (1080, 2340),
            'redmi': (1080, 2340),
            'xiaomi': (1080, 2340),

            # 华为
            'huawei': (1080, 2240),
            'honor': (1080, 2240),
            'p40': (1200, 2640),
            'mate': (1440, 3120),

            # OPPO/Vivo
            'oppo': (1080, 2340),
            'vivo': (1080, 2340),
            'oneplus': (1440, 3120),

            # 其他
            'iphone': (1125, 2436),  # iPhone X/XS/11 Pro
            'ipad': (1668, 2388),    # iPad Pro
        }

        for keyword, resolution in resolution_map.items():
            if keyword in device_lower:
                self.log_message(f"📏 根据设备名猜测分辨率: {resolution[0]}x{resolution[1]}", "all", "INFO")
                return resolution

        # 网络设备可能包含IP地址，使用常见手机分辨率
        if ':' in self.current_device and '.' in self.current_device.split(':')[0]:
            self.log_message("🌐 网络设备，使用常见手机分辨率", "all", "INFO")
            return (1080, 1920)

        # 默认值
        self.log_message("📏 使用默认分辨率: 1080x1920", "all", "INFO")
        return (1080, 1920)

    def safe_press(self, x: int, y: int, duration_ms: Optional[int] = None, purpose: str = "") -> bool:
        """
        安全按压模拟 - 所有"点击"操作的唯一入口
        """
        if not self.controller_id:
            self.log_message("设备未连接，无法执行安全按压", "llm", "ERROR")
            return False

        # 获取设备分辨率用于验证
        device_width, device_height = self.get_device_resolution()

        # 验证坐标范围
        if not (0 <= x <= device_width and 0 <= y <= device_height):
            self.log_message(f"坐标超出设备范围: ({x}, {y}) 设备分辨率: {device_width}x{device_height}", "llm", "WARNING")

        duration = duration_ms if duration_ms is not None else self.press_duration_ms
        jitter = self.press_jitter_px

        # 注入自然抖动（模拟人类手指微动）
        dx = random.randint(-jitter, jitter) if jitter > 0 else 0
        dy = random.randint(-jitter, jitter) if jitter > 0 else 0

        # 滑动模拟按压：起点=目标点+偏移，终点=目标点
        start_x, start_y = x + dx, y + dy
        end_x, end_y = x, y

        # 日志记录（含安全标识）
        self.log_message(
            f"👆 安全按压 ({start_x},{start_y})→({end_x},{end_y}) {duration}ms | 抖动±{jitter}px | {purpose}",
            "llm"
        )

        # 执行滑动（核心安全机制）
        try:
            success = swipe(self.controller_id, start_x, start_y, end_x, end_y, duration)
            if not success:
                self.log_message(f"安全按压失败: ({x},{y})", "llm", "WARNING")
            return success
        except Exception as e:
            self.log_message(f"安全按压异常: {str(e)}", "llm", "ERROR")
            return False
    
    def safe_swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, 
                   duration_ms: int = 300, purpose: str = "") -> bool:
        """
        安全滑动操作（保留原始滑动能力，用于页面滚动等）
        """
        if not self.controller_id:
            return False
        
        self.log_message(
            f"👆 安全滑动 ({start_x},{start_y})→({end_x},{end_y}) {duration_ms}ms | {purpose}",
            "llm"
        )
        
        try:
            return swipe(self.controller_id, start_x, start_y, end_x, end_y, duration_ms)
        except Exception as e:
            self.log_message(f"安全滑动异常: {str(e)}", "llm", "ERROR")
            return False
    
    # ==================== VLM集成核心 ====================
    def build_vlm_prompt(self, content_window: Dict) -> str:
        """将content_window转换为VLM可理解的文本提示"""
        prompt = f"""# 明日方舟：终末地 LLM自动化助手

## 全局目标
{content_window['global_goal']}

## 任务步骤
"""
        for i, step in enumerate(content_window['task_list']):
            prompt += f"{i+1}. {step}\n"
        
        prompt += "\n## 当前子任务状态（队列形式）\n"
        for st in content_window['splited_task']:
            status_text = {"pending": "待完成", "in_progress": "进行中", "completed": "已完成"}.get(st['status'], "未知")
            status_emoji = {"pending": "▫", "in_progress": "▸", "completed": "✓"}.get(st['status'], "•")
            prompt += f"{status_emoji} [{st['status']}] {st['desc']} (ID: {st['id']})\n"
            if st['subtasks']:
                for sub in st['subtasks']:
                    sub_emoji = {"pending": "▫", "in_progress": "▸", "completed": "✓"}.get(sub['status'], "•")
                    prompt += f"  {sub_emoji} {sub['desc']} (ID: {sub['id']})\n"
        
        prompt += f"\n## 持久化知识库（最近10条）\n"
        for i, kb in enumerate(content_window['markdown'][-10:]):
            prompt += f"{i+1}. [{kb['type']}] {kb['content']}"
            if 'coordinates' in kb:
                coords = kb['coordinates']
                prompt += f" | 位置比例: ({coords['x_ratio']:.2f}, {coords['y_ratio']:.2f}) ±({coords['width_ratio']:.2f}, {coords['height_ratio']:.2f})"
            if 'image_path' in kb:
                prompt += f" | 截图: {os.path.basename(kb['image_path'])}"
            prompt += "\n"
        
        prompt += f"\n## 最近操作历史（最近5次）\n"
        for i, func in enumerate(content_window['function'][-5:]):
            prompt += f"{i+1}. {func['timestamp'][-12:]} | {func['action']} | {func.get('purpose', 'N/A')}\n"
        
        prompt += """

## 屏幕状态
- 分辨率: 1080x1920 (标准安卓设备)
- 时间戳: {timestamp}
- 当前界面: 请分析提供的截图

## 坐标系统
- 使用比例坐标 (0.0-1.0) 替代像素坐标
- 屏幕左上角: (0.0, 0.0)
- 屏幕右下角: (1.0, 1.0)
- 示例：屏幕中心 = (0.5, 0.5)

## 重要：坐标格式
所有工具调用必须使用比例坐标：
- safe_press: {"x": 0.5, "y": 0.5, "purpose": "点击中心"}
- safe_swipe: {"start_x": 0.5, "start_y": 0.8, "end_x": 0.5, "end_y": 0.2, "purpose": "向上滑动"}

## 操作规范
1. 所有"点击"必须使用 safe_press 工具（内部已实现安全滑动模拟，100ms按压+随机抖动）
2. 坐标单位：使用比例坐标 (0.0-1.0) 替代像素坐标
3. 屏幕左上角: (0.0, 0.0)，屏幕右下角: (1.0, 1.0)
4. 示例：屏幕中心 = (0.5, 0.5)
5. 每次只调用一个工具，完成后再进行下一步决策
6. 操作前必须在purpose参数中说明目的（例如："点击战术终端入口以进入关卡选择"）
7. 避免连续快速操作（两次操作间隔建议≥800ms）
8. 子任务管理：
   - 创建新子任务: create_subtask(desc, parent_id?)
   - 更新状态: update_subtask_status(task_id, status, notes?)
9. 知识库更新：
   - 识别到新按钮/元素时，使用 add_knowledge_entry 记录（含坐标比例和截图）

## 可用工具
- safe_press: 安全按压（点击）
- safe_swipe: 安全滑动（页面滚动/拖拽）
- wait: 等待（界面加载/动画）
- input_text: 输入文本
- press_key: 按键（BACK/HOME）
- create_subtask: 创建子任务
- update_subtask_status: 更新子任务状态
- add_knowledge_entry: 添加知识库词条

## 重要安全提示
禁止使用原始click API！所有点击必须通过safe_press实现安全按压模拟
操作必须符合人类行为模式（自然时长+随机抖动）
避免高频操作（可能触发反作弊）

请直接返回工具调用，无需解释思考过程。
"""
        # 注入实际timestamp
        timestamp = content_window['device_vision'].get('timestamp', 'N/A')
        prompt = prompt.replace("{timestamp}", timestamp)
        return prompt
    
    def call_vlm(self, content_window: Dict) -> List[Dict]:
        """
        调用VLM服务器，返回解析后的工具调用列表
        支持本地VLM和云VLM服务的互斥切换
        返回: [{"action": "safe_press", "params": {...}, "purpose": "..."}, ...]
        """
        # 检查是否启用云VLM服务
        if hasattr(self, 'use_cloud_var') and self.use_cloud_var.get():
            # 详细记录云服务检查过程
            self.log_message("🌐 检查云VLM服务可用性...", "llm", "INFO")

            # 增强云客户端状态检查
            cloud_client_status = self._check_cloud_client_status()
            if not cloud_client_status['is_connected']:
                error_msg = cloud_client_status['error_msg']
                self.log_message(f"云VLM服务状态异常: {error_msg}", "llm", "WARNING")

                # 尝试重新连接
                if self._try_reconnect_cloud_client():
                    self.log_message("云VLM服务重新连接成功，使用云服务", "llm", "INFO")
                    return self._call_cloud_vlm_with_retry(content_window)
                else:
                    self.log_message("云VLM服务不可用，尝试回退到本地VLM", "llm", "WARNING")

                    # 回退到本地VLM检查
                    if not VLM_AVAILABLE:
                        self.log_message("本地VLM也不可用，无法执行任务", "llm", "ERROR")
                        messagebox.showerror("VLM错误", "云VLM服务和本地VLM都不可用！\n\n请确保：\n1. 云服务连接正常，或\n2. 本地VLM服务器正在运行\n\n程序无法在没有VLM的情况下执行任务。")
                        return []
                    return self._call_local_vlm(content_window)
            else:
                self.log_message("🌐 云VLM服务状态正常，使用云服务处理请求", "llm", "INFO")
                return self._call_cloud_vlm_with_retry(content_window)

        # 使用本地VLM
        if not VLM_AVAILABLE:
            self.log_message("VLM不可用，无法执行任务", "llm", "ERROR")
            messagebox.showerror("VLM错误", "VLM服务器不可用！\n\n请确保：\n1. VLM服务器正在运行\n2. 配置文件正确\n\n程序无法在没有VLM的情况下执行任务。")
            return []

        return self._call_local_vlm(content_window)

    def _process_cloud_response(self, response: Dict) -> List[Dict]:
        """处理云VLM响应的通用逻辑"""
        try:
            if not response or response.get('status') == 'error':
                error_msg = response.get('msg', '云VLM服务无响应') if response else '云VLM服务无响应'
                self.log_message(f"云VLM调用失败: {error_msg}", "llm", "ERROR")
                return []

            # 解析云VLM响应
            choices = response.get('choices', [])
            if not choices:
                self.log_message("云VLM返回空响应", "llm", "WARNING")
                return []

            message = choices[0].get('message', {})
            tool_calls = message.get('tool_calls', [])

            if not tool_calls:
                self.log_message("云VLM未返回工具调用", "llm", "WARNING")
                # 尝试回退到等待操作
                return [{"action": "wait", "params": {"duration_ms": 1500}, "purpose": "等待界面变化"}]

            # 解析工具调用参数
            parsed_tool_calls = []
            for tc in tool_calls:
                try:
                    function = tc.get('function', {})
                    tool_name = function.get('name')
                    arguments = function.get('arguments', '{}')

                    if tool_name:
                        # 解析JSON参数
                        args = json.loads(arguments) if isinstance(arguments, str) else arguments
                        # 构建标准工具调用格式
                        tool_call = {
                            "action": tool_name,
                            "params": args,
                            "purpose": args.get('purpose', '未指定目的')
                        }
                        parsed_tool_calls.append(tool_call)
                        self.log_message(f"🌐 云工具调用: {tool_name} | {tool_call['purpose']}", "llm")

                except json.JSONDecodeError as e:
                    self.log_message(f"云工具参数解析失败: {str(e)}", "llm", "WARNING")
                except Exception as e:
                    self.log_message(f"云工具调用处理异常: {str(e)}", "llm", "ERROR")

            if not parsed_tool_calls:
                self.log_message("云VLM未返回有效工具调用", "llm", "WARNING")
                return [{"action": "wait", "params": {"duration_ms": 1500}, "purpose": "等待界面变化"}]

            return parsed_tool_calls

        except Exception as e:
            self.log_message(f"处理云VLM响应时发生异常: {str(e)}", "llm", "ERROR")
            return []

    def _call_cloud_vlm(self, content_window: Dict) -> List[Dict]:
        """调用云VLM服务"""
        # 增强云客户端状态检查
        cloud_client_status = self._check_cloud_client_status()
        if not cloud_client_status['is_connected']:
            error_msg = cloud_client_status['error_msg']
            self.log_message(f"云VLM服务客户端状态异常: {error_msg}", "llm", "ERROR")

            # 尝试重新连接一次
            if self._try_reconnect_cloud_client():
                self.log_message("云VLM服务重新连接成功，继续执行", "llm", "INFO")
            else:
                self.log_message("云VLM服务重新连接失败，回退到本地VLM", "llm", "WARNING")
                if VLM_AVAILABLE:
                    return self._call_local_vlm(content_window)
                else:
                    self.log_message("本地VLM也不可用，无法执行任务", "llm", "ERROR")
                    return []

        try:
            self.log_message(f"🌐 调用云VLM分析界面 (timestamp: {content_window['device_vision']['timestamp'][-12:]})", "llm")

            # 构建云VLM请求
            prompt = self.build_vlm_prompt(content_window)
            img_path = content_window['device_vision']['screenshot_path']

            # 读取图像并转换为base64
            with open(img_path, 'rb') as f:
                image_data = f.read()
                image_b64 = base64.b64encode(image_data).decode('utf-8')

            # 构建OpenAI格式请求 (模型将由服务器覆盖)
            cloud_request = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                }
                            }
                        ]
                    }
                ],
                "tools": self.tools,
                "tool_choice": "required",
                "temperature": 0.7
                # 移除max_tokens限制，让模型使用默认值
            }

            # 发送云VLM请求
            response = self.cloud_client.chat_completion(cloud_request)

            if not response or response.get('status') == 'error':
                error_msg = response.get('msg', '云VLM服务无响应') if response else '云VLM服务无响应'
                self.log_message(f"云VLM调用失败: {error_msg}", "llm", "ERROR")
                return []

            # 处理响应
            return self._process_cloud_response(response)

        except Exception as e:
            error_msg = f"云VLM调用失败: {str(e)}"
            self.log_message(error_msg, "llm", "ERROR")

            # 🔧 增强错误处理：针对连接错误尝试重连
            if "10053" in str(e) or "连接被中止" in str(e) or "ConnectionAbortedError" in str(e):
                self.log_message("🔄 检测到连接中断，尝试自动重连", "llm", "INFO")
                if self._try_reconnect_cloud_client():
                    self.log_message("🌐 重连成功，重试云VLM调用", "llm", "INFO")
                    # 重试一次（避免无限递归）
                    try:
                        response = self.cloud_client.chat_completion(cloud_request)
                        if response and response.get('status') != 'error':
                            self.log_message("🌐 重连后调用成功，处理响应", "llm", "INFO")
                            return self._process_cloud_response(response)
                    except Exception as retry_e:
                        self.log_message(f"⚠️ 重连后仍失败: {str(retry_e)}", "llm", "ERROR")

            # 云服务调用失败，尝试回退到本地VLM
            self.log_message("云VLM服务调用异常，回退到本地VLM", "llm", "WARNING")
            if VLM_AVAILABLE:
                return self._call_local_vlm(content_window)
            else:
                self.log_message("本地VLM不可用，无法执行任务", "llm", "ERROR")
                return []


    def _call_cloud_vlm_with_retry(self, content_window: Dict, max_retries: int = 2) -> List[Dict]:
        """带重试机制的云VLM调用"""
        for attempt in range(max_retries + 1):
            try:
                # 直接执行调用，不再依赖不存在的方法
                cloud_client_status = self._check_cloud_client_status()
                if not cloud_client_status['is_connected']:
                    self.log_message(f"云服务连接异常，尝试重新连接 {attempt + 1}/{max_retries + 1}", "llm", "WARNING")

                    # 尝试重新连接
                    if self._try_reconnect_cloud_client():
                        self.log_message("云服务重新连接成功", "llm", "INFO")
                    else:
                        if attempt < max_retries:
                            time.sleep(1.0)
                            continue
                        else:
                            self.log_message("云服务重连失败，回退到本地VLM", "llm", "ERROR")
                            return self._call_local_vlm(content_window) if VLM_AVAILABLE else []

                # 构建云VLM请求
                prompt = self.build_vlm_prompt(content_window)
                img_path = content_window['device_vision']['screenshot_path']

                # 读取图像并转换为base64
                with open(img_path, 'rb') as f:
                    image_data = f.read()
                    image_b64 = base64.b64encode(image_data).decode('utf-8')

                cloud_request = {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_b64}"
                                    }
                                }
                            ]
                        }
                    ],
                    "tools": self.tools,
                    "tool_choice": "required",
                    "temperature": 0.7
                    # 移除max_tokens限制，让模型使用默认值
                }

                # 发送请求并处理响应
                response = self.cloud_client.chat_completion(cloud_request)
                return self._process_cloud_response(response)

            except Exception as e:
                self.log_message(f"云VLM调用第 {attempt + 1} 次尝试失败: {str(e)}", "llm", "WARNING")

                # 特定错误处理
                if "10053" in str(e) or "连接被中止" in str(e):
                    self.log_message("检测到连接中断，强制重连", "llm", "INFO")
                    self._try_reconnect_cloud_client()

                if attempt < max_retries:
                    time.sleep(2.0)
                else:
                    self.log_message("所有重试均失败，回退到本地VLM", "llm", "ERROR")
                    return self._call_local_vlm(content_window) if VLM_AVAILABLE else []

        return []

    def _check_cloud_client_status(self) -> Dict:
        """检查云客户端状态"""
        try:
            if not hasattr(self, 'cloud_client') or not self.cloud_client:
                return {
                    'is_connected': False,
                    'error_msg': '云客户端未初始化'
                }

            # 检查连接状态
            if hasattr(self.cloud_client, 'is_connected'):
                is_connected = self.cloud_client.is_connected
                if is_connected:
                    return {
                        'is_connected': True,
                        'error_msg': ''
                    }
                else:
                    return {
                        'is_connected': False,
                        'error_msg': '云客户端未连接'
                    }

            # 如果没有is_connected属性，假设已连接
            return {
                'is_connected': True,
                'error_msg': ''
            }
        except Exception as e:
            return {
                'is_connected': False,
                'error_msg': f'检查云客户端状态时出错: {str(e)}'
            }

    def _try_reconnect_cloud_client(self) -> bool:
        """尝试重新连接云客户端"""
        try:
            if hasattr(self, 'cloud_client') and self.cloud_client:
                # 检查是否有重连方法
                if hasattr(self.cloud_client, 'reconnect'):
                    success = self.cloud_client.reconnect()
                    if success:
                        self.log_message("云VLM服务重连成功", "llm", "INFO")
                        return True
                else:
                    self.log_message("云客户端不支持重连方法", "llm", "WARNING")
            return False
        except Exception as e:
            self.log_message(f"云VLM服务重连过程中发生异常: {str(e)}", "llm", "ERROR")
            return False

    def _call_local_vlm(self, content_window: Dict) -> List[Dict]:
        """调用本地VLM服务"""

        # 构建prompt和图像路径
        prompt = self.build_vlm_prompt(content_window)
        img_path = content_window['device_vision']['screenshot_path']

        tool_calls = []  # 累积tool_calls（支持多工具调用）
        accumulated_text = ""  # 累积LLM思考文本

        try:
            self.log_message(f"🧠 调用本地VLM分析界面 (timestamp: {content_window['device_vision']['timestamp'][-12:]})", "llm")

            # 流式调用VLM
            for chunk in llm_requests(prompt, img_path, tools=self.tools, tool_choice="required"):
                if self.llm_stop_flag:
                    self.log_message("VLM调用被用户中断", "llm", "WARNING")
                    return []

                # 处理流式响应
                if 'choices' in chunk and chunk['choices']:
                    delta = chunk['choices'][0].get('delta', {})

                    # 累积文本（用于显示思考过程）
                    if 'content' in delta and delta['content']:
                        accumulated_text += delta['content']
                        # 实时显示思考文本（每50字符更新一次）
                        if len(accumulated_text) % 50 == 0:
                            self.root.after(0, self.log_message, f"💭 {accumulated_text[-50:]}", "llm", "INFO")

                    # 处理tool_calls（OpenAI格式）
                    if 'tool_calls' in delta:
                        for tc_delta in delta['tool_calls']:
                            index = tc_delta['index']
                            # 确保tool_calls列表有足够长度
                            while len(tool_calls) <= index:
                                tool_calls.append({
                                    "id": None,
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                })

                            tc = tool_calls[index]
                            if 'id' in tc_delta:
                                tc['id'] = tc_delta['id']
                            if 'function' in tc_delta:
                                func_delta = tc_delta['function']
                                if 'name' in func_delta:
                                    tc['function']['name'] = func_delta['name']
                                if 'arguments' in func_delta:
                                    tc['function']['arguments'] += func_delta['arguments']

            # 显示完整思考文本（简化）
            if accumulated_text.strip():
                preview = accumulated_text[:150] + "..." if len(accumulated_text) > 150 else accumulated_text
                self.log_message(f"💭 LLM思考: {preview}", "llm")

            # 解析tool_calls参数
            parsed_tool_calls = []
            for tc in tool_calls:
                try:
                    # 解析JSON参数
                    args = json.loads(tc['function']['arguments'])
                    # 构建标准工具调用格式
                    tool_call = {
                        "action": tc['function']['name'],
                        "params": args,
                        "purpose": args.get('purpose', '未指定目的')
                    }
                    parsed_tool_calls.append(tool_call)
                    self.log_message(f"🔧 工具调用: {tc['function']['name']} | {tool_call['purpose']}", "llm")
                except json.JSONDecodeError as e:
                    self.log_message(f"工具参数解析失败: {tc['function']['arguments'][:50]}... | 错误: {str(e)}", "llm", "WARNING")
                except Exception as e:
                    self.log_message(f"工具调用处理异常: {str(e)}", "llm", "ERROR")

            if not parsed_tool_calls:
                self.log_message("VLM未返回有效工具调用", "llm", "WARNING")
                # 尝试回退到等待操作
                return [{"action": "wait", "params": {"duration_ms": 1500}, "purpose": "等待界面变化"}]

            return parsed_tool_calls

        except Exception as e:
            error_msg = f"本地VLM调用失败: {str(e)}"
            self.log_message(error_msg, "llm", "ERROR")
            # 尝试提取关键错误信息
            if "Connection refused" in str(e):
                self.log_message("💡 提示: 请确保VLM服务器 (http://127.0.0.1:8080) 正在运行", "llm", "INFO")
            return []
    
    # ==================== LLM执行控制台（修改：支持任务队列） ====================
    def setup_llm_page(self):
        """LLM执行控制台 - 支持任务队列管理"""
        frame = ttk.Frame(self.llm_page_frame, padding="10")
        frame.pack(fill='both', expand=True)

        # 左右分栏：控制面板 | Content Window
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill='both', expand=True)

        # 左：控制面板
        control_frame = ttk.Frame(paned)
        paned.add(control_frame, weight=1)

        # === 任务队列管理（修改部分）===
        task_queue_frame = ttk.LabelFrame(control_frame, text="任务队列", padding="10")
        task_queue_frame.pack(fill='x', pady=(0, 10))

        # 任务队列列表
        self.task_queue_listbox = tk.Listbox(task_queue_frame, height=8, font=('Arial', 10))
        self.task_queue_listbox.pack(fill='both', expand=True, pady=(0, 5))

        # 绑定双击事件
        self.task_queue_listbox.bind('<Double-Button-1>', lambda e: self.open_selected_task_settings())

        # 添加上下文菜单
        self.task_queue_context_menu = tk.Menu(self.root, tearoff=0)
        self.task_queue_context_menu.add_command(label="打开设置", command=self.open_selected_task_settings)
        self.task_queue_context_menu.add_separator()
        self.task_queue_context_menu.add_command(label="上移", command=self.move_task_up)
        self.task_queue_context_menu.add_command(label="下移", command=self.move_task_down)
        self.task_queue_context_menu.add_separator()
        self.task_queue_context_menu.add_command(label="删除", command=self.remove_task_from_queue)

        self.task_queue_listbox.bind('<Button-3>', self.show_task_context_menu)

        # 任务队列操作按钮
        queue_btn_frame = ttk.Frame(task_queue_frame)
        queue_btn_frame.pack(fill='x')

        # 第一行按钮
        row1_frame = ttk.Frame(queue_btn_frame)
        row1_frame.pack(fill='x', pady=(0, 5))

        self.create_btn(row1_frame, "添加任务", self.add_task_to_queue, None, tk.LEFT, padx=2, width=15)
        self.create_btn(row1_frame, "⚙️ 任务设置", self.open_selected_task_settings, None, tk.LEFT, padx=2, width=15)
        self.create_btn(row1_frame, "➖ 移除选中", self.remove_task_from_queue, None, tk.LEFT, padx=2, width=15)

        # 第二行按钮
        row2_frame = ttk.Frame(queue_btn_frame)
        row2_frame.pack(fill='x')

        self.create_btn(row2_frame, "上移", self.move_task_up, None, tk.LEFT, padx=2, width=10)
        self.create_btn(row2_frame, "下移", self.move_task_down, None, tk.LEFT, padx=2, width=10)
        self.create_btn(row2_frame, "清空队列", self.clear_task_queue, None, tk.LEFT, padx=2, width=12)

        # 队列信息显示
        self.queue_info_label = ttk.Label(task_queue_frame, text="队列: 0个任务", font=('Arial', 9))
        self.queue_info_label.pack(anchor=tk.W, pady=(5, 0))

        # 设备状态显示（仅保留状态信息）
        self.device_info_frame = ttk.Frame(control_frame)
        self.device_info_frame.pack(fill='x', pady=(0, 10))

        self.device_status_label = ttk.Label(self.device_info_frame, text="设备: 未连接", font=('Arial', 9))
        self.device_status_label.pack(anchor=tk.W)

        # 执行控制
        exec_frame = ttk.LabelFrame(control_frame, text="执行控制", padding="10")
        exec_frame.pack(fill='x', pady=(0, 10))
        self.llm_start_btn = self.create_btn(exec_frame, "▶ 启动推理", self.start_llm_execution, 'Security.TButton', tk.TOP, fill='x', pady=(0, 5))
        self.llm_stop_btn = self.create_btn(exec_frame, "■ 停止执行", self.stop_llm_execution, 'Stop.TButton', tk.TOP, fill='x', pady=(5, 0))
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

        # 保存spinbox的引用以便后续控制
        self.execution_count_entry = execution_count_spinbox

        # 添加持续循环选项
        self.continuous_loop_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(count_frame, text="持续循环",
                       variable=self.continuous_loop_var,
                       command=self.on_continuous_loop_changed).pack(side=tk.LEFT, padx=(20, 5))

        # 当前任务状态显示
        self.current_task_label = ttk.Label(exec_frame, text="当前: 无", font=('Arial', 9), justify=tk.LEFT)
        self.current_task_label.pack(anchor=tk.W, pady=(5, 0))

        # 子任务管理
        subtask_frame = ttk.LabelFrame(control_frame, text="🧩 当前任务子任务", padding="10")
        subtask_frame.pack(fill='both', expand=True)
        self.subtask_tree = ttk.Treeview(subtask_frame, columns=('status', 'desc', 'progress'), show='headings', height=10)
        self.subtask_tree.heading('status', text='状态')
        self.subtask_tree.heading('desc', text='任务描述')
        self.subtask_tree.heading('progress', text='进度')
        self.subtask_tree.column('status', width=80, anchor='center')
        self.subtask_tree.column('desc', width=200)
        self.subtask_tree.column('progress', width=80, anchor='center')
        self.subtask_tree.pack(fill='both', expand=True, pady=(0, 5))

        subtask_btn_frame = ttk.Frame(subtask_frame)
        subtask_btn_frame.pack(fill='x')
        self.create_btn(subtask_btn_frame, "添加子任务", self.add_subtask, None, tk.LEFT, padx=(0,5))
        self.create_btn(subtask_btn_frame, "✓ 标记完成", lambda: self.update_subtask_status("completed"), None, tk.LEFT, padx=5)
        self.create_btn(subtask_btn_frame, "▶ 标记进行中", lambda: self.update_subtask_status("in_progress"), None, tk.LEFT, padx=5)

        # 右：Content Window
        content_frame = ttk.Frame(paned)
        paned.add(content_frame, weight=2)

        # Content Window 标签页
        self.content_notebook = ttk.Notebook(content_frame)
        self.content_notebook.pack(fill='both', expand=True)

        # 完整Content Window
        full_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(full_frame, text='🧠 完整上下文')
        self.full_content_text = scrolledtext.ScrolledText(full_frame, wrap=tk.WORD, font=('Consolas', 9))
        self.full_content_text.pack(fill='both', expand=True)
        self.full_content_text.insert(1.0, "LLM接收的完整content_window将显示在这里...\n")

        # 设备视觉
        vision_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(vision_frame, text='设备视觉')
        self.vision_canvas = tk.Canvas(vision_frame, bg='black', highlightthickness=0)
        self.vision_canvas.pack(fill='both', expand=True)

        # 执行日志
        log_frame = ttk.Frame(content_frame)
        log_frame.pack(fill='x', pady=(5, 0))
        self.llm_log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
        self.llm_log_text.pack(fill='both', expand=True)
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill='x', pady=(5, 0))
        self.create_btn(log_btn_frame, "清空", lambda: self.clear_log("llm"), None, tk.LEFT, padx=(0, 5))
        self.create_btn(log_btn_frame, "💾 保存", lambda: self.save_log("llm"), None, tk.LEFT)

        # 刷新任务队列显示
        self.refresh_task_queue_display()

    def create_device_task_item(self):
        """创建设备连接任务项"""
        return {
            "template_id": "__device_setup__",
            "template_copy": {
                "template_id": "__device_setup__",  # 添加这个字段
                "id": "__device_setup__",
                "name": "📱 设备连接",
                "description": "连接目标Android设备，为后续任务做准备",
                "type": "device_setup",
                "fixed": True,
                "variables": [],
                "task_steps": ["自动连接设备并确保屏幕已解锁"],
                "success_indicators": ["设备已连接"]
            },
            "task_settings": {
                "retry_count": 3,
                "timeout": 10,
                "continue_on_failure": False
            },
            "variables_override": {},
            "enabled": True,
            "order": 0
        }

    def load_task_queue(self):
        """从文件加载任务队列"""
        try:
            queue_path = "tasks/task_queue.json"
            if os.path.exists(queue_path):
                with open(queue_path, 'r', encoding='utf-8') as f:
                    queue_data = json.load(f)

                # 转换为内部格式
                task_queue = []
                for item in queue_data:
                    # 查找模板（如果模板不存在，则跳过）
                    template_id = item.get("template_id")
                    template_copy = item.get("template_copy")

                    if template_copy:
                        task_queue.append({
                            "template_id": template_id,
                            "template_copy": template_copy,
                            "task_settings": item.get("task_settings", {}),
                            "variables_override": item.get("variables_override", {}),
                            "enabled": item.get("enabled", True),
                            "order": item.get("order", len(task_queue))
                        })

                # 确保设备连接任务存在
                has_device_task = any(item["template_id"] == "__device_setup__" for item in task_queue)
                if not has_device_task:
                    # 插入设备连接任务到开始
                    device_task = self.create_device_task_item()
                    task_queue.insert(0, device_task)

                return task_queue
            else:
                # 创建默认队列（设备连接 + 空列表）
                return [self.create_device_task_item()]
        except Exception as e:
            self.log_message(f"加载任务队列失败: {e}", "llm", "ERROR")
            return [self.create_device_task_item()]

    def save_task_queue(self):
        """保存任务队列到文件"""
        try:
            os.makedirs("tasks", exist_ok=True)
            queue_path = "tasks/task_queue.json"

            # 准备保存的数据
            save_data = []
            for item in self.task_queue:
                save_data.append({
                    "template_id": item.get("template_id"),
                    "template_copy": item.get("template_copy"),
                    "task_settings": item.get("task_settings", {}),
                    "variables_override": item.get("variables_override", {}),
                    "enabled": item.get("enabled", True),
                    "order": item.get("order", 0)
                })

            with open(queue_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            self.log_message(f"任务队列已保存 ({len(self.task_queue)}个任务)", "llm", "INFO")
        except Exception as e:
            self.log_message(f"保存任务队列失败: {e}", "llm", "ERROR")

    def add_subtask(self):
        """添加子任务（手动）"""
        desc = simpledialog.askstring("添加子任务", "子任务描述:")
        if desc and desc.strip():
            subtask = {
                "id": f"st_{len(self.current_subtasks)+1}_{int(time.time())}",
                "desc": desc.strip(),
                "status": "pending",
                "subtasks": []
            }
            self.current_subtasks.append(subtask)
            self.refresh_subtask_ui()
            self.log_message(f"手动添加子任务: {desc}", "llm")
    
    def update_subtask_status(self, new_status: str):
        """手动更新子任务状态"""
        selection = self.subtask_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择子任务")
            return
        
        item_id = selection[0]
        # 查找对应子任务
        for st in self.current_subtasks:
            if st['id'] == item_id:
                st['status'] = new_status
                self.refresh_subtask_ui()
                self.log_message(f"手动更新子任务状态: {st['desc']} → {new_status}", "llm")
                return
    
    def refresh_subtask_ui(self):
        """刷新子任务UI"""
        self.subtask_tree.delete(*self.subtask_tree.get_children())
        for st in self.current_subtasks:
            status_text = {"pending": "待完成", "in_progress": "进行中", "completed": "已完成"}[st['status']]
            progress = f"{len([s for s in st['subtasks'] if s.get('status') == 'completed'])}/{len(st['subtasks'])}" if st['subtasks'] else "-"
            self.subtask_tree.insert("", "end", iid=st['id'], values=(status_text, st['desc'], progress))

    # ==================== 任务队列管理方法 ====================

    def add_task_to_queue(self):
        """添加任务到队列"""
        # 创建对话框选择任务模板
        dialog = tk.Toplevel(self.root)
        dialog.title("选择任务模板")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # 任务模板列表
        ttk.Label(dialog, text="选择要添加的任务模板:", font=('Arial', 10, 'bold')).pack(pady=10)

        listbox_frame = ttk.Frame(dialog)
        listbox_frame.pack(fill='both', expand=True, padx=10, pady=5)

        template_listbox = tk.Listbox(listbox_frame, height=12, font=('Arial', 10))
        template_listbox.pack(side=tk.LEFT, fill='both', expand=True)

        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=template_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill='y')
        template_listbox.config(yscrollcommand=scrollbar.set)

        # 填充任务模板
        for i, template in enumerate(self.task_templates):
            template_listbox.insert(tk.END, f"{template['name']} - {template['description'][:60]}...")

        def add_selected():
            selection = template_listbox.curselection()
            if not selection:
                messagebox.showwarning("警告", "请选择一个任务模板")
                return

            selected_index = selection[0]
            if selected_index < len(self.task_templates):
                template = self.task_templates[selected_index]
                template_id = template['id']

                # 检查是否已在队列中
                if template_id in [task['template_copy']['id'] for task in self.task_queue]:
                    messagebox.showinfo("提示", "该任务已在队列中")
                else:
                    # 创建深拷贝
                    import copy
                    template_copy = copy.deepcopy(template)

                    # 创建任务项
                    task_item = {
                        "template_id": template_id,
                        "template_copy": template_copy,
                        "task_settings": {
                            "retry_count": 3,
                            "timeout": 300,
                            "continue_on_failure": False
                        },
                        "variables_override": {},  # 初始无覆盖，用户可在任务设置中配置
                        "enabled": True,
                        "order": len(self.task_queue)
                    }

                    self.task_queue.append(task_item)

                    # 确保设备连接任务始终是第一个
                    has_device_task = any(item["template_id"] == "__device_setup__" for item in self.task_queue)
                    if not has_device_task:
                        # 插入设备连接任务到开始
                        device_task = self.create_device_task_item()
                        self.task_queue.insert(0, device_task)
                        # 更新所有任务的order
                        for i, task in enumerate(self.task_queue):
                            task["order"] = i

                    self.save_task_queue()  # 立即保存
                    self.refresh_task_queue_display()
                    self.log_message(f"已添加任务到队列: {template['name']}", "llm")

            dialog.destroy()

        # 按钮框架
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10, padx=10)

        ttk.Button(btn_frame, text="✅ 添加", command=add_selected,
                   style='Security.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="❌ 取消",
                   command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def configure_variables_dialog(self, template, select_variables):
        """配置变量多选值的对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"配置变量 - {template['name']}")
        dialog.geometry("600x450")
        dialog.transient(self.root)
        dialog.grab_set()

        result = {'confirmed': False, 'variables': {}}

        ttk.Label(dialog, text="请配置以下变量的值:", font=('Arial', 10, 'bold')).pack(pady=10)

        # 创建滚动的变量配置区域
        canvas = tk.Canvas(dialog, highlightthickness=0)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding="10")

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        canvas.configure(yscrollcommand=scrollbar.set)

        variables_config = {}

        for i, var in enumerate(select_variables):
            var_frame = ttk.LabelFrame(scrollable_frame, text=f"变量: {var['name']}", padding="10")
            var_frame.pack(fill='x', pady=5)

            ttk.Label(var_frame, text="描述:").pack(anchor=tk.W)
            ttk.Label(var_frame, text=var.get('desc', '无描述'), font=('Arial', 9)).pack(anchor=tk.W, pady=(0, 5))

            ttk.Label(var_frame, text="可选值:").pack(anchor=tk.W)

            # 根据可选值数量选择UI
            multi_values = var.get('multi_values', [])
            if len(multi_values) <= 4:
                # 使用Radio Buttons
                selected_var = tk.StringVar(value=var.get('default', multi_values[0] if multi_values else ''))
                for value in multi_values:
                    ttk.Radiobutton(var_frame, text=value, variable=selected_var, value=value).pack(anchor=tk.W)
                variables_config[var['name']] = selected_var
            else:
                # 使用Combobox
                ttk.Label(var_frame, text="选择值:").pack(anchor=tk.W, pady=(5, 0))
                selected_var = tk.StringVar(value=var.get('default', multi_values[0] if multi_values else ''))
                combo = ttk.Combobox(var_frame, textvariable=selected_var, values=multi_values, state='readonly')
                combo.pack(fill='x', pady=2)
                variables_config[var['name']] = selected_var

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        # 按钮区域
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', padx=10, pady=10)

        def on_confirm():
            result['confirmed'] = True
            for var_name, var_widget in variables_config.items():
                result['variables'][var_name] = var_widget.get()
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        ttk.Button(btn_frame, text="确认", command=on_confirm, style='Security.TButton').pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.RIGHT, padx=5)

        # 添加鼠标滚轮支持
        def _on_mousewheel(event):
            if sys.platform.startswith('win') or sys.platform.startswith('darwin'):
                delta = -1 * (event.delta // 120) if event.delta else 0
                canvas.yview_scroll(delta, "units")
            else:
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")

        dialog.bind("<MouseWheel>", _on_mousewheel)
        dialog.bind("<Button-4>", _on_mousewheel)
        dialog.bind("<Button-5>", _on_mousewheel)

        dialog.wait_window()

        if result['confirmed']:
            # 将配置的变量保存到模板的变量覆盖中
            # 这里需要在调用处处理
            self.last_variable_config = result['variables']

        return result['confirmed']

    def remove_task_from_queue(self):
        """从队列中移除选中的任务 - 确保索引0的任务无法被删除"""
        selection = self.task_queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个任务")
            return

        selected_index = selection[0]

        # 禁止删除索引0的任务
        if selected_index == 0:
            messagebox.showwarning("警告", "设备连接任务必须保持在队列首位，不能删除")
            return

        if 0 < selected_index < len(self.task_queue):
            task_item = self.task_queue[selected_index]
            # 双重检查：基于模板ID和索引位置
            if task_item.get("template_id") == "__device_setup__":
                messagebox.showwarning("警告", "设备连接任务不可删除")
                return
            task_name = task_item["template_copy"]["name"]
            self.task_queue.pop(selected_index)
            self.refresh_task_queue_display()
            self.save_task_queue()  # 保存更改
            self.log_message(f"🗑️ 已从队列移除任务: {task_name}", "llm")

    def move_task_up(self):
        """将选中的任务上移 - 禁止移动索引0的任务和索引1的任务上移"""
        selection = self.task_queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个任务")
            return

        selected_index = selection[0]

        # 禁止移动索引0和索引1的任务上移
        if selected_index <= 1:
            messagebox.showwarning("警告", "设备连接任务必须保持在队列首位，不能移动其他任务到它前面")
            return

        if selected_index > 1 and selected_index < len(self.task_queue):
            # 交换位置
            self.task_queue[selected_index], self.task_queue[selected_index-1] = \
                self.task_queue[selected_index-1], self.task_queue[selected_index]
            self.refresh_task_queue_display()
            self.save_task_queue()  # 保存更改
            # 保持选中状态
            self.task_queue_listbox.selection_set(selected_index-1)
            self.log_message(f"⬆️ 任务已上移", "llm")

    def move_task_down(self):
        """将选中的任务下移 - 禁止索引0的任务下移"""
        selection = self.task_queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个任务")
            return

        selected_index = selection[0]

        # 禁止索引0的任务下移
        if selected_index == 0:
            messagebox.showwarning("警告", "设备连接任务必须保持在队列首位，不能下移")
            return

        if selected_index < len(self.task_queue) - 1:
            # 交换位置
            self.task_queue[selected_index], self.task_queue[selected_index+1] = \
                self.task_queue[selected_index+1], self.task_queue[selected_index]
            self.refresh_task_queue_display()
            self.save_task_queue()  # 保存更改
            # 保持选中状态
            self.task_queue_listbox.selection_set(selected_index+1)
            self.log_message(f"⬇️ 任务已下移", "llm")

    def clear_task_queue(self):
        """清空任务队列"""
        if not self.task_queue:
            return

        if messagebox.askyesno("确认清空", "确定要清空整个任务队列吗？"):
            # 保留设备连接任务
            device_task = None
            for task in self.task_queue:
                if task.get("template_id") == "__device_setup__":
                    device_task = task
                    break

            self.task_queue = [device_task] if device_task else []
            self.refresh_task_queue_display()
            self.save_task_queue()  # 保存更改
            self.log_message("🗑️ 任务队列已清空（保留设备连接任务）", "llm")

    def refresh_task_queue_display(self):
        """刷新任务队列显示"""
        def _update():
            self.task_queue_listbox.delete(0, tk.END)

            for i, task_item in enumerate(self.task_queue):
                task = task_item["template_copy"]
                status_prefix = "▶ " if i == self.current_task_index else f"{i+1}. "

                # 添加设置图标标记
                settings_mark = " ⚙" if task_item.get("variables_override") else ""

                # 对于设备连接任务特殊标记
                if task_item.get("template_id") == "__device_setup__":
                    display_text = f"{status_prefix}📱 {task['name']}{settings_mark}"
                else:
                    display_text = f"{status_prefix}{task['name']}{settings_mark}"

                self.task_queue_listbox.insert(tk.END, display_text)

            # 更新队列信息
            queue_info = f"队列: {len(self.task_queue)}个任务"
            if self.task_queue:
                if self.current_task_index < len(self.task_queue):
                    current_task = self.task_queue[self.current_task_index]["template_copy"]["name"]
                    queue_info += f" | 当前: {current_task}"
                else:
                    queue_info += f" | 当前: 已完成"

            self.queue_info_label.config(text=queue_info)

        self.root.after(0, _update)

    def show_task_context_menu(self, event):
        """显示任务上下文菜单"""
        selection = self.task_queue_listbox.curselection()
        if selection:
            task_index = selection[0]
            task_item = self.task_queue[task_index]

            # 检查是否为设备连接任务（不可删除）
            if task_item.get("template_id") == "__device_setup__":
                self.task_queue_context_menu.entryconfig("删除", state="disabled")
            else:
                self.task_queue_context_menu.entryconfig("删除", state="normal")

            self.task_queue_context_menu.post(event.x_root, event.y_root)

    def open_selected_task_settings(self):
        """打开选中任务的设置"""
        selection = self.task_queue_listbox.curselection()
        if selection:
            self.open_task_settings(selection[0])

    def open_task_settings(self, task_index: int):
        """在标签页中打开任务特定设置 - 分离设备连接任务和普通任务的UI"""
        if task_index < 0 or task_index >= len(self.task_queue):
            return

        task_item = self.task_queue[task_index]
        task_template = task_item["template_copy"]

        # 1. 寻找"完整上下文"的位置
        target_idx = 0
        for i in range(self.content_notebook.index("end")):
            tab_text = self.content_notebook.tab(i, "text")
            if "完整上下文" in tab_text or "Content Window" in tab_text:
                target_idx = i
                break

        # 2. 创建新标签页
        settings_tab = ttk.Frame(self.content_notebook)
        tab_name = f"⚙️ {task_template['name']} 设置"
        self.content_notebook.insert(target_idx, settings_tab, text=tab_name)

        # 切换到新标签页
        self.content_notebook.select(settings_tab)

        # 3. 创建滚动容器
        canvas = tk.Canvas(settings_tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(settings_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 4. 检查是否是设备连接任务
        is_device_setup_task = task_template.get('template_id') == '__device_setup__'

        if is_device_setup_task:
            # === 设备连接任务的独有UI ===
            ttk.Label(scrollable_frame, text="📱 设备连接配置", font=('Arial', 12, 'bold')).pack(pady=(10, 5), anchor=tk.W)

            # 设备选择（从LLM执行控制台移动到任务设置）
            device_frame = ttk.LabelFrame(scrollable_frame, text="📱 执行设备配置", padding="10")
            device_frame.pack(fill='x', pady=(10, 5))

            # 设备选择和输入框架
            device_input_frame = ttk.Frame(device_frame)
            device_input_frame.pack(fill='x', pady=(0, 5))

            ttk.Label(device_input_frame, text="选择设备:").pack(side=tk.LEFT, padx=5)
            task_settings_device_combo = ttk.Combobox(device_input_frame, state="readonly", width=30)
            task_settings_device_combo.pack(side=tk.LEFT, padx=5, fill='x', expand=True)

            # 初始化设备列表
            all_devices = list(dict.fromkeys(self.device_cache))
            if hasattr(self, 'last_successful_device') and self.last_successful_device and self.last_successful_device in all_devices:
                all_devices.remove(self.last_successful_device)
                all_devices.insert(0, self.last_successful_device)
            task_settings_device_combo['values'] = all_devices if all_devices else ["未检测到设备"]

            # 默认选中最近一个连接成功的设备
            if self.last_successful_device:
                task_settings_device_combo.set(self.last_successful_device)

            # 刷新按钮
            refresh_btn = ttk.Button(device_input_frame, text="🔄 刷新列表",
                                    command=lambda: self.refresh_device_combo(task_settings_device_combo))
            refresh_btn.pack(side=tk.LEFT, padx=5)

            # 手动输入按钮
            manual_btn = ttk.Button(device_input_frame, text="手动输入",
                                   command=lambda: self.manual_input_device_for_settings(task_settings_device_combo))
            manual_btn.pack(side=tk.LEFT, padx=5)

            # 连接状态显示
            device_status_frame = ttk.Frame(device_frame)
            device_status_frame.pack(fill='x', pady=(5, 0))

            device_connection_status = ttk.Label(device_status_frame, text="设备状态: 未连接",
                                               font=('Arial', 9), foreground='gray')
            device_connection_status.pack(side=tk.LEFT)

            # 连接按钮
            connect_btn = ttk.Button(device_status_frame, text="🔌 连接设备",
                                    command=lambda: self.connect_device_from_settings(task_settings_device_combo, device_connection_status))
            connect_btn.pack(side=tk.RIGHT, padx=5)

            # 保存设备选择的引用，以便后续使用
            settings_tab.task_settings_device_combo = task_settings_device_combo
            settings_tab.device_connection_status = device_connection_status
            settings_tab.task_index = task_index

            # 设备连接任务说明
            info_frame = ttk.LabelFrame(scrollable_frame, text="📋 任务说明", padding="10")
            info_frame.pack(fill='x', pady=(10, 5))

            info_text = """设备连接任务说明：
• 此任务负责建立与Android设备的连接
• 支持USB和网络连接方式
• 连接成功后才能执行后续任务
• 此任务始终固定在队列第一位

注意事项：
• 确保设备已开启USB调试
• 网络连接需要输入IP:端口格式
• 连接失败时会自动重试"""

            ttk.Label(info_frame, text=info_text, font=('Arial', 9), justify=tk.LEFT).pack(anchor=tk.W)

            # 隐藏其他设置部分
            variable_widgets = {}

        else:
            # === 普通任务的UI ===
            # 检查模板是否有变量
            template_variables = task_template.get("variables", [])

            # 根据任务类型决定是否显示设备设置
            show_device_settings = len(template_variables) > 0

            if show_device_settings:
                # 4. 设备选择（从LLM执行控制台移动到任务设置）
                device_frame = ttk.LabelFrame(scrollable_frame, text="📱 执行设备配置", padding="10")
                device_frame.pack(fill='x', pady=(10, 5))

                # 设备选择和输入框架
                device_input_frame = ttk.Frame(device_frame)
                device_input_frame.pack(fill='x', pady=(0, 5))

                ttk.Label(device_input_frame, text="选择设备:").pack(side=tk.LEFT, padx=5)
                task_settings_device_combo = ttk.Combobox(device_input_frame, state="readonly", width=30)
                task_settings_device_combo.pack(side=tk.LEFT, padx=5, fill='x', expand=True)

                # 初始化设备列表
                all_devices = list(dict.fromkeys(self.device_cache))
                if hasattr(self, 'last_successful_device') and self.last_successful_device and self.last_successful_device in all_devices:
                    all_devices.remove(self.last_successful_device)
                    all_devices.insert(0, self.last_successful_device)
                task_settings_device_combo['values'] = all_devices if all_devices else ["未检测到设备"]

                # 默认选中最近一个连接成功的设备
                if self.last_successful_device:
                    task_settings_device_combo.set(self.last_successful_device)

                # 刷新按钮
                refresh_btn = ttk.Button(device_input_frame, text="🔄 刷新列表",
                                        command=lambda: self.refresh_device_combo(task_settings_device_combo))
                refresh_btn.pack(side=tk.LEFT, padx=5)

                # 手动输入按钮
                manual_btn = ttk.Button(device_input_frame, text="手动输入",
                                       command=lambda: self.manual_input_device_for_settings(task_settings_device_combo))
                manual_btn.pack(side=tk.LEFT, padx=5)

                # 连接状态显示
                device_status_frame = ttk.Frame(device_frame)
                device_status_frame.pack(fill='x', pady=(5, 0))

                device_connection_status = ttk.Label(device_status_frame, text="设备状态: 未连接",
                                                   font=('Arial', 9), foreground='gray')
                device_connection_status.pack(side=tk.LEFT)

                # 连接按钮
                connect_btn = ttk.Button(device_status_frame, text="🔌 连接设备",
                                        command=lambda: self.connect_device_from_settings(task_settings_device_combo, device_connection_status))
                connect_btn.pack(side=tk.RIGHT, padx=5)

                # 保存设备选择的引用，以便后续使用
                settings_tab.task_settings_device_combo = task_settings_device_combo
                settings_tab.device_connection_status = device_connection_status
                settings_tab.task_index = task_index

            # 5. 变量设置部分
            ttk.Label(scrollable_frame, text="任务变量设置", font=('Arial', 11, 'bold')).pack(pady=(10, 5), anchor=tk.W)

            if not template_variables:
                # 显示"无可用设置"
                no_settings_label = ttk.Label(scrollable_frame, text="无可用设置",
                                            font=('Arial', 10), foreground='gray')
                no_settings_label.pack(pady=20, anchor=tk.W)
                variable_widgets = {}
            else:
                # 获取当前覆盖值
                current_overrides = task_item.get("variables_override", {})

                # 为每个变量创建输入框
                variable_widgets = {}
                for var_def in template_variables:
                    var_frame = ttk.Frame(scrollable_frame)
                    var_frame.pack(fill='x', padx=10, pady=5)

                    var_name = var_def["name"]
                    var_type = var_def["type"]
                    default_val = var_def["default"]

                    # 使用覆盖值或默认值
                    current_val = current_overrides.get(var_name, default_val)

                    ttk.Label(var_frame, text=f"{var_name} ({var_type}):", width=20).pack(side=tk.LEFT)

                    # 根据变量类型创建不同的输入控件
                    if var_type == "bool":
                        var_var = tk.BooleanVar(value=str(current_val).lower() in ['true', '1', 'yes'])
                        ttk.Checkbutton(var_frame, variable=var_var).pack(side=tk.LEFT)
                    elif var_type == "int":
                        var_var = tk.StringVar(value=str(current_val))
                        ttk.Spinbox(var_frame, textvariable=var_var, from_=-1000000, to=1000000, width=15).pack(side=tk.LEFT, padx=5)
                    elif var_type == "float":
                        var_var = tk.StringVar(value=str(current_val))
                        ttk.Entry(var_frame, textvariable=var_var, width=20).pack(side=tk.LEFT, padx=5)
                    elif var_type == "select":
                        # 多选值类型使用Combobox
                        multi_values = var_def.get('multi_values', [])
                        if multi_values:
                            # 确保当前值在可选值中，如果不在则使用默认值
                            effective_value = current_val
                            if effective_value not in multi_values:
                                # 使用模板中的默认值或第一个可选值
                                template_default = var_def.get('default')
                                if template_default and template_default in multi_values:
                                    effective_value = template_default
                                elif multi_values:
                                    effective_value = multi_values[0]

                            var_var = tk.StringVar(value=effective_value)
                            combo = ttk.Combobox(var_frame, textvariable=var_var, values=multi_values, state='readonly', width=25)
                            combo.pack(side=tk.LEFT, padx=5)
                        else:
                            # 如果没有可选值，回退到普通输入框
                            var_var = tk.StringVar(value=str(current_val))
                            ttk.Entry(var_frame, textvariable=var_var, width=30).pack(side=tk.LEFT, padx=5)
                    else:  # string
                        var_var = tk.StringVar(value=str(current_val))
                        ttk.Entry(var_frame, textvariable=var_var, width=30).pack(side=tk.LEFT, padx=5)

                    # 显示默认值提示
                    if var_type == "select" and var_def.get('multi_values'):
                        ttk.Label(var_frame, text=f"可选: {', '.join(var_def['multi_values'])}", font=('Arial', 8), foreground='blue').pack(side=tk.LEFT, padx=10)
                    else:
                        ttk.Label(var_frame, text=f"默认: {default_val}", font=('Arial', 8), foreground='gray').pack(side=tk.LEFT, padx=10)

                    variable_widgets[var_name] = (var_var, var_type)

            # 6. 其他设置
            ttk.Label(scrollable_frame, text="其他设置", font=('Arial', 11, 'bold')).pack(pady=(20, 5), anchor=tk.W)

            # 启用/禁用任务
            enabled_var = tk.BooleanVar(value=task_item.get("enabled", True))
            enabled_frame = ttk.Frame(scrollable_frame)
            enabled_frame.pack(fill='x', padx=10, pady=5)
            ttk.Label(enabled_frame, text="启用任务:").pack(side=tk.LEFT)
            ttk.Checkbutton(enabled_frame, variable=enabled_var).pack(side=tk.LEFT)

            # 执行顺序
            order_var = tk.IntVar(value=task_item.get("order", task_index))
            order_frame = ttk.Frame(scrollable_frame)
            order_frame.pack(fill='x', padx=10, pady=5)
            ttk.Label(order_frame, text="执行顺序:").pack(side=tk.LEFT)
            ttk.Spinbox(order_frame, textvariable=order_var, from_=0, to=len(self.task_queue)-1, width=10).pack(side=tk.LEFT, padx=5)

        # 7. 保存设置并关闭的函数
        def save_and_close():
            """保存任务特定设置并关闭标签页"""
            # 仅对非设备连接任务处理变量覆盖
            if not is_device_setup_task:
                # 收集变量覆盖值
                new_overrides = {}
                for var_name, (var_widget, var_type) in variable_widgets.items():
                    try:
                        if var_type == "bool":
                            value = var_widget.get()
                        elif var_type == "int":
                            value = int(var_widget.get())
                        elif var_type == "float":
                            value = float(var_widget.get())
                        else:
                            value = var_widget.get()

                        # 检查是否与默认值不同
                        original_default = next((v["default"] for v in task_template.get("variables", []) if v["name"] == var_name), "")
                        if str(value) != str(original_default):
                            new_overrides[var_name] = value
                    except Exception as e:
                        self.log_message(f"变量 {var_name} 解析失败: {e}", "llm", "WARNING")

                # 更新任务项
                task_item["variables_override"] = new_overrides
                task_item["enabled"] = enabled_var.get() if 'enabled_var' in locals() else True
                task_item["order"] = order_var.get() if 'order_var' in locals() else task_index

            # 保存到本地
            self.save_task_queue()

            # 更新UI显示
            self.refresh_task_queue_display()

            self.log_message(f"已保存任务设置: {task_template['name']}", "llm")

            # 关闭当前标签页
            self.content_notebook.forget(settings_tab)

            # 切换回控制台
            self.notebook.select(self.llm_page_frame)

        # 8. 按钮区域
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.pack(fill='x', pady=20)

        # 根据任务类型显示不同的按钮
        if is_device_setup_task:
            # 设备连接任务只显示退出按钮
            ttk.Button(btn_frame, text="退出", command=save_and_close,
                      style='Security.TButton').pack(side=tk.LEFT, padx=10)
        else:
            # 普通任务显示完整按钮组
            ttk.Button(btn_frame, text="退出", command=save_and_close,
                      style='Security.TButton').pack(side=tk.LEFT, padx=10)
            ttk.Button(btn_frame, text="❌ 取消",
                      command=lambda: self.content_notebook.forget(settings_tab)).pack(side=tk.LEFT, padx=10)
            ttk.Button(btn_frame, text="🗑️ 重置为默认",
                      command=lambda: self.reset_task_settings(task_index, settings_tab)).pack(side=tk.LEFT, padx=10)

    def reset_task_settings(self, task_index: int, settings_tab: ttk.Frame):
        """重置任务设置为默认值（适配标签页模式）"""
        if messagebox.askyesno("确认重置", "确定重置所有设置为默认值吗？"):
            task_item = self.task_queue[task_index]
            task_item["variables_override"] = {}
            task_item["enabled"] = True
            task_item["order"] = task_index
            self.save_task_queue()
            self.refresh_task_queue_display()
            self.log_message(f"已重置任务设置: {task_item['template_copy']['name']}", "llm")

            # 重新加载标签页内容以显示重置后的默认值
            # 1. 保存当前任务名称和标签页位置
            current_task_name = task_item['template_copy']['name']

            # 2. 关闭当前标签页
            self.content_notebook.forget(settings_tab)

            # 3. 重新打开任务设置标签页（会加载默认值）
            self.open_task_settings(task_index)

    def refresh_device_combo(self, combo: ttk.Combobox):
        """刷新设备下拉框列表"""
        self.scan_devices()
        all_devices = list(dict.fromkeys(self.device_cache))
        if hasattr(self, 'last_successful_device') and self.last_successful_device and self.last_successful_device in all_devices:
            all_devices.remove(self.last_successful_device)
            all_devices.insert(0, self.last_successful_device)
        combo['values'] = all_devices if all_devices else ["未检测到设备"]
        self.log_message("设备列表已刷新", "llm", "INFO")

    def manual_input_device_for_settings(self, combo: ttk.Combobox):
        """为任务设置手动输入设备"""
        dialog = tk.Toplevel(self.root)  # 🔧 修复：使用self.root而不是self
        dialog.title("手动输入设备")
        dialog.geometry("300x120")
        dialog.resizable(False, False)

        ttk.Label(dialog, text="请输入设备名称:", font=('Arial', 10)).pack(pady=10)

        device_var = tk.StringVar()
        device_entry = ttk.Entry(dialog, textvariable=device_var, width=30)
        device_entry.pack(pady=5)
        device_entry.focus()

        def save_device():
            device_name = device_var.get().strip()
            if device_name:
                self.device_cache = [d for d in self.device_cache if d != device_name]
                self.device_cache.insert(0, device_name)
                if len(self.device_cache) > 50:
                    self.device_cache = self.device_cache[:50]
                combo['values'] = self.device_cache
                combo.set(device_name)
                dialog.destroy()
                self.log_message(f"已添加设备: {device_name}", "llm")
            else:
                messagebox.showwarning("警告", "设备名称不能为空")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="确定", command=save_device).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def connect_device_from_settings(self, combo: ttk.Combobox, status_label: ttk.Label):
        """从任务设置连接设备 (已修复)"""
        device_name = combo.get().strip()
        if not device_name or device_name == "未检测到设备":
            messagebox.showwarning("警告", "请先选择或输入设备名称")
            return

        # 更新UI状态为连接中
        status_label.config(text=f"正在连接 {device_name}...", foreground='orange')
        self.log_message(f"正在从设置页连接设备: {device_name}", "llm")

        def connect_thread():
            try:
                # 1. 尝试连接 (使用 android_control 中的函数)
                # 注意：如果 device_name 是 IP:Port 格式，可能需要先 add_network_device
                if ':' in device_name and '.' in device_name:
                    try:
                        ip, port = device_name.split(':')
                        add_network_device(ip, port)
                    except:
                        pass # 忽略格式解析错误，直接尝试连接

                controller_id = connect_adb_device(device_name)

                # 2. 处理连接结果
                if controller_id:
                    def _on_success():
                        self.controller_id = controller_id
                        self.current_device = device_name

                        # 更新上次成功设备
                        self.last_successful_device = device_name
                        self.save_last_successful_device(device_name)

                        # 刷新设备列表缓存
                        if device_name not in self.device_cache:
                            self.device_cache.insert(0, device_name)
                            self.save_device_cache()

                        self.log_message(f"设备已连接: {device_name} (ID: {self.controller_id})", "llm")
                        status_label.config(text=f"设备状态: 已连接", foreground='green')

                        # 同步更新其他页面的设备状态（如果存在）
                        if hasattr(self, 'device_status'):
                            self.device_status.config(text=f"{device_name}", style='Status.Ready.TLabel')
                        if hasattr(self, 'app_status'):
                            self.app_status.config(text="就绪", style='Status.Ready.TLabel')

                        # 尝试获取分辨率
                        threading.Thread(target=lambda: self.get_device_resolution(), daemon=True).start()

                    self.root.after(0, _on_success)
                else:
                    def _on_fail():
                        error_msg = "ADB返回空ID"
                        self.log_message(f"连接失败: {error_msg}", "llm", "ERROR")
                        status_label.config(text=f"连接失败", foreground='red')
                    self.root.after(0, _on_fail)

            except Exception as e:
                def _on_error(err_msg):
                    self.log_message(f"连接异常: {err_msg}", "llm", "ERROR")
                    status_label.config(text=f"连接异常", foreground='red')
                self.root.after(0, _on_error, str(e))

        # 启动后台线程
        threading.Thread(target=connect_thread, daemon=True).start()

    def open_task_editor_tab(self, task_index: Optional[int] = None, create_new: bool = False):
        """
        在完整上下文左侧新开一页进行编辑
        """
        # 1. 确定插入位置：在 "完整上下文" 标签页之前插入
        insert_index = 0  # "完整上下文" 是第一个标签页，插入到索引0（它前面）

        # 2. 创建编辑器容器
        editor_frame = ttk.Frame(self.content_notebook)

        # 3. 将此 frame 插入 notebook
        self.content_notebook.insert(insert_index, editor_frame, text="📝 任务详细编辑")
        self.content_notebook.select(editor_frame)  # 切换到新页

        # 4. 构建编辑器内容
        self._setup_task_editor_content(editor_frame, task_index)

        # 5. 底部按钮（保存和关闭）
        btn_frame = ttk.Frame(editor_frame)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10, padx=10)

        save_btn = ttk.Button(btn_frame, text="💾 保存并关闭",
                             command=lambda: self.save_and_close_task_editor(editor_frame))
        save_btn.pack(side=tk.RIGHT, padx=20)

        cancel_btn = ttk.Button(btn_frame, text="❌ 取消",
                               command=lambda: self.content_notebook.forget(editor_frame))
        cancel_btn.pack(side=tk.RIGHT, padx=10)

    def _setup_task_editor_content(self, editor_frame: ttk.Frame, task_index: Optional[int]):
        """设置任务编辑器的内容"""
        # 主容器
        main_container = ttk.Frame(editor_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 任务基本信息
        info_frame = ttk.LabelFrame(main_container, text="任务信息", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        # 任务名称
        name_frame = ttk.Frame(info_frame)
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="任务名称:").pack(side=tk.LEFT, padx=5)
        name_var = tk.StringVar()
        if task_index is not None and task_index < len(self.task_queue):
            name_var.set(self.task_queue[task_index]["template_copy"]["name"])
        name_entry = ttk.Entry(name_frame, textvariable=name_var, width=40)
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        editor_frame.name_var = name_var

        # 任务描述
        desc_frame = ttk.Frame(info_frame)
        desc_frame.pack(fill=tk.X, pady=5)
        ttk.Label(desc_frame, text="任务描述:").pack(side=tk.LEFT, padx=5)
        desc_var = tk.StringVar()
        if task_index is not None and task_index < len(self.task_queue):
            desc_var.set(self.task_queue[task_index]["template_copy"]["description"])
        desc_entry = ttk.Entry(desc_frame, textvariable=desc_var, width=60)
        desc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        editor_frame.desc_var = desc_var

        # 任务步骤编辑器
        steps_frame = ttk.LabelFrame(main_container, text="任务步骤", padding="10")
        steps_frame.pack(fill=tk.BOTH, expand=True)

        # 任务步骤的文本编辑框
        steps_text = scrolledtext.ScrolledText(steps_frame, wrap=tk.WORD, font=('Consolas', 10), height=10)
        steps_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # 加载现有步骤（如果编辑现有任务）
        if task_index is not None and task_index < len(self.task_queue):
            steps = self.task_queue[task_index]["template_copy"]["task_steps"]
            steps_text.insert(1.0, "\n".join(steps))

        editor_frame.steps_text = steps_text
        editor_frame.task_index = task_index

        # 添加使用说明
        help_label = ttk.Label(steps_frame, text="提示：每个步骤一行，支持任意文本", font=('Arial', 9), foreground='gray')
        help_label.pack(pady=5)

        # 标签页引用
        editor_frame.close_editor = lambda: self.content_notebook.forget(editor_frame)

    def save_and_close_task_editor(self, editor_frame: ttk.Frame):
        """保存任务编辑器的内容并关闭"""
        try:
            # 1. 获取编辑器中的数据
            task_name = editor_frame.name_var.get().strip()
            task_desc = editor_frame.desc_var.get().strip()
            task_steps_raw = editor_frame.steps_text.get(1.0, tk.END).strip()

            # 验证数据
            if not task_name:
                messagebox.showerror("错误", "任务名称不能为空")
                return

            if not task_steps_raw:
                messagebox.showerror("错误", "任务步骤不能为空")
                return

            # 2. 处理任务步骤
            task_steps = [step.strip() for step in task_steps_raw.split('\n') if step.strip()]

            # 3. 创建或更新任务
            task_index = editor_frame.task_index
            if task_index is not None and task_index < len(self.task_queue):
                # 更新现有任务
                task_item = self.task_queue[task_index]
                task_item["template_copy"]["name"] = task_name
                task_item["template_copy"]["description"] = task_desc
                task_item["template_copy"]["task_steps"] = task_steps
                self.log_message(f"已更新任务: {task_name}", "llm", "INFO")
            else:
                # 创建新任务
                import copy
                new_task = {
                    "template_id": f"custom_{int(time.time())}",
                    "template_copy": {
                        "id": f"custom_{int(time.time())}",
                        "name": task_name,
                        "description": task_desc,
                        "type": "custom",
                        "variables": [],
                        "task_steps": task_steps,
                        "success_indicators": []
                    },
                    "task_settings": {
                        "retry_count": 3,
                        "timeout": 300,
                        "continue_on_failure": False
                    },
                    "variables_override": {},
                    "enabled": True,
                    "order": len(self.task_queue)
                }
                self.task_queue.append(new_task)
                self.log_message(f"已创建新任务: {task_name}", "llm", "INFO")

            # 4. 保存到文件
            self.save_task_queue()
            self.refresh_task_queue_display()

            # 5. 关闭编辑器标签页
            self.content_notebook.forget(editor_frame)

            # 6. 提示保存成功
            messagebox.showinfo("成功", f"任务 '{task_name}' 已保存")

        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
            self.log_message(f"保存任务失败: {str(e)}", "llm", "ERROR")

    def start_llm_execution(self):
        """启动推理"""
        if not self.task_queue:
            messagebox.showwarning("警告", "任务队列为空，请添加任务")
            return

        # 检查设备连接，如果没有连接则自动连接
        if not self.controller_id:
            device_address = self.get_active_device_address()
            if device_address:
                self.log_message(f"🔄 自动连接设备: {device_address}", "llm")
                success = self.connect_device_by_address(device_address)
                if not success:
                    messagebox.showerror("错误", "设备连接失败，请检查设备状态")
                    return
            else:
                messagebox.showerror("错误", "未找到设备配置，请先配置设备")
                return

        # 重置状态
        self.llm_running = True
        self.llm_stop_flag = False
        self.current_task_index = 0  # 重置任务索引
        self.llm_start_btn.config(state='disabled')
        self.llm_stop_btn.config(state='normal')
        self.app_status.config(text="🧠 LLM运行中...", style='Status.Running.TLabel')

        # 更新当前任务显示
        self.update_current_task_display()

        self.log_message(f"▶ 启动推理，共 {len(self.task_queue)} 个任务", "llm")
        self.log_message(f"   安全参数: 按压{self.press_duration_ms}ms ±{self.press_jitter_px}px", "llm")
        self.log_message(f"   VLM模式: {'真实调用' if VLM_AVAILABLE else '模拟'}", "llm")

        # 启动执行线程
        def execute_thread():
            try:
                self.llm_execution_loop()
            except Exception as e:
                self.root.after(0, self.log_message, f"❌ LLM执行异常: {str(e)}", "llm", "ERROR")
                self.root.after(0, self.log_message, f"   堆栈: {traceback.format_exc()[:300]}", "llm")
                self.root.after(0, self.stop_llm_execution)

        self.llm_thread = threading.Thread(target=execute_thread, daemon=True)
        self.llm_thread.start()

    def get_active_device_address(self) -> Optional[str]:
        """获取当前活动的设备地址"""
        # 优先使用最近成功连接的设备
        if hasattr(self, 'last_successful_device') and self.last_successful_device:
            return self.last_successful_device

        # 从配置读取
        return self.load_device_address()

    def update_current_task_display(self):
        """更新当前任务显示"""
        if self.current_task_index < len(self.task_queue):
            current_task = self.task_queue[self.current_task_index]
            # 获取任务名称，支持两种格式
            if 'template_copy' in current_task and 'name' in current_task['template_copy']:
                task_name = current_task['template_copy']['name']
            elif 'name' in current_task:
                task_name = current_task['name']
            else:
                task_name = '未知任务'

            self.current_task_label.config(
                text=f"当前: {task_name} ({self.current_task_index+1}/{len(self.task_queue)})"
            )
        else:
            self.current_task_label.config(text="当前: 已完成")

    def llm_execution_loop(self):
        """LLM执行主循环（支持任务队列）"""
        # 获取持续循环状态
        is_continuous_loop = getattr(self, 'continuous_loop_var', tk.BooleanVar()).get()

        # 执行次数计数器
        execution_round = 0
        max_executions = self.execution_count if not is_continuous_loop else float('inf')

        while (self.current_task_index < len(self.task_queue) or is_continuous_loop) and not self.llm_stop_flag:
            # 检查是否达到最大执行次数（非持续循环模式）
            if not is_continuous_loop and execution_round >= max_executions:
                self.log_message(f"✅ 已完成 {max_executions} 轮执行", "llm")
                break

            # 每轮开始时重置任务索引（除第一轮外）
            if execution_round > 0:
                self.current_task_index = 1  # 跳过设备连接任务
                self.log_message(f"🔄 开始第 {execution_round + 1} 轮执行", "llm")

            # 执行一轮任务队列
            while self.current_task_index < len(self.task_queue) and not self.llm_stop_flag:
                task_item = self.task_queue[self.current_task_index]

                # 确保任务启用
                if not task_item.get("enabled", True):
                    self.log_message(f"⏭️ 跳过已禁用的任务: [{self.current_task_index+1}/{len(self.task_queue)}]")
                    self.current_task_index += 1
                    continue

                # 应用变量覆盖到深拷贝的模板
                task_template = self.apply_variables_to_template(task_item)

                # 更新当前任务显示
                self.root.after(0, self.update_current_task_display)
                self.root.after(0, self.refresh_task_queue_display)

                # 获取任务名称，支持两种格式
                if 'template_copy' in task_item and 'name' in task_item['template_copy']:
                    task_name = task_item['template_copy']['name']
                elif 'name' in task_item:
                    task_name = task_item['name']
                else:
                    task_name = '未知任务'

                self.log_message(f"📋 开始执行任务 [{self.current_task_index+1}/{len(self.task_queue)}]: {task_name}", "llm")

                # 显示变量覆盖信息
                overrides = task_item.get("variables_override", {})
                if overrides:
                    self.log_message(f"   🔧 应用变量覆盖: {overrides}", "llm", "INFO")

                # 初始化当前任务的子任务
                self.current_subtasks = [
                    {
                        "id": f"st_{i+1}_{int(time.time())}",
                        "desc": step.split('.', 1)[-1].strip() if '.' in step else step.strip(),
                        "status": "pending",
                        "subtasks": []
                    }
                    for i, step in enumerate(task_template.get('task_steps', []))
                ]
                self.root.after(0, self.refresh_subtask_ui)

                # 执行单个任务
                task_completed = self.execute_single_task(task_template)

                if task_completed:
                    self.log_message(f"✅ 任务完成: {task_name}", "llm")
                    self.current_task_index += 1

                    # 任务间暂停
                    if self.current_task_index < len(self.task_queue) and not self.llm_stop_flag:
                        self.log_message("⏸️ 准备下一个任务...", "llm")
                        # time.sleep(2.0)  # 移除延迟，提高执行效率
                else:
                    self.log_message(f"❌ 任务失败或中断: {task_name}", "llm", "ERROR")
                    break

            # 完成一轮执行
            execution_round += 1

        # 执行完成处理
        self.root.after(0, self.on_llm_complete)

    def execute_single_task(self, task_template: Dict) -> bool:
        """执行单个任务"""
        max_iterations = 30  # 最大迭代次数（防无限循环）
        iteration = 0

        # 如果是设备连接任务，先尝试连接设备
        if task_template.get('template_id') == '__device_setup__':
            self.root.after(0, self.log_message, "📱 正在连接设备...", "llm")

            # 优先使用最新一次连接成功的设备
            device_address = None

            # 首先尝试使用last_successful_device属性
            if hasattr(self, 'last_successful_device') and self.last_successful_device:
                device_address = self.last_successful_device
                self.root.after(0, self.log_message, f"🎯 使用上次成功设备: {device_address}", "llm")
            else:
                # 回退到从任务设置中获取设备地址
                device_address = self.load_device_address()
                if device_address:
                    self.root.after(0, self.log_message, f"⚙️ 从配置加载设备: {device_address}", "llm")

            if device_address:
                success = self.connect_device_by_address(device_address)
                if not success:
                    self.root.after(0, self.log_message, "❌ 设备连接失败", "llm", "ERROR")
                    return False
                self.root.after(0, self.log_message, "✅ 设备连接成功", "llm")
            else:
                self.root.after(0, self.log_message, "⚠️ 未找到设备地址配置", "llm", "ERROR")
                return False

            # 设备连接任务标记为完成
            return True

        while iteration < max_iterations and not self.llm_stop_flag:
            iteration += 1

            # 1. 获取设备视觉（截图+timestamp）
            timestamp, screenshot_path = self.capture_device_vision()
            if not timestamp or not screenshot_path:
                self.root.after(0, self.log_message, "⚠️ 截图失败，终止执行", "llm", "ERROR")
                return False

            # 2. 构建content_window
            content_window = self.build_content_window(task_template, timestamp, screenshot_path)

            # 3. 显示content_window到UI
            self.root.after(0, self.display_content_window, content_window)

            # 4. 调用VLM获取工具调用
            tool_calls = self.call_vlm(content_window)

            if not tool_calls:
                self.root.after(0, self.log_message, "⚠️ 无有效工具调用，等待0.5秒后重试", "llm", "WARNING")
                time.sleep(0.5)  # 减少重试延迟，提高响应速度
                continue

            # 5. 顺序执行工具调用
            for tool_call in tool_calls:
                if self.llm_stop_flag:
                    break

                # 执行工具
                success = self.execute_tool_call(tool_call)

                # 工具执行后等待（模拟人类操作间隔）
                if success and tool_call['action'] in ['safe_press', 'safe_swipe']:
                    time.sleep(0.8)  # 800ms自然间隔

                # 检查子任务完成状态
                if all(st['status'] == 'completed' for st in self.current_subtasks):
                    self.root.after(0, self.log_message, "✅ 所有子任务已完成", "llm")
                    return True

            # 迭代间隔
            if not self.llm_stop_flag:
                time.sleep(0.3)

        # 如果达到最大迭代次数
        if iteration >= max_iterations:
            self.root.after(0, self.log_message, f"⚠️ 达到最大迭代次数({max_iterations})，任务终止", "llm", "WARNING")

        return False  # 任务未完成

    def on_llm_complete(self):
        """LLM执行完成"""
        self.llm_running = False
        self.llm_start_btn.config(state='normal')
        self.llm_stop_btn.config(state='disabled')

        if self.current_task_index >= len(self.task_queue):
            self.app_status.config(text="✅ 所有任务完成", style='Status.Complete.TLabel')
            self.log_message("✅ 所有任务执行完成", "llm")
        else:
            self.app_status.config(text="⏹️ LLM已停止", style='Status.Ready.TLabel')
            self.log_message("⏹️ LLM执行已停止", "llm")

        # 刷新队列显示
        self.refresh_task_queue_display()
        self.current_task_label.config(text="当前: 无")

        # 🔧 任务完成后异步断开ADB连接（不阻塞任何操作）
        self._disconnect_adb_async()

    # ... [后面的代码保持不变，只需确保其他方法兼容] ...

    # 注意：需要更新以下方法的调用以适配任务队列
    # 1. stop_llm_execution 方法中需要重置 current_task_index
    def stop_llm_execution(self):
        """停止LLM执行"""
        def _update():
            self.llm_stop_flag = True
            self.llm_running = False  # 🔧 重置运行状态
            self.log_message("■ 停止请求已发送", "llm")
            if self.llm_thread and self.llm_thread.is_alive():
                self.llm_thread.join(timeout=3.0)
            self.llm_start_btn.config(state='normal')
            self.llm_stop_btn.config(state='disabled')
            self.app_status.config(text="⏹️ LLM已停止", style='Status.Ready.TLabel')

            # 重置当前任务索引
            self.current_task_index = 0
            self.refresh_task_queue_display()
            self.current_task_label.config(text="当前: 无")

        self.root.after(0, _update)

    def apply_variables_to_template(self, task_item: Dict) -> Dict:
        """将变量覆盖应用到深拷贝的模板上"""
        import copy

        # 获取深拷贝的模板
        template_copy = task_item.get("template_copy", {})
        if not template_copy:
            return task_item

        # 再次深拷贝以确保执行时的隔离
        final_template = copy.deepcopy(template_copy)

        # 获取变量覆盖
        variables_override = task_item.get("variables_override", {})

        # 应用变量覆盖到模板的各个字段
        if variables_override:
            # 1. 更新模板中的变量定义
            template_variables = final_template.get("variables", [])
            for var_def in template_variables:
                var_name = var_def.get("name")
                if var_name in variables_override:
                    var_def["default"] = variables_override[var_name]

            # 2. 更新描述字段中的变量占位符
            description = final_template.get("description", "")
            for var_name, var_value in variables_override.items():
                description = description.replace(f"{{{var_name}}}", str(var_value))
            final_template["description"] = description

            # 3. 更新任务步骤中的变量占位符
            task_steps = final_template.get("task_steps", [])
            updated_steps = []
            for step in task_steps:
                updated_step = step
                for var_name, var_value in variables_override.items():
                    updated_step = updated_step.replace(f"{{{var_name}}}", str(var_value))
                updated_steps.append(updated_step)
            final_template["task_steps"] = updated_steps

            # 4. 更新成功指标中的变量占位符
            success_indicators = final_template.get("success_indicators", [])
            updated_indicators = []
            for indicator in success_indicators:
                updated_indicator = indicator
                for var_name, var_value in variables_override.items():
                    updated_indicator = updated_indicator.replace(f"{{{var_name}}}", str(var_value))
                updated_indicators.append(updated_indicator)
            final_template["success_indicators"] = updated_indicators

        self.log_message(f"🔧 应用 {len(variables_override)} 个变量覆盖到模板", "llm", "DEBUG")
        return final_template

    # 2. 在 build_content_window 方法中，确保使用正确的任务模板
    def build_content_window(self, task_template: Dict, timestamp: str, screenshot_path: str) -> Dict:
        """构建LLM content_window（六大模块）"""
        # 过滤子任务：仅保留最近5个活跃任务 + 2个最近完成
        active_subtasks = [
            st for st in self.current_subtasks
            if st['status'] in ['pending', 'in_progress']
        ][:5]
        completed_subtasks = [
            st for st in self.current_subtasks
            if st['status'] == 'completed'
        ][-2:]
        all_subtasks = active_subtasks + completed_subtasks

        # 构建function历史（最近5次操作）
        recent_actions = self.get_recent_actions()[-5:]

        return {
            "device_vision": {
                "timestamp": timestamp,
                "screenshot_path": screenshot_path,
                "resolution": "1080x1920"
            },
            "global_goal": task_template.get('description', '无描述'),
            "task_list": task_template.get('task_steps', []),
            "splited_task": [
                {
                    "id": st['id'],
                    "desc": st['desc'],
                    "status": st['status'],
                    "subtasks": st['subtasks']
                } for st in all_subtasks
            ],
            "markdown": self.knowledge_base[-10:],  # 最近10条知识
            "function": recent_actions
        }
    
    def capture_device_vision(self) -> tuple:
        """捕获设备视觉（截图+timestamp）"""
        try:
            if not self.controller_id:
                self.log_message("⚠️ 设备未连接，无法截图", "llm", "ERROR")
                return None, None

            image_obj = screencap(self.controller_id)
            if not image_obj or not hasattr(image_obj, 'data'):
                return None, None
            
            timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
            b64_data = image_obj.data.split(',', 1)[1] if ',' in image_obj.data else image_obj.data
            image_data = base64.b64decode(b64_data)
            image = Image.open(io.BytesIO(image_data))
            
            os.makedirs("screenshots", exist_ok=True)
            filename = f"llm_{timestamp.replace(':', '-').replace('.', '_')}.jpg"
            path = os.path.join("screenshots", filename)
            image.save(path, "JPEG", quality=85)
            
            # 显示在UI
            self.root.after(0, self.display_vision_image, image, path)
            
            return timestamp, path
        except Exception as e:
            self.log_message(f"⚠️ 截图失败: {str(e)}", "llm", "ERROR")
            return None, None
    
    def display_vision_image(self, image: Image.Image, path: str):
        """在LLM页面显示视觉图像"""
        def _update():
            try:
                canvas_width = self.vision_canvas.winfo_width() or 640
                canvas_height = self.vision_canvas.winfo_height() or 480
                img_width, img_height = image.size
                scale = min(canvas_width / img_width, canvas_height / img_height, 1.0)
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)

                display_img = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(display_img)
                self.vision_canvas.delete("all")
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                self.vision_canvas.create_image(x, y, anchor=tk.NW, image=photo)
                self.vision_canvas.image = photo
            except (tk.TclError, ValueError, IOError):
                # 图像加载失败时忽略错误，保持画布空白
                pass

        self.root.after(0, _update)
    
    def get_recent_actions(self) -> List[Dict]:
        """获取最近操作历史（模拟，实际应持久化）"""
        # 简化实现：返回空列表（实际应用应记录历史操作）
        return []
    
    def display_content_window(self, content_window: Dict):
        """显示content_window到UI"""
        def _update():
            try:
                # 完整上下文
                self.full_content_text.delete(1.0, tk.END)
                self.full_content_text.insert(1.0, json.dumps(content_window, ensure_ascii=False, indent=2))
            except Exception as e:
                self.log_message(f"⚠️ 显示content_window失败: {str(e)}", "llm")

        self.root.after(0, _update)
    
    def execute_tool_call(self, tool_call: Dict) -> bool:
        """
        执行LLM工具调用 - 设备交互/任务管理的统一入口
        支持8种工具：safe_press, safe_swipe, wait, input_text, press_key,
        create_subtask, update_subtask_status, add_knowledge_entry
        """
        try:
            action = tool_call['action']
            params = tool_call['params']
            purpose = tool_call.get('purpose', '未指定目的')
            
            # ===== 设备操作工具 =====
            if action == 'safe_press':
                # 关键修复：检查坐标类型并正确转换
                x_param = params.get('x')
                y_param = params.get('y')
                duration = params.get('duration_ms', self.press_duration_ms)

                if x_param is None or y_param is None:
                    self.log_message(f"❌ safe_press参数缺失: x={x_param}, y={y_param}", "llm", "ERROR")
                    return False

                # 判断坐标类型：比例坐标(0.0-1.0)还是像素坐标
                actual_x, actual_y = self._convert_coordinates(x_param, y_param)

                self.log_message(f"📐 坐标转换: ({x_param}, {y_param}) → ({actual_x}, {actual_y})", "llm")

                return self.safe_press(actual_x, actual_y, duration, purpose)
            
            elif action == 'safe_swipe':
                sx = params.get('start_x')
                sy = params.get('start_y')
                ex = params.get('end_x')
                ey = params.get('end_y')
                duration = params.get('duration_ms', 300)
                
                if None in [sx, sy, ex, ey]:
                    self.log_message(f"❌ safe_swipe参数缺失: {params}", "llm", "ERROR")
                    return False
                
                return self.safe_swipe(sx, sy, ex, ey, duration, purpose)
            
            elif action == 'wait':
                duration = params.get('duration_ms', 1000)
                self.log_message(f"⏳ 等待 {duration}ms | {purpose}", "llm")
                time.sleep(duration / 1000.0)
                return True
            
            elif action == 'input_text':
                text = params.get('text', '')
                self.log_message(f"⌨️ 输入文本: '{text}' | {purpose}", "llm")
                if self.controller_id:
                    return input_text(self.controller_id, text)
                return False
            
            elif action == 'press_key':
                key = params.get('key', 'BACK').upper()
                key_map = {"BACK": KeyCode.BACK, "HOME": KeyCode.HOME}
                key_code = key_map.get(key, KeyCode.BACK)
                self.log_message(f"⌨️ 按键: {key} | {purpose}", "llm")
                if self.controller_id:
                    return click_key(self.controller_id, key_code)
                return False
            
            # ===== 任务管理工具 =====
            elif action == 'create_subtask':
                desc = params.get('desc', '未命名子任务')
                parent_id = params.get('parent_id')
                
                # 创建新子任务
                new_subtask = {
                    "id": f"st_{len(self.current_subtasks)+1}_{int(time.time())}",
                    "desc": desc,
                    "status": "pending",
                    "subtasks": []
                }
                
                if parent_id:
                    # 查找父任务并添加嵌套子任务
                    for st in self.current_subtasks:
                        if st['id'] == parent_id:
                            st['subtasks'].append(new_subtask)
                            self.log_message(f"✅ 创建嵌套子任务: {desc} (父任务: {parent_id})", "llm")
                            self.root.after(0, self.refresh_subtask_ui)
                            return True
                    self.log_message(f"⚠️ 未找到父任务ID: {parent_id}", "llm", "WARNING")
                
                # 顶级子任务
                self.current_subtasks.append(new_subtask)
                self.log_message(f"✅ 创建子任务: {desc}", "llm")
                self.root.after(0, self.refresh_subtask_ui)
                return True
            
            elif action == 'update_subtask_status':
                task_id = params.get('task_id')
                status = params.get('status', 'pending')
                notes = params.get('notes', '')
                
                if not task_id:
                    self.log_message(f"❌ update_subtask_status缺少task_id", "llm", "ERROR")
                    return False
                
                # 查找并更新子任务
                for st in self.current_subtasks:
                    if st['id'] == task_id:
                        old_status = st['status']
                        st['status'] = status
                        self.log_message(f"✅ 更新子任务状态: '{st['desc']}' {old_status} → {status} | {notes}", "llm")
                        self.root.after(0, self.refresh_subtask_ui)
                        return True
                    # 检查嵌套子任务
                    for sub in st['subtasks']:
                        if sub['id'] == task_id:
                            old_status = sub['status']
                            sub['status'] = status
                            self.log_message(f"✅ 更新嵌套子任务状态: '{sub['desc']}' {old_status} → {status} | {notes}", "llm")
                            self.root.after(0, self.refresh_subtask_ui)
                            return True
                
                self.log_message(f"⚠️ 未找到子任务ID: {task_id}", "llm", "WARNING")
                return False
            
            # ===== 知识库工具 =====
            elif action == 'add_knowledge_entry':
                # 验证必要参数
                required = ['type', 'content', 'x_ratio', 'y_ratio', 'width_ratio', 'height_ratio']
                if not all(k in params for k in required):
                    self.log_message(f"❌ add_knowledge_entry缺少必要参数", "llm", "ERROR")
                    return False
                
                # 创建知识库条目
                entry = {
                    "id": f"kb_{int(time.time()*1000)}",
                    "type": params['type'],
                    "content": params['content'],
                    "coordinates": {
                        "x_ratio": params['x_ratio'],
                        "y_ratio": params['y_ratio'],
                        "width_ratio": params['width_ratio'],
                        "height_ratio": params['height_ratio']
                    },
                    "image_path": params.get('image_path'),  # 可选：VLM可要求截图
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "purpose": params.get('purpose', '自动添加')
                }
                
                # 保存截图（如果VLM提供了图像数据）
                if 'image_data' in params:
                    try:
                        img_data = base64.b64decode(params['image_data'])
                        img = Image.open(io.BytesIO(img_data))
                        os.makedirs("knowledge", exist_ok=True)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                        path = os.path.join("knowledge", f"auto_{timestamp}.jpg")
                        img.save(path, "JPEG", quality=90)
                        entry['image_path'] = path
                    except Exception as e:
                        self.log_message(f"⚠️ 知识库截图保存失败: {str(e)}", "llm", "WARNING")
                
                # 添加到知识库
                self.knowledge_base.append(entry)
                self.save_knowledge_base()
                self.root.after(0, self.refresh_knowledge_base_ui)
                self.log_message(f"✅ 添加知识库词条: [{entry['type']}] {entry['content'][:30]}...", "llm")
                return True
            
            else:
                self.log_message(f"⚠️ 未知工具调用: {action}", "llm", "WARNING")
                return False
                
        except Exception as e:
            self.log_message(f"❌ 工具执行异常 ({tool_call.get('action', 'unknown')}): {str(e)}", "llm", "ERROR")
            return False

    def test_llm_execution(self):
        """测试LLM执行（设计器页）"""
        if not self.controller_id:
            messagebox.showwarning("警告", "请先连接测试设备")
            return
        self.log_message("▶ 启动LLM执行测试（VLM集成模拟）", "designer")
        self.content_preview.delete(1.0, tk.END)
        self.content_preview.insert(1.0, "【VLM执行模拟开始】\n")
        steps = [
            "1. 捕获设备视觉 (timestamp: 2024-06-01T12:30:45.123Z)",
            "2. 构建content_window (六大模块)",
            "3. 调用VLM服务器分析界面",
            "4. VLM返回工具调用: safe_press(x=950, y=1800)",
            "5. 执行安全按压 (滑动模拟: 952,1801 → 950,1800, 100ms)",
            "6. 更新子任务状态 → '进入战术终端' 标记为完成",
            "7. 迭代继续..."
        ]
        for step in steps:
            self.content_preview.insert(tk.END, step + "\n")
            self.content_preview.see(tk.END)
            self.log_message(step, "designer")
            time.sleep(0.4)
            self.root.update()
        self.content_preview.insert(tk.END, "\n【VLM执行模拟结束】✓")
        self.log_message("✅ LLM测试执行完成", "designer")
    
    # ==================== 知识库管理 ====================
    def load_current_task_group(self) -> Dict:
        """加载当前任务组"""
        try:
            path = "tasks/current_task_group.json"
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 确保必要字段存在
                if "tasks" not in data:
                    data["tasks"] = []
                if "global_settings" not in data:
                    data["global_settings"] = {
                        "operation_delay": 0.8,
                        "vlm_think_timeout": 30,
                        "max_retries": 3,
                        "screenshot_interval": 2.0
                    }
                return data
        except Exception as e:
            self.log_message(f"⚠️ 任务组加载失败: {str(e)}", "llm")
            # 返回默认任务组
            return {
                "name": "终末地日常",
                "tasks": [],
                "global_settings": {
                    "operation_delay": 0.8,
                    "vlm_think_timeout": 30,
                    "max_retries": 3,
                    "screenshot_interval": 2.0
                },
                "created_at": datetime.now().isoformat()
            }
    
    def load_knowledge_base(self) -> List[Dict]:
        try:
            path = "knowledge/knowledge_base.json"
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except (OSError, json.JSONDecodeError):
            # 文件不存在、权限问题或JSON格式错误时返回空列表
            return []
    
    def save_knowledge_base(self):
        try:
            os.makedirs("knowledge", exist_ok=True)
            with open("knowledge/knowledge_base.json", 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_base, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_message(f"⚠️ 知识库保存失败: {str(e)}", "designer")
    
    def add_knowledge_entry(self):
        # [修复] 在打开窗口前清除上一张截图的缓存路径
        if hasattr(self, 'kb_image_path'):
            del self.kb_image_path

        dialog = tk.Toplevel(self.root)
        dialog.title("添加知识库词条")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="类型:").pack(anchor=tk.W, padx=10, pady=(10,0))
        type_var = tk.StringVar(value="button")
        ttk.Combobox(dialog, textvariable=type_var, values=["button", "enemy", "ally", "resource", "ui_element"], 
                    state='readonly', width=20).pack(fill='x', padx=10)
        
        ttk.Label(dialog, text="描述:").pack(anchor=tk.W, padx=10, pady=(10,0))
        desc_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=desc_var).pack(fill='x', padx=10)
        
        ttk.Label(dialog, text="坐标比例 (0.0-1.0):").pack(anchor=tk.W, padx=10, pady=(10,0))
        coord_frame = ttk.Frame(dialog)
        coord_frame.pack(fill='x', padx=10)
        ttk.Label(coord_frame, text="X:").pack(side=tk.LEFT)
        x_var = tk.DoubleVar(value=0.5)
        ttk.Spinbox(coord_frame, from_=0.0, to=1.0, increment=0.01, textvariable=x_var, width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(coord_frame, text="Y:").pack(side=tk.LEFT, padx=(10,0))
        y_var = tk.DoubleVar(value=0.5)
        ttk.Spinbox(coord_frame, from_=0.0, to=1.0, increment=0.01, textvariable=y_var, width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(coord_frame, text="宽:").pack(side=tk.LEFT, padx=(10,0))
        w_var = tk.DoubleVar(value=0.1)
        ttk.Spinbox(coord_frame, from_=0.01, to=1.0, increment=0.01, textvariable=w_var, width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(coord_frame, text="高:").pack(side=tk.LEFT, padx=(10,0))
        h_var = tk.DoubleVar(value=0.06)
        ttk.Spinbox(coord_frame, from_=0.01, to=1.0, increment=0.01, textvariable=h_var, width=6).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(dialog, text="截图:").pack(anchor=tk.W, padx=10, pady=(10,0))
        img_frame = ttk.Frame(dialog)
        img_frame.pack(fill='x', padx=10)
        self.kb_preview_label = ttk.Label(img_frame, text="无截图", width=30, anchor=tk.W)
        self.kb_preview_label.pack(side=tk.LEFT)
        ttk.Button(img_frame, text="📸 捕获当前屏幕", 
                  command=lambda: self.capture_kb_screenshot(dialog, x_var, y_var, w_var, h_var)).pack(side=tk.LEFT, padx=5)
        
        def save_entry():
            entry = {
                "id": f"kb_{int(time.time()*1000)}",
                "type": type_var.get(),
                "content": desc_var.get().strip(),
                "coordinates": {
                    "x_ratio": x_var.get(),
                    "y_ratio": y_var.get(),
                    "width_ratio": w_var.get(),
                    "height_ratio": h_var.get()
                },
                "image_path": getattr(self, 'kb_image_path', None),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.knowledge_base.append(entry)
            self.save_knowledge_base()
            self.refresh_knowledge_base_ui()
            dialog.destroy()
            self.log_message(f"✅ 添加知识库词条: {entry['content']}", "designer")
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', pady=10, padx=10)
        ttk.Button(btn_frame, text="✅ 保存", command=save_entry, style='Security.TButton').pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="❌ 取消", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def capture_kb_screenshot(self, dialog, x_var, y_var, w_var, h_var):
        if not self.current_image:
            messagebox.showwarning("警告", "请先获取设备截图")
            return
        
        img_width, img_height = self.current_image.size
        x = int(x_var.get() * img_width)
        y = int(y_var.get() * img_height)
        w = int(w_var.get() * img_width)
        h = int(h_var.get() * img_height)
        
        left = max(0, x - w//2)
        top = max(0, y - h//2)
        right = min(img_width, x + w//2)
        bottom = min(img_height, y + h//2)
        
        cropped = self.current_image.crop((left, top, right, bottom))
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        os.makedirs("knowledge", exist_ok=True)
        path = os.path.join("knowledge", f"kb_{timestamp}.jpg")
        cropped.save(path, "JPEG", quality=90)
        
        display = cropped.resize((80, int(80*h/w)) if w > 0 else (80, 80), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(display)
        self.kb_preview_label.config(image=photo, text="")
        self.kb_preview_label.image = photo
        self.kb_image_path = path
        
        self.log_message(f"📸 已捕获知识库截图: {path}", "designer")
    
    def refresh_knowledge_base_ui(self):
        self.kb_tree.delete(*self.kb_tree.get_children())
        for entry in self.knowledge_base[-20:]:
            content = entry.get('content', '')[:40] + "..." if len(entry.get('content', '')) > 40 else entry.get('content', '')
            self.kb_tree.insert("", "end", values=(
                entry.get('type', 'unknown'),
                content,
                entry.get('timestamp', '')[:19].replace('T', ' ')
            ))
    
    def clear_knowledge_base(self):
        if messagebox.askyesno("确认", "确定清空整个知识库？此操作不可恢复！"):
            self.knowledge_base = []
            self.save_knowledge_base()
            self.refresh_knowledge_base_ui()
            self.log_message("✅ 知识库已清空", "designer")
    
    def _check_and_deploy_vlm_model(self):
        """
        启动时检测是否首次使用，根据arkpass文件判断是否需要提示模型选择
        """
        # 🔧 检查是否已有arkpass文件（判断是否为首次使用）
        import glob
        arkpass_files = glob.glob("*.arkpass")
        if arkpass_files:
            # 已存在arkpass文件，说明不是首次使用，直接检查模型
            self._check_model_exists()
            return

        # 首次使用，延迟显示模式选择对话框（确保主窗口完全加载）
        self.root.after(500, self._show_first_run_dialog)

        # 定义模型部署所需的变量（修复作用域问题）
        repo_url = "https://www.modelscope.cn/xray4668/Qwen3vl8b_finetune_q6k.git"
        target_path = os.path.normpath("model/vision_llm/Qwen3-VL-8B-abliterated-v2.0")

        def deploy_task():
            git_executable = os.path.normpath("3rd-part/Git/bin/git.exe")
            temp_dir = os.path.normpath("model/vision_llm/qwen_clone_temp")
            try:
                self.log_message("🚨 正在启动本地模型部署流程...", "llm", "WARNING")

                # 校验 Git 路径
                if not os.path.exists(git_executable):
                    self.log_message(f"❌ 错误: 未找到 Git 执行文件 {git_executable}", "llm", "ERROR")
                    return

                # 清理并准备临时目录
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                os.makedirs(os.path.dirname(temp_dir), exist_ok=True)

                # 3. 执行 Git 克隆
                self.log_message(f"📥 正在克隆模型仓库，请耐心等待...", "llm")
                result = subprocess.run(
                    [git_executable, "clone", repo_url, temp_dir],
                    capture_output=True, text=True, encoding='utf-8'
                )

                if result.returncode != 0:
                    raise RuntimeError(f"Git 克隆异常: {result.stderr}")

                # 4. 转移文件内容
                self.log_message("🚚 正在整理并转移模型文件...", "llm")
                os.makedirs(target_path, exist_ok=True)
                for item in os.listdir(temp_dir):
                    src = os.path.join(temp_dir, item)
                    dst = os.path.join(target_path, item)
                    # 覆盖式移动
                    if os.path.exists(dst):
                        if os.path.isdir(dst):
                            shutil.rmtree(dst)
                        else:
                            os.remove(dst)
                    shutil.move(src, dst)

                # 5. 清理残留
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)

                self.log_message("✨ 本地模型部署成功！", "llm")
                self.root.after(0, lambda: messagebox.showinfo("部署完成", "模型已成功克隆至本地目录。"))
                self.root.after(10000, lambda: messagebox.showinfo("提示", "模型部署完成，请重启程序以确保所有功能正常。"))

            except Exception as e:
                error_msg = str(e)
                self.log_message(f"❌ 部署失败: {error_msg}", "llm", "ERROR")
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("部署失败", f"模型部署过程中出现错误:\n{msg}"))

        threading.Thread(target=deploy_task, daemon=True).start()

    def _show_first_run_dialog(self):
        """显示首次运行对话框，让用户选择使用模式"""
        # 确保主窗口已完全显示且可操作
        if not self.root.winfo_exists():
            return

        # 创建自定义对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("欢迎使用ArkStudio")
        dialog.geometry("550x220")  # 增加高度以确保按钮可见
        dialog.resizable(False, False)

        # 设置为模态对话框
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_set()

        # 确保对话框显示在最前面
        dialog.lift()
        dialog.attributes('-topmost', True)
        dialog.after(100, lambda: dialog.attributes('-topmost', False))

        # 居中显示
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

        # 主容器
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill='both', expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="你希望使用本地模型推理模式吗？", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(10, 10))

        # 说明文字
        desc_label = ttk.Label(main_frame, text="如使用，请点击下载模型\n如希望使用我们提供的运算服务，点击跳过", justify=tk.CENTER)
        desc_label.pack(pady=(5, 20))

        # 按钮框架 - 使用更大的填充
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10, fill='x')

        # 下载模型按钮 - 不使用样式避免样式问题
        download_btn = ttk.Button(btn_frame, text="下载模型",
                                  command=lambda: self._start_download_and_close(dialog))
        download_btn.pack(side=tk.LEFT, padx=20, pady=5)

        # 跳过按钮
        skip_btn = ttk.Button(btn_frame, text="跳过",
                              command=lambda: self._skip_model_download_and_close(dialog))
        skip_btn.pack(side=tk.LEFT, padx=20, pady=5)

        # 禁止关闭对话框（必须选择一个选项）
        dialog.protocol("WM_DELETE_WINDOW", lambda: None)

        # 强制刷新布局
        dialog.update_idletasks()
        dialog.update()

    def _start_download_and_close(self, dialog):
        """开始下载模型并关闭对话框"""
        dialog.destroy()
        self._deploy_vlm_model()

    def _skip_model_download_and_close(self, dialog):
        """跳过模型下载并关闭对话框"""
        self.log_message("⚠️ 用户选择跳过本地模型，将使用云服务", "llm", "INFO")
        dialog.destroy()

    def _check_model_exists(self):
        """检查模型是否存在，如果已登录云服务则自动启用云服务"""
        target_path = os.path.normpath("model/vision_llm/Qwen3-VL-8B-abliterated-v2.0")
        if os.path.exists(target_path) and os.listdir(target_path):
            self.log_message(f"✅ VLM 模型目录检查通过", "llm")
        else:
            self.log_message("⚠️ 本地VLM模型文件缺失，建议下载模型或使用云服务", "llm", "WARNING")

        # 🔧 检查是否已登录云服务，如果已登录则自动启用云服务
        if hasattr(self, 'cloud_client') and self.cloud_client and not self.use_cloud_var.get():
            self.use_cloud_var.set(True)
            self.toggle_cloud_vlm()
            self.log_message("🌐 检测到云服务已登录，已自动启用云VLM服务", "llm", "INFO")

    def _deploy_vlm_model(self):
        """部署VLM模型"""
        target_path = os.path.normpath("model/vision_llm/Qwen3-VL-8B-abliterated-v2.0")
        git_executable = os.path.normpath("3rd-part/Git/bin/git.exe")
        repo_url = "https://www.modelscope.cn/xray4668/Qwen3vl8b_finetune_q6k.git"

        def deploy_task():
            temp_dir = os.path.normpath("model/vision_llm/qwen_clone_temp")
            try:
                self.log_message("🚨 正在启动本地模型部署流程...", "llm", "WARNING")

                # 校验 Git 路径
                if not os.path.exists(git_executable):
                    self.log_message(f"❌ 错误: 未找到 Git 执行文件 {git_executable}", "llm", "ERROR")
                    return

                # 清理并准备临时目录
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                os.makedirs(os.path.dirname(temp_dir), exist_ok=True)

                # 执行 Git 克隆
                self.log_message(f"📥 正在克隆模型仓库，请耐心等待...", "llm")
                result = subprocess.run(
                    [git_executable, "clone", repo_url, temp_dir],
                    capture_output=True, text=True, encoding='utf-8'
                )

                if result.returncode != 0:
                    raise RuntimeError(f"Git 克隆异常: {result.stderr}")

                # 转移文件内容
                self.log_message("🚚 正在整理并转移模型文件...", "llm")
                os.makedirs(target_path, exist_ok=True)
                for item in os.listdir(temp_dir):
                    src = os.path.join(temp_dir, item)
                    dst = os.path.join(target_path, item)
                    # 覆盖式移动
                    if os.path.exists(dst):
                        if os.path.isdir(dst):
                            shutil.rmtree(dst)
                        else:
                            os.remove(dst)
                    shutil.move(src, dst)

                # 清理残留
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)

                self.log_message("✨ 本地模型部署成功！", "llm")
                self.root.after(0, lambda: messagebox.showinfo("部署完成", "模型已成功克隆至本地目录。"))
                self.root.after(10000, lambda: messagebox.showinfo("提示", "模型部署完成，请重启程序以确保所有功能正常。"))

            except Exception as e:
                error_msg = str(e)
                self.log_message(f"❌ 部署失败: {error_msg}", "llm", "ERROR")
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("部署失败", f"模型部署过程中出现错误:\n{msg}"))

        threading.Thread(target=deploy_task, daemon=True).start()

    # ==================== 辅助方法 ====================
    def clear_log(self, page: str = "test"):
        target = {
            "test": getattr(self, 'test_log_text', None),
            "designer": getattr(self, 'designer_log_text', None),
            "llm": getattr(self, 'llm_log_text', None)
        }.get(page)
        if target:
            target.delete(1.0, tk.END)
    
    def save_log(self, page: str = "test"):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            logs_dir = "logs"
            os.makedirs(logs_dir, exist_ok=True)
            
            target = {
                "test": getattr(self, 'test_log_text', None),
                "designer": getattr(self, 'designer_log_text', None),
                "llm": getattr(self, 'llm_log_text', None)
            }.get(page)
            
            if not target:
                return
            
            content = target.get(1.0, tk.END)
            filename = os.path.join(logs_dir, f"{page}_log_{timestamp}.log")
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            self.log_message(f"💾 日志已保存: {filename}", page)
            messagebox.showinfo("成功", f"日志已保存至:\n{filename}")
        except Exception as e:
            messagebox.showerror("错误", f"保存日志失败:\n{str(e)}")
    
    # ==================== 云服务页面 ====================
    def setup_cloud_page(self):
        """设置云服务页面"""
        frame = ttk.Frame(self.cloud_page_frame, padding="10")
        frame.pack(fill='both', expand=True)

        # 左右分栏：连接管理 | 服务详情
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill='both', expand=True)

        # 左：连接管理面板
        left_panel = ttk.Frame(paned)
        paned.add(left_panel, weight=1)

        # 连接配置
        conn_frame = ttk.LabelFrame(left_panel, text="云服务连接", padding="10")
        conn_frame.pack(fill='x', pady=(0, 10))

        # 服务器配置（硬编码，不可修改）
        server_frame = ttk.Frame(conn_frame)
        server_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(server_frame, text="服务器: 已配置", foreground='green').pack(side=tk.LEFT)

        # 固定服务器地址配置
        self.cloud_host = "api.r54134544.nyat.app"
        self.cloud_port = 57460

        # 用户认证
        auth_frame = ttk.Frame(conn_frame)
        auth_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(auth_frame, text="用户ID:").pack(side=tk.LEFT)
        self.cloud_user_var = tk.StringVar(value="")
        ttk.Entry(auth_frame, textvariable=self.cloud_user_var, width=20).pack(side=tk.LEFT, padx=5)

        # 密钥显示
        key_frame = ttk.Frame(conn_frame)
        key_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(key_frame, text="API密钥:").pack(side=tk.LEFT)
        self.cloud_key_var = tk.StringVar(value="")
        self.cloud_key_entry = ttk.Entry(key_frame, textvariable=self.cloud_key_var, width=30, show="*")
        self.cloud_key_entry.pack(side=tk.LEFT, padx=5, fill='x', expand=True)
        self.show_key_var = tk.BooleanVar()
        ttk.Checkbutton(key_frame, text="显示", variable=self.show_key_var,
                       command=self.toggle_key_visibility).pack(side=tk.LEFT, padx=5)

        # 连接框架 - 只包含注册和登入按钮
        btn_frame = ttk.Frame(conn_frame)
        btn_frame.pack(fill='x')
        self.cloud_register_btn = self.create_btn(btn_frame, "注册", self.register_cloud_user, 'Action.TButton')
        self.cloud_login_btn = self.create_btn(btn_frame, "登入", self.login_cloud_user, 'Action.TButton')

        # 连接状态
        self.cloud_status_label = ttk.Label(btn_frame, text="未登录", foreground='gray')
        self.cloud_status_label.pack(side=tk.RIGHT, padx=10)

        # 连接状态
        status_frame = ttk.LabelFrame(left_panel, text="用户信息", padding="10")
        status_frame.pack(fill='x', pady=(0, 10))
        self.cloud_status_text = scrolledtext.ScrolledText(status_frame, height=6, wrap=tk.WORD, font=('Consolas', 9))
        self.cloud_status_text.pack(fill='both', expand=True)

        # 服务层级信息
        tier_frame = ttk.LabelFrame(left_panel, text="服务信息", padding="10")
        tier_frame.pack(fill='x')
        self.cloud_tier_label = ttk.Label(tier_frame, text="未连接", font=('Arial', 10, 'bold'))
        self.cloud_tier_label.pack(pady=5)
        self.cloud_stats_label = ttk.Label(tier_frame, text="暂无统计信息", font=('Arial', 9))
        self.cloud_stats_label.pack(pady=5)

        # 右：服务使用面板
        right_panel = ttk.Frame(paned)
        paned.add(right_panel, weight=2)

        # VLM集成配置
        vlm_frame = ttk.LabelFrame(right_panel, text="VLM云服务集成", padding="10")
        vlm_frame.pack(fill='x', pady=(0, 10))

        # 云服务开关
        cloud_enable_frame = ttk.Frame(vlm_frame)
        cloud_enable_frame.pack(fill='x', pady=(0, 10))
        self.use_cloud_var = tk.BooleanVar()
        ttk.Checkbutton(cloud_enable_frame, text="启用VLM云服务",
                       variable=self.use_cloud_var, command=self.toggle_cloud_vlm).pack(side=tk.LEFT)
        self.cloud_vlm_status = ttk.Label(cloud_enable_frame, text="未启用", foreground='gray')
        self.cloud_vlm_status.pack(side=tk.LEFT, padx=10)

        test_frame = ttk.LabelFrame(right_panel, text="云服务测试", padding="10")
        test_frame.pack(fill='both', expand=True, pady=(0, 10))

        test_input_frame = ttk.Frame(test_frame)
        test_input_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(test_input_frame, text="测试消息:").pack(side=tk.LEFT)
        self.cloud_test_var = tk.StringVar(value="测试消息")
        ttk.Entry(test_input_frame, textvariable=self.cloud_test_var, width=30).pack(side=tk.LEFT, padx=5, fill='x', expand=True)

        test_btn_frame = ttk.Frame(test_frame)
        test_btn_frame.pack(fill='x', pady=(0, 10))
        self.create_btn(test_btn_frame, "发送测试", self.test_cloud_service)
        self.create_btn(test_btn_frame, "测试子任务", self.test_cloud_subtask)

        self.cloud_test_result = scrolledtext.ScrolledText(test_frame, height=10, wrap=tk.WORD, font=('Consolas', 9))
        self.cloud_test_result.pack(fill='both', expand=True)

        self.cloud_client = None

        # 初始化
        self.update_cloud_ui_state()

    def toggle_key_visibility(self):
        """切换密钥显示/隐藏"""
        if self.show_key_var.get():
            self.cloud_key_entry.config(show="")
        else:
            self.cloud_key_entry.config(show="*")

    def connect_cloud_service(self):
        """已弃用：该方法已不再使用，由login_cloud_user替代"""
        messagebox.showwarning("提示", "请使用 登入 按钮进行云服务连接")

    def on_cloud_connect_success(self):
        """云服务连接成功"""
        self.cloud_register_btn.config(state='disabled')
        self.cloud_login_btn.config(state='disabled')

        # 获取用户信息
        self.update_cloud_user_info()

        # 🔧 登入后默认启用云服务
        if not self.use_cloud_var.get():
            self.use_cloud_var.set(True)
            self.toggle_cloud_vlm()

        self.log_message("云服务连接成功", "cloud")
        messagebox.showinfo("成功", "云服务连接成功\n\n已自动启用云VLM服务")

    def on_cloud_connect_failed(self, error_msg):
        """云服务连接失败"""
        self.cloud_register_btn.config(state='normal')
        self.cloud_login_btn.config(state='normal')

        self.log_message(f"云服务连接失败: {error_msg}", "cloud", "ERROR")
        messagebox.showerror("连接失败", error_msg)

    def disconnect_cloud_service(self):
        """已弃用：该方法已不再使用"""
        messagebox.showwarning("提示", "使用ArkPass文件登录时无需手动断开")

    def login_cloud_user(self):
        """登入功能 - 选择arkpass文件并执行登录"""
        if not CLOUD_AVAILABLE:
            messagebox.showerror("错误", "云服务客户端不可用")
            return

        arkpass_file = filedialog.askopenfilename(
            title="选择ArkPass文件",
            filetypes=[("ArkPass文件", "*.arkpass"), ("所有文件", "*.*")]
        )

        if not arkpass_file:
            return

        host = self.cloud_host
        port = self.cloud_port

        try:
            port = int(port)
        except ValueError:
            messagebox.showerror("错误", "端口号必须是数字")
            return

        self.auto_login_with_arkpass(arkpass_file)

    def auto_login_with_arkpass(self, arkpass_file):
        """使用指定的arkpass文件自动登录"""
        host = self.cloud_host
        port = self.cloud_port

        filename = os.path.basename(arkpass_file)
        self.log_message(f"正在使用 {filename} 登录...", "cloud")

        def login_thread():
            try:
                client = CloudClient(host, port)
                success, layer = client.login_with_file(arkpass_file)

                if success:
                    self.root.after(0, lambda: self.on_cloud_login_success(client, layer, filename))
                else:
                    self.root.after(0, lambda: self.log_message(f"登录失败: {layer}", "cloud", "ERROR"))
                    self.root.after(0, lambda: messagebox.showerror("登录失败", layer))

            except Exception as e:
                error_message = str(e)
                self.root.after(0, lambda: self.log_message(f"登录异常: {error_message}", "cloud", "ERROR"))
                self.root.after(0, lambda: messagebox.showerror("登录失败", error_message))

        threading.Thread(target=login_thread, daemon=True).start()

    def register_cloud_user(self):
        """注册新用户"""
        if not CLOUD_AVAILABLE:
            messagebox.showerror("错误", "云服务客户端不可用")
            return

        # 弹窗获取用户名
        user_id = simpledialog.askstring("注册用户", "请输入用户名:", parent=self.root)
        if not user_id or not user_id.strip():
            return

        user_id = user_id.strip()
        host = self.cloud_host
        port = self.cloud_port

        self.log_message(f"正在注册用户 {user_id}...", "cloud")

        def register_thread():
            try:
                client = CloudClient(host, port)
                api_key = client.register(user_id)

                if api_key:
                    # 注册成功，ArkPass文件已自动保存
                    arkpass_file = f"{user_id}.arkpass"
                    self.root.after(0, lambda: self.log_message(f"注册成功，ArkPass文件已保存为 {arkpass_file}", "cloud"))
                    self.root.after(0, lambda: messagebox.showinfo("注册成功", f"用户 {user_id} 注册成功\nArkPass文件: {arkpass_file}\n系统将自动登录"))

                    # 自动登录
                    self.root.after(1000, lambda: self.auto_login_with_arkpass(arkpass_file))
                else:
                    error = "用户ID可能已存在"
                    self.root.after(0, lambda: self.log_message(f"注册失败: {error}", "cloud", "ERROR"))
                    self.root.after(0, lambda: messagebox.showerror("注册失败", error))

            except Exception as e:
                self.root.after(0, lambda: self.log_message(f"注册异常: {str(e)}", "cloud", "ERROR"))
                self.root.after(0, lambda: messagebox.showerror("注册失败", str(e)))

        threading.Thread(target=register_thread, daemon=True).start()

    def on_cloud_login_success(self, client, layer, filename):
        """云服务登录成功回调"""
        self.cloud_client = client

        # 提取用户ID
        user_id = filename.replace('.arkpass', '')

        # 更新UI状态
        self.cloud_status_label.config(text=f"已登录: {user_id}", foreground='green')
        self.log_message(f"登录成功: {layer}", "cloud")
        self.cloud_status_text.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M:%S')}] 用户: {user_id}")
        self.cloud_status_text.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M:%S')}] 状态: {layer}")
        self.cloud_status_text.see(tk.END)

        # 更新用户信息
        self.update_cloud_user_info()

        # 启用云服务相关按钮
        self.cloud_register_btn.config(state='disabled')
        self.cloud_login_btn.config(state='disabled')

        # 🔧 登录成功后检查是否需要自动启用云服务
        self._check_model_exists()

    def auto_check_and_login_cloud(self):
        """启动时自动检测并登录云服务"""
        # 查找默认位置的arkpass文件
        current_dir = os.getcwd()

        # 查找所有的.arkpass文件
        arkpass_files = [f for f in os.listdir(current_dir) if f.endswith('.arkpass')]

        if arkpass_files:
            # 如果有arkpass文件，使用第一个自动登录
            arkpass_file = os.path.join(current_dir, arkpass_files[0])
            self.log_message(f"检测到arkpass文件: {arkpass_files[0]}，正在自动登录...", "cloud")
            self.auto_login_with_arkpass(arkpass_file)

    def update_cloud_user_info(self):
        """更新云服务用户信息"""
        if not self.cloud_client:
            return

        def update_thread():
            try:
                # 获取统计信息
                stats = self.cloud_client.get_stats()
                if stats:
                    tier = stats.get('layer', 'free')
                    expiry = stats.get('expiry', 0)
                    recent_stats = stats.get('stats', [])

                    self.root.after(0, lambda: self.cloud_tier_label.config(
                        text=f"当前层级: {tier.upper()}\n到期时间: {time.ctime(expiry) if expiry > 0 else '永久'}"))

                    # 显示最近使用统计
                    if recent_stats and len(recent_stats) > 0:
                        # 确保recent_stats是可迭代的列表
                        if isinstance(recent_stats, list):
                            stats_list = recent_stats[:5]  # 取前5条记录
                            if stats_list:
                                stats_text = f"最近使用记录 (最近{len(stats_list)}次):\n"
                                for i, record in enumerate(stats_list):
                                    if isinstance(record, (list, tuple)) and len(record) >= 3:
                                        ts, tokens, duration = record[:3]
                                        stats_text += f"  {i+1}. 时间: {time.ctime(ts)}, 令牌: {tokens}, 耗时: {duration:.2f}s\n"
                                self.root.after(0, lambda: self.cloud_stats_label.config(text=stats_text))
                            else:
                                self.root.after(0, lambda: self.cloud_stats_label.config(text="暂无使用记录"))
                        else:
                            self.root.after(0, lambda: self.cloud_stats_label.config(text="统计格式错误"))
                    else:
                        self.root.after(0, lambda: self.cloud_stats_label.config(text="暂无使用记录"))
                else:
                    self.root.after(0, lambda: self.cloud_stats_label.config(text="无法获取统计信息"))

            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: self.log_message(f"获取用户信息失败: {error_msg}", "cloud", "ERROR"))

        threading.Thread(target=update_thread, daemon=True).start()

    def toggle_cloud_vlm(self):
        """切换VLM云服务"""
        if self.use_cloud_var.get():
            if not self.cloud_client:
                messagebox.showwarning("警告", "请先连接云服务")
                self.use_cloud_var.set(False)
                return

            self.cloud_vlm_status.config(text="已启用", foreground='green')
            self.log_message("VLM云服务已启用", "cloud")

            # 云服务VLM调用逻辑已在call_vlm方法中实现，支持自动回退机制
        else:
            self.cloud_vlm_status.config(text="未启用", foreground='gray')
            self.log_message("VLM云服务已禁用", "cloud")

    def refresh_cloud_models(self):
        """模型现在由服务器自动分配"""
        self.log_message("模型由服务器分配，无需手动刷新", "cloud", "INFO")

    def test_cloud_service(self):
        """测试云服务"""
        if not self.cloud_client:
            messagebox.showwarning("警告", "请先连接云服务")
            return

        test_msg = self.cloud_test_var.get().strip()
        if not test_msg:
            messagebox.showwarning("警告", "请输入测试消息")
            return

        self.cloud_test_result.delete(1.0, tk.END)
        self.cloud_test_result.insert(tk.END, "发送请求中...\n")

        def test_thread():
            try:
                # 构造测试请求 (模型将由服务器覆盖)
                payload = {
                    "messages": [{"role": "user", "content": test_msg}],
                    "temperature": 0.7
                }

                response = self.cloud_client.chat_completion(payload)

                if response:
                    result = f"请求成功!\n响应: {json.dumps(response, ensure_ascii=False, indent=2)}"
                else:
                    result = "请求失败: 无响应"

            except Exception as e:
                result = f"请求异常: {str(e)}"

            self.root.after(0, lambda: self.display_test_result(result))

        threading.Thread(target=test_thread, daemon=True).start()

    def test_cloud_subtask(self):
        """测试云服务子任务管理"""
        if not self.cloud_client:
            messagebox.showwarning("警告", "请先连接云服务")
            return

        test_payload = {
            "messages": [{"role": "user", "content": "请创建一个子任务：检查游戏状态"}],
            "temperature": 0.7
        }

        self.cloud_test_result.delete(1.0, tk.END)
        self.cloud_test_result.insert(tk.END, "测试子任务创建中...\n")

        def subtask_test_thread():
            try:
                response = self.cloud_client.chat_completion(test_payload)

                if response:
                    content = response.get('choices', [{}])[0].get('message', {}).get('content', '无内容')
                    result = f"子任务测试成功!\nAI回复: {content}"
                else:
                    result = "子任务测试失败: 无响应"

            except Exception as e:
                result = f"子任务测试异常: {str(e)}"

            self.root.after(0, lambda: self.display_test_result(result))

        threading.Thread(target=subtask_test_thread, daemon=True).start()

    def display_test_result(self, result):
        """显示测试结果"""
        self.cloud_test_result.delete(1.0, tk.END)
        self.cloud_test_result.insert(tk.END, result)
        self.cloud_test_result.see(tk.END)

    def update_cloud_ui_state(self):
        """更新云服务UI状态"""
        if self.cloud_client and hasattr(self.cloud_client, 'is_connected') and self.cloud_client.is_connected():
            self.cloud_tier_label.config(text="已连接")
        else:
            self.cloud_tier_label.config(text="未连接")
            self.cloud_stats_label.config(text="暂无统计信息")
            self.cloud_vlm_status.config(text="未启用", foreground='gray')
            self.use_cloud_var.set(False)

    def on_closing(self):
        """简化的关闭窗口逻辑 - 不处理ADB断开"""
        # 尝试停止LLM执行但不阻塞
        if self.llm_running:
            self.llm_stop_flag = True
            self.llm_running = False
            self.log_message("■ 发送停止信号，正在关闭窗口", "llm")

        # 断开云服务连接
        if hasattr(self, 'cloud_client') and self.cloud_client:
            try:
                self.cloud_client.disconnect()
            except Exception as e:
                self.log_message(f"断开云服务时出错: {str(e)}", "cloud", "WARNING")

        # 保存知识库
        self.save_knowledge_base()

        # 直接销毁窗口，不等待任何异步操作
        self.root.destroy()

        # 强制退出程序，确保所有线程和资源都被正确释放
        import sys
        import os
        if sys.platform == "win32":
            os._exit(0)
        else:
            sys.exit(0)

    def _disconnect_adb_async(self):
        """异步断开ADB连接 - 不阻塞任何步骤"""
        def disconnect_thread():
            if self.controller_id:
                try:
                    # 在后台线程中执行ADB断开，避免阻塞主线程
                    success = disconnect_device(self.controller_id)
                    if success:
                        self.root.after(0, lambda: self.log_message("设备已自动断开", "all"))
                    else:
                        self.root.after(0, lambda: self.log_message("设备断开失败", "all", "WARNING"))

                    # 重置设备状态
                    self.controller_id = None
                    self.current_device = None

                    # 更新UI状态（如果窗口还存在）
                    self.root.after(0, self._update_device_ui_disconnected)

                except Exception as e:
                    self.root.after(0, lambda: self.log_message(f"自动断开设备时出错: {str(e)}", "all", "WARNING"))

        # 启动后台线程执行ADB断开
        threading.Thread(target=disconnect_thread, daemon=True).start()

    def _update_device_ui_disconnected(self):
        """更新设备UI为断开状态"""
        try:
            # 检查窗口是否仍然存在
            if self.root.winfo_exists():
                self.device_status.config(text="无设备", style='Status.Error.TLabel')
                self.app_status.config(text="设备已断开", style='Status.Ready.TLabel')
        except (AttributeError, tk.TclError):
            # 窗口已经关闭或组件未初始化，忽略更新
            pass

    def update_resolution_display(self, width: int, height: int, page: str):
        """
        线程安全的分辨率状态更新
        """
        def _update():
            if hasattr(self, 'resolution_status'):
                self.resolution_status.config(text=f"📐 分辨率: {width}x{height}")
            self.log_message(f"📊 当前使用分辨率: {width}x{height}", page)

        self.root.after(0, _update)

def main():
    root = tk.Tk()
    try:
        app = LLMTaskAutomationGUI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("致命错误", f"应用启动失败:\n{str(e)}\n{traceback.format_exc()}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())