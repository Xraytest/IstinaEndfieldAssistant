"""任务管理GUI模块 - 处理任务队列和执行控制的UI逻辑"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from ui.theme import configure_listbox, COLORS


class TaskManagerGUI:
    """任务管理GUI类"""
    
    def __init__(self, parent_frame, task_queue_manager, execution_manager, log_callback):
        self.parent_frame = parent_frame
        self.task_queue_manager = task_queue_manager
        self.execution_manager = execution_manager
        self.log_callback = log_callback
        
        # UI组件引用
        self.task_queue_listbox = None
        self.queue_info_label = None
        self.execution_count_var = None
        self.execution_count_entry = None
        self.infinite_loop_var = None
        self.llm_start_btn = None
        self.llm_stop_btn = None
        self.available_tasks_listbox = None
        self.available_tasks_label = None
        self.available_tasks_panel = None  # 可用任务面板
        self.add_task_btn = None
        
        # 拖拽排序相关变量
        self.drag_start_index = None
        self.drag_data = None
        self._original_drag_index = None
        
        # 可用任务列表数据缓存
        self.available_tasks_cache = []
        
        # 跨列表拖拽相关变量
        self.cross_drag_source = None  # 'available' 或 'queue'
        self.cross_drag_task_data = None
        
        # 可用任务面板展开状态
        self.available_panel_expanded = False
        
        self.setup_ui()
        # 初始化后更新任务队列显示
        self.update_queue_display()
        
    def setup_ui(self):
        """设置任务管理UI - 可折叠的可用任务面板，右侧任务队列"""
        # 主容器
        self.main_container = ttk.Frame(self.parent_frame)
        self.main_container.pack(fill='both', expand=True)
        
        # 可用任务面板（可折叠，默认隐藏）
        self.available_tasks_panel = ttk.LabelFrame(self.main_container, text="可用任务 (双击或拖拽添加)", padding="6")
        # 初始不显示 - 不调用pack
        
        # 可用任务列表容器
        available_list_container = ttk.Frame(self.available_tasks_panel)
        available_list_container.pack(fill='both', expand=True)
        
        available_scrollbar = ttk.Scrollbar(available_list_container, orient="vertical")
        available_scrollbar.pack(side=tk.RIGHT, fill='y')
        
        self.available_tasks_listbox = tk.Listbox(
            available_list_container,
            width=25,
            height=10,
            yscrollcommand=available_scrollbar.set
        )
        configure_listbox(self.available_tasks_listbox)
        self.available_tasks_listbox.pack(side=tk.LEFT, fill='both', expand=True)
        available_scrollbar.config(command=self.available_tasks_listbox.yview)
        
        # 可用任务列表信息
        self.available_tasks_label = ttk.Label(self.available_tasks_panel, text="可用: 0个任务", style='Muted.TLabel')
        self.available_tasks_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 关闭按钮
        close_btn = ttk.Button(self.available_tasks_panel, text="收起", command=self.toggle_available_panel, style='Outline.TButton')
        close_btn.pack(anchor=tk.W, pady=(5, 0))
        
        # 绑定可用任务列表事件（双击添加和拖拽开始）
        self.available_tasks_listbox.bind('<Double-Button-1>', self.on_available_task_double_click)
        self.available_tasks_listbox.bind('<Button-1>', self.on_available_drag_start)
        self.available_tasks_listbox.bind('<B1-Motion>', self.on_cross_drag_motion)
        self.available_tasks_listbox.bind('<ButtonRelease-1>', self.on_cross_drag_release)
        
        # 任务队列和执行控制区域
        self.right_frame = ttk.Frame(self.main_container)
        self.right_frame.pack(fill='both', expand=True)
        
        # 任务队列管理
        task_queue_frame = ttk.LabelFrame(self.right_frame, text="任务队列 (拖拽排序)", padding="6")
        task_queue_frame.pack(fill='both', expand=True)
        
        # 任务队列列表
        list_container = ttk.Frame(task_queue_frame)
        list_container.pack(fill='both', expand=True, pady=(0, 5))
        
        scrollbar = ttk.Scrollbar(list_container, orient="vertical")
        scrollbar.pack(side=tk.RIGHT, fill='y')
        
        self.task_queue_listbox = tk.Listbox(
            list_container,
            height=12,
            yscrollcommand=scrollbar.set
        )
        configure_listbox(self.task_queue_listbox)
        self.task_queue_listbox.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.config(command=self.task_queue_listbox.yview)
        
        # 绑定拖拽排序事件和接收拖入事件
        self.task_queue_listbox.bind('<Button-1>', self.on_queue_drag_start)
        self.task_queue_listbox.bind('<B1-Motion>', self.on_drag_motion)
        self.task_queue_listbox.bind('<ButtonRelease-1>', self.on_drag_release)
        
        # 队列信息显示
        self.queue_info_label = ttk.Label(task_queue_frame, text="队列: 0个任务", style='Muted.TLabel')
        self.queue_info_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 任务队列操作按钮
        queue_btn_frame = ttk.Frame(self.right_frame)
        queue_btn_frame.pack(fill='x', pady=(6, 0))
        
        self.add_task_btn = ttk.Button(queue_btn_frame, text="添加任务", command=self.toggle_available_panel, style='Primary.TButton')
        self.add_task_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        edit_task_btn = ttk.Button(queue_btn_frame, text="设置选中", command=self.show_edit_task_dialog, style='Outline.TButton')
        edit_task_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        delete_task_btn = ttk.Button(queue_btn_frame, text="删除选中", command=self.delete_selected_task, style='Danger.TButton')
        delete_task_btn.pack(side=tk.LEFT)
        
        # 执行控制
        exec_frame = ttk.LabelFrame(self.right_frame, text="执行控制", padding="6")
        exec_frame.pack(fill='x', pady=(6, 0))
        
        self.llm_start_btn = ttk.Button(exec_frame, text="▶ 启动推理", command=self.start_llm_execution, style='Success.TButton')
        self.llm_start_btn.pack(fill='x', pady=(0, 5))
        
        self.llm_stop_btn = ttk.Button(exec_frame, text="■ 停止执行", command=self.stop_llm_execution, style='Danger.TButton')
        self.llm_stop_btn.pack(fill='x', pady=(5, 0))
        self.llm_stop_btn.config(state='disabled')
        
        # 执行次数设置
        count_frame = ttk.Frame(exec_frame)
        count_frame.pack(fill='x', pady=(5, 0))
        ttk.Label(count_frame, text="执行次数:", style='Muted.TLabel').pack(side=tk.LEFT)
        self.execution_count_var = tk.IntVar(value=self.task_queue_manager.get_execution_count())
        execution_count_spinbox = ttk.Spinbox(count_frame, from_=1, to=99, textvariable=self.execution_count_var, width=5)
        execution_count_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        execution_count_spinbox.bind('<Return>', lambda e: self.on_execution_count_changed())
        execution_count_spinbox.bind('<FocusOut>', lambda e: self.on_execution_count_changed())
        self.execution_count_entry = execution_count_spinbox
        
        # 持续循环复选框
        self.infinite_loop_var = tk.BooleanVar(value=False)
        infinite_loop_check = ttk.Checkbutton(count_frame, text="持续循环", variable=self.infinite_loop_var, command=self.on_infinite_loop_changed)
        infinite_loop_check.pack(side=tk.LEFT, padx=(10, 0))
        
    def toggle_available_panel(self):
        """切换可用任务面板的展开/收起状态"""
        if self.available_panel_expanded:
            # 收起面板
            self.available_tasks_panel.pack_forget()
            self.available_panel_expanded = False
            self.add_task_btn.config(text="添加任务")
        else:
            # 展开面板
            if not self.execution_manager.auth_manager.get_login_status():
                messagebox.showwarning("未登录", "请先登录后再添加任务")
                return
            # 将面板放在左侧，在right_frame之前
            self.available_tasks_panel.pack(side=tk.LEFT, fill='both', expand=False, padx=(0, 5), before=self.right_frame)
            self.available_panel_expanded = True
            self.add_task_btn.config(text="收起面板")
            # 刷新可用任务列表
            self.refresh_available_tasks()
            
    def update_queue_display(self):
        """更新任务队列显示"""
        self.task_queue_listbox.delete(0, tk.END)
        queue_info = self.task_queue_manager.get_queue_info()
        for task in queue_info['tasks']:
            self.task_queue_listbox.insert(tk.END, f"{task.get('name', 'Unknown')}")
        self.queue_info_label.config(text=f"队列: {queue_info['count']}个任务")
        
        
    def show_edit_task_dialog(self):
        """显示编辑任务对话框"""
        selection = self.task_queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个任务")
            return
            
        task_index = selection[0]
        task = self.task_queue_manager.get_queue_info()['tasks'][task_index]
        task_id = task.get('id', '')
        
        # 从服务器获取最新的任务定义
        latest_task_def = self.get_task_definition_from_server(task_id)
        if latest_task_def:
            # 使用服务器最新的变量定义
            variables = latest_task_def.get('variables', [])
            # 保留用户已缓存的自定义变量值
            cached_variables = task.get('custom_variables', {})
            # 同步更新队列中的任务定义
            task['variables'] = variables
        else:
            # 如果获取失败，使用本地缓存的数据
            variables = task.get('variables', [])
            cached_variables = task.get('custom_variables', {})
        
        # 创建对话框
        dialog = tk.Toplevel(self.parent_frame.winfo_toplevel())
        dialog.title("设置任务")
        dialog.geometry("400x300")
        dialog.transient(self.parent_frame.winfo_toplevel())
        dialog.grab_set()
        
        # 任务名称
        ttk.Label(dialog, text="任务名称:", style='Header.TLabel').pack(pady=(10, 5))
        name_var = tk.StringVar(value=task.get('custom_name', task.get('name', '')))
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.pack(pady=5)
        
        # 仅执行一次选项
        execute_once_var = tk.BooleanVar(value=task.get('execute_once', False))
        execute_once_check = ttk.Checkbutton(dialog, text="仅执行一次（在多轮循环中只执行一次）", variable=execute_once_var)
        execute_once_check.pack(pady=(5, 10), anchor=tk.W)
        
        # 任务变量
        ttk.Label(dialog, text="任务变量:", style='Header.TLabel').pack(pady=(10, 5))
        
        variables_frame = ttk.Frame(dialog)
        variables_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        variable_entries = {}
        
        for var_def in variables:
            var_name = var_def.get('name', '')
            var_type = var_def.get('type', 'string')
            var_default = var_def.get('default', '')
            var_desc = var_def.get('desc', '')
            var_options = var_def.get('options', [])
            
            # 优先使用用户缓存值，否则使用默认值
            current_value = cached_variables.get(var_name, var_default)
            
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
            elif var_type == 'select' and var_options:
                # select类型，使用下拉选择框
                # 如果当前值不在新选项中，使用第一个选项或默认值
                if current_value not in var_options:
                    current_value = var_options[0] if var_options else var_default
                var_var = tk.StringVar(value=str(current_value) if current_value else (var_options[0] if var_options else ''))
                var_entry = ttk.Combobox(var_frame, textvariable=var_var, values=var_options, width=15, state='readonly')
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
                
            # 更新任务队列中的任务
            queue_info = self.task_queue_manager.get_queue_info()
            queue_info['tasks'][task_index]['custom_name'] = new_name
            queue_info['tasks'][task_index]['name'] = new_name
            queue_info['tasks'][task_index]['execute_once'] = execute_once_var.get()
            
            # 同步最新的变量定义到任务对象
            queue_info['tasks'][task_index]['variables'] = variables
            
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
                    
            queue_info['tasks'][task_index]['custom_variables'] = custom_vars
            
            # 保存到本地持久化存储
            self.task_queue_manager.save_task_queue()
            
            self.update_queue_display()
            self.log_callback(f"任务 '{new_name}' 已更新", "task", "INFO")
            dialog.destroy()
            
        def on_cancel():
            dialog.destroy()
            
        # 按钮
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="保存", command=on_save, style='Primary.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
    def sync_all_tasks_definitions_from_server(self) -> bool:
        """
        从服务器同步所有队列任务的最新定义（启动时调用）
        
        Returns:
            同步是否成功
        """
        if not self.execution_manager.auth_manager.get_login_status():
            return False
            
        if not self.execution_manager.communicator:
            self.log_callback("通信模块未初始化", "task", "ERROR")
            return False
        
        queue_info = self.task_queue_manager.get_queue_info()
        task_ids = [task.get('id', '') for task in queue_info['tasks'] if task.get('id')]
        
        if not task_ids:
            return True  # 无需同步
        
        try:
            # 批量请求所有任务定义
            response = self.execution_manager.communicator.send_request(
                "sync_all_tasks_definitions",
                {"task_ids": task_ids}
            )
            
            if response and response.get('status') == 'success':
                tasks_map = response.get('tasks', {})
                updated_count = 0
                
                # 更新队列中每个任务的变量定义
                for task in queue_info['tasks']:
                    task_id = task.get('id', '')
                    if task_id in tasks_map:
                        latest_def = tasks_map[task_id]
                        # 更新variables定义
                        task['variables'] = latest_def.get('variables', [])
                        updated_count += 1
                
                # 保存更新后的队列
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
        """
        从服务器获取指定任务的最新定义（编辑时调用）
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务定义字典或None（如果获取失败）
        """
        if not self.execution_manager.auth_manager.get_login_status():
            return None
            
        if not self.execution_manager.communicator:
            self.log_callback("通信模块未初始化", "task", "ERROR")
            return None
            
        try:
            # 发送请求获取任务定义
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
            # 发送请求获取默认任务（可用任务）
            response = self.execution_manager.communicator.send_request("get_default_tasks", {})
            if response and response.get('status') == 'success':
                tasks = response.get('tasks', [])
                # 过滤掉不可见的任务
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
            # 如果没有提供任务模板，不执行任何操作
            return
        else:
            # 添加指定的任务模板
            import time
            # 创建新的任务实例，使用带时间戳的ID确保队列中唯一性
            # 服务端会自动从ID中提取原始模板ID（格式: template_id_timestamp）
            new_task = task_template.copy()
            new_task['id'] = f"{task_template['id']}_{int(time.time())}"
            new_task['name'] = task_template.get('name', '新任务')
            new_task['custom_name'] = new_task['name']  # 用于自定义名称
            self.task_queue_manager.add_task(new_task)
            self.update_queue_display()
            self.log_callback(f"已添加任务 '{new_task['name']}' 到队列", "task", "INFO")
            # 保存到本地持久化存储
            self.task_queue_manager.save_task_queue()
        
    def remove_task_from_queue(self):
        """从队列中移除任务"""
        selection = self.task_queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个任务")
            return
            
        index = selection[0]
        removed_task = self.task_queue_manager.remove_task(index)
        if removed_task:
            self.update_queue_display()
            self.log_callback(f"任务 '{removed_task['name']}' 已从队列中移除", "execution", "INFO")
        
    def clear_task_queue(self):
        """清空任务队列"""
        if messagebox.askyesno("确认", "确定要清空任务队列吗？"):
            self.task_queue_manager.clear_queue()
            self.update_queue_display()
            self.log_callback("任务队列已清空", "execution", "INFO")
            
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
            # 禁用执行次数输入框
            self.execution_count_entry.config(state='disabled')
            self.task_queue_manager.set_execution_count(-1)  # -1表示无限循环
            self.log_callback("已启用持续循环模式", "execution", "INFO")
        else:
            # 启用执行次数输入框
            self.execution_count_entry.config(state='normal')
            count = self.execution_count_var.get()
            self.task_queue_manager.set_execution_count(count)
            self.log_callback(f"执行次数设置为: {count}", "execution", "INFO")
            
    def start_llm_execution(self):
        """开始LLM执行"""
        # 获取主GUI管理器以传递预览更新回调
        main_gui = None
        if hasattr(self.parent_frame, 'winfo_toplevel'):
            root = self.parent_frame.winfo_toplevel()
            if hasattr(root, 'gui_manager'):
                main_gui = root.gui_manager
        
        # 创建预览更新回调
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
            
    def get_current_task_index(self):
        """获取当前任务索引"""
        return self.task_queue_manager.get_queue_info()['current_index']
        
    def advance_to_next_task(self):
        """前进到下一个任务"""
        return self.task_queue_manager.advance_to_next_task()
        
    def reset_current_task_index(self):
        """重置当前任务索引"""
        self.task_queue_manager.reset_current_task_index()
        
    def is_queue_empty(self):
        """检查队列是否为空"""
        return self.task_queue_manager.is_queue_empty()
        
    def get_current_task(self):
        """获取当前任务"""
        return self.task_queue_manager.get_current_task()
        
    def get_execution_count(self):
        """获取执行次数"""
        return self.task_queue_manager.get_execution_count()
        
    def get_task_variables(self, task_id):
        """获取任务变量"""
        return self.task_queue_manager.get_task_variables(task_id)
        
    def delete_selected_task(self):
        """删除选中的任务（无需确认）"""
        selection = self.task_queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个任务")
            return
            
        task_index = selection[0]
        removed_task = self.task_queue_manager.remove_task(task_index)
        if removed_task:
            self.update_queue_display()
            self.log_callback(f"任务 '{removed_task['name']}' 已从队列中删除", "task", "INFO")
            # 保存到本地持久化存储
            self.task_queue_manager.save_task_queue()
    
    def refresh_available_tasks(self):
        """刷新可用任务列表"""
        if not self.execution_manager.auth_manager.get_login_status():
            self.available_tasks_listbox.delete(0, tk.END)
            self.available_tasks_listbox.insert(tk.END, "请先登录...")
            self.available_tasks_label.config(text="可用: 0个任务")
            self.available_tasks_cache = []
            return
            
        available_tasks = self.get_available_tasks_from_server()
        self.available_tasks_cache = available_tasks
        
        self.available_tasks_listbox.delete(0, tk.END)
        if not available_tasks:
            self.available_tasks_listbox.insert(tk.END, "暂无可用任务")
            self.available_tasks_label.config(text="可用: 0个任务")
        else:
            for task in available_tasks:
                self.available_tasks_listbox.insert(tk.END, f"{task.get('name', '未知任务')}")
            self.available_tasks_label.config(text=f"可用: {len(available_tasks)}个任务")
            
    def on_available_task_double_click(self, event):
        """双击可用任务添加到队列"""
        selection = self.available_tasks_listbox.curselection()
        if not selection or not self.available_tasks_cache:
            return
            
        selected_task = self.available_tasks_cache[selection[0]]
        self.add_task_to_queue(selected_task)
        self.log_callback(f"已添加任务 '{selected_task.get('name', '未知任务')}' 到队列", "task", "INFO")
        
    def on_available_drag_start(self, event):
        """从可用任务列表开始拖拽"""
        self.cross_drag_source = 'available'
        self.drag_start_index = self.available_tasks_listbox.nearest(event.y)
        if self.available_tasks_cache and self.drag_start_index < len(self.available_tasks_cache):
            self.cross_drag_task_data = self.available_tasks_cache[self.drag_start_index]
        else:
            self.cross_drag_task_data = None
            
    def on_queue_drag_start(self, event):
        """从任务队列开始拖拽（内部排序）"""
        self.cross_drag_source = 'queue'
        self.drag_start_index = self.task_queue_listbox.nearest(event.y)
        self._original_drag_index = self.drag_start_index
        self.drag_data = self.task_queue_listbox.get(self.drag_start_index)
        self.cross_drag_task_data = None
        
    def on_cross_drag_motion(self, event):
        """跨列表拖拽移动事件处理"""
        if self.cross_drag_source == 'queue':
            # 任务队列内部拖拽排序
            if self.drag_start_index is None:
                return
            current_index = self.task_queue_listbox.nearest(event.y)
            if current_index != self.drag_start_index:
                self.task_queue_listbox.delete(self.drag_start_index)
                self.task_queue_listbox.insert(current_index, self.drag_data)
                self.drag_start_index = current_index
        elif self.cross_drag_source == 'available':
            # 从可用任务列表拖拽到任务队列
            # 检查鼠标是否在任务队列范围内
            try:
                queue_y = event.y_root - self.task_queue_listbox.winfo_rooty()
                if 0 <= queue_y <= self.task_queue_listbox.winfo_height():
                    # 鼠标在任务队列范围内，可以显示提示
                    pass
            except:
                pass
                
    def on_cross_drag_release(self, event):
        """跨列表拖拽释放事件处理"""
        if self.cross_drag_source == 'available' and self.cross_drag_task_data:
            # 从可用任务列表拖拽到任务队列
            try:
                queue_y = event.y_root - self.task_queue_listbox.winfo_rooty()
                if 0 <= queue_y <= self.task_queue_listbox.winfo_height():
                    # 添加任务到队列
                    self.add_task_to_queue(self.cross_drag_task_data)
                    self.log_callback(f"已拖拽添加任务 '{self.cross_drag_task_data.get('name', '未知任务')}' 到队列", "task", "INFO")
            except:
                pass
        elif self.cross_drag_source == 'queue':
            # 任务队列内部拖拽排序
            if self.drag_start_index is None:
                return
            final_index = self.drag_start_index
            self.update_queue_display()
            self.reorder_task_queue(self._original_drag_index, final_index)
            
        # 重置所有拖拽状态
        self.cross_drag_source = None
        self.cross_drag_task_data = None
        self.drag_start_index = None
        self.drag_data = None
        self._original_drag_index = None
        
    def on_drag_motion(self, event):
        """拖拽移动事件处理（任务队列内部排序）"""
        if self.drag_start_index is None:
            return
        # 获取当前鼠标位置对应的索引
        current_index = self.task_queue_listbox.nearest(event.y)
        if current_index != self.drag_start_index:
            # 临时显示拖拽效果
            self.task_queue_listbox.delete(self.drag_start_index)
            self.task_queue_listbox.insert(current_index, self.drag_data)
            self.drag_start_index = current_index
            
    def on_drag_release(self, event):
        """拖拽释放事件处理"""
        if self.drag_start_index is None:
            return
        # 获取最终位置（在拖拽过程中已经更新了显示，所以当前drag_start_index就是最终位置）
        final_index = self.drag_start_index
        # 获取原始起始位置（需要从任务队列数据中获取）
        # 由于拖拽过程中显示已经更新，我们需要使用保存的原始数据重新计算
        # 先恢复原始显示状态，再计算实际移动
        self.update_queue_display()
        # 执行实际的任务队列重排序
        self.reorder_task_queue(self._original_drag_index, final_index)
        # 重置拖拽状态
        self.drag_start_index = None
        self.drag_data = None
        self._original_drag_index = None
        
    def reorder_task_queue(self, from_index, to_index):
        """重新排序任务队列"""
        if from_index is None or to_index is None or from_index == to_index:
            return
        queue_info = self.task_queue_manager.get_queue_info()
        tasks = queue_info['tasks']
        if from_index < len(tasks) and to_index < len(tasks):
            # 移动任务
            task = tasks.pop(from_index)
            tasks.insert(to_index, task)
            # 保存到本地持久化存储
            self.task_queue_manager.save_task_queue()
            self.update_queue_display()
            self.log_callback(f"任务已从位置 {from_index+1} 移动到位置 {to_index+1}", "task", "INFO")