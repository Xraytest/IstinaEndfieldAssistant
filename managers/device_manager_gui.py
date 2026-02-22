"""设备管理GUI模块 - 处理设备连接和屏幕预览的UI逻辑"""
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import base64
import io


class DeviceManagerGUI:
    """设备管理GUI类"""
    
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
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置设备管理UI"""
        # 设备连接区域
        conn_frame = ttk.LabelFrame(self.parent_frame, text="设备连接", padding="10")
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
        device_list_frame = ttk.LabelFrame(self.parent_frame, text="可用设备", padding="10")
        device_list_frame.pack(fill='both', expand=True, pady=(0, 10))
        
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
        device_btn_frame = ttk.Frame(self.parent_frame)
        device_btn_frame.pack(fill='x', pady=(0, 10))
        
        connect_device_btn = ttk.Button(device_btn_frame, text="连接选中设备", command=self.connect_selected_device)
        connect_device_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        disconnect_device_btn = ttk.Button(device_btn_frame, text="断开连接", command=self.disconnect_device)
        disconnect_device_btn.pack(side=tk.LEFT)
        
        # 屏幕预览（缩小比例）
        preview_frame = ttk.LabelFrame(self.parent_frame, text="屏幕预览", padding="10")
        preview_frame.pack(fill='both', expand=True)
        
        self.preview_canvas = tk.Canvas(preview_frame, bg='black', highlightthickness=0, height=200)
        self.preview_canvas.pack(fill='both', expand=True)
        
    def scan_devices(self):
        """扫描设备"""
        devices = self.device_manager.scan_devices()
        
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
            last_connected = self.device_manager.get_last_connected_device()
            if last_connected and device['serial'] == last_connected:
                self.device_tree.selection_set(item_id)
                last_device_selected = True
                
        if not last_device_selected and last_connected:
            # 保留上次成功的设备缓存，即使当前不可用
            self.log_callback(f"上次连接的设备 {last_connected} 不在当前设备列表中，但保留缓存", "device", "INFO")
            
        self.log_callback(f"发现 {len(devices)} 个设备", "device", "INFO")
        
    def connect_selected_device(self):
        """连接选中的设备"""
        selection = self.device_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个设备")
            return
            
        item = self.device_tree.item(selection[0])
        device_serial = item['values'][0]
        
        if self.device_manager.connect_device(device_serial):
            self.update_device_status(f"已连接: {device_serial}")
            self.log_callback(f"成功连接到设备: {device_serial}", "device", "INFO")
            # 更新屏幕预览
            self.update_screen_preview()
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
            self.update_device_status(f"已连接: {device_serial}")
            self.log_callback(f"成功连接到设备: {device_serial}", "device", "INFO")
            # 更新屏幕预览
            self.update_screen_preview()
        else:
            messagebox.showerror("连接失败", f"无法连接到设备: {device_serial}")
            self.log_callback(f"连接设备失败: {device_serial}", "device", "ERROR")
            
    def disconnect_device(self):
        """断开设备连接"""
        self.device_manager.disconnect_device()
        self.update_device_status("未连接设备")
        self.log_callback("设备连接已断开", "device", "INFO")
        
    def update_device_status(self, status_text, color='gray'):
        """更新设备状态显示"""
        if color == 'green':
            self.device_status_label.config(text=status_text, foreground='green')
        else:
            self.device_status_label.config(text=status_text, foreground=color)
            
    def update_screen_preview(self):
        """更新屏幕预览"""
        current_device = self.device_manager.get_current_device()
        if not current_device or not self.screen_capture:
            return
            
        try:
            screen_data = self.screen_capture.capture_screen(current_device)
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
            self.log_callback(f"屏幕预览更新失败: {e}", "device", "ERROR")
            
    def get_current_device(self):
        """获取当前连接的设备"""
        return self.device_manager.get_current_device()