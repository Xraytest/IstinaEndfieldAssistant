import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
from .auth_manager_gui import AuthManagerGUI
from .device_manager_gui import DeviceManagerGUI
from .task_manager_gui import TaskManagerGUI
from .settings_manager_gui import SettingsManagerGUI
from .cloud_service_manager_gui import CloudServiceManagerGUI
from ..theme import configure_scrolledtext, configure_canvas, COLORS, get_font

class MainGUIManager:

    def __init__(self, root, auth_manager, device_manager, execution_manager, task_queue_manager, config, log_callback, client_main_ref=None):
        self.root = root
        self.auth_manager = auth_manager
        self.device_manager = device_manager
        self.execution_manager = execution_manager
        self.task_queue_manager = task_queue_manager
        self.config = config
        self.log_callback = log_callback
        self.client_main_ref = client_main_ref
        self.notebook = None
        self.execution_page_frame = None
        self.settings_page_frame = None
        self.cloud_service_page_frame = None
        self.status_bar = None
        self.content_notebook = None
        self.log_text = None
        self.current_task_label = None
        self.progress_label = None
        self.progress_var = None
        self.auth_gui = None
        self.device_gui = None
        self.task_gui = None
        self.settings_gui = None
        self.cloud_service_gui = None
        self.setup_main_ui()

    def setup_main_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=0, pady=0)
        self.execution_page_frame = ttk.Frame(self.notebook)
        self.settings_page_frame = ttk.Frame(self.notebook)
        self.cloud_service_page_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.execution_page_frame, text='一键长草')
        self.notebook.add(self.settings_page_frame, text='设置')
        self.notebook.add(self.cloud_service_page_frame, text='云服务')
        self._configure_notebook_tabs()
        self.status_bar = tk.Label(self.root, text='就绪', bg=COLORS['surface_container_low'], fg=COLORS['text_secondary'], font=get_font('body_small'), anchor=tk.W, padx=10, pady=4)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.setup_execution_page()
        self.setup_settings_page()
        self.setup_cloud_service_page()
        self.root.after(100, self.auto_scan_and_connect_devices)
        self.notebook.bind('<<NotebookTabChanged>>', self.on_notebook_tab_changed)

    def _configure_notebook_tabs(self):
        style = ttk.Style()
        style.configure('TNotebook.Tab', background=COLORS['surface'], foreground=COLORS['text_secondary'], font=get_font('body_medium', bold=True), padding=[20, 10], borderwidth=0)
        style.map('TNotebook.Tab', background=[('selected', COLORS['surface']), ('active', COLORS['surface'])], foreground=[('selected', COLORS['primary']), ('active', COLORS['text_primary'])], expand=[('selected', [0, 0, 0, 2])])
        style.configure('TNotebook', background=COLORS['surface'], borderwidth=0, tabmargins=[0, 0, 0, 0])

    def _bind_hover_effect(self, button, normal_bg, hover_bg, normal_fg, hover_fg):

        def on_enter(e):
            button.configure(bg=hover_bg, fg=hover_fg)

        def on_leave(e):
            button.configure(bg=normal_bg, fg=normal_fg)
        button.bind('<Enter>', on_enter)
        button.bind('<Leave>', on_leave)

    def _goto_task_settings(self):
        self.settings_notebook.select(self.task_settings_frame)

    def _on_task_settings_click(self, task_index):
        self._update_task_settings_content(task_index)
        self.settings_notebook.select(self.task_settings_frame)

    def _update_task_settings_content(self, task_index):
        if not hasattr(self, 'task_settings_content_frame'):
            return
        for widget in self.task_settings_content_frame.winfo_children():
            widget.destroy()
        if task_index < 0 or task_index >= len(self.task_queue_manager.get_queue_info()['tasks']):
            tk.Label(self.task_settings_content_frame, text='任务设置\n\n点击任务列表右侧的⚙️图标\n来配置单个任务', bg=COLORS['surface'], fg=COLORS['text_secondary'], font=get_font('body_medium'), justify=tk.CENTER).pack(expand=True)
            return
        task = self.task_queue_manager.get_queue_info()['tasks'][task_index]
        task_id = task.get('id', '')
        task_name = task.get('custom_name', task.get('name', '未知任务'))
        latest_task_def = self.task_gui.get_task_definition_from_server(task_id) if self.task_gui else None
        if latest_task_def:
            variables = latest_task_def.get('variables', [])
            cached_variables = task.get('custom_variables', {})
            task['variables'] = variables
        else:
            variables = task.get('variables', [])
            cached_variables = task.get('custom_variables', {})
        form_frame = tk.Frame(self.task_settings_content_frame, bg=COLORS['surface'])
        form_frame.pack(fill='both', expand=True, padx=15, pady=15)
        name_label = tk.Label(form_frame, text='任务名称', bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('title_small', bold=True))
        name_label.pack(pady=(0, 5), anchor=tk.W)
        name_var = tk.StringVar(value=task_name)
        name_entry = tk.Entry(form_frame, textvariable=name_var, bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('body_medium'), relief='solid', borderwidth=1, highlightbackground=COLORS['border_color'])
        name_entry.pack(fill='x', pady=(0, 10))
        execute_once_var = tk.BooleanVar(value=task.get('execute_once', False))
        execute_once_check = tk.Checkbutton(form_frame, text='仅执行一次（在多轮循环中只执行一次）', variable=execute_once_var, bg=COLORS['surface_container_low'], fg=COLORS['text_primary'], font=get_font('body_small'), selectcolor=COLORS['surface_container_low'], activebackground=COLORS['surface_container'], relief='solid', borderwidth=1)
        execute_once_check.pack(pady=(0, 10), anchor=tk.W)
        variable_entries = {}
        if variables:
            var_label = tk.Label(form_frame, text='任务变量', bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('title_small', bold=True))
            var_label.pack(pady=(10, 5), anchor=tk.W)
            for var_def in variables:
                var_name = var_def.get('name', '')
                var_type = var_def.get('type', 'string')
                var_default = var_def.get('default', '')
                var_options = var_def.get('options', [])
                current_value = cached_variables.get(var_name, var_default)
                var_frame = tk.Frame(form_frame, bg=COLORS['surface'])
                var_frame.pack(fill='x', pady=4)
                name_lbl = tk.Label(var_frame, text=f'{var_name}:', bg=COLORS['surface'], fg=COLORS['text_secondary'], font=get_font('body_small'))
                name_lbl.pack(side=tk.LEFT)
                if var_type == 'bool':
                    var_var = tk.BooleanVar(value=bool(current_value))
                    var_entry = tk.Checkbutton(var_frame, variable=var_var, bg=COLORS['surface_container_low'], selectcolor=COLORS['surface_container_low'], relief='solid', borderwidth=1)
                    var_entry.pack(side=tk.RIGHT)
                elif var_type == 'int':
                    var_var = tk.StringVar(value=str(current_value))
                    var_entry = tk.Entry(var_frame, textvariable=var_var, width=10, bg=COLORS['surface'], fg=COLORS['text_primary'], relief='solid', borderwidth=1)
                    var_entry.pack(side=tk.RIGHT)
                elif var_type == 'select' and var_options:
                    if current_value not in var_options:
                        current_value = var_options[0] if var_options else var_default
                    var_var = tk.StringVar(value=str(current_value))
                    var_entry = ttk.Combobox(var_frame, textvariable=var_var, values=var_options, width=15, state='readonly')
                    var_entry.pack(side=tk.RIGHT)
                else:
                    var_var = tk.StringVar(value=str(current_value))
                    var_entry = tk.Entry(var_frame, textvariable=var_var, width=20, bg=COLORS['surface'], fg=COLORS['text_primary'], relief='solid', borderwidth=1)
                    var_entry.pack(side=tk.RIGHT)
                variable_entries[var_name] = (var_var, var_type)

        def on_save():
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showwarning('警告', '任务名称不能为空')
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
            self.task_gui.update_queue_display()
            self.log_callback(f"任务 '{new_name}' 已更新", 'task', 'INFO')
        save_btn = tk.Button(form_frame, text='保存设置', command=on_save, bg=COLORS['surface_container_low'], fg=COLORS['text_primary'], font=get_font('body_medium', bold=True), relief='solid', borderwidth=1, padx=20, pady=8, cursor='hand2')
        save_btn.pack(pady=(15, 0), anchor=tk.E)
        self._bind_hover_effect(save_btn, COLORS['surface_container_low'], COLORS['surface_container'], COLORS['text_primary'], COLORS['text_primary'])

    def _configure_execution_settings_notebook(self):
        style = ttk.Style()
        style.configure('ExecutionSettings.TNotebook.Tab', background=COLORS['surface_container_low'], foreground=COLORS['text_secondary'], font=get_font('body_medium', bold=True), padding=[20, 8], borderwidth=0)
        style.map('ExecutionSettings.TNotebook.Tab', background=[('selected', COLORS['surface']), ('active', COLORS['surface_container_low'])], foreground=[('selected', COLORS['primary']), ('active', COLORS['text_primary'])])
        self.settings_notebook.configure(style='ExecutionSettings.TNotebook')

    def _configure_settings_notebook(self):
        style = ttk.Style()
        style.configure('Settings.TNotebook.Tab', background=COLORS['surface_container_low'], foreground=COLORS['text_secondary'], font=get_font('body_medium', bold=True), padding=[20, 8], borderwidth=0)
        style.map('Settings.TNotebook.Tab', background=[('selected', COLORS['surface']), ('active', COLORS['surface_container_low'])], foreground=[('selected', COLORS['primary']), ('active', COLORS['text_primary'])])
        self.settings_notebook.configure(style='Settings.TNotebook')

    def setup_execution_page(self):
        main_frame = tk.Frame(self.execution_page_frame, bg=COLORS['surface'])
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        content_frame = tk.Frame(main_frame, bg=COLORS['surface'])
        content_frame.pack(fill='both', expand=True)
        left_frame = tk.Frame(content_frame, bg=COLORS['surface'], width=280)
        left_frame.pack(side=tk.LEFT, fill='y', padx=(0, 0))
        left_frame.pack_propagate(False)
        left_separator = tk.Frame(content_frame, bg=COLORS['border_color'], width=1)
        left_separator.pack(side=tk.LEFT, fill='y', padx=0)
        center_frame = tk.Frame(content_frame, bg=COLORS['surface'])
        center_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=(10, 0))
        center_separator = tk.Frame(content_frame, bg=COLORS['border_color'], width=1)
        center_separator.pack(side=tk.LEFT, fill='y', padx=(10, 0))
        right_frame = tk.Frame(content_frame, bg=COLORS['surface'], width=350)
        right_frame.pack(side=tk.RIGHT, fill='y', padx=(10, 0))
        right_frame.pack_propagate(False)
        self.task_gui = TaskManagerGUI(left_frame, self.task_queue_manager, self.execution_manager, self.log_callback, on_task_settings_click=self._on_task_settings_click, get_device_type_callback=self._get_current_device_type)
        self.settings_notebook = ttk.Notebook(center_frame)
        self.settings_notebook.pack(fill='both', expand=True, padx=0, pady=0)
        self.device_settings_frame = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(self.device_settings_frame, text='设备设置')
        self.task_settings_frame = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(self.task_settings_frame, text='任务设置')
        self._configure_execution_settings_notebook()
        self.task_settings_content_frame = tk.Frame(self.task_settings_frame, bg=COLORS['surface'])
        self.task_settings_content_frame.pack(fill='both', expand=True, padx=20, pady=20)
        tk.Label(self.task_settings_content_frame, text='任务设置\n\n点击任务列表右侧的⚙️图标\n来配置单个任务', bg=COLORS['surface'], fg=COLORS['text_secondary'], font=get_font('body_medium'), justify=tk.CENTER).pack(expand=True)
        self.device_settings_gui = DeviceManagerGUI(self.device_settings_frame, self.device_manager, self.execution_manager.screen_capture, self.log_callback, execution_manager=self.execution_manager)
        self.device_gui = self.device_settings_gui
        self.settings_notebook.select(self.device_settings_frame)
        self._setup_log_panel(right_frame)
        self.root.after(200, lambda: self._sync_tasks_on_startup())

    def _setup_log_panel(self, parent):
        log_header = tk.Label(parent, text='📋 执行日志', bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('title_medium', bold=True), anchor=tk.W)
        log_header.pack(fill='x', pady=(0, 8))
        self.log_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('body_small'), padx=8, pady=8, relief='solid', borderwidth=1, highlightthickness=0)
        self.log_text.pack(fill='both', expand=True)
        self.log_text.configure(selectbackground=COLORS['selection_bg'], selectforeground=COLORS['text_primary'])

    def setup_settings_page(self):
        self.settings_gui = SettingsManagerGUI(self.settings_page_frame, self.config, self.log_callback, self.client_main_ref)

    def setup_cloud_service_page(self):
        self.cloud_service_gui = CloudServiceManagerGUI(self.cloud_service_page_frame, self.auth_manager, self.log_callback)

    def on_notebook_tab_changed(self, event):
        selected_tab = self.notebook.select()
        if selected_tab == str(self.cloud_service_page_frame):
            if self.auth_manager.get_login_status():
                self.cloud_service_gui.refresh_user_info()

    def get_log_text_widget(self):
        return self.log_text

    def update_current_task_display(self, task_name):
        self.current_task_label.config(text=f'当前任务: {task_name}')

    def update_progress_display(self, current, total):
        self.progress_var.set(f'进度: {current}/{total}')

    def _sync_tasks_on_startup(self):
        if self.task_gui and hasattr(self.task_gui, 'sync_all_tasks_definitions_from_server'):
            self.task_gui.sync_all_tasks_definitions_from_server()

    def auto_scan_and_connect_devices(self):
        try:
            if self.device_gui:
                self.device_gui.scan_devices()
            last_device = self.device_manager.get_last_connected_device()
            if not last_device:
                self.log_callback('没有上次连接的设备记录，跳过自动连接', 'device', 'INFO')
                return
            current_device = self.device_manager.get_current_device()
            if current_device:
                self.log_callback(f'已有设备连接: {current_device}，跳过自动连接', 'device', 'INFO')
                return
            self.log_callback(f'尝试自动连接上次设备: {last_device}', 'device', 'INFO')
            if self.device_manager.connect_device_manual(last_device):
                if self.device_gui:
                    self.device_gui.update_device_status(f'已连接: {last_device}', 'green')
                    self.device_gui.start_preview_refresh()
                self.log_callback(f'自动连接到上次的设备: {last_device}', 'device', 'INFO')
            else:
                self.log_callback(f'连接上次设备 {last_device} 失败', 'device', 'ERROR')
        except Exception as e:
            self.log_callback(f'自动扫描和连接设备时出错: {e}', 'device', 'ERROR')

    def _get_current_device_type(self):
        if hasattr(self, 'device_settings_gui') and self.device_settings_gui and hasattr(self.device_settings_gui, 'device_type_var'):
            return self.device_settings_gui.device_type_var.get()
        return None

    def stop_execution_ui(self):
        if self.task_gui:
            self.task_gui.llm_start_btn.config(state='normal')
            self.task_gui.llm_stop_btn.config(state='disabled')

    def on_preview_update(self, screen_data):
        if self.device_gui:
            self.device_gui.update_screen_preview(screen_data)