"""设备管理GUI模块 - 处理设备连接和屏幕预览的UI逻辑"""
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import base64
import io
from ui.theme import configure_canvas


class DeviceManagerGUI:
    """设备管理GUI类"""
    
    def __init__(self, parent_frame, device_manager, screen_capture, log_callback,
                 touch_executor=None, config=None):
        self.parent_frame = parent_frame
        self.device_manager = device_manager
        self.screen_capture = screen_capture
        self.log_callback = log_callback
        self.touch_executor = touch_executor  # TouchManager实例
        self.config = config or {}
        self.current_image = None
        
        # 获取触控方式配置
        touch_config = self.config.get('touch', {})
        self.touch_method = touch_config.get('touch_method', 'maatouch')
        self.is_pc_mode = self.touch_method == 'pc_foreground'
        
        # UI组件引用
        self.device_tree = None
        self.device_status_label = None
        self.preview_canvas = None
        self.manual_device_var = None
        self.window_title_var = None  # PC窗口标题
        
        # 预览自动刷新相关
        self.preview_refresh_job = None
        self.preview_refresh_interval = 500  # 500毫秒刷新一次
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置设备管理UI"""
        if self.is_pc_mode:
            self._setup_pc_ui()
        else:
            self._setup_android_ui()
        
        # 屏幕预览（缩小比例）- 两种模式都需要
        preview_frame = ttk.LabelFrame(self.parent_frame, text="屏幕预览", padding="6")
        preview_frame.pack(fill='both', expand=True)
        
        self.preview_canvas = tk.Canvas(preview_frame, bg='black', highlightthickness=0, height=150)
        configure_canvas(self.preview_canvas)
        self.preview_canvas.pack(fill='both', expand=True)
    
    def _setup_pc_ui(self):
        """设置PC模式UI"""
        # 固定窗口标题
        self.window_title = "Endfield"
        
        # PC窗口连接区域
        conn_frame = ttk.LabelFrame(self.parent_frame, text="PC窗口连接", padding="6")
        conn_frame.pack(fill='x', pady=(0, 6))
        
        # 显示固定窗口标题
        window_frame = ttk.Frame(conn_frame)
        window_frame.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(window_frame, text=f"目标窗口: {self.window_title}", style='Header.TLabel').pack(side=tk.LEFT)
        
        connect_btn = ttk.Button(window_frame, text="连接窗口", command=self.connect_pc_window)
        connect_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # 连接状态
        self.device_status_label = ttk.Label(conn_frame, text="未连接PC窗口", style='Muted.TLabel')
        self.device_status_label.pack(side=tk.LEFT)
        
        # 操作按钮
        device_btn_frame = ttk.Frame(self.parent_frame)
        device_btn_frame.pack(fill='x', pady=(0, 6))
        
        disconnect_btn = ttk.Button(device_btn_frame, text="断开连接", command=self.disconnect_device)
        disconnect_btn.pack(side=tk.LEFT)
        
        # 提示信息
        info_frame = ttk.LabelFrame(self.parent_frame, text="PC模式说明", padding="6")
        info_frame.pack(fill='x', pady=(0, 6))
        ttk.Label(info_frame, text="PC前台模式：直接控制PC上的Endfield游戏窗口，无需Android设备。",
                  style='Muted.TLabel').pack(anchor=tk.W)
        ttk.Label(info_frame, text="请确保Endfield游戏窗口已打开。",
                  style='Muted.TLabel').pack(anchor=tk.W)
    
    def _setup_android_ui(self):
        """设置Android模式UI"""
        # 设备连接区域
        conn_frame = ttk.LabelFrame(self.parent_frame, text="设备连接", padding="6")
        conn_frame.pack(fill='x', pady=(0, 6))
        
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
        self.device_status_label = ttk.Label(conn_frame, text="未连接设备", style='Muted.TLabel')
        self.device_status_label.pack(side=tk.LEFT)
        
        # 设备列表
        device_list_frame = ttk.LabelFrame(self.parent_frame, text="可用设备", padding="6")
        device_list_frame.pack(fill='both', expand=True, pady=(0, 6))
        
        # 设备列表
        self.device_tree = ttk.Treeview(device_list_frame, columns=('serial', 'model', 'state'), show='headings', height=3)
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
        device_btn_frame = ttk.Frame(self.parent_frame)
        device_btn_frame.pack(fill='x', pady=(0, 6))
        
        connect_device_btn = ttk.Button(device_btn_frame, text="连接选中设备", command=self.connect_selected_device)
        connect_device_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        disconnect_device_btn = ttk.Button(device_btn_frame, text="断开连接", command=self.disconnect_device)
        disconnect_device_btn.pack(side=tk.LEFT)
        
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
            # 如果这是上次连接的设备，自动选中它
            if last_connected and device['serial'] == last_connected:
                self.device_tree.selection_set(item_id)
                last_device_selected = True
                
        if not last_device_selected and last_connected:
            # 保留上次成功的设备缓存，即使当前不可用
            self.log_callback(f"上次连接的设备 {last_connected} 不在当前设备列表中，但保留缓存", "device", "INFO")
            
        self.log_callback(f"发现 {len(devices)} 个设备", "device", "INFO")
        
    def connect_selected_device(self):
        """连接选中的设备，如果没有选中则尝试连接上次设备"""
        selection = self.device_tree.selection()
        
        # 如果没有选中设备，尝试连接上次连接的设备
        if not selection:
            last_connected = self.device_manager.get_last_connected_device()
            if last_connected:
                self.log_callback(f"未选择设备，尝试连接上次设备: {last_connected}", "device", "INFO")
                # 使用手动连接模式，不验证设备是否存在
                if self.device_manager.connect_device_manual(last_connected):
                    self.update_device_status(f"已连接: {last_connected}", color='success')
                    self.log_callback(f"成功连接到上次设备: {last_connected}", "device", "INFO")
                    # 启动屏幕预览自动刷新
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
            # 启动屏幕预览自动刷新
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
            # 启动屏幕预览自动刷新
            self.start_preview_refresh()
        else:
            messagebox.showerror("连接失败", f"无法连接到设备: {device_serial}")
            self.log_callback(f"连接设备失败: {device_serial}", "device", "ERROR")
            
    def connect_pc_window(self):
        """连接PC窗口"""
        if not self.touch_executor:
            messagebox.showerror("错误", "触控执行器未初始化")
            return
        
        # 使用固定的窗口标题
        window_title = self.window_title
        
        self.log_callback(f"尝试连接PC窗口: {window_title}", "device", "INFO")
        
        # 获取触控配置
        touch_config = self.config.get('touch', {})
        maa_style_config = touch_config.get('maa_style', {})
        
        # 创建配置字典
        win32_config = {
            'press_duration_ms': maa_style_config.get('press_duration_ms', 50),
            'swipe_delay_min_ms': maa_style_config.get('swipe_delay_min_ms', 100),
            'swipe_delay_max_ms': maa_style_config.get('swipe_delay_max_ms', 300),
            'fail_on_error': True
        }
        
        if self.touch_executor.connect_pc(window_title, win32_config):
            self.update_device_status(f"已连接PC窗口: {window_title}", color='success')
            self.log_callback(f"成功连接到PC窗口: {window_title}", "device", "INFO")
            # 启动屏幕预览自动刷新
            self.start_preview_refresh()
        else:
            messagebox.showerror("连接失败", f"无法连接到PC窗口: {window_title}\n请确保窗口已打开且标题正确")
            self.log_callback(f"连接PC窗口失败: {window_title}", "device", "ERROR")
    
    def disconnect_device(self):
        """断开设备连接"""
        # 停止屏幕预览自动刷新
        self.stop_preview_refresh()
        
        if self.is_pc_mode:
            # PC模式断开触控管理器
            if self.touch_executor:
                self.touch_executor.disconnect()
            self.update_device_status("未连接PC窗口")
        else:
            # Android模式断开设备管理器
            self.device_manager.disconnect_device()
            self.update_device_status("未连接设备")
        self.log_callback("设备连接已断开", "device", "INFO")
        
    def update_device_status(self, status_text, color='muted'):
        """更新设备状态显示"""
        if color == 'success':
            self.device_status_label.config(text=status_text, style='Success.TLabel')
        elif color == 'warning':
            self.device_status_label.config(text=status_text, style='Warning.TLabel')
        elif color == 'danger':
            self.device_status_label.config(text=status_text, style='Danger.TLabel')
        else:
            self.device_status_label.config(text=status_text, style='Muted.TLabel')
            
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
        """更新屏幕预览
        
        Args:
            screen_data: 可选的屏幕数据（Base64编码），如果提供则直接使用，否则重新捕获
        """
        # 检查连接状态
        if self.is_pc_mode:
            # PC模式检查触控管理器连接
            if not self.touch_executor or not self.touch_executor.is_connected:
                if self.preview_refresh_job:
                    self.preview_refresh_job = None
                return
        else:
            # Android模式检查设备连接
            current_device = self.device_manager.get_current_device()
            if not current_device or not self.screen_capture:
                if self.preview_refresh_job:
                    self.preview_refresh_job = None
                return
            
        try:
            # 如果没有提供screen_data，则重新捕获
            if screen_data is None:
                if self.is_pc_mode:
                    # PC模式使用触控管理器截图
                    screen_bytes = self.touch_executor.screencap()
                    if screen_bytes:
                        screen_data = base64.b64encode(screen_bytes).decode('utf-8')
                    else:
                        self.preview_refresh_job = self.parent_frame.after(self.preview_refresh_interval, self.update_screen_preview)
                        return
                else:
                    # Android模式使用ScreenCapture
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
                scale = min(scale_x, scale_y)
                
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                
                resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                self.current_image = ImageTk.PhotoImage(resized_image)
                
                self.preview_canvas.delete("all")
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                self.preview_canvas.create_image(x, y, anchor=tk.NW, image=self.current_image)
            
            # 安排下一次刷新（仅当没有提供screen_data时）
            if screen_data is None:
                self.preview_refresh_job = self.parent_frame.after(self.preview_refresh_interval, self.update_screen_preview)
                    
        except Exception as e:
            self.log_callback(f"屏幕预览更新失败: {e}", "device", "ERROR")
            # 出错后仍然安排下一次刷新尝试
            self.preview_refresh_job = self.parent_frame.after(self.preview_refresh_interval, self.update_screen_preview)
            
    def get_current_device(self):
        """获取当前连接的设备"""
        return self.device_manager.get_current_device()