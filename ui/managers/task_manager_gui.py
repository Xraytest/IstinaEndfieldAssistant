"""任务管理GUI模块"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from ..theme import configure_listbox, COLORS, get_font, CORNER_RADIUS


class TaskManagerGUI:
    """任务管理GUI类 - MAA风格带拖拽排序"""
    
    def __init__(self, parent_frame, task_queue_manager, execution_manager, log_callback, on_task_settings_click=None, get_device_type_callback=None):
        self.parent_frame = parent_frame
        self.task_queue_manager = task_queue_manager
        self.execution_manager = execution_manager
        self.log_callback = log_callback
        self.on_task_settings_click = on_task_settings_click  # 任务设置点击回调
        self.get_device_type_callback = get_device_type_callback  # 获取当前设备类型的回调
        
        # UI组件引用
        self.task_frame = None
        self.task_canvas = None
        self.task_inner_frame = None
        self.task_items = {}  # 存储任务项框架
        self.selected_task_index = -1
        
        # 拖拽相关
        self.dragging = False
        self.dragged_index = -1
        self.dragged_widget = None
        self.drag_ghost = None  # 拖拽时的虚影
        self.drag_start_y = 0
        self.drag_current_y = 0
        
        self.queue_info_label = None
        self.execution_count_var = None
        self.execution_count_entry = None
        self.infinite_loop_var = None
        self.llm_start_btn = None
        self.llm_stop_btn = None
        
        self.setup_ui()
        self.update_queue_display()
        
    def setup_ui(self):
        """设置任务管理UI - MAA风格带动画效果"""
        # 任务队列区域 - 卡片式容器
        self.task_frame = tk.Frame(
            self.parent_frame, 
            bg=COLORS['surface'],
            highlightbackground=COLORS['border_color'],
            highlightthickness=1
        )
        self.task_frame.pack(fill='both', expand=True)
        
        # 标题栏
        header_frame = tk.Frame(self.task_frame, bg=COLORS['surface'], height=40)
        header_frame.pack(fill='x', padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame,
            text="任务队列",
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('title_medium', bold=True),
            anchor=tk.W
        )
        title_label.pack(side=tk.LEFT, fill='y', padx=12, pady=8)
        
        # 提示文字
        hint_label = tk.Label(
            header_frame,
            text="(可拖拽排序)",
            bg=COLORS['surface'],
            fg=COLORS['text_muted'],
            font=get_font('body_small'),
            anchor=tk.W
        )
        hint_label.pack(side=tk.LEFT, fill='y', padx=(5, 0), pady=10)
        
        # 任务列表容器 - 使用Canvas实现滚动
        list_container = tk.Frame(self.task_frame, bg=COLORS['surface'])
        list_container.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        
        # Canvas和滚动条
        self.task_canvas = tk.Canvas(
            list_container,
            bg=COLORS['surface'],
            highlightthickness=0,
            borderwidth=0
        )
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.task_canvas.yview)
        
        self.task_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.task_canvas.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.pack(side=tk.RIGHT, fill='y')
        
        # 内部框架用于放置任务项
        self.task_inner_frame = tk.Frame(self.task_canvas, bg=COLORS['surface'])
        self.canvas_window = self.task_canvas.create_window((0, 0), window=self.task_inner_frame, anchor='nw', width=250)
        
        # 绑定滚动事件
        self.task_inner_frame.bind('<Configure>', self._on_frame_configure)
        self.task_canvas.bind('<Configure>', self._on_canvas_configure)
        
        # 队列信息
        self.queue_info_label = tk.Label(
            self.task_frame,
            text="队列: 0个任务",
            bg=COLORS['surface'],
            fg=COLORS['text_secondary'],
            font=get_font('body_small'),
            anchor=tk.W
        )
        self.queue_info_label.pack(fill='x', padx=12, pady=(0, 8))
        
        # 底部按钮区域
        btn_frame = tk.Frame(self.parent_frame, bg=COLORS['surface'])
        btn_frame.pack(fill='x', pady=(10, 0))
        
        # 添加任务按钮 - 使用ttk样式按钮
        add_task_btn = ttk.Button(
            btn_frame,
            text="+ 添加任务",
            command=self.show_add_task_dialog,
            style='Primary.TButton'
        )
        add_task_btn.pack(fill='x', pady=(0, 6))
        
        # 删除按钮
        delete_task_btn = ttk.Button(
            btn_frame,
            text="删除",
            command=self.delete_selected_task,
            style='OutlineDanger.TButton'
        )
        delete_task_btn.pack(fill='x', pady=(0, 6))
        
        # 执行控制区域
        exec_frame = tk.Frame(self.parent_frame, bg=COLORS['surface'])
        exec_frame.pack(fill='x', pady=(15, 0))
        
        # 执行控制标题
        exec_title = tk.Label(
            exec_frame,
            text="执行控制",
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('title_medium', bold=True),
            anchor=tk.W
        )
        exec_title.pack(fill='x', pady=(0, 8))
        
        # 启动按钮 - 绿色成功按钮（ttk样式）
        self.llm_start_btn = ttk.Button(
            exec_frame,
            text="▶ 启动",
            command=self.start_llm_execution,
            style='Success.TButton'
        )
        self.llm_start_btn.pack(fill='x', pady=(0, 6))
        
        # 停止按钮 - 红色危险按钮（ttk样式）
        self.llm_stop_btn = ttk.Button(
            exec_frame,
            text="■ 停止",
            command=self.stop_llm_execution,
            style='Danger.TButton'
        )
        self.llm_stop_btn.pack(fill='x', pady=(0, 6))
        
        # 执行次数设置
        count_frame = tk.Frame(exec_frame, bg=COLORS['surface'])
        count_frame.pack(fill='x', pady=(8, 0))
        
        count_label = tk.Label(
            count_frame,
            text="执行次数:",
            bg=COLORS['surface'],
            fg=COLORS['text_secondary'],
            font=get_font('body_small')
        )
        count_label.pack(side=tk.LEFT)
        
        self.execution_count_var = tk.IntVar(value=self.task_queue_manager.get_execution_count())
        execution_count_spinbox = tk.Spinbox(
            count_frame, 
            from_=1, 
            to=99, 
            textvariable=self.execution_count_var, 
            width=5,
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('body_medium'),
            relief='solid',
            borderwidth=1,
            highlightbackground=COLORS['border_color']
        )
        execution_count_spinbox.pack(side=tk.LEFT, padx=(8, 0))
        execution_count_spinbox.bind('<Return>', lambda e: self.on_execution_count_changed())
        execution_count_spinbox.bind('<FocusOut>', lambda e: self.on_execution_count_changed())
        self.execution_count_entry = execution_count_spinbox
        
        # 持续循环复选框
        self.infinite_loop_var = tk.BooleanVar(value=False)
        infinite_loop_check = tk.Checkbutton(
            count_frame,
            text="持续循环",
            variable=self.infinite_loop_var,
            command=self.on_infinite_loop_changed,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_small'),
            selectcolor=COLORS['surface_container_low'],
            activebackground=COLORS['surface_container'],
            activeforeground=COLORS['text_primary'],
            relief='solid',
            borderwidth=1
        )
        infinite_loop_check.pack(side=tk.LEFT, padx=(15, 0))
        
    def _bind_hover_effect(self, button, normal_bg, hover_bg, normal_fg, hover_fg):
        """绑定按钮悬停效果"""
        def on_enter(e):
            button.configure(bg=hover_bg, fg=hover_fg)
        def on_leave(e):
            button.configure(bg=normal_bg, fg=normal_fg)
        
        button.bind('<Enter>', on_enter)
        button.bind('<Leave>', on_leave)
        
    def _on_frame_configure(self, event=None):
        """内部框架大小改变时更新滚动区域"""
        self.task_canvas.configure(scrollregion=self.task_canvas.bbox('all'))
        
    def _on_canvas_configure(self, event=None):
        """Canvas大小改变时更新内部框架宽度"""
        self.task_canvas.itemconfig(self.canvas_window, width=event.width)
        
    def _check_task_compatibility(self, task):
        """检查任务与当前设备类型的兼容性
        
        Returns:
            tuple: (is_compatible, platform_info)
                - is_compatible: bool, 是否兼容
                - platform_info: str, 平台信息描述
        """
        # 获取当前设备类型
        current_device_type = None
        if self.get_device_type_callback:
            current_device_type = self.get_device_type_callback()
        
        if not current_device_type:
            # 无法获取设备类型，默认兼容
            return (True, "")
        
        # 映射设备类型到平台
        device_to_platform = {
            "安卓": "android",
            "PC": "pc"
        }
        current_platform = device_to_platform.get(current_device_type, "")
        
        # 检查新格式任务模板的platforms字段
        platforms = task.get('platforms', {})
        if platforms:
            # 新格式：检查platforms中是否有当前平台
            if current_platform in platforms:
                return (True, platforms[current_platform].get('name', ''))
            else:
                # 不兼容，返回可用的平台信息
                available_platforms = list(platforms.keys())
                return (False, f"仅支持: {', '.join([platforms[p].get('name', p) for p in available_platforms])}")
        
        # 检查旧格式任务模板的controller_types字段
        controller_types = task.get('controller_types', [])
        if controller_types:
            # 根据设备类型判断兼容性
            if current_device_type == "安卓":
                # 安卓设备需要ADB控制器
                is_compatible = "ADB" in controller_types
                if not is_compatible:
                    return (False, "仅支持: PC版")
            elif current_device_type == "PC":
                # PC设备需要Win32系列控制器
                pc_types = ["Win32", "Win32-Window", "Win32-Front"]
                is_compatible = any(ct in controller_types for ct in pc_types)
                if not is_compatible:
                    return (False, "仅支持: 安卓版")
            return (True, "")
        
        # 没有平台信息，默认兼容
        return (True, "")
    
    def update_queue_display(self):
        """更新任务队列显示 - 带拖拽功能和MAA风格"""
        # 清除现有任务项
        for widget in self.task_inner_frame.winfo_children():
            widget.destroy()
        
        self.task_items.clear()
        
        queue_info = self.task_queue_manager.get_queue_info()
        tasks = queue_info['tasks']
        
        for idx, task in enumerate(tasks):
            task_name = task.get('name', 'Unknown')
            
            # 检查任务兼容性
            is_compatible, platform_info = self._check_task_compatibility(task)
            
            # 创建任务项框架 - 带淡灰色半透明分界线
            task_row = tk.Frame(
                self.task_inner_frame,
                bg=COLORS['surface'],
                highlightbackground=COLORS['border_color'],
                highlightthickness=0
            )
            task_row.pack(fill='x', pady=1)
            
            # 分界线 - 淡灰色半透明（第一项除外）
            if idx > 0:
                separator = tk.Frame(
                    task_row,
                    bg=COLORS['border_color'],
                    height=1
                )
                separator.pack(fill='x', side=tk.TOP)
            
            # 内容容器 - 添加内边距
            content_frame = tk.Frame(task_row, bg=COLORS['surface'], height=36)
            content_frame.pack(fill='x', pady=2)
            content_frame.pack_propagate(False)
            
            # 兼容性标识 - 显示在最左侧
            if not is_compatible:
                compat_label = tk.Label(
                    content_frame,
                    text="⚠️",
                    bg=COLORS['surface'],
                    fg=COLORS['warning'],
                    font=get_font('body_small'),
                    cursor='hand2'
                )
                compat_label.pack(side=tk.LEFT, padx=(6, 0))
                # 绑定悬停提示
                self._create_tooltip(compat_label, f"不兼容: {platform_info}")
            else:
                # 兼容时显示空白占位
                compat_spacer = tk.Label(
                    content_frame,
                    text="",
                    bg=COLORS['surface'],
                    width=2
                )
                compat_spacer.pack(side=tk.LEFT, padx=(6, 0))
            
            # 拖拽手柄 (三道横线) - MAA风格
            drag_handle = tk.Label(
                content_frame,
                text="☰",
                bg=COLORS['surface'],
                fg=COLORS['text_muted'],
                font=get_font('body_small'),
                cursor='hand2',
                width=2
            )
            drag_handle.pack(side=tk.LEFT, padx=(0, 2))
            
            # 序号标签 - MAA风格
            index_label = tk.Label(
                content_frame,
                text=f"{idx + 1}.",
                bg=COLORS['surface'],
                fg=COLORS['text_muted'],
                font=get_font('body_small'),
                width=3,
                anchor=tk.E
            )
            index_label.pack(side=tk.LEFT, padx=(2, 4))
            
            # 选中状态变量
            var = tk.BooleanVar(value=(idx == self.selected_task_index))
            
            # 任务名称标签 - 不兼容时显示灰色
            task_label = tk.Label(
                content_frame,
                text=task_name,
                bg=COLORS['surface'],
                fg=COLORS['text_muted'] if not is_compatible else COLORS['text_primary'],
                font=get_font('body_medium'),
                anchor=tk.W
            )
            task_label.pack(side=tk.LEFT, fill='x', expand=True, padx=(0, 8))
            
            # 设置图标 - 使用Label显示齿轮符号
            settings_label = tk.Label(
                content_frame,
                text="⚙️",
                bg=COLORS['surface'],
                fg=COLORS['text_muted'],
                font=get_font('body_medium'),
                cursor='hand2'
            )
            settings_label.pack(side=tk.RIGHT, padx=(0, 8))
            
            # 绑定点击事件到设置图标
            settings_label.bind('<Button-1>', lambda e, i=idx: self.show_edit_task_dialog_for_task(i))
            
            # 存储引用
            self.task_items[idx] = {
                'frame': task_row,
                'content': content_frame,
                'label': task_label,
                'settings_label': settings_label,
                'var': var,
                'drag_handle': drag_handle,
                'index_label': index_label
            }
            
            # 绑定点击事件
            content_frame.bind('<Button-1>', lambda e, i=idx: self.on_task_select(i))
            task_label.bind('<Button-1>', lambda e, i=idx: self.on_task_select(i))
            index_label.bind('<Button-1>', lambda e, i=idx: self.on_task_select(i))
            
            # 绑定拖拽事件
            drag_handle.bind('<Button-1>', lambda e, i=idx: self._on_drag_start(e, i))
            drag_handle.bind('<B1-Motion>', lambda e, i=idx: self._on_drag_move(e, i))
            drag_handle.bind('<ButtonRelease-1>', lambda e, i=idx: self._on_drag_end(e, i))
            
            # 悬停效果
            self._bind_task_hover(task_row, content_frame, task_label, drag_handle, index_label)
        
        self.queue_info_label.config(text=f"队列: {queue_info['count']}个任务")
        
        # 更新选中样式
        self._update_task_selection_style()
        
        # 更新Canvas滚动区域
        self.task_inner_frame.update_idletasks()
        self.task_canvas.configure(scrollregion=self.task_canvas.bbox('all'))
        
    def _bind_task_hover(self, row_frame, content_frame, label, drag_handle, index_label=None):
        """绑定任务项悬停效果"""
        def on_enter(e):
            if not self.dragging:
                content_frame.configure(bg=COLORS['surface_container_low'])
                label.configure(bg=COLORS['surface_container_low'])
                drag_handle.configure(bg=COLORS['surface_container_low'])
                if index_label:
                    index_label.configure(bg=COLORS['surface_container_low'])
                
        def on_leave(e):
            if not self.dragging:
                content_frame.configure(bg=COLORS['surface'])
                label.configure(bg=COLORS['surface'])
                drag_handle.configure(bg=COLORS['surface'])
                if index_label:
                    index_label.configure(bg=COLORS['surface'])
                self._update_task_selection_style()
                
        row_frame.bind('<Enter>', on_enter)
        row_frame.bind('<Leave>', on_leave)
        
    def _on_drag_start(self, event, index):
        """开始拖拽"""
        self.dragging = True
        self.dragged_index = index
        self.drag_start_y = event.y_root
        
        # 获取被拖拽的项
        item = self.task_items.get(index)
        if item:
            self.dragged_widget = item['frame']
            
            # 创建虚影效果
            self._create_drag_ghost(item)
            
            # 应用虚化效果到原项
            self._apply_blur_effect(item, True)
            
            # 添加缩放动画效果
            self._animate_drag_start(item)
            
    def _animate_drag_start(self, item):
        """拖拽开始时的动画效果"""
        # 临时改变边框样式表示正在拖拽
        item['frame'].configure(
            highlightbackground=COLORS['primary'],
            highlightthickness=2
        )
            
    def _create_drag_ghost(self, item):
        """创建拖拽虚影"""
        if self.drag_ghost:
            self.drag_ghost.destroy()
            
        # 创建虚影窗口
        self.drag_ghost = tk.Toplevel(self.parent_frame)
        self.drag_ghost.overrideredirect(True)
        self.drag_ghost.attributes('-alpha', 0.7)  # 半透明
        self.drag_ghost.attributes('-topmost', True)
        
        # 复制内容到虚影
        ghost_frame = tk.Frame(
            self.drag_ghost,
            bg=COLORS['surface'],
            highlightbackground=COLORS['primary'],
            highlightthickness=2
        )
        ghost_frame.pack(fill='both', expand=True)
        
        # 添加标签
        tk.Label(
            ghost_frame,
            text=item['label'].cget('text'),
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('body_medium'),
            padx=20,
            pady=10
        ).pack()
        
        # 设置虚影位置
        self._update_ghost_position(event=None)
        
    def _update_ghost_position(self, event):
        """更新虚影位置"""
        if self.drag_ghost and event:
            x = self.task_canvas.winfo_rootx() + 20
            y = event.y_root
            self.drag_ghost.geometry(f"+{x}+{y}")
            
    def _on_drag_move(self, event, index):
        """拖拽中"""
        if not self.dragging or self.dragged_index != index:
            return
            
        # 更新虚影位置
        if self.drag_ghost:
            x = self.task_canvas.winfo_rootx() + 20
            y = event.y_root
            self.drag_ghost.geometry(f"+{x}+{y}")
            
        # 计算当前位置对应的索引
        current_y = event.y_root - self.task_inner_frame.winfo_rooty()
        new_index = self._calculate_drop_index(current_y)
        
        # 如果位置改变，显示插入指示器
        if new_index != self.dragged_index:
            self._show_drop_indicator(new_index)
            
    def _calculate_drop_index(self, y):
        """计算拖放位置对应的索引"""
        # 获取实际的任务项高度
        if self.task_items:
            first_item = list(self.task_items.values())[0]['frame']
            item_height = first_item.winfo_height()
            if item_height < 10:  # 如果高度未计算，使用默认值
                item_height = 40
        else:
            item_height = 40
            
        # 计算索引，限制在有效范围内
        index = int(y / item_height)
        max_index = len(self.task_items) - 1
        return max(0, min(index, max_index))
        
    def _show_drop_indicator(self, index):
        """显示拖放指示器 - 在目标位置上方显示蓝色线条"""
        # 移除之前的指示器
        for item in self.task_items.values():
            # 恢复原始边框
            item['frame'].configure(highlightthickness=0)
            # 移除可能存在的插入线
            for child in item['frame'].winfo_children():
                if isinstance(child, tk.Frame) and hasattr(child, '_is_drop_indicator'):
                    child.destroy()
        
        # 在新位置上方显示插入线指示器
        if index in self.task_items and index != self.dragged_index:
            target_item = self.task_items[index]
            
            # 创建蓝色插入线
            insert_line = tk.Frame(
                target_item['frame'],
                bg=COLORS['primary'],
                height=3
            )
            insert_line._is_drop_indicator = True
            insert_line.pack(fill='x', side=tk.TOP, before=target_item['frame'].winfo_children()[0] if target_item['frame'].winfo_children() else None)
            
            # 添加动画效果 - 闪烁
            self._animate_drop_indicator(insert_line, 0)
            
    def _animate_drop_indicator(self, indicator, step):
        """为拖放指示器添加闪烁动画"""
        if not indicator.winfo_exists():
            return
            
        # 简单的透明度动画（通过颜色变化模拟）
        colors = [COLORS['primary'], '#42A5F5', '#64B5F6', '#42A5F5', COLORS['primary']]
        if step < len(colors):
            indicator.configure(bg=colors[step])
            # 继续动画
            self.parent_frame.after(100, lambda: self._animate_drop_indicator(indicator, step + 1))
            
    def _on_drag_end(self, event, index):
        """结束拖拽"""
        if not self.dragging or self.dragged_index != index:
            return
            
        self.dragging = False
        
        # 移除虚影
        if self.drag_ghost:
            self.drag_ghost.destroy()
            self.drag_ghost = None
            
        # 移除虚化效果
        item = self.task_items.get(index)
        if item:
            self._apply_blur_effect(item, False)
            
        # 计算最终位置
        current_y = event.y_root - self.task_inner_frame.winfo_rooty()
        new_index = self._calculate_drop_index(current_y)
        
        # 清除所有拖放指示器
        self._clear_drop_indicators()
            
        # 如果位置改变，重新排序
        if new_index != index and 0 <= new_index < len(self.task_items):
            # 添加平滑过渡效果
            self._animate_reorder(index, new_index)
        else:
            # 位置未改变，刷新显示
            self.update_queue_display()
            
        self.dragged_index = -1
        self.dragged_widget = None
        
    def _clear_drop_indicators(self):
        """清除所有拖放指示器"""
        for item in self.task_items.values():
            item['frame'].configure(highlightthickness=0)
            # 移除插入线指示器
            for child in item['frame'].winfo_children()[:]:
                if isinstance(child, tk.Frame) and hasattr(child, '_is_drop_indicator'):
                    child.destroy()
                    
    def _animate_reorder(self, from_index, to_index):
        """执行重排序动画"""
        # 先执行重排序
        self._reorder_tasks(from_index, to_index)
        
    def _apply_blur_effect(self, item, blur):
        """应用/移除虚化效果"""
        if blur:
            # 虚化效果：降低对比度和透明度
            item['frame'].configure(bg='#F0F0F0')
            item['content'].configure(bg='#F0F0F0')
            item['label'].configure(bg='#F0F0F0', fg='#999999')
            item['drag_handle'].configure(bg='#F0F0F0', fg='#CCCCCC')
        else:
            # 恢复正常
            item['frame'].configure(bg=COLORS['surface'])
            item['content'].configure(bg=COLORS['surface'])
            item['label'].configure(bg=COLORS['surface'], fg=COLORS['text_primary'])
            item['drag_handle'].configure(bg=COLORS['surface'], fg=COLORS['text_muted'])
            
    def _reorder_tasks(self, from_index, to_index):
        """重新排序任务 - 使用TaskQueueManager的move_task方法"""
        # 调用TaskQueueManager的move_task方法进行重排
        success = self.task_queue_manager.move_task(from_index, to_index)
        
        if success:
            # 更新选中索引
            if self.selected_task_index == from_index:
                self.selected_task_index = to_index
            elif from_index < self.selected_task_index <= to_index:
                self.selected_task_index -= 1
            elif to_index <= self.selected_task_index < from_index:
                self.selected_task_index += 1
            
            # 保存到本地
            self.task_queue_manager.save_task_queue()
            
            # 刷新显示
            self.update_queue_display()
            self.log_callback(f"任务已从位置 {from_index+1} 移动到位置 {to_index+1}", "task", "INFO")
            
    def on_task_select(self, index):
        """任务选中处理"""
        # 取消之前的选中
        if self.selected_task_index >= 0 and self.selected_task_index in self.task_items:
            old_item = self.task_items[self.selected_task_index]
            old_item['var'].set(False)
        
        # 设置新的选中
        self.selected_task_index = index
        if index in self.task_items:
            new_item = self.task_items[index]
            new_item['var'].set(True)
        
        self._update_task_selection_style()
        
    def _update_task_selection_style(self):
        """更新任务选中样式 - MAA风格"""
        for idx, item in self.task_items.items():
            if idx == self.selected_task_index:
                # 选中样式 - 蓝色背景和边框
                item['content'].configure(bg=COLORS['selection_bg'])
                item['frame'].configure(
                    highlightbackground=COLORS['primary'],
                    highlightthickness=1
                )
                item['label'].configure(
                    bg=COLORS['selection_bg'],
                    fg=COLORS['primary']
                )
                item['var'].set(True)
                item['drag_handle'].configure(bg=COLORS['selection_bg'])
                if 'index_label' in item:
                    item['index_label'].configure(
                        bg=COLORS['selection_bg'],
                        fg=COLORS['primary']
                    )
            else:
                # 普通样式
                item['frame'].configure(
                    bg=COLORS['surface'],
                    highlightthickness=0
                )
                item['content'].configure(bg=COLORS['surface'])
                item['label'].configure(
                    bg=COLORS['surface'],
                    fg=COLORS['text_primary']
                )
                item['var'].set(False)
                item['drag_handle'].configure(bg=COLORS['surface'])
                if 'index_label' in item:
                    item['index_label'].configure(
                        bg=COLORS['surface'],
                        fg=COLORS['text_muted']
                    )
                
    def show_add_task_dialog(self):
        """显示添加任务对话框"""
        if not self.execution_manager.auth_manager.get_login_status():
            messagebox.showwarning("未登录", "请先登录后再添加任务")
            return
            
        available_tasks = self.get_available_tasks_from_server()
        if not available_tasks:
            messagebox.showinfo("提示", "暂无可用任务")
            return
            
        dialog = tk.Toplevel(self.parent_frame.winfo_toplevel())
        dialog.title("添加任务")
        dialog.geometry("500x400")
        dialog.transient(self.parent_frame.winfo_toplevel())
        dialog.grab_set()
        dialog.configure(bg=COLORS['surface'])
        
        # 标题
        title_label = tk.Label(
            dialog,
            text="选择要添加的任务",
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('title_medium', bold=True)
        )
        title_label.pack(pady=(15, 10), padx=15, anchor=tk.W)
        
        # 任务列表
        list_frame = tk.Frame(dialog, bg=COLORS['surface'])
        list_frame.pack(fill='both', expand=True, padx=15, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        scrollbar.pack(side=tk.RIGHT, fill='y')
        
        task_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('body_medium'),
            selectbackground=COLORS['selection_bg'],
            selectforeground=COLORS['primary'],
            relief='solid',
            borderwidth=1,
            highlightthickness=0
        )
        task_listbox.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.config(command=task_listbox.yview)
        
        for task in available_tasks:
            task_listbox.insert(tk.END, f"{task.get('name', '未知任务')}")
            
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
        btn_frame = tk.Frame(dialog, bg=COLORS['surface'])
        btn_frame.pack(pady=15, fill='x', padx=15)
        
        add_btn = tk.Button(
            btn_frame,
            text="添加",
            command=on_add,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_medium', bold=True),
            relief='solid',
            borderwidth=1,
            padx=20,
            pady=8,
            cursor='hand2'
        )
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        self._bind_hover_effect(add_btn, COLORS['surface_container_low'], COLORS['surface_container'],
                               COLORS['text_primary'], COLORS['text_primary'])
        
        cancel_btn = tk.Button(
            btn_frame,
            text="取消",
            command=on_cancel,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_medium'),
            relief='solid',
            borderwidth=1,
            highlightbackground=COLORS['border_color'],
            padx=20,
            pady=8,
            cursor='hand2'
        )
        cancel_btn.pack(side=tk.RIGHT)
        self._bind_hover_effect(cancel_btn, COLORS['surface_container_low'], COLORS['surface_container'],
                               COLORS['text_primary'], COLORS['text_primary'])
        
    def show_edit_task_dialog_for_task(self, task_index):
        """显示指定任务的编辑对话框 - 如果有回调则切换到页面内标签，否则打开新窗口"""
        if task_index < 0 or task_index >= len(self.task_queue_manager.get_queue_info()['tasks']):
            return
            
        # 设置当前选中的任务
        self.on_task_select(task_index)
        
        # 如果有回调函数，使用回调切换到页面内任务设置标签
        if self.on_task_settings_click:
            self.on_task_settings_click(task_index)
            return
        
        # 否则使用原来的弹窗方式
        task = self.task_queue_manager.get_queue_info()['tasks'][task_index]
        task_id = task.get('id', '')
        
        latest_task_def = self.get_task_definition_from_server(task_id)
        if latest_task_def:
            variables = latest_task_def.get('variables', [])
            cached_variables = task.get('custom_variables', {})
            task['variables'] = variables
        else:
            variables = task.get('variables', [])
            cached_variables = task.get('custom_variables', {})
        
        dialog = tk.Toplevel(self.parent_frame.winfo_toplevel())
        dialog.title("设置任务")
        dialog.geometry("450x400")
        dialog.transient(self.parent_frame.winfo_toplevel())
        dialog.grab_set()
        dialog.configure(bg=COLORS['surface'])
        
        # 任务名称
        name_label = tk.Label(
            dialog,
            text="任务名称",
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('title_small', bold=True)
        )
        name_label.pack(pady=(15, 5), padx=15, anchor=tk.W)
        
        name_var = tk.StringVar(value=task.get('custom_name', task.get('name', '')))
        name_entry = tk.Entry(
            dialog,
            textvariable=name_var,
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('body_medium'),
            relief='solid',
            borderwidth=1,
            highlightbackground=COLORS['border_color']
        )
        name_entry.pack(fill='x', padx=15, pady=5)
        
        # 仅执行一次选项
        execute_once_var = tk.BooleanVar(value=task.get('execute_once', False))
        execute_once_check = tk.Checkbutton(
            dialog,
            text="仅执行一次（在多轮循环中只执行一次）",
            variable=execute_once_var,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_small'),
            selectcolor=COLORS['surface_container_low'],
            activebackground=COLORS['surface_container'],
            relief='solid',
            borderwidth=1
        )
        execute_once_check.pack(pady=(5, 10), padx=15, anchor=tk.W)
        
        # 任务变量
        if variables:
            var_label = tk.Label(
                dialog,
                text="任务变量",
                bg=COLORS['surface'],
                fg=COLORS['text_primary'],
                font=get_font('title_small', bold=True)
            )
            var_label.pack(pady=(10, 5), padx=15, anchor=tk.W)
            
            variables_frame = tk.Frame(dialog, bg=COLORS['surface'])
            variables_frame.pack(fill='both', expand=True, padx=15, pady=5)
            
            variable_entries = {}
            cascade_widgets = {}  # 存储级联变量控件引用
            
            # 辅助函数：提取选项值
            def extract_option_value(opt):
                """从选项中提取值，支持字符串和对象格式"""
                if isinstance(opt, dict):
                    return opt.get('value', '')
                return opt
            
            def extract_option_label(opt):
                """从选项中提取标签，支持字符串和对象格式"""
                if isinstance(opt, dict):
                    return opt.get('label', opt.get('value', ''))
                return opt
            
            # 辅助函数：检查级联变量是否应该显示
            def should_show_cascade_var(var_def, parent_values):
                """检查级联变量是否应该显示"""
                depends_on = var_def.get('depends_on')
                if not depends_on:
                    return True  # 非级联变量始终显示
                
                parent_var = depends_on.get('variable')
                trigger_values = depends_on.get('values', [])
                
                if parent_var in parent_values:
                    parent_value = parent_values.get(parent_var, '')
                    return parent_value in trigger_values
                return False
            
            # 辅助函数：更新级联变量显示状态
            def update_cascade_visibility():
                """更新所有级联变量的显示状态"""
                # 收集当前所有父级变量的值
                current_values = {}
                for v_name, (v_var, v_type) in variable_entries.items():
                    current_values[v_name] = v_var.get()
                
                # 更新每个级联变量的显示状态
                for v_name, widget_info in cascade_widgets.items():
                    var_def = widget_info['var_def']
                    frame = widget_info['frame']
                    
                    if should_show_cascade_var(var_def, current_values):
                        frame.pack(fill='x', pady=4)
                    else:
                        frame.pack_forget()
            
            # 构建变量依赖关系图
            var_dependencies = {}  # var_name -> list of dependent var_names
            for var_def in variables:
                var_name = var_def.get('name', '')
                depends_on = var_def.get('depends_on')
                if depends_on:
                    parent_var = depends_on.get('variable')
                    if parent_var:
                        if parent_var not in var_dependencies:
                            var_dependencies[parent_var] = []
                        var_dependencies[parent_var].append(var_name)
            
            for var_def in variables:
                var_name = var_def.get('name', '')
                var_type = var_def.get('type', 'string')
                var_default = var_def.get('default', '')
                var_options = var_def.get('options', [])
                depends_on = var_def.get('depends_on')
                
                current_value = cached_variables.get(var_name, var_default)
                
                var_frame = tk.Frame(variables_frame, bg=COLORS['surface'])
                
                # 级联变量初始时检查是否应该显示
                is_cascade = var_type == 'cascade_select' or depends_on is not None
                if is_cascade:
                    # 存储级联变量信息
                    cascade_widgets[var_name] = {
                        'frame': var_frame,
                        'var_def': var_def
                    }
                    # 检查初始显示状态
                    parent_values = {}
                    for v_name, (v_var, v_type) in variable_entries.items():
                        parent_values[v_name] = v_var.get()
                    if should_show_cascade_var(var_def, parent_values):
                        var_frame.pack(fill='x', pady=4)
                else:
                    var_frame.pack(fill='x', pady=4)
                
                # 显示级联标识
                display_name = var_name
                if is_cascade:
                    display_name = f"  └─ {var_name}"  # 添加缩进表示级联
                
                name_lbl = tk.Label(
                    var_frame,
                    text=f"{display_name}:",
                    bg=COLORS['surface'],
                    fg=COLORS['text_secondary'],
                    font=get_font('body_small')
                )
                name_lbl.pack(side=tk.LEFT)
                
                if var_type == 'bool':
                    var_var = tk.BooleanVar(value=bool(current_value))
                    var_entry = tk.Checkbutton(
                        var_frame,
                        variable=var_var,
                        bg=COLORS['surface_container_low'],
                        selectcolor=COLORS['surface_container_low'],
                        relief='solid',
                        borderwidth=1
                    )
                    var_entry.pack(side=tk.RIGHT)
                elif var_type == 'int':
                    var_var = tk.StringVar(value=str(current_value))
                    var_entry = tk.Entry(
                        var_frame,
                        textvariable=var_var,
                        width=10,
                        bg=COLORS['surface'],
                        fg=COLORS['text_primary'],
                        relief='solid',
                        borderwidth=1
                    )
                    var_entry.pack(side=tk.RIGHT)
                elif var_type in ('select', 'cascade_select') and var_options:
                    # 提取选项值和标签
                    option_values = [extract_option_value(opt) for opt in var_options]
                    option_labels = [extract_option_label(opt) for opt in var_options]
                    
                    if current_value not in option_values:
                        current_value = option_values[0] if option_values else var_default
                    var_var = tk.StringVar(value=str(current_value))
                    var_entry = ttk.Combobox(
                        var_frame,
                        textvariable=var_var,
                        values=option_labels,  # 显示标签
                        width=15,
                        state='readonly'
                    )
                    var_entry.pack(side=tk.RIGHT)
                    
                    # 存储选项映射（标签->值）
                    variable_entries[var_name + '_label_map'] = (dict(zip(option_labels, option_values)), 'label_map')
                    
                    # 如果是父级变量，绑定更新事件
                    if var_name in var_dependencies:
                        def on_parent_change(event, vn=var_name):
                            # 延迟更新，确保变量值已更新
                            dialog.after(10, update_cascade_visibility)
                        var_entry.bind('<<ComboboxSelected>>', on_parent_change)
                else:
                    var_var = tk.StringVar(value=str(current_value))
                    var_entry = tk.Entry(
                        var_frame,
                        textvariable=var_var,
                        width=20,
                        bg=COLORS['surface'],
                        fg=COLORS['text_primary'],
                        relief='solid',
                        borderwidth=1
                    )
                    var_entry.pack(side=tk.RIGHT)
                    
                variable_entries[var_name] = (var_var, var_type)
        
        def on_save():
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showwarning("警告", "任务名称不能为空")
                return
                
            queue_info = self.task_queue_manager.get_queue_info()
            queue_info['tasks'][task_index]['custom_name'] = new_name
            queue_info['tasks'][task_index]['name'] = new_name
            queue_info['tasks'][task_index]['execute_once'] = execute_once_var.get()
            queue_info['tasks'][task_index]['variables'] = variables
            
            custom_vars = {}
            for var_name, (var_var, var_type) in variable_entries.items():
                # 跳过内部使用的标签映射
                if var_type == 'label_map':
                    continue
                    
                value = var_var.get()
                
                # 如果有标签映射，将标签转换为值
                label_map_key = var_name + '_label_map'
                if label_map_key in variable_entries:
                    label_map, _ = variable_entries[label_map_key]
                    # 将标签转换为值
                    value = label_map.get(value, value)
                
                if var_type == 'int':
                    try:
                        custom_vars[var_name] = int(value)
                    except ValueError:
                        custom_vars[var_name] = 0
                elif var_type == 'bool':
                    custom_vars[var_name] = bool(value)
                else:
                    custom_vars[var_name] = str(value)
                    
            queue_info['tasks'][task_index]['custom_variables'] = custom_vars
            
            self.task_queue_manager.save_task_queue()
            self.update_queue_display()
            self.log_callback(f"任务 '{new_name}' 已更新", "task", "INFO")
            dialog.destroy()
            
        def on_cancel():
            dialog.destroy()
            
        # 按钮
        btn_frame = tk.Frame(dialog, bg=COLORS['surface'])
        btn_frame.pack(pady=15, fill='x', padx=15)
        
        save_btn = tk.Button(
            btn_frame,
            text="保存",
            command=on_save,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_medium', bold=True),
            relief='solid',
            borderwidth=1,
            padx=20,
            pady=8,
            cursor='hand2'
        )
        save_btn.pack(side=tk.RIGHT, padx=(5, 0))
        self._bind_hover_effect(save_btn, COLORS['surface_container_low'], COLORS['surface_container'],
                               COLORS['text_primary'], COLORS['text_primary'])
        
        cancel_btn = tk.Button(
            btn_frame,
            text="取消",
            command=on_cancel,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_medium'),
            relief='solid',
            borderwidth=1,
            highlightbackground=COLORS['border_color'],
            padx=20,
            pady=8,
            cursor='hand2'
        )
        cancel_btn.pack(side=tk.RIGHT)
        self._bind_hover_effect(cancel_btn, COLORS['surface_container_low'], COLORS['surface_container'],
                               COLORS['text_primary'], COLORS['text_primary'])
    
    def show_edit_task_dialog(self):
        """显示编辑任务对话框 - 保留用于向后兼容"""
        if self.selected_task_index < 0:
            messagebox.showwarning("警告", "请先选择一个任务")
            return
            
        self.show_edit_task_dialog_for_task(self.selected_task_index)
        
        latest_task_def = self.get_task_definition_from_server(task_id)
        if latest_task_def:
            variables = latest_task_def.get('variables', [])
            cached_variables = task.get('custom_variables', {})
            task['variables'] = variables
        else:
            variables = task.get('variables', [])
            cached_variables = task.get('custom_variables', {})
        
        dialog = tk.Toplevel(self.parent_frame.winfo_toplevel())
        dialog.title("设置任务")
        dialog.geometry("450x400")
        dialog.transient(self.parent_frame.winfo_toplevel())
        dialog.grab_set()
        dialog.configure(bg=COLORS['surface'])
        
        # 任务名称
        name_label = tk.Label(
            dialog,
            text="任务名称",
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('title_small', bold=True)
        )
        name_label.pack(pady=(15, 5), padx=15, anchor=tk.W)
        
        name_var = tk.StringVar(value=task.get('custom_name', task.get('name', '')))
        name_entry = tk.Entry(
            dialog,
            textvariable=name_var,
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('body_medium'),
            relief='solid',
            borderwidth=1,
            highlightbackground=COLORS['border_color']
        )
        name_entry.pack(fill='x', padx=15, pady=5)
        
        # 仅执行一次选项
        execute_once_var = tk.BooleanVar(value=task.get('execute_once', False))
        execute_once_check = tk.Checkbutton(
            dialog,
            text="仅执行一次（在多轮循环中只执行一次）",
            variable=execute_once_var,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_small'),
            selectcolor=COLORS['surface_container_low'],
            activebackground=COLORS['surface_container'],
            relief='solid',
            borderwidth=1
        )
        execute_once_check.pack(pady=(5, 10), padx=15, anchor=tk.W)
        
        # 任务变量
        if variables:
            var_label = tk.Label(
                dialog,
                text="任务变量",
                bg=COLORS['surface'],
                fg=COLORS['text_primary'],
                font=get_font('title_small', bold=True)
            )
            var_label.pack(pady=(10, 5), padx=15, anchor=tk.W)
            
            variables_frame = tk.Frame(dialog, bg=COLORS['surface'])
            variables_frame.pack(fill='both', expand=True, padx=15, pady=5)
            
            variable_entries = {}
            
            for var_def in variables:
                var_name = var_def.get('name', '')
                var_type = var_def.get('type', 'string')
                var_default = var_def.get('default', '')
                var_options = var_def.get('options', [])
                
                current_value = cached_variables.get(var_name, var_default)
                
                var_frame = tk.Frame(variables_frame, bg=COLORS['surface'])
                var_frame.pack(fill='x', pady=4)
                
                name_lbl = tk.Label(
                    var_frame,
                    text=f"{var_name}:",
                    bg=COLORS['surface'],
                    fg=COLORS['text_secondary'],
                    font=get_font('body_small')
                )
                name_lbl.pack(side=tk.LEFT)
                
                if var_type == 'bool':
                    var_var = tk.BooleanVar(value=bool(current_value))
                    var_entry = tk.Checkbutton(
                        var_frame,
                        variable=var_var,
                        bg=COLORS['surface_container_low'],
                        selectcolor=COLORS['surface_container_low'],
                        relief='solid',
                        borderwidth=1
                    )
                    var_entry.pack(side=tk.RIGHT)
                elif var_type == 'int':
                    var_var = tk.StringVar(value=str(current_value))
                    var_entry = tk.Entry(
                        var_frame,
                        textvariable=var_var,
                        width=10,
                        bg=COLORS['surface'],
                        fg=COLORS['text_primary'],
                        relief='solid',
                        borderwidth=1
                    )
                    var_entry.pack(side=tk.RIGHT)
                elif var_type == 'select' and var_options:
                    if current_value not in var_options:
                        current_value = var_options[0] if var_options else var_default
                    var_var = tk.StringVar(value=str(current_value))
                    var_entry = ttk.Combobox(
                        var_frame,
                        textvariable=var_var,
                        values=var_options,
                        width=15,
                        state='readonly'
                    )
                    var_entry.pack(side=tk.RIGHT)
                else:
                    var_var = tk.StringVar(value=str(current_value))
                    var_entry = tk.Entry(
                        var_frame,
                        textvariable=var_var,
                        width=20,
                        bg=COLORS['surface'],
                        fg=COLORS['text_primary'],
                        relief='solid',
                        borderwidth=1
                    )
                    var_entry.pack(side=tk.RIGHT)
                    
                variable_entries[var_name] = (var_var, var_type)
        
        def on_save():
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showwarning("警告", "任务名称不能为空")
                return
                
            queue_info = self.task_queue_manager.get_queue_info()
            queue_info['tasks'][task_index]['custom_name'] = new_name
            queue_info['tasks'][task_index]['name'] = new_name
            queue_info['tasks'][task_index]['execute_once'] = execute_once_var.get()
            queue_info['tasks'][task_index]['variables'] = variables
            
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
                    
            queue_info['tasks'][task_index]['custom_variables'] = custom_vars
            
            self.task_queue_manager.save_task_queue()
            self.update_queue_display()
            self.log_callback(f"任务 '{new_name}' 已更新", "task", "INFO")
            dialog.destroy()
            
        def on_cancel():
            dialog.destroy()
            
        # 按钮
        btn_frame = tk.Frame(dialog, bg=COLORS['surface'])
        btn_frame.pack(pady=15, fill='x', padx=15)
        
        save_btn = tk.Button(
            btn_frame,
            text="保存",
            command=on_save,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_medium', bold=True),
            relief='solid',
            borderwidth=1,
            padx=20,
            pady=8,
            cursor='hand2'
        )
        save_btn.pack(side=tk.RIGHT, padx=(5, 0))
        self._bind_hover_effect(save_btn, COLORS['surface_container_low'], COLORS['surface_container'],
                               COLORS['text_primary'], COLORS['text_primary'])
        
        cancel_btn = tk.Button(
            btn_frame,
            text="取消",
            command=on_cancel,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_medium'),
            relief='solid',
            borderwidth=1,
            highlightbackground=COLORS['border_color'],
            padx=20,
            pady=8,
            cursor='hand2'
        )
        cancel_btn.pack(side=tk.RIGHT)
        self._bind_hover_effect(cancel_btn, COLORS['surface_container_low'], COLORS['surface_container'],
                               COLORS['text_primary'], COLORS['text_primary'])
        
    def sync_all_tasks_definitions_from_server(self) -> bool:
        """从服务器同步所有队列任务的最新定义"""
        if not self.execution_manager.auth_manager.get_login_status():
            return False
            
        if not self.execution_manager.communicator:
            self.log_callback("通信模块未初始化", "task", "ERROR")
            return False
        
        queue_info = self.task_queue_manager.get_queue_info()
        task_ids = [task.get('id', '') for task in queue_info['tasks'] if task.get('id')]
        
        if not task_ids:
            return True
        
        try:
            response = self.execution_manager.communicator.send_request(
                "sync_all_tasks_definitions",
                {"task_ids": task_ids}
            )
            
            if response and response.get('status') == 'success':
                tasks_map = response.get('tasks', {})
                updated_count = 0
                
                for task in queue_info['tasks']:
                    task_id = task.get('id', '')
                    if task_id in tasks_map:
                        latest_def = tasks_map[task_id]
                        task['variables'] = latest_def.get('variables', [])
                        updated_count += 1
                
                self.task_queue_manager.save_task_queue()
                self.log_callback(f"启动时同步完成: {updated_count}个任务已更新", "task", "INFO")
                return True
            else:
                error_msg = response.get('message', '未知错误') if response else '无响应'
                self.log_callback(f"批量同步任务定义失败: {error_msg}", "task", "ERROR")
                return False
        except Exception as e:
            self.log_callback(f"批量同步任务定义异常: {e}", "task", "ERROR")
            return False
    
    def get_task_definition_from_server(self, task_id: str):
        """从服务器获取指定任务的最新定义"""
        if not self.execution_manager.auth_manager.get_login_status():
            return None
            
        if not self.execution_manager.communicator:
            self.log_callback("通信模块未初始化", "task", "ERROR")
            return None
            
        try:
            response = self.execution_manager.communicator.send_request(
                "get_task_definition",
                {"task_id": task_id}
            )
            if response and response.get('status') == 'success':
                task = response.get('task')
                self.log_callback(f"成功获取任务 '{task_id}' 的最新定义", "task", "INFO")
                return task
            else:
                error_msg = response.get('message', '未知错误') if response else '无响应'
                self.log_callback(f"获取任务定义失败: {error_msg}", "task", "ERROR")
                return None
        except Exception as e:
            self.log_callback(f"获取任务定义异常: {e}", "task", "ERROR")
            return None
    
    def get_available_tasks_from_server(self):
        """从服务器获取可用任务列表"""
        if not self.execution_manager.auth_manager.get_login_status():
            return []
            
        if not self.execution_manager.communicator:
            self.log_callback("通信模块未初始化", "task", "ERROR")
            return []
            
        try:
            response = self.execution_manager.communicator.send_request("get_default_tasks", {})
            if response and response.get('status') == 'success':
                tasks = response.get('tasks', [])
                visible_tasks = [task for task in tasks if task.get('visible', True)]
                self.log_callback(f"成功从服务器获取 {len(visible_tasks)} 个可用任务", "task", "INFO")
                return visible_tasks
            else:
                error_msg = response.get('message', '未知错误') if response else '无响应'
                self.log_callback(f"获取可用任务失败: {error_msg}", "task", "ERROR")
                return []
        except Exception as e:
            self.log_callback(f"获取可用任务异常: {e}", "task", "ERROR")
            return []
            
    def add_task_to_queue(self, task_template=None):
        """添加任务到队列"""
        if task_template is None:
            return
        else:
            import time
            new_task = task_template.copy()
            new_task['id'] = f"{task_template['id']}_{int(time.time())}"
            new_task['name'] = task_template.get('name', '新任务')
            new_task['custom_name'] = new_task['name']
            self.task_queue_manager.add_task(new_task)
            self.update_queue_display()
            self.log_callback(f"已添加任务 '{new_task['name']}' 到队列", "task", "INFO")
            self.task_queue_manager.save_task_queue()
        
    def on_execution_count_changed(self):
        """执行次数改变时的处理"""
        try:
            count = self.execution_count_var.get()
            self.task_queue_manager.set_execution_count(count)
            self.log_callback(f"执行次数设置为: {count}", "execution", "INFO")
        except tk.TclError:
            pass
            
    def on_infinite_loop_changed(self):
        """持续循环选项改变时的处理"""
        is_infinite = self.infinite_loop_var.get()
        if is_infinite:
            self.execution_count_entry.config(state='disabled')
            self.task_queue_manager.set_execution_count(-1)
            self.log_callback("已启用持续循环模式", "execution", "INFO")
        else:
            self.execution_count_entry.config(state='normal')
            count = self.execution_count_var.get()
            self.task_queue_manager.set_execution_count(count)
            self.log_callback(f"执行次数设置为: {count}", "execution", "INFO")
            
    def start_llm_execution(self):
        """开始LLM执行"""
        main_gui = None
        if hasattr(self.parent_frame, 'winfo_toplevel'):
            root = self.parent_frame.winfo_toplevel()
            if hasattr(root, 'gui_manager'):
                main_gui = root.gui_manager
        
        preview_update_callback = None
        if main_gui and hasattr(main_gui, 'on_preview_update'):
            preview_update_callback = main_gui.on_preview_update
        
        success, message = self.execution_manager.start_execution(
            self.log_callback,
            self.update_ui_callback,
            preview_update_callback
        )
        if not success:
            messagebox.showwarning("警告", message)
        else:
            self.llm_start_btn.config(state='disabled')
            self.llm_stop_btn.config(state='normal')
            
    def stop_llm_execution(self):
        """停止LLM执行"""
        self.execution_manager.stop_execution()
        self.llm_start_btn.config(state='normal')
        self.llm_stop_btn.config(state='disabled')
        self.log_callback("执行已停止", "execution", "INFO")
        
    def update_ui_callback(self, event_type, data):
        """UI更新回调"""
        if event_type == 'stop_execution':
            self.llm_start_btn.config(state='normal')
            self.llm_stop_btn.config(state='disabled')
            
    def delete_selected_task(self):
        """删除选中的任务"""
        if self.selected_task_index < 0:
            messagebox.showwarning("警告", "请先选择一个任务")
            return
            
        task_index = self.selected_task_index
        queue_info = self.task_queue_manager.get_queue_info()
        if task_index < len(queue_info['tasks']):
            task_name = queue_info['tasks'][task_index].get('name', '未知任务')
        else:
            task_name = '未知任务'
            
        confirm = messagebox.askyesno(
            "确认删除",
            f"确定要删除任务 '{task_name}' 吗？\n此操作无法撤销！"
        )
        
        if confirm:
            removed_task = self.task_queue_manager.remove_task(task_index)
            if removed_task:
                self.selected_task_index = -1
                self.update_queue_display()
                self.log_callback(f"任务 '{removed_task['name']}' 已从队列中删除", "task", "INFO")
                self.task_queue_manager.save_task_queue()
    
    def _create_tooltip(self, widget, text):
        """创建悬停提示
        
        Args:
            widget: 要绑定提示的控件
            text: 提示文本
        """
        tooltip_window = None
        
        def show_tooltip(event):
            nonlocal tooltip_window
            if tooltip_window:
                return
            # 获取控件在屏幕上的位置
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + widget.winfo_height() + 5
            
            # 创建提示窗口
            tooltip_window = tk.Toplevel(widget)
            tooltip_window.wm_overrideredirect(True)
            tooltip_window.wm_geometry(f"+{x}+{y}")
            
            # 提示标签
            label = tk.Label(
                tooltip_window,
                text=text,
                bg=COLORS['surface_container_high'],
                fg=COLORS['text_primary'],
                font=get_font('body_small'),
                relief='solid',
                borderwidth=1,
                padx=8,
                pady=4
            )
            label.pack()
        
        def hide_tooltip(event):
            nonlocal tooltip_window
            if tooltip_window:
                tooltip_window.destroy()
                tooltip_window = None
        
        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)
