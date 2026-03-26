"""设备管理GUI模块 - MAA风格带动画效果"""
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import base64
import io
from ..theme import configure_canvas, COLORS, get_font


class DeviceManagerGUI:
    """设备管理GUI类 - MAA风格带动画"""
    
    def __init__(self, parent_frame, device_manager, screen_capture, log_callback):
        self.parent_frame = parent_frame
        self.device_manager = device_manager
        self.screen_capture = screen_capture
        self.log_callback = log_callback
        self.current_image = None
        
        # UI组件引用
        self.device_tree = None
        self.device_status_label = None
        self.preview_canvas = None
        self.manual_device_var = None
        
        # 设备类型相关
        self.device_type_var = None
        self.android_frame = None
        self.pc_frame = None
        
        # 预览自动刷新相关
        self.preview_refresh_job = None
        self.preview_refresh_interval = 500
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置设备管理UI - MAA风格"""
        # 设备类型选择区域 - 卡片式
        type_frame = tk.Frame(
            self.parent_frame,
            bg=COLORS['surface'],
            highlightbackground=COLORS['border_color'],
            highlightthickness=1
        )
        type_frame.pack(fill='x', pady=(0, 10))
        
        # 标题栏
        type_header = tk.Frame(type_frame, bg=COLORS['surface'], height=35)
        type_header.pack(fill='x')
        type_header.pack_propagate(False)
        
        type_title = tk.Label(
            type_header,
            text="设备类型",
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('title_medium', bold=True),
            anchor=tk.W
        )
        type_title.pack(side=tk.LEFT, fill='y', padx=12, pady=8)
        
        # 类型选择内容区域
        type_content = tk.Frame(type_frame, bg=COLORS['surface'])
        type_content.pack(fill='x', padx=12, pady=10)
        
        # 设备类型选择
        type_row = tk.Frame(type_content, bg=COLORS['surface'])
        type_row.pack(fill='x')
        
        type_label = tk.Label(
            type_row,
            text="选择设备:",
            bg=COLORS['surface'],
            fg=COLORS['text_secondary'],
            font=get_font('body_small')
        )
        type_label.pack(side=tk.LEFT)
        
        self.device_type_var = tk.StringVar(value="安卓")
        type_combo = ttk.Combobox(
            type_row,
            textvariable=self.device_type_var,
            values=["安卓", "PC"],
            state="readonly",
            width=15
        )
        type_combo.pack(side=tk.LEFT, padx=(8, 0))
        type_combo.bind('<<ComboboxSelected>>', self._on_device_type_change)
        
        # 状态显示
        self.device_status_label = tk.Label(
            type_row,
            text="未连接设备",
            bg=COLORS['surface'],
            fg=COLORS['text_secondary'],
            font=get_font('body_small')
        )
        self.device_status_label.pack(side=tk.RIGHT)
        
        # 安卓设备区域（包含现有的设备连接和列表功能）
        self.android_frame = tk.Frame(self.parent_frame, bg=COLORS['surface'])
        
        # 安卓设备连接区域
        conn_frame = tk.Frame(
            self.android_frame,
            bg=COLORS['surface'],
            highlightbackground=COLORS['border_color'],
            highlightthickness=1
        )
        conn_frame.pack(fill='x', pady=(0, 10))
        
        # 标题栏
        conn_header = tk.Frame(conn_frame, bg=COLORS['surface'], height=35)
        conn_header.pack(fill='x')
        conn_header.pack_propagate(False)
        
        conn_title = tk.Label(
            conn_header,
            text="设备连接",
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('title_medium', bold=True),
            anchor=tk.W
        )
        conn_title.pack(side=tk.LEFT, fill='y', padx=12, pady=8)
        
        # 连接内容区域
        conn_content = tk.Frame(conn_frame, bg=COLORS['surface'])
        conn_content.pack(fill='x', padx=12, pady=10)
        
        # 扫描和手动输入行
        top_row = tk.Frame(conn_content, bg=COLORS['surface'])
        top_row.pack(fill='x', pady=(0, 8))
        
        # 扫描按钮
        scan_btn = tk.Button(
            top_row,
            text="🔍 扫描设备",
            command=self.scan_devices,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_small', bold=True),
            relief='solid',
            borderwidth=1,
            padx=12,
            pady=6,
            cursor='hand2'
        )
        scan_btn.pack(side=tk.LEFT)
        self._bind_hover_effect(scan_btn, COLORS['surface_container_low'], COLORS['surface_container'],
                               COLORS['text_primary'], COLORS['text_primary'])
        
        # 手动输入行
        manual_row = tk.Frame(conn_content, bg=COLORS['surface'])
        manual_row.pack(fill='x')
        
        manual_label = tk.Label(
            manual_row,
            text="手动输入:",
            bg=COLORS['surface'],
            fg=COLORS['text_secondary'],
            font=get_font('body_small')
        )
        manual_label.pack(side=tk.LEFT)
        
        # 获取上次连接的设备地址作为默认值
        last_device = self.device_manager.get_last_connected_device()
        default_device = last_device if last_device else "127.0.0.1:16512"
        self.manual_device_var = tk.StringVar(value=default_device)
        manual_entry = tk.Entry(
            manual_row,
            textvariable=self.manual_device_var,
            width=25,
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('body_small'),
            relief='solid',
            borderwidth=1,
            highlightbackground=COLORS['border_color']
        )
        manual_entry.pack(side=tk.LEFT, padx=(8, 8))
        
        manual_connect_btn = tk.Button(
            manual_row,
            text="连接",
            command=self.manual_connect_device,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_small', bold=True),
            relief='solid',
            borderwidth=1,
            highlightbackground=COLORS['border_color'],
            padx=12,
            pady=4,
            cursor='hand2'
        )
        manual_connect_btn.pack(side=tk.LEFT)
        self._bind_hover_effect(manual_connect_btn, COLORS['surface_container_low'], COLORS['surface_container'],
                               COLORS['text_primary'], COLORS['text_primary'])
        
        # 设备列表区域
        device_list_frame = tk.Frame(
            self.android_frame,
            bg=COLORS['surface'],
            highlightbackground=COLORS['border_color'],
            highlightthickness=1
        )
        device_list_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # 标题栏
        list_header = tk.Frame(device_list_frame, bg=COLORS['surface'], height=35)
        list_header.pack(fill='x')
        list_header.pack_propagate(False)
        
        list_title = tk.Label(
            list_header,
            text="可用设备",
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('title_medium', bold=True),
            anchor=tk.W
        )
        list_title.pack(side=tk.LEFT, fill='y', padx=12, pady=8)
        
        # 设备列表内容
        list_content = tk.Frame(device_list_frame, bg=COLORS['surface'])
        list_content.pack(fill='both', expand=True, padx=12, pady=10)
        
        # 设备列表
        self.device_tree = ttk.Treeview(
            list_content,
            columns=('serial', 'model', 'state'),
            show='headings',
            height=4
        )
        self.device_tree.heading('serial', text='设备序列号')
        self.device_tree.heading('model', text='设备型号')
        self.device_tree.heading('state', text='状态')
        self.device_tree.column('serial', width=180)
        self.device_tree.column('model', width=120)
        self.device_tree.column('state', width=80)
        self.device_tree.pack(side=tk.LEFT, fill='both', expand=True)
        
        # 滚动条
        device_scroll = ttk.Scrollbar(list_content, orient=tk.VERTICAL, command=self.device_tree.yview)
        device_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.device_tree.configure(yscrollcommand=device_scroll.set)
        
        # 设备操作按钮
        device_btn_frame = tk.Frame(device_list_frame, bg=COLORS['surface'])
        device_btn_frame.pack(fill='x', padx=12, pady=(0, 10))
        
        connect_device_btn = tk.Button(
            device_btn_frame,
            text="🔗 连接选中",
            command=self.connect_selected_device,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_small', bold=True),
            relief='solid',
            borderwidth=1,
            padx=15,
            pady=6,
            cursor='hand2'
        )
        connect_device_btn.pack(side=tk.LEFT, padx=(0, 8))
        self._bind_hover_effect(connect_device_btn, COLORS['surface_container_low'], COLORS['surface_container'],
                               COLORS['text_primary'], COLORS['text_primary'])
        
        disconnect_device_btn = tk.Button(
            device_btn_frame,
            text="断开",
            command=self.disconnect_device,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_small'),
            relief='solid',
            borderwidth=1,
            highlightbackground=COLORS['border_color'],
            padx=15,
            pady=6,
            cursor='hand2'
        )
        disconnect_device_btn.pack(side=tk.LEFT)
        self._bind_hover_effect(disconnect_device_btn, COLORS['surface_container_low'], COLORS['surface_container'],
                               COLORS['text_primary'], COLORS['text_primary'])
        
        # PC设备区域（包含触控方案选择和窗口画面预览）
        self.pc_frame = tk.Frame(self.parent_frame, bg=COLORS['surface'])
        
        # PC窗口连接区域 - 卡片式
        pc_conn_frame = tk.Frame(
            self.pc_frame,
            bg=COLORS['surface'],
            highlightbackground=COLORS['border_color'],
            highlightthickness=1
        )
        pc_conn_frame.pack(fill='x', pady=(0, 10))
        
        # 标题栏
        pc_conn_header = tk.Frame(pc_conn_frame, bg=COLORS['surface'], height=35)
        pc_conn_header.pack(fill='x')
        pc_conn_header.pack_propagate(False)
        
        pc_conn_title = tk.Label(
            pc_conn_header,
            text="窗口连接",
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('title_medium', bold=True),
            anchor=tk.W
        )
        pc_conn_title.pack(side=tk.LEFT, fill='y', padx=12, pady=8)
        
        # 连接内容区域
        pc_conn_content = tk.Frame(pc_conn_frame, bg=COLORS['surface'])
        pc_conn_content.pack(fill='x', padx=12, pady=10)
        
        # 窗口标题输入行
        window_row = tk.Frame(pc_conn_content, bg=COLORS['surface'])
        window_row.pack(fill='x')
        
        window_label = tk.Label(
            window_row,
            text="窗口标题:",
            bg=COLORS['surface'],
            fg=COLORS['text_secondary'],
            font=get_font('body_small')
        )
        window_label.pack(side=tk.LEFT)
        
        self.pc_window_title_var = tk.StringVar(value="Endfield")
        window_entry = tk.Entry(
            window_row,
            textvariable=self.pc_window_title_var,
            width=25,
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('body_small'),
            relief='solid',
            borderwidth=1,
            highlightbackground=COLORS['border_color']
        )
        window_entry.pack(side=tk.LEFT, padx=(8, 8))
        
        pc_connect_btn = tk.Button(
            window_row,
            text="连接窗口",
            command=self.connect_pc_window,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_small', bold=True),
            relief='solid',
            borderwidth=1,
            highlightbackground=COLORS['border_color'],
            padx=12,
            pady=4,
            cursor='hand2'
        )
        pc_connect_btn.pack(side=tk.LEFT)
        self._bind_hover_effect(pc_connect_btn, COLORS['surface_container_low'], COLORS['surface_container'],
                               COLORS['text_primary'], COLORS['text_primary'])
        
        # PC触控方案选择区域 - 卡片式
        pc_control_frame = tk.Frame(
            self.pc_frame,
            bg=COLORS['surface'],
            highlightbackground=COLORS['border_color'],
            highlightthickness=1
        )
        pc_control_frame.pack(fill='x', pady=(0, 10))
        
        # 标题栏
        pc_control_header = tk.Frame(pc_control_frame, bg=COLORS['surface'], height=35)
        pc_control_header.pack(fill='x')
        pc_control_header.pack_propagate(False)
        
        pc_control_title = tk.Label(
            pc_control_header,
            text="触控方案",
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('title_medium', bold=True),
            anchor=tk.W
        )
        pc_control_title.pack(side=tk.LEFT, fill='y', padx=12, pady=8)
        
        # 触控方案内容区域
        pc_control_content = tk.Frame(pc_control_frame, bg=COLORS['surface'])
        pc_control_content.pack(fill='x', padx=12, pady=10)
        
        # 触控方案选择行
        control_row = tk.Frame(pc_control_content, bg=COLORS['surface'])
        control_row.pack(fill='x')
        
        control_label = tk.Label(
            control_row,
            text="选择方案:",
            bg=COLORS['surface'],
            fg=COLORS['text_secondary'],
            font=get_font('body_small')
        )
        control_label.pack(side=tk.LEFT)
        
        # PC触控方案选项 - 参考MaaEnd
        self.pc_control_var = tk.StringVar(value="Win32-Window")
        self.pc_control_options = {
            "Win32-Window": {
                "label": "电脑端-默认",
                "description": "兼容性最好，适合日常使用。支持游戏最小化，会间接性抢占鼠标"
            },
            "Win32-Window-Background": {
                "label": "电脑端-后台",
                "description": "纯后台控制器。支持游戏最小化，不抢占鼠标。但可能导致游戏窗口乱飞"
            },
            "Win32-Express": {
                "label": "电脑端-极速",
                "description": "大幅提升响应速度，适合追求效率的用户。部分电脑可能无法使用"
            },
            "Win32-Front": {
                "label": "电脑端-前台",
                "description": "最稳定的控制方式。需要游戏窗口保持在最前且不被遮挡，会完全抢占鼠标"
            }
        }
        
        control_combo = ttk.Combobox(
            control_row,
            textvariable=self.pc_control_var,
            values=[f"{v['label']}" for v in self.pc_control_options.values()],
            state="readonly",
            width=20
        )
        control_combo.pack(side=tk.LEFT, padx=(8, 0))
        control_combo.current(0)  # 默认选择第一项
        control_combo.bind('<<ComboboxSelected>>', self._on_pc_control_change)
        
        # 触控方案描述
        self.pc_control_desc = tk.Label(
            pc_control_content,
            text=self.pc_control_options["Win32-Window"]["description"],
            bg=COLORS['surface'],
            fg=COLORS['text_muted'],
            font=get_font('body_small'),
            wraplength=400,
            justify=tk.LEFT,
            anchor=tk.W
        )
        self.pc_control_desc.pack(fill='x', pady=(8, 0))
        
        # 屏幕预览区域 - 卡片式
        preview_frame = tk.Frame(
            self.parent_frame,
            bg=COLORS['surface'],
            highlightbackground=COLORS['border_color'],
            highlightthickness=1
        )
        preview_frame.pack(fill='both', expand=True)
        
        # 标题栏
        preview_header = tk.Frame(preview_frame, bg=COLORS['surface'], height=35)
        preview_header.pack(fill='x')
        preview_header.pack_propagate(False)
        
        preview_title = tk.Label(
            preview_header,
            text="窗口画面",
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('title_medium', bold=True),
            anchor=tk.W
        )
        preview_title.pack(side=tk.LEFT, fill='y', padx=12, pady=8)
        
        # 预览画布
        preview_content = tk.Frame(preview_frame, bg=COLORS['surface'])
        preview_content.pack(fill='both', expand=True, padx=12, pady=10)
        
        self.preview_canvas = tk.Canvas(
            preview_content,
            bg=COLORS['surface_container_low'],
            highlightthickness=0,
            height=200
        )
        self.preview_canvas.pack(fill='both', expand=True)
        
        # 添加默认提示文字
        self.preview_canvas.create_text(
            self.preview_canvas.winfo_width() // 2,
            100,
            text="连接设备后显示画面预览",
            fill=COLORS['text_muted'],
            font=get_font('body_medium'),
            tags='placeholder'
        )
        
        # 默认显示安卓设备区域
        self._show_android_frame()
        
    def _on_device_type_change(self, event=None):
        """设备类型切换回调"""
        device_type = self.device_type_var.get()
        if device_type == "安卓":
            self._show_android_frame()
        else:
            self._show_pc_frame()
            
    def _show_android_frame(self):
        """显示安卓设备区域"""
        self.pc_frame.pack_forget()
        self.android_frame.pack(fill='both', expand=True)
        self.update_device_status("未连接设备")
        
    def _show_pc_frame(self):
        """显示PC设备区域（包含触控方案选择和窗口画面预览）"""
        self.android_frame.pack_forget()
        self.pc_frame.pack(fill='both', expand=True)
        # 更新状态显示当前选择的触控方案
        selected_label = self.pc_control_var.get()
        self.update_device_status(f"PC模式 - {selected_label}")
        # 停止安卓预览刷新
        self.stop_preview_refresh()
    
    def _on_pc_control_change(self, event=None):
        """PC触控方案切换回调"""
        selected_label = self.pc_control_var.get()
        # 查找对应的方案key
        for key, value in self.pc_control_options.items():
            if value['label'] == selected_label:
                # 更新描述
                self.pc_control_desc.config(text=value['description'])
                # 更新状态栏
                self.update_device_status(f"PC模式 - {selected_label}")
                # 记录日志
                self.log_callback(f"切换PC触控方案: {key} - {selected_label}", "device", "INFO")
                break
        
    def _bind_hover_effect(self, button, normal_bg, hover_bg, normal_fg, hover_fg):
        """绑定按钮悬停效果"""
        def on_enter(e):
            button.configure(bg=hover_bg, fg=hover_fg)
        def on_leave(e):
            button.configure(bg=normal_bg, fg=normal_fg)
        
        button.bind('<Enter>', on_enter)
        button.bind('<Leave>', on_leave)
        
    def scan_devices(self):
        """扫描设备"""
        devices = self.device_manager.scan_devices()
        
        # 清空设备列表
        for item in self.device_tree.get_children():
            self.device_tree.delete(item)
            
        # 获取上次连接的设备
        last_connected = self.device_manager.get_last_connected_device()
        
        # 添加设备到列表
        last_device_selected = False
        for device in devices:
            item_id = self.device_tree.insert('', 'end', values=(
                device['serial'],
                device['model'] or 'Unknown',
                device['state']
            ))
            if last_connected and device['serial'] == last_connected:
                self.device_tree.selection_set(item_id)
                last_device_selected = True
                
        if not last_device_selected and last_connected:
            self.log_callback(f"上次连接的设备 {last_connected} 不在当前设备列表中，但保留缓存", "device", "INFO")
            
        self.log_callback(f"发现 {len(devices)} 个设备", "device", "INFO")
        
    def connect_selected_device(self):
        """连接选中的设备"""
        selection = self.device_tree.selection()
        
        if not selection:
            last_connected = self.device_manager.get_last_connected_device()
            if last_connected:
                self.log_callback(f"未选择设备，尝试连接上次设备: {last_connected}", "device", "INFO")
                if self.device_manager.connect_device_manual(last_connected):
                    self.update_device_status(f"已连接: {last_connected}", color='success')
                    self.log_callback(f"成功连接到上次设备: {last_connected}", "device", "INFO")
                    self.start_preview_refresh()
                    return
                else:
                    self.log_callback(f"连接上次设备失败: {last_connected}", "device", "ERROR")
            messagebox.showwarning("警告", "请先选择一个设备")
            return
            
        item = self.device_tree.item(selection[0])
        device_serial = item['values'][0]
        
        if self.device_manager.connect_device(device_serial):
            self.update_device_status(f"已连接: {device_serial}", color='success')
            self.log_callback(f"成功连接到设备: {device_serial}", "device", "INFO")
            self.start_preview_refresh()
        else:
            messagebox.showerror("连接失败", "无法连接到选中的设备")
            self.log_callback(f"连接设备失败: {device_serial}", "device", "ERROR")
            
    def manual_connect_device(self):
        """手动连接设备"""
        device_serial = self.manual_device_var.get().strip()
        if not device_serial:
            messagebox.showwarning("警告", "请输入设备序列号")
            return
            
        if self.device_manager.connect_device_manual(device_serial):
            self.update_device_status(f"已连接: {device_serial}", color='success')
            self.log_callback(f"成功连接到设备: {device_serial}", "device", "INFO")
            self.start_preview_refresh()
        else:
            messagebox.showerror("连接失败", f"无法连接到设备: {device_serial}")
            self.log_callback(f"连接设备失败: {device_serial}", "device", "ERROR")
            
    def disconnect_device(self):
        """断开设备连接"""
        self.stop_preview_refresh()
        self.device_manager.disconnect_device()
        self.update_device_status("未连接设备")
        self.log_callback("设备连接已断开", "device", "INFO")
        
        # 清除预览
        self.preview_canvas.delete("all")
        self.preview_canvas.create_text(
            self.preview_canvas.winfo_width() // 2,
            100,
            text="连接设备后显示屏幕预览",
            fill=COLORS['text_muted'],
            font=get_font('body_medium'),
            tags='placeholder'
        )
        
    def update_device_status(self, status_text, color='muted'):
        """更新设备状态显示"""
        if color == 'success':
            self.device_status_label.config(text=status_text, fg=COLORS['success'])
        elif color == 'warning':
            self.device_status_label.config(text=status_text, fg=COLORS['warning'])
        elif color == 'danger':
            self.device_status_label.config(text=status_text, fg=COLORS['danger'])
        else:
            self.device_status_label.config(text=status_text, fg=COLORS['text_secondary'])
            
    def start_preview_refresh(self):
        """启动屏幕预览自动刷新"""
        if self.preview_refresh_job is None:
            self.update_screen_preview()
            
    def stop_preview_refresh(self):
        """停止屏幕预览自动刷新"""
        if self.preview_refresh_job:
            self.parent_frame.after_cancel(self.preview_refresh_job)
            self.preview_refresh_job = None
            
    def update_screen_preview(self, screen_data=None):
        """更新屏幕预览"""
        current_device = self.device_manager.get_current_device()
        if not current_device or not self.screen_capture:
            if self.preview_refresh_job:
                self.preview_refresh_job = None
            return
            
        try:
            if screen_data is None:
                screen_data = self.screen_capture.capture_screen(current_device)
                if not screen_data:
                    self.preview_refresh_job = self.parent_frame.after(self.preview_refresh_interval, self.update_screen_preview)
                    return
            
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
                scale = min(scale_x, scale_y, 1.0)
                
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                
                resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                self.current_image = ImageTk.PhotoImage(resized_image)
                
                self.preview_canvas.delete("all")
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                self.preview_canvas.create_image(x, y, anchor=tk.NW, image=self.current_image)
            
            if screen_data is None:
                self.preview_refresh_job = self.parent_frame.after(self.preview_refresh_interval, self.update_screen_preview)
                    
        except Exception as e:
            self.log_callback(f"屏幕预览更新失败: {e}", "device", "ERROR")
            self.preview_refresh_job = self.parent_frame.after(self.preview_refresh_interval, self.update_screen_preview)
            
    def get_current_device(self):
        """获取当前连接的设备"""
        return self.device_manager.get_current_device()
    
    def get_pc_control_scheme(self) -> str:
        """
        获取当前选择的PC触控方案
        
        Returns:
            方案名称 (Win32-Window, Win32-Window-Background, Win32-Express, Win32-Front)
        """
        selected_label = self.pc_control_var.get()
        # 查找对应的方案key
        for key, value in self.pc_control_options.items():
            if value['label'] == selected_label:
                return key
        return "Win32-Window"  # 默认返回
    
    def get_pc_window_title(self) -> str:
        """获取PC窗口标题"""
        return self.pc_window_title_var.get().strip()
    
    def connect_pc_window(self):
        """连接PC窗口"""
        window_title = self.pc_window_title_var.get().strip()
        if not window_title:
            messagebox.showwarning("警告", "请输入窗口标题")
            return
        
        # 获取当前选择的触控方案
        control_scheme = self.get_pc_control_scheme()
        
        # 设置PC设备模式和窗口信息
        self.device_manager.set_pc_mode(True)
        self.device_manager.set_current_device(f"PC:{window_title}")
        self.device_manager.set_pc_window_title(window_title)
        self.device_manager.set_pc_control_scheme(control_scheme)
        
        self.update_device_status(f"已连接: {window_title} ({control_scheme})", color='success')
        self.log_callback(f"成功连接到PC窗口: {window_title}, 触控方案: {control_scheme}", "device", "INFO")
