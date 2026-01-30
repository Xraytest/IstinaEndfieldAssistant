import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont
import json
import os
import time 
import threading
from typing import List, Tuple
from utils.adb_function import MiniTouchController, DeviceInfo

def create_iea_interface():
    # 创建主窗口
    root = tk.Tk()
    root.title("IstinaEndfieldAssistant")
    root.geometry("1000x650")
    root.minsize(800, 500)
    
    # 设置全局字体
    default_font = tkfont.nametofont("TkDefaultFont")
    default_font.configure(size=10)
    
    # 创建样式配置
    style = ttk.Style()
    style.configure('TCombobox', 
                   foreground='black',
                   background='white',
                   fieldbackground='white')
    
    # 创建 MiniTouchController 实例
    controller = MiniTouchController()
    
    # 创建设备选择相关变量
    selected_device = tk.StringVar()
    device_list = []  # 存储设备信息列表
    
    # 创建选项卡控件
    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True, padx=5, pady=5)
    
    # 创建四个选项卡
    tab_frames = [ttk.Frame(notebook) for _ in range(4)]
    tab_names = ["一键长草", "云服务", "小工具", "设置"]
    
    for frame, name in zip(tab_frames, tab_names):
        notebook.add(frame, text=name)
    
    # ====================== 一键长草选项卡 ======================
    tab1 = tab_frames[0]
    tab1.columnconfigure(0, weight=5)    # 左侧任务列表
    tab1.columnconfigure(1, weight=20)   # 中间设置面板（扩大）
    tab1.columnconfigure(2, weight=4)    # 右侧日志区域（收窄）
    tab1.rowconfigure(0, weight=1)
    
    # 创建三个主要区域
    left_frame = ttk.LabelFrame(tab1, text="任务列表", padding=5)
    left_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
    left_frame.columnconfigure((0, 1), weight=1)
    
    middle_frame = ttk.Frame(tab1)
    middle_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
    middle_frame.columnconfigure(0, weight=1)
    middle_frame.rowconfigure(0, weight=1)
    
    right_frame = ttk.Frame(tab1)
    right_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
    right_frame.columnconfigure(0, weight=1)
    right_frame.rowconfigure(0, weight=1)
    
    # 存储任务设置面板的字典
    task_settings = {}
    current_settings_panel = None
    
    # 创建任务设置面板
    def create_task_settings_panel(parent, task_name):
        panel = ttk.Frame(parent)
        panel.columnconfigure(0, weight=1)
        
        # 根据任务名称创建不同的设置内容
        task_configs = {
            "开始唤醒": [
                ("支持从打开游戏到进入世界，暂无可调选项")
            ],
            "理智作战": [
                ("理智阈值", "spinbox", 150),
                ("作战次数", "spinbox", 10),
                ("关卡选择", "combobox", "1-7", ["1-7", "2-4", "3-5"]),
                ("代理设置", "combobox", "AUTO", ["AUTO", "手动"])
            ],
            "据点交易": [
                ("交易物品", "combobox", "源石晶壳", ["源石晶壳", "其他物品1", "其他物品2"]),
                ("交易数量", "spinbox", 8000),
                ("交易频率", "combobox", "每次运行时", ["每次运行时", "每日仅一次", "每周仅一次"])
            ],
            "领取奖励": [
                ("日常", "checkbox"),
                ("周常", "checkbox"),
                ("通行证", "checkbox")
            ]
        }
        
        settings = task_configs.get(task_name, [])
        
        # 创建设置项 - 使用grid布局
        row_index = 0
        for item in settings:
            if isinstance(item, str):  # 单行提示文本
                label = ttk.Label(panel, text=item, anchor="w")
                label.grid(row=row_index, column=0, columnspan=2, padx=5, pady=3, sticky="w")
                row_index += 1
                continue
                
            text, widget_type = item[0], item[1]
            
            # 创建标签
            label = ttk.Label(panel, text=text, width=10, anchor="w")
            label.grid(row=row_index, column=0, padx=5, pady=3, sticky="w")
            
            if widget_type == "spinbox":
                value = item[2]
                spin = ttk.Spinbox(panel, from_=0, to=1000, width=5)
                spin.set(value)
                spin.grid(row=row_index, column=1, padx=5, pady=3, sticky="w")
                
            elif widget_type == "combobox":
                value = item[2]
                options = item[3] if len(item) > 3 else []
                cb = ttk.Combobox(panel, values=options, width=10)
                cb.set(value)
                cb.grid(row=row_index, column=1, padx=5, pady=3, sticky="w")
                
            elif widget_type == "checkbox":
                # 对于复选框，我们创建一个变量和复选框
                var = tk.BooleanVar()
                cb = ttk.Checkbutton(panel, text=text, variable=var)
                cb.grid(row=row_index, column=0, columnspan=2, padx=5, pady=3, sticky="w")
            
            row_index += 1
        
        return panel
    
    # 切换任务设置面板的函数
    def switch_task_settings(task_name):
        nonlocal current_settings_panel
        
        # 隐藏当前面板
        if current_settings_panel:
            current_settings_panel.grid_forget()
        
        # 显示新面板
        panel = task_settings[task_name]
        panel.grid(row=0, column=0, sticky="nsew")
        current_settings_panel = panel
    
    # 创建所有任务的设置面板
    task_names = ["开始唤醒", "理智作战", "据点交易", "领取奖励"]
    for task_name in task_names:
        task_settings[task_name] = create_task_settings_panel(middle_frame, task_name)
    
    # ====== 修正后的关键实现：半选中 ↔ 未选中 两态循环 ======
    checkboxes = []  # 保存复选框引用

    # 创建统一的点击处理函数（通过 event.widget 识别具体复选框）
    def on_checkbox_click(event):
        cb = event.widget
        
        # 检测当前是否为半选中状态
        if cb.instate(['alternate']):
            # 半选中 → 未选中：清除 alternate 和 selected
            cb.state(['!selected', '!alternate'])
        else:
            # 未选中 → 半选中：清除 selected，设置 alternate
            cb.state(['!selected', 'alternate'])
        
        # 关键：返回 "break" 阻止 ttk 的默认点击行为
        return "break"

    for i, task_name in enumerate(task_names):
        # 创建无 variable 的 Checkbutton（避免自动状态管理）
        cb = ttk.Checkbutton(left_frame, text=task_name)
        cb.grid(row=i, column=0, sticky="w", padx=(10, 5), pady=3)
        
        # 初始状态设为半选中（必须先清除 selected 再设置 alternate）
        cb.state(['!selected', 'alternate'])
        checkboxes.append(cb)
        
        # 绑定点击事件并阻止默认行为
        cb.bind('<Button-1>', on_checkbox_click)
        
        # 齿轮设置按钮
        btn = ttk.Button(left_frame, text="⚙", width=2,
                        command=lambda t=task_name: switch_task_settings(t))
        btn.grid(row=i, column=1, padx=5, pady=3)

    # 底部操作按钮
    btn_frame = ttk.Frame(left_frame)
    btn_frame.grid(row=len(task_names), column=0, columnspan=2, pady=10, padx=10, sticky="ew")
    btn_frame.columnconfigure((0, 1, 2, 3), weight=1)

    ttk.Button(btn_frame, text="+", width=3).grid(row=0, column=0, padx=2)

    # 全选按钮：全部设为半选中
    def select_all():
        for cb in checkboxes:
            cb.state(['!selected', 'alternate'])
    ttk.Button(btn_frame, text="全选", width=6, command=select_all).grid(row=0, column=1, padx=2)

    # 清空按钮：全部设为未选中
    def clear_all():
        for cb in checkboxes:
            cb.state(['!selected', '!alternate'])
    ttk.Button(btn_frame, text="清空", width=6, command=clear_all).grid(row=0, column=2, padx=2)

    ttk.Button(btn_frame, text="Link Start!", width=10).grid(row=0, column=3, padx=2)

    # 右侧日志区域
    log_frame = ttk.Frame(right_frame)
    log_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    
    log_text = tk.Text(log_frame, wrap=tk.WORD, width=30)
    log_text.grid(row=0, column=0, sticky="nsew")
    
    scrollbar = ttk.Scrollbar(log_frame, command=log_text.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    log_text.config(yscrollcommand=scrollbar.set)
    
    # 动态调整日志区域宽度
    def on_resize(event):
        # 计算日志区域理想宽度（总宽的15%~20%）
        total_width = tab1.winfo_width()
        ideal_width = max(200, min(350, int(total_width * 0.18)))
        right_frame.config(width=ideal_width)
    tab1.bind("<Configure>", on_resize)
    
    # ====================== 云服务选项卡 ======================
    tab2 = tab_frames[1]
    ttk.Label(tab2, text="云服务功能区域", font=("Arial", 12)).pack(pady=20)
    
    # ====================== 小工具选项卡 ======================
    tab3 = tab_frames[2]
    ttk.Label(tab3, text="小工具功能区域", font=("Arial", 12)).pack(pady=20)
    
    # ====================== 设置选项卡 ======================
    tab4 = tab_frames[3]
    tab4.columnconfigure(0, weight=1)
    
    # 创建设备选择框架
    device_frame = ttk.LabelFrame(tab4, text="设备连接设置", padding=10)
    device_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
    device_frame.columnconfigure(1, weight=1)
    
    # 设备标签
    ttk.Label(device_frame, text="选择设备:").grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
    
    # 设备选择下拉框
    device_combo = ttk.Combobox(device_frame, 
                               textvariable=selected_device,
                               state="readonly",
                               width=40)
    device_combo.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")
    
    # 刷新按钮
    def refresh_devices():
        """刷新设备列表"""
        try:
            global device_list
            device_list = controller.list_devices()
            
            if not device_list:
                device_combo.set("")
                device_combo['values'] = ["未检测到设备"]
                return
            
            # 创建设备显示字符串列表
            display_list = []
            for device in device_list:
                if device.model:
                    display_text = f"{device.model} ({device.id})"
                else:
                    display_text = device.id
                display_list.append(display_text)
            
            device_combo['values'] = display_list
            
            # 如果有设备，选择第一个
            if display_list:
                device_combo.set(display_list[0])
                selected_device.set(display_list[0])
            
            # 在日志中显示刷新结果
            log_text.insert(tk.END, f"已刷新设备列表，找到 {len(device_list)} 个设备\n")
            log_text.see(tk.END)
            
        except Exception as e:
            log_text.insert(tk.END, f"刷新设备失败: {str(e)}\n")
            log_text.see(tk.END)
            device_combo.set("刷新失败")
            device_combo['values'] = ["刷新失败"]
    
    refresh_btn = ttk.Button(device_frame, text="刷新设备", command=refresh_devices)
    refresh_btn.grid(row=0, column=2, padx=(0, 10), pady=5)
    
    # 连接/断开按钮
    device_connection_status = {"connected": False, "device_id": ""}
    
    def toggle_connection():
        """连接/断开设备"""
        selected = selected_device.get()
        if not selected or selected == "未检测到设备" or selected == "刷新失败":
            log_text.insert(tk.END, "请先选择有效设备\n")
            log_text.see(tk.END)
            return
        
        # 从显示字符串中提取设备ID
        try:
            # 格式可能是 "设备型号 (设备ID)" 或直接是设备ID
            if "(" in selected and ")" in selected:
                device_id = selected.split("(")[-1].rstrip(")")
            else:
                device_id = selected
        except Exception as e:
            log_text.insert(tk.END, f"解析设备ID失败: {str(e)}\n")
            log_text.see(tk.END)
            return
        
        if not device_connection_status["connected"]:
            # 连接设备
            try:
                success = controller.connect(device_id)
                if success:
                    device_connection_status["connected"] = True
                    device_connection_status["device_id"] = device_id
                    connect_btn.config(text="断开连接")
                    
                    # 获取屏幕尺寸
                    try:
                        width, height = controller.get_screen_size(device_id)
                        log_text.insert(tk.END, f"已连接设备: {device_id}\n")
                        log_text.insert(tk.END, f"屏幕分辨率: {width}x{height}\n")
                    except Exception as e:
                        log_text.insert(tk.END, f"已连接设备但无法获取屏幕尺寸: {str(e)}\n")
                    
                    log_text.see(tk.END)
                else:
                    log_text.insert(tk.END, f"连接设备失败: {device_id}\n")
                    log_text.see(tk.END)
            except Exception as e:
                log_text.insert(tk.END, f"连接设备异常: {str(e)}\n")
                log_text.see(tk.END)
        else:
            # 断开设备
            try:
                controller.disconnect(device_connection_status["device_id"])
                device_connection_status["connected"] = False
                device_connection_status["device_id"] = ""
                connect_btn.config(text="连接设备")
                log_text.insert(tk.END, f"已断开设备: {device_id}\n")
                log_text.see(tk.END)
            except Exception as e:
                log_text.insert(tk.END, f"断开设备异常: {str(e)}\n")
                log_text.see(tk.END)
    
    connect_btn = ttk.Button(device_frame, text="连接设备", command=toggle_connection)
    connect_btn.grid(row=0, column=3, pady=5)
    
    # 新增：手动输入设备地址和搜索功能
    manual_frame = ttk.LabelFrame(tab4, text="手动连接/搜索设备", padding=10)
    manual_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
    manual_frame.columnconfigure(1, weight=1)
    
    # 输入ADB设备地址
    ttk.Label(manual_frame, text="ADB设备地址:").grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
    
    device_address_var = tk.StringVar()
    device_address_entry = ttk.Entry(manual_frame, textvariable=device_address_var, width=30)
    device_address_entry.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")
    device_address_entry.insert(0, "例如: 192.168.1.100:5555")
    
    def connect_manual_device():
        """手动连接设备"""
        device_address = device_address_var.get().strip()
        
        if not device_address or device_address == "例如: 192.168.1.100:5555":
            log_text.insert(tk.END, "请输入有效的ADB设备地址\n")
            log_text.see(tk.END)
            return
        
        try:
            log_text.insert(tk.END, f"正在连接设备: {device_address}\n")
            log_text.see(tk.END)
            
            # 尝试连接设备
            result = controller._run_adb(['connect', device_address])
            if result.returncode == 0 and 'connected' in result.stdout:
                log_text.insert(tk.END, f"连接成功: {result.stdout}\n")
                log_text.see(tk.END)
                
                # 刷新设备列表
                refresh_devices()
                
                # 尝试自动选择新连接的设备
                if device_list:
                    for i, device in enumerate(device_list):
                        if device.id == device_address or device_address in device.id:
                            selected_device.set(f"{device.model} ({device.id})" if device.model else device.id)
                            break
            else:
                log_text.insert(tk.END, f"连接失败: {result.stderr if result.stderr else result.stdout}\n")
                log_text.see(tk.END)
                
        except Exception as e:
            log_text.insert(tk.END, f"连接设备异常: {str(e)}\n")
            log_text.see(tk.END)
    
    connect_manual_btn = ttk.Button(manual_frame, text="连接", command=connect_manual_device)
    connect_manual_btn.grid(row=0, column=2, padx=(0, 10), pady=5)
    
    # 搜索局域网设备
    ttk.Label(manual_frame, text="搜索IP段:").grid(row=1, column=0, padx=(0, 10), pady=5, sticky="w")
    
    ip_range_var = tk.StringVar()
    ip_range_entry = ttk.Entry(manual_frame, textvariable=ip_range_var, width=30)
    ip_range_entry.grid(row=1, column=1, padx=(0, 10), pady=5, sticky="ew")
    ip_range_entry.insert(0, "192.168.1.")
    
    # 进度条变量
    progress_bar = None
    progress_frame = None
    
    def update_progress(value):
        """更新进度条的值"""
        if progress_bar:
            progress_bar['value'] = value
            root.update_idletasks()
    
    def search_devices():
        """搜索局域网内的设备"""
        ip_range = ip_range_var.get().strip()
        
        if not ip_range:
            ip_range = "192.168.1."
        
        log_text.insert(tk.END, f"开始搜索IP段: {ip_range}*\n")
        log_text.see(tk.END)
        
        # 清理之前的进度条
        nonlocal progress_frame, progress_bar
        if progress_frame:
            progress_frame.destroy()
        
        # 创建新的进度条框架
        progress_frame = ttk.Frame(manual_frame)
        progress_frame.grid(row=2, column=0, columnspan=4, pady=(10, 5), sticky="ew")
        
        progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=300)
        progress_bar.pack(pady=5, fill='x', expand=True)
        
        def search_worker():
            found_devices = []
            port = 5555  # 默认ADB端口
            
            # 搜索常用IP范围
            for i in range(1, 255):
                ip_address = f"{ip_range}{i}"
                try:
                    log_text.insert(tk.END, f"尝试连接: {ip_address}:{port}\n")
                    log_text.see(tk.END)
                    
                    result = controller._run_adb(['connect', f"{ip_address}:{port}"])
                    if result.returncode == 0 and 'connected' in result.stdout:
                        log_text.insert(tk.END, f"找到设备: {ip_address}:{port}\n")
                        log_text.see(tk.END)
                        found_devices.append(f"{ip_address}:{port}")
                        
                except Exception as e:
                    # 忽略连接失败的错误
                    pass
                
                # 更新进度显示 - 使用函数而不是lambda中的赋值
                root.after(0, update_progress, (i / 254) * 100)
            
            # 搜索完成后刷新设备列表
            root.after(0, lambda: on_search_complete(found_devices))
        
        # 在新线程中执行搜索
        search_thread = threading.Thread(target=search_worker, daemon=True)
        search_thread.start()
    
    def on_search_complete(found_devices):
        """搜索完成后的回调"""
        if found_devices:
            log_text.insert(tk.END, f"搜索完成，找到 {len(found_devices)} 个设备\n")
            log_text.see(tk.END)
            refresh_devices()
        else:
            log_text.insert(tk.END, "搜索完成，未找到任何设备\n")
            log_text.see(tk.END)
    
    search_btn = ttk.Button(manual_frame, text="搜索设备", command=search_devices)
    search_btn.grid(row=1, column=2, padx=(0, 10), pady=5)
    
    # 快速连接按钮（常用端口）
    quick_connect_frame = ttk.Frame(manual_frame)
    quick_connect_frame.grid(row=3, column=0, columnspan=4, pady=(10, 0), sticky="ew")
    
    ttk.Label(quick_connect_frame, text="快速连接:").pack(side=tk.LEFT, padx=(0, 10))
    
    def quick_connect(ip):
        """快速连接指定IP的设备"""
        device_address_var.set(f"{ip}:5555")
        connect_manual_device()
    
    quick_ips = ["127.0.0.1", "localhost"]
    for ip in quick_ips:
        btn = ttk.Button(quick_connect_frame, text=ip, width=10,
                        command=lambda ip=ip: quick_connect(ip))
        btn.pack(side=tk.LEFT, padx=2)
    
    # 断开所有连接
    def disconnect_all():
        """断开所有ADB连接"""
        try:
            result = controller._run_adb(['disconnect'])
            log_text.insert(tk.END, f"断开所有连接: {result.stdout}\n")
            log_text.see(tk.END)
            
            # 刷新设备列表
            refresh_devices()
            
            # 更新连接状态
            if device_connection_status["connected"]:
                controller.disconnect(device_connection_status["device_id"])
                device_connection_status["connected"] = False
                device_connection_status["device_id"] = ""
                connect_btn.config(text="连接设备")
                
        except Exception as e:
            log_text.insert(tk.END, f"断开所有连接失败: {str(e)}\n")
            log_text.see(tk.END)
    
    disconnect_all_btn = ttk.Button(quick_connect_frame, text="断开所有", command=disconnect_all)
    disconnect_all_btn.pack(side=tk.LEFT, padx=(20, 0))
    
    # 设备信息显示
    info_frame = ttk.Frame(tab4)
    info_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
    info_frame.columnconfigure(1, weight=1)
    
    # 设备状态标签
    status_label = ttk.Label(info_frame, text="设备状态: 未连接", foreground="red")
    status_label.grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky="w")
    
    # 分辨率标签
    resolution_label = ttk.Label(info_frame, text="分辨率: 未知")
    resolution_label.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="w")
    
    # 测试按钮框架
    test_frame = ttk.LabelFrame(tab4, text="设备测试", padding=10)
    test_frame.grid(row=5, column=0, padx=10, pady=10, sticky="ew")
    test_frame.columnconfigure((0, 1, 2, 3), weight=1)
    
    def test_tap():
        """测试点击功能"""
        if not device_connection_status["connected"]:
            log_text.insert(tk.END, "请先连接设备\n")
            log_text.see(tk.END)
            return
        
        try:
            # 在屏幕中心点击
            device_id = device_connection_status["device_id"]
            width, height = controller.get_screen_size(device_id)
            x = width // 2
            y = height // 2
            
            controller.tap(device_id, x, y, duration_ms=50)
            log_text.insert(tk.END, f"测试点击: ({x}, {y})\n")
            log_text.see(tk.END)
        except Exception as e:
            log_text.insert(tk.END, f"测试点击失败: {str(e)}\n")
            log_text.see(tk.END)
    
    def test_swipe():
        """测试滑动功能"""
        if not device_connection_status["connected"]:
            log_text.insert(tk.END, "请先连接设备\n")
            log_text.see(tk.END)
            return
        
        try:
            device_id = device_connection_status["device_id"]
            width, height = controller.get_screen_size(device_id)
            
            # 从中心向上滑动
            start_x = width // 2
            start_y = height // 2
            end_x = width // 2
            end_y = height // 4
            
            controller.swipe(device_id, start_x, start_y, end_x, end_y, duration_ms=300)
            log_text.insert(tk.END, f"测试滑动: ({start_x}, {start_y}) → ({end_x}, {end_y})\n")
            log_text.see(tk.END)
        except Exception as e:
            log_text.insert(tk.END, f"测试滑动失败: {str(e)}\n")
            log_text.see(tk.END)
    
    def update_device_info():
        """更新设备信息显示"""
        if device_connection_status["connected"]:
            status_label.config(text="设备状态: 已连接", foreground="green")
            try:
                device_id = device_connection_status["device_id"]
                width, height = controller.get_screen_size(device_id)
                resolution_label.config(text=f"分辨率: {width}x{height}")
            except Exception as e:
                resolution_label.config(text=f"分辨率: 获取失败 ({str(e)})")
        else:
            status_label.config(text="设备状态: 未连接", foreground="red")
            resolution_label.config(text="分辨率: 未知")
        
        # 每隔1秒更新一次
        root.after(1000, update_device_info)
    
    # 创建测试按钮
    ttk.Button(test_frame, text="测试点击", command=test_tap).grid(row=0, column=0, padx=5, pady=5)
    ttk.Button(test_frame, text="测试滑动", command=test_swipe).grid(row=0, column=1, padx=5, pady=5)
    ttk.Button(test_frame, text="长按测试", command=lambda: None).grid(row=0, column=2, padx=5, pady=5)
    ttk.Button(test_frame, text="多点测试", command=lambda: None).grid(row=0, column=3, padx=5, pady=5)
    
    # 其他设置
    other_frame = ttk.LabelFrame(tab4, text="其他设置", padding=10)
    other_frame.grid(row=6, column=0, padx=10, pady=10, sticky="ew")
    other_frame.columnconfigure(1, weight=1)
    
    # 添加其他设置项
    ttk.Label(other_frame, text="操作延迟(ms):").grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
    delay_spin = ttk.Spinbox(other_frame, from_=0, to=1000, width=10)
    delay_spin.set(100)
    delay_spin.grid(row=0, column=1, pady=5, sticky="w")
    
    ttk.Label(other_frame, text="点击压力:").grid(row=1, column=0, padx=(0, 10), pady=5, sticky="w")
    pressure_spin = ttk.Spinbox(other_frame, from_=0, to=255, width=10)
    pressure_spin.set(100)
    pressure_spin.grid(row=1, column=1, pady=5, sticky="w")
    
    # 初始化显示第一个任务的设置
    switch_task_settings("开始唤醒")
    
    # 启动设备信息更新
    update_device_info()
    
    # 初始化时自动刷新设备列表
    root.after(500, refresh_devices)
    
    # 添加清空日志按钮
    def clear_log():
        log_text.delete(1.0, tk.END)
    
    clear_log_btn = ttk.Button(right_frame, text="清空日志", command=clear_log)
    clear_log_btn.grid(row=1, column=0, pady=5)
    
    return root

if __name__ == "__main__":
    app = create_iea_interface()
    app.mainloop()