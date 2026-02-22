"""任务管理GUI模块 - 处理任务队列和执行控制的UI逻辑"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json


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
        self.llm_start_btn = None
        self.llm_stop_btn = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置任务管理UI"""
        # 任务队列管理
        task_queue_frame = ttk.LabelFrame(self.parent_frame, text="任务队列", padding="10")
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
        queue_btn_frame = ttk.Frame(self.parent_frame)
        queue_btn_frame.pack(fill='x', pady=(10, 0))
        
        add_task_btn = ttk.Button(queue_btn_frame, text="添加任务", command=self.show_add_task_dialog)
        add_task_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        edit_task_btn = ttk.Button(queue_btn_frame, text="设置选中", command=self.show_edit_task_dialog)
        edit_task_btn.pack(side=tk.LEFT)
        
        # 执行控制
        exec_frame = ttk.LabelFrame(self.parent_frame, text="执行控制", padding="10")
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
        self.execution_count_var = tk.IntVar(value=self.task_queue_manager.get_execution_count())
        execution_count_spinbox = ttk.Spinbox(count_frame, from_=1, to=99, textvariable=self.execution_count_var, width=5)
        execution_count_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        execution_count_spinbox.bind('<Return>', lambda e: self.on_execution_count_changed())
        execution_count_spinbox.bind('<FocusOut>', lambda e: self.on_execution_count_changed())
        self.execution_count_entry = execution_count_spinbox
        
    def update_queue_display(self):
        """更新任务队列显示"""
        self.task_queue_listbox.delete(0, tk.END)
        queue_info = self.task_queue_manager.get_queue_info()
        for task in queue_info['tasks']:
            self.task_queue_listbox.insert(tk.END, f"{task.get('name', 'Unknown')}")
        self.queue_info_label.config(text=f"队列: {queue_info['count']}个任务")
        
    def show_add_task_dialog(self):
        """显示添加任务对话框"""
        if not self.execution_manager.auth_manager.get_login_status():
            messagebox.showwarning("未登录", "请先登录后再添加任务")
            return
            
        # 从服务器获取可用任务
        available_tasks = self.get_available_tasks_from_server()
        if not available_tasks:
            messagebox.showinfo("提示", "暂无可用任务")
            return
            
        # 创建对话框
        dialog = tk.Toplevel(self.parent_frame.winfo_toplevel())
        dialog.title("添加任务")
        dialog.geometry("500x400")
        dialog.transient(self.parent_frame.winfo_toplevel())
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
        task = self.task_queue_manager.get_queue_info()['tasks'][task_index]
        
        # 创建对话框
        dialog = tk.Toplevel(self.parent_frame.winfo_toplevel())
        dialog.title("设置任务")
        dialog.geometry("400x300")
        dialog.transient(self.parent_frame.winfo_toplevel())
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
                
            # 更新任务队列中的任务
            queue_info = self.task_queue_manager.get_queue_info()
            queue_info['tasks'][task_index]['custom_name'] = new_name
            queue_info['tasks'][task_index]['name'] = new_name
            
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
        
        ttk.Button(btn_frame, text="保存", command=on_save, style='Action.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
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
            # 如果没有提供任务模板，使用默认任务
            tasks = self.task_queue_manager.load_default_tasks()
            if not tasks:
                self.log_callback("未找到默认任务", "execution", "WARNING")
                return
                
            for task in tasks:
                self.task_queue_manager.add_task(task)
            self.update_queue_display()
            self.log_callback(f"已添加 {len(tasks)} 个默认任务到队列", "execution", "INFO")
            # 保存到本地持久化存储
            self.task_queue_manager.save_task_queue()
        else:
            # 添加指定的任务模板
            import time
            # 创建新的任务实例，使用不同的ID但相同的模板
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
            
    def start_llm_execution(self):
        """开始LLM执行"""
        success, message = self.execution_manager.start_execution(
            self.log_callback,
            self.update_ui_callback
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