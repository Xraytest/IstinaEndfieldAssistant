"""任务队列UI组件"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

class TaskQueueUI:
    """任务队列UI类"""
    
    def __init__(self, parent_frame, task_queue_manager, log_callback):
        self.parent_frame = parent_frame
        self.task_queue_manager = task_queue_manager
        self.log_callback = log_callback
        
        # UI组件引用
        self.task_queue_listbox = None
        self.queue_info_label = None
        self.execution_count_var = None
        self.execution_count_entry = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置任务队列UI"""
        # 左右分栏
        paned = ttk.PanedWindow(self.parent_frame, orient=tk.HORIZONTAL)
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
        
    def update_queue_display(self):
        """更新任务队列显示"""
        self.task_queue_listbox.delete(0, tk.END)
        queue_info = self.task_queue_manager.get_queue_info()
        for task in queue_info['tasks']:
            self.task_queue_listbox.insert(tk.END, f"{task.get('name', 'Unknown')}")
        self.queue_info_label.config(text=f"队列: {queue_info['count']}个任务")
        
    def add_default_tasks(self):
        """添加默认任务到队列"""
        tasks = self.task_queue_manager.load_default_tasks()
        if tasks:
            self.update_queue_display()
            self.log_callback(f"已添加 {len(tasks)} 个默认任务到队列", "execution", "INFO")
        else:
            self.log_callback("未找到默认任务", "execution", "WARNING")
            
    def remove_selected_task(self):
        """移除选中的任务"""
        selection = self.task_queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个任务")
            return
            
        index = selection[0]
        removed_task = self.task_queue_manager.remove_task(index)
        if removed_task:
            self.update_queue_display()
            self.log_callback(f"任务 '{removed_task['name']}' 已从队列中移除", "execution", "INFO")
            
    def clear_queue(self):
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
            
    def get_log_text_widget(self):
        """获取日志文本控件"""
        return self.log_text
        
    def get_full_content_text_widget(self):
        """获取完整上下文文本控件"""
        return self.full_content_text
        
    def get_vision_canvas(self):
        """获取设备视觉画布"""
        return self.vision_canvas
        
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