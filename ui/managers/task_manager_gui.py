import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from ..theme import configure_listbox, COLORS, get_font, CORNER_RADIUS

class TaskManagerGUI:

    def __init__(self, parent_frame, task_queue_manager, execution_manager, log_callback, on_task_settings_click=None, get_device_type_callback=None):
        self.parent_frame = parent_frame
        self.task_queue_manager = task_queue_manager
        self.execution_manager = execution_manager
        self.log_callback = log_callback
        self.on_task_settings_click = on_task_settings_click
        self.get_device_type_callback = get_device_type_callback
        self.task_frame = None
        self.task_canvas = None
        self.task_inner_frame = None
        self.task_items = {}
        self.selected_task_index = -1
        self.dragging = False
        self.dragged_index = -1
        self.dragged_widget = None
        self.drag_ghost = None
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
        self.task_frame = tk.Frame(self.parent_frame, bg=COLORS['surface'], highlightbackground=COLORS['border_color'], highlightthickness=1)
        self.task_frame.pack(fill='both', expand=True)
        header_frame = tk.Frame(self.task_frame, bg=COLORS['surface'], height=40)
        header_frame.pack(fill='x', padx=0, pady=0)
        header_frame.pack_propagate(False)
        title_label = tk.Label(header_frame, text='任务队列', bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('title_medium', bold=True), anchor=tk.W)
        title_label.pack(side=tk.LEFT, fill='y', padx=12, pady=8)
        hint_label = tk.Label(header_frame, text='(可拖拽排序)', bg=COLORS['surface'], fg=COLORS['text_muted'], font=get_font('body_small'), anchor=tk.W)
        hint_label.pack(side=tk.LEFT, fill='y', padx=(5, 0), pady=10)
        list_container = tk.Frame(self.task_frame, bg=COLORS['surface'])
        list_container.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        self.task_canvas = tk.Canvas(list_container, bg=COLORS['surface'], highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(list_container, orient='vertical', command=self.task_canvas.yview)
        self.task_canvas.configure(yscrollcommand=scrollbar.set)
        self.task_canvas.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.pack(side=tk.RIGHT, fill='y')
        self.task_inner_frame = tk.Frame(self.task_canvas, bg=COLORS['surface'])
        self.canvas_window = self.task_canvas.create_window((0, 0), window=self.task_inner_frame, anchor='nw', width=250)
        self.task_inner_frame.bind('<Configure>', self._on_frame_configure)
        self.task_canvas.bind('<Configure>', self._on_canvas_configure)
        self.queue_info_label = tk.Label(self.task_frame, text='队列: 0个任务', bg=COLORS['surface'], fg=COLORS['text_secondary'], font=get_font('body_small'), anchor=tk.W)
        self.queue_info_label.pack(fill='x', padx=12, pady=(0, 8))
        btn_frame = tk.Frame(self.parent_frame, bg=COLORS['surface'])
        btn_frame.pack(fill='x', pady=(10, 0))
        add_task_btn = ttk.Button(btn_frame, text='+ 添加任务', command=self.show_add_task_dialog, style='Primary.TButton')
        add_task_btn.pack(fill='x', pady=(0, 6))
        delete_task_btn = ttk.Button(btn_frame, text='删除', command=self.delete_selected_task, style='OutlineDanger.TButton')
        delete_task_btn.pack(fill='x', pady=(0, 6))
        exec_frame = tk.Frame(self.parent_frame, bg=COLORS['surface'])
        exec_frame.pack(fill='x', pady=(15, 0))
        exec_title = tk.Label(exec_frame, text='执行控制', bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('title_medium', bold=True), anchor=tk.W)
        exec_title.pack(fill='x', pady=(0, 8))
        self.llm_start_btn = ttk.Button(exec_frame, text='▶ 启动', command=self.start_llm_execution, style='Success.TButton')
        self.llm_start_btn.pack(fill='x', pady=(0, 6))
        self.llm_stop_btn = ttk.Button(exec_frame, text='■ 停止', command=self.stop_llm_execution, style='Danger.TButton')
        self.llm_stop_btn.pack(fill='x', pady=(0, 6))
        count_frame = tk.Frame(exec_frame, bg=COLORS['surface'])
        count_frame.pack(fill='x', pady=(8, 0))
        count_label = tk.Label(count_frame, text='执行次数:', bg=COLORS['surface'], fg=COLORS['text_secondary'], font=get_font('body_small'))
        count_label.pack(side=tk.LEFT)
        self.execution_count_var = tk.IntVar(value=self.task_queue_manager.get_execution_count())
        execution_count_spinbox = tk.Spinbox(count_frame, from_=1, to=99, textvariable=self.execution_count_var, width=5, bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('body_medium'), relief='solid', borderwidth=1, highlightbackground=COLORS['border_color'])
        execution_count_spinbox.pack(side=tk.LEFT, padx=(8, 0))
        execution_count_spinbox.bind('<Return>', lambda e: self.on_execution_count_changed())
        execution_count_spinbox.bind('<FocusOut>', lambda e: self.on_execution_count_changed())
        self.execution_count_entry = execution_count_spinbox
        self.infinite_loop_var = tk.BooleanVar(value=False)
        infinite_loop_check = tk.Checkbutton(count_frame, text='持续循环', variable=self.infinite_loop_var, command=self.on_infinite_loop_changed, bg=COLORS['surface_container_low'], fg=COLORS['text_primary'], font=get_font('body_small'), selectcolor=COLORS['surface_container_low'], activebackground=COLORS['surface_container'], activeforeground=COLORS['text_primary'], relief='solid', borderwidth=1)
        infinite_loop_check.pack(side=tk.LEFT, padx=(15, 0))

    def _bind_hover_effect(self, button, normal_bg, hover_bg, normal_fg, hover_fg):

        def on_enter(e):
            button.configure(bg=hover_bg, fg=hover_fg)

        def on_leave(e):
            button.configure(bg=normal_bg, fg=normal_fg)
        button.bind('<Enter>', on_enter)
        button.bind('<Leave>', on_leave)

    def _on_frame_configure(self, event=None):
        self.task_canvas.configure(scrollregion=self.task_canvas.bbox('all'))

    def _on_canvas_configure(self, event=None):
        self.task_canvas.itemconfig(self.canvas_window, width=event.width)

    def _check_task_compatibility(self, task):
        current_device_type = None
        if self.get_device_type_callback:
            current_device_type = self.get_device_type_callback()
        if not current_device_type:
            return (True, '')
        device_to_platform = {'安卓': 'android', 'PC': 'pc'}
        current_platform = device_to_platform.get(current_device_type, '')
        platforms = task.get('platforms', {})
        if platforms:
            if current_platform in platforms:
                return (True, platforms[current_platform].get('name', ''))
            else:
                available_platforms = list(platforms.keys())
                return (False, f"仅支持: {', '.join([platforms[p].get('name', p) for p in available_platforms])}")
        controller_types = task.get('controller_types', [])
        if controller_types:
            if current_device_type == '安卓':
                is_compatible = 'ADB' in controller_types
                if not is_compatible:
                    return (False, '仅支持: PC版')
            elif current_device_type == 'PC':
                pc_types = ['Win32', 'Win32-Window', 'Win32-Front']
                is_compatible = any((ct in controller_types for ct in pc_types))
                if not is_compatible:
                    return (False, '仅支持: 安卓版')
            return (True, '')
        return (True, '')

    def update_queue_display(self):
        for widget in self.task_inner_frame.winfo_children():
            widget.destroy()
        self.task_items.clear()
        queue_info = self.task_queue_manager.get_queue_info()
        tasks = queue_info['tasks']
        for idx, task in enumerate(tasks):
            task_name = task.get('name', 'Unknown')
            is_compatible, platform_info = self._check_task_compatibility(task)
            task_row = tk.Frame(self.task_inner_frame, bg=COLORS['surface'], highlightbackground=COLORS['border_color'], highlightthickness=0)
            task_row.pack(fill='x', pady=1)
            if idx > 0:
                separator = tk.Frame(task_row, bg=COLORS['border_color'], height=1)
                separator.pack(fill='x', side=tk.TOP)
            content_frame = tk.Frame(task_row, bg=COLORS['surface'], height=36)
            content_frame.pack(fill='x', pady=2)
            content_frame.pack_propagate(False)
            if not is_compatible:
                compat_label = tk.Label(content_frame, text='⚠️', bg=COLORS['surface'], fg=COLORS['warning'], font=get_font('body_small'), cursor='hand2')
                compat_label.pack(side=tk.LEFT, padx=(6, 0))
                self._create_tooltip(compat_label, f'不兼容: {platform_info}')
            else:
                compat_spacer = tk.Label(content_frame, text='', bg=COLORS['surface'], width=2)
                compat_spacer.pack(side=tk.LEFT, padx=(6, 0))
            drag_handle = tk.Label(content_frame, text='☰', bg=COLORS['surface'], fg=COLORS['text_muted'], font=get_font('body_small'), cursor='hand2', width=2)
            drag_handle.pack(side=tk.LEFT, padx=(0, 2))
            index_label = tk.Label(content_frame, text=f'{idx + 1}.', bg=COLORS['surface'], fg=COLORS['text_muted'], font=get_font('body_small'), width=3, anchor=tk.E)
            index_label.pack(side=tk.LEFT, padx=(2, 4))
            var = tk.BooleanVar(value=idx == self.selected_task_index)
            task_label = tk.Label(content_frame, text=task_name, bg=COLORS['surface'], fg=COLORS['text_muted'] if not is_compatible else COLORS['text_primary'], font=get_font('body_medium'), anchor=tk.W)
            task_label.pack(side=tk.LEFT, fill='x', expand=True, padx=(0, 8))
            settings_label = tk.Label(content_frame, text='⚙️', bg=COLORS['surface'], fg=COLORS['text_muted'], font=get_font('body_medium'), cursor='hand2')
            settings_label.pack(side=tk.RIGHT, padx=(0, 8))
            settings_label.bind('<Button-1>', lambda e, i=idx: self.show_edit_task_dialog_for_task(i))
            self.task_items[idx] = {'frame': task_row, 'content': content_frame, 'label': task_label, 'settings_label': settings_label, 'var': var, 'drag_handle': drag_handle, 'index_label': index_label}
            content_frame.bind('<Button-1>', lambda e, i=idx: self.on_task_select(i))
            task_label.bind('<Button-1>', lambda e, i=idx: self.on_task_select(i))
            index_label.bind('<Button-1>', lambda e, i=idx: self.on_task_select(i))
            drag_handle.bind('<Button-1>', lambda e, i=idx: self._on_drag_start(e, i))
            drag_handle.bind('<B1-Motion>', lambda e, i=idx: self._on_drag_move(e, i))
            drag_handle.bind('<ButtonRelease-1>', lambda e, i=idx: self._on_drag_end(e, i))
            self._bind_task_hover(task_row, content_frame, task_label, drag_handle, index_label)
        self.queue_info_label.config(text=f"队列: {queue_info['count']}个任务")
        self._update_task_selection_style()
        self.task_inner_frame.update_idletasks()
        self.task_canvas.configure(scrollregion=self.task_canvas.bbox('all'))

    def _bind_task_hover(self, row_frame, content_frame, label, drag_handle, index_label=None):

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
        self.dragging = True
        self.dragged_index = index
        self.drag_start_y = event.y_root
        item = self.task_items.get(index)
        if item:
            self.dragged_widget = item['frame']
            self._create_drag_ghost(item)
            self._apply_blur_effect(item, True)
            self._animate_drag_start(item)

    def _animate_drag_start(self, item):
        item['frame'].configure(highlightbackground=COLORS['primary'], highlightthickness=2)

    def _create_drag_ghost(self, item):
        if self.drag_ghost:
            self.drag_ghost.destroy()
        self.drag_ghost = tk.Toplevel(self.parent_frame)
        self.drag_ghost.overrideredirect(True)
        self.drag_ghost.attributes('-alpha', 0.7)
        self.drag_ghost.attributes('-topmost', True)
        ghost_frame = tk.Frame(self.drag_ghost, bg=COLORS['surface'], highlightbackground=COLORS['primary'], highlightthickness=2)
        ghost_frame.pack(fill='both', expand=True)
        tk.Label(ghost_frame, text=item['label'].cget('text'), bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('body_medium'), padx=20, pady=10).pack()
        self._update_ghost_position(event=None)

    def _update_ghost_position(self, event):
        if self.drag_ghost and event:
            x = self.task_canvas.winfo_rootx() + 20
            y = event.y_root
            self.drag_ghost.geometry(f'+{x}+{y}')

    def _on_drag_move(self, event, index):
        if not self.dragging or self.dragged_index != index:
            return
        if self.drag_ghost:
            x = self.task_canvas.winfo_rootx() + 20
            y = event.y_root
            self.drag_ghost.geometry(f'+{x}+{y}')
        current_y = event.y_root - self.task_inner_frame.winfo_rooty()
        new_index = self._calculate_drop_index(current_y)
        if new_index != self.dragged_index:
            self._show_drop_indicator(new_index)

    def _calculate_drop_index(self, y):
        if self.task_items:
            first_item = list(self.task_items.values())[0]['frame']
            item_height = first_item.winfo_height()
            if item_height < 10:
                item_height = 40
        else:
            item_height = 40
        index = int(y / item_height)
        max_index = len(self.task_items) - 1
        return max(0, min(index, max_index))

    def _show_drop_indicator(self, index):
        for item in self.task_items.values():
            item['frame'].configure(highlightthickness=0)
            for child in item['frame'].winfo_children():
                if isinstance(child, tk.Frame) and hasattr(child, '_is_drop_indicator'):
                    child.destroy()
        if index in self.task_items and index != self.dragged_index:
            target_item = self.task_items[index]
            insert_line = tk.Frame(target_item['frame'], bg=COLORS['primary'], height=3)
            insert_line._is_drop_indicator = True
            insert_line.pack(fill='x', side=tk.TOP, before=target_item['frame'].winfo_children()[0] if target_item['frame'].winfo_children() else None)
            self._animate_drop_indicator(insert_line, 0)

    def _animate_drop_indicator(self, indicator, step):
        if not indicator.winfo_exists():
            return
        colors = [COLORS['primary'], '#42A5F5', '#64B5F6', '#42A5F5', COLORS['primary']]
        if step < len(colors):
            indicator.configure(bg=colors[step])
            self.parent_frame.after(100, lambda: self._animate_drop_indicator(indicator, step + 1))

    def _on_drag_end(self, event, index):
        if not self.dragging or self.dragged_index != index:
            return
        self.dragging = False
        if self.drag_ghost:
            self.drag_ghost.destroy()
            self.drag_ghost = None
        item = self.task_items.get(index)
        if item:
            self._apply_blur_effect(item, False)
        current_y = event.y_root - self.task_inner_frame.winfo_rooty()
        new_index = self._calculate_drop_index(current_y)
        self._clear_drop_indicators()
        if new_index != index and 0 <= new_index < len(self.task_items):
            self._animate_reorder(index, new_index)
        else:
            self.update_queue_display()
        self.dragged_index = -1
        self.dragged_widget = None

    def _clear_drop_indicators(self):
        for item in self.task_items.values():
            item['frame'].configure(highlightthickness=0)
            for child in item['frame'].winfo_children()[:]:
                if isinstance(child, tk.Frame) and hasattr(child, '_is_drop_indicator'):
                    child.destroy()

    def _animate_reorder(self, from_index, to_index):
        self._reorder_tasks(from_index, to_index)

    def _apply_blur_effect(self, item, blur):
        if blur:
            item['frame'].configure(bg='#F0F0F0')
            item['content'].configure(bg='#F0F0F0')
            item['label'].configure(bg='#F0F0F0', fg='#999999')
            item['drag_handle'].configure(bg='#F0F0F0', fg='#CCCCCC')
        else:
            item['frame'].configure(bg=COLORS['surface'])
            item['content'].configure(bg=COLORS['surface'])
            item['label'].configure(bg=COLORS['surface'], fg=COLORS['text_primary'])
            item['drag_handle'].configure(bg=COLORS['surface'], fg=COLORS['text_muted'])

    def _reorder_tasks(self, from_index, to_index):
        success = self.task_queue_manager.move_task(from_index, to_index)
        if success:
            if self.selected_task_index == from_index:
                self.selected_task_index = to_index
            elif from_index < self.selected_task_index <= to_index:
                self.selected_task_index -= 1
            elif to_index <= self.selected_task_index < from_index:
                self.selected_task_index += 1
            self.task_queue_manager.save_task_queue()
            self.update_queue_display()
            self.log_callback(f'任务已从位置 {from_index + 1} 移动到位置 {to_index + 1}', 'task', 'INFO')

    def on_task_select(self, index):
        if self.selected_task_index >= 0 and self.selected_task_index in self.task_items:
            old_item = self.task_items[self.selected_task_index]
            old_item['var'].set(False)
        self.selected_task_index = index
        if index in self.task_items:
            new_item = self.task_items[index]
            new_item['var'].set(True)
        self._update_task_selection_style()

    def _update_task_selection_style(self):
        for idx, item in self.task_items.items():
            if idx == self.selected_task_index:
                item['content'].configure(bg=COLORS['selection_bg'])
                item['frame'].configure(highlightbackground=COLORS['primary'], highlightthickness=1)
                item['label'].configure(bg=COLORS['selection_bg'], fg=COLORS['primary'])
                item['var'].set(True)
                item['drag_handle'].configure(bg=COLORS['selection_bg'])
                if 'index_label' in item:
                    item['index_label'].configure(bg=COLORS['selection_bg'], fg=COLORS['primary'])
            else:
                item['frame'].configure(bg=COLORS['surface'], highlightthickness=0)
                item['content'].configure(bg=COLORS['surface'])
                item['label'].configure(bg=COLORS['surface'], fg=COLORS['text_primary'])
                item['var'].set(False)
                item['drag_handle'].configure(bg=COLORS['surface'])
                if 'index_label' in item:
                    item['index_label'].configure(bg=COLORS['surface'], fg=COLORS['text_muted'])
    _task_panel_visible = False
    _task_panel = None
    _task_panel_items = {}
    _panel_dragging = False
    _panel_dragged_task = None
    _panel_drag_ghost = None

    def show_add_task_dialog(self):
        if not self.execution_manager.auth_manager.get_login_status():
            messagebox.showwarning('未登录', '请先登录后再添加任务')
            return
        if self._task_panel_visible:
            self._hide_task_panel()
            return
        available_tasks = self.get_available_tasks_from_server()
        if not available_tasks:
            messagebox.showinfo('提示', '暂无可用任务')
            return
        self._show_task_panel(available_tasks)

    def _show_task_panel(self, available_tasks):
        self._task_panel_visible = True
        main_window = self.parent_frame.winfo_toplevel()
        self._task_panel = tk.Toplevel(main_window)
        self._task_panel.title('添加任务')
        self._task_panel.geometry('300x450')
        self._task_panel.resizable(True, True)
        self._task_panel.transient(main_window)
        content_frame = tk.Frame(self._task_panel, bg=COLORS['surface'], highlightbackground=COLORS['primary'], highlightthickness=2)
        content_frame.pack(fill='both', expand=True)
        self._task_panel_content = content_frame
        self._create_task_panel_content(available_tasks)

    def _create_task_panel_content(self, available_tasks):
        parent = self._task_panel_content if hasattr(self, '_task_panel_content') and self._task_panel_content else self._task_panel
        header_frame = tk.Frame(parent, bg=COLORS['surface'], height=40)
        header_frame.pack(fill='x', padx=0, pady=0)
        header_frame.pack_propagate(False)
        title_label = tk.Label(header_frame, text='可用任务 (拖拽添加)', bg=COLORS['surface'], fg=COLORS['primary'], font=get_font('title_medium', bold=True), anchor=tk.W)
        title_label.pack(side=tk.LEFT, fill='y', padx=12, pady=8)
        list_container = tk.Frame(parent, bg=COLORS['surface'])
        list_container.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        panel_canvas = tk.Canvas(list_container, bg=COLORS['surface'], highlightthickness=0, borderwidth=0)
        panel_scrollbar = ttk.Scrollbar(list_container, orient='vertical', command=panel_canvas.yview)
        panel_canvas.configure(yscrollcommand=panel_scrollbar.set)
        panel_canvas.pack(side=tk.LEFT, fill='both', expand=True)
        panel_scrollbar.pack(side=tk.RIGHT, fill='y')
        panel_inner_frame = tk.Frame(panel_canvas, bg=COLORS['surface'])
        panel_canvas.create_window((0, 0), window=panel_inner_frame, anchor='nw')
        panel_inner_frame.bind('<Configure>', lambda e: panel_canvas.configure(scrollregion=panel_canvas.bbox('all')))
        panel_canvas.bind('<Configure>', lambda e: panel_canvas.itemconfig(1, width=e.width))

        def _on_mousewheel(event):
            panel_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        panel_canvas.bind('<MouseWheel>', _on_mousewheel)
        panel_inner_frame.bind('<MouseWheel>', _on_mousewheel)
        self._task_panel.bind('<MouseWheel>', _on_mousewheel)
        self._task_panel_items.clear()
        for idx, task in enumerate(available_tasks):
            task_name = task.get('name', '未知任务')
            task_group = task.get('group', '')
            is_compatible, platform_info = self._check_task_compatibility(task)
            task_row = tk.Frame(panel_inner_frame, bg=COLORS['surface'], highlightbackground=COLORS['border_color'], highlightthickness=0)
            task_row.pack(fill='x', pady=1)
            if idx > 0:
                separator = tk.Frame(task_row, bg=COLORS['border_color'], height=1)
                separator.pack(fill='x', side=tk.TOP)
            content_frame = tk.Frame(task_row, bg=COLORS['surface'], height=36)
            content_frame.pack(fill='x', pady=2)
            content_frame.pack_propagate(False)
            drag_handle = tk.Label(content_frame, text='☰', bg=COLORS['surface'], fg=COLORS['text_muted'], font=get_font('body_small'), cursor='hand2', width=2)
            drag_handle.pack(side=tk.LEFT, padx=(6, 2))
            task_label = tk.Label(content_frame, text=task_name, bg=COLORS['surface'], fg=COLORS['text_muted'] if not is_compatible else COLORS['text_primary'], font=get_font('body_medium'), anchor=tk.W)
            task_label.pack(side=tk.LEFT, fill='x', expand=True, padx=(0, 4))
            if not is_compatible:
                compat_label = tk.Label(content_frame, text='⚠️', bg=COLORS['surface'], fg=COLORS['warning'], font=get_font('body_small'), cursor='hand2')
                compat_label.pack(side=tk.RIGHT, padx=(0, 6))
                self._create_tooltip(compat_label, f'不兼容: {platform_info}')
            self._task_panel_items[idx] = {'frame': task_row, 'content': content_frame, 'label': task_label, 'drag_handle': drag_handle, 'task': task}
            drag_handle.bind('<Button-1>', lambda e, t=task, i=idx: self._on_panel_drag_start(e, t, i))
            drag_handle.bind('<B1-Motion>', lambda e: self._on_panel_drag_move(e))
            drag_handle.bind('<ButtonRelease-1>', lambda e: self._on_panel_drag_end(e))
            content_frame.bind('<Button-1>', lambda e, t=task, i=idx: self._on_panel_drag_start(e, t, i))
            content_frame.bind('<B1-Motion>', lambda e: self._on_panel_drag_move(e))
            content_frame.bind('<ButtonRelease-1>', lambda e: self._on_panel_drag_end(e))
            task_label.bind('<Button-1>', lambda e, t=task, i=idx: self._on_panel_drag_start(e, t, i))
            task_label.bind('<B1-Motion>', lambda e: self._on_panel_drag_move(e))
            task_label.bind('<ButtonRelease-1>', lambda e: self._on_panel_drag_end(e))
            content_frame.bind('<Double-Button-1>', lambda e, t=task: self._on_panel_double_click(t))
            task_label.bind('<Double-Button-1>', lambda e, t=task: self._on_panel_double_click(t))
            self._bind_panel_task_hover(task_row, content_frame, task_label, drag_handle)
        parent = self._task_panel_content if hasattr(self, '_task_panel_content') and self._task_panel_content else self._task_panel
        hint_label = tk.Label(parent, text='拖拽任务到右侧队列或双击添加', bg=COLORS['surface'], fg=COLORS['text_muted'], font=get_font('body_small'), anchor=tk.W)
        hint_label.pack(fill='x', padx=12, pady=(0, 8))
    _panel_target_width = 280
    _panel_target_height = 500
    _panel_animation_step = 20
    _panel_animation_delay = 16
    _panel_animation_id = None
    _panel_window_x = 0
    _panel_window_y = 0

    def _animate_slide_out(self):
        if not self._task_panel or not self._task_panel.winfo_exists():
            return
        current_width = self._task_panel.winfo_width()
        if current_width >= self._panel_target_width:
            self._task_panel.geometry(f'{self._panel_target_width}x{self._panel_target_height}+{self._panel_window_x}+{self._panel_window_y}')
            return
        new_width = min(current_width + self._panel_animation_step, self._panel_target_width)
        self._task_panel.geometry(f'{new_width}x{self._panel_target_height}+{self._panel_window_x}+{self._panel_window_y}')
        self._panel_animation_id = self._task_panel.after(self._panel_animation_delay, self._animate_slide_out)

    def _animate_slide_in(self):
        if not self._task_panel or not self._task_panel.winfo_exists():
            self._finalize_hide_panel()
            return
        current_width = self._task_panel.winfo_width()
        if current_width <= 0:
            self._finalize_hide_panel()
            return
        new_width = max(current_width - self._panel_animation_step, 0)
        self._task_panel.geometry(f'{new_width}x{self._panel_target_height}+{self._panel_window_x}+{self._panel_window_y}')
        self._panel_animation_id = self._task_panel.after(self._panel_animation_delay, self._animate_slide_in)

    def _finalize_hide_panel(self):
        self._task_panel_visible = False
        if self._task_panel:
            self._task_panel.destroy()
            self._task_panel = None
        if hasattr(self, '_task_panel_content'):
            self._task_panel_content = None
        self._task_panel_items.clear()
        if self._panel_drag_ghost:
            self._panel_drag_ghost.destroy()
            self._panel_drag_ghost = None
        self._panel_animation_id = None

    def _hide_task_panel(self):
        if self._panel_animation_id:
            if self._task_panel and self._task_panel.winfo_exists():
                self._task_panel.after_cancel(self._panel_animation_id)
            self._panel_animation_id = None
        self._animate_slide_in()

    def _bind_panel_task_hover(self, row_frame, content_frame, label, drag_handle):

        def on_enter(e):
            if not self._panel_dragging:
                content_frame.configure(bg=COLORS['surface_container_low'])
                label.configure(bg=COLORS['surface_container_low'])
                drag_handle.configure(bg=COLORS['surface_container_low'], fg=COLORS['primary'])

        def on_leave(e):
            if not self._panel_dragging:
                content_frame.configure(bg=COLORS['surface'])
                label.configure(bg=COLORS['surface'])
                drag_handle.configure(bg=COLORS['surface'], fg=COLORS['text_muted'])
        row_frame.bind('<Enter>', on_enter)
        row_frame.bind('<Leave>', on_leave)

    def _on_panel_drag_start(self, event, task, index):
        self._panel_dragging = True
        self._panel_dragged_task = task
        self._create_panel_drag_ghost(task, event)
        if index in self._task_panel_items:
            item = self._task_panel_items[index]
            item['content'].configure(bg=COLORS['selection_bg'])
            item['label'].configure(bg=COLORS['selection_bg'], fg=COLORS['primary'])
            item['drag_handle'].configure(bg=COLORS['selection_bg'], fg=COLORS['primary'])

    def _create_panel_drag_ghost(self, task, event):
        if self._panel_drag_ghost:
            self._panel_drag_ghost.destroy()
        self._panel_drag_ghost = tk.Toplevel(self.parent_frame)
        self._panel_drag_ghost.overrideredirect(True)
        self._panel_drag_ghost.attributes('-alpha', 0.8)
        self._panel_drag_ghost.attributes('-topmost', True)
        ghost_frame = tk.Frame(self._panel_drag_ghost, bg=COLORS['primary'], highlightbackground=COLORS['primary'], highlightthickness=2)
        ghost_frame.pack(fill='both', expand=True)
        tk.Label(ghost_frame, text=f"➕ {task.get('name', '未知任务')}", bg=COLORS['primary'], fg=COLORS['surface'], font=get_font('body_medium', bold=True), padx=15, pady=8).pack()
        self._panel_drag_ghost.geometry(f'+{event.x_root + 10}+{event.y_root + 10}')

    def _on_panel_drag_move(self, event):
        if not self._panel_dragging or not self._panel_drag_ghost:
            return
        self._panel_drag_ghost.geometry(f'+{event.x_root + 10}+{event.y_root + 10}')
        queue_x = self.task_frame.winfo_rootx()
        queue_y = self.task_frame.winfo_rooty()
        queue_w = self.task_frame.winfo_width()
        queue_h = self.task_frame.winfo_height()
        if queue_x <= event.x_root <= queue_x + queue_w and queue_y <= event.y_root <= queue_y + queue_h:
            current_y = event.y_root - self.task_inner_frame.winfo_rooty()
            new_index = self._calculate_drop_index(current_y)
            self._show_drop_indicator(new_index)
        else:
            self._clear_drop_indicators()

    def _on_panel_drag_end(self, event):
        if not self._panel_dragging:
            return
        self._panel_dragging = False
        if self._panel_drag_ghost:
            self._panel_drag_ghost.destroy()
            self._panel_drag_ghost = None
        for idx, item in self._task_panel_items.items():
            item['content'].configure(bg=COLORS['surface'])
            item['label'].configure(bg=COLORS['surface'], fg=COLORS['text_primary'])
            item['drag_handle'].configure(bg=COLORS['surface'], fg=COLORS['text_muted'])
        self._clear_drop_indicators()
        queue_x = self.task_frame.winfo_rootx()
        queue_y = self.task_frame.winfo_rooty()
        queue_w = self.task_frame.winfo_width()
        queue_h = self.task_frame.winfo_height()
        if queue_x <= event.x_root <= queue_x + queue_w and queue_y <= event.y_root <= queue_y + queue_h:
            current_y = event.y_root - self.task_inner_frame.winfo_rooty()
            insert_index = self._calculate_drop_index(current_y)
            if self._panel_dragged_task:
                self._add_task_at_index(self._panel_dragged_task, insert_index)
        self._panel_dragged_task = None

    def _on_panel_double_click(self, task):
        self.add_task_to_queue(task)

    def _add_task_at_index(self, task_template, insert_index):
        import time
        new_task = task_template.copy()
        new_task['id'] = f"{task_template.get('id', 'task')}_{int(time.time())}"
        new_task['name'] = task_template.get('name', '新任务')
        new_task['custom_name'] = new_task['name']
        if hasattr(self.task_queue_manager, 'insert_task'):
            self.task_queue_manager.insert_task(new_task, insert_index)
        else:
            self.task_queue_manager.add_task(new_task)
            current_index = len(self.task_queue_manager.get_queue_info()['tasks']) - 1
            if current_index != insert_index:
                self.task_queue_manager.move_task(current_index, insert_index)
        self.update_queue_display()
        self.log_callback(f"已添加任务 '{new_task['name']}' 到位置 {insert_index + 1}", 'task', 'INFO')
        self.task_queue_manager.save_task_queue()

    def show_edit_task_dialog_for_task(self, task_index):
        if task_index < 0 or task_index >= len(self.task_queue_manager.get_queue_info()['tasks']):
            return
        self.on_task_select(task_index)
        if self.on_task_settings_click:
            self.on_task_settings_click(task_index)
            return
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
        dialog.title('设置任务')
        dialog.geometry('450x400')
        dialog.transient(self.parent_frame.winfo_toplevel())
        dialog.grab_set()
        dialog.configure(bg=COLORS['surface'])
        name_label = tk.Label(dialog, text='任务名称', bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('title_small', bold=True))
        name_label.pack(pady=(15, 5), padx=15, anchor=tk.W)
        name_var = tk.StringVar(value=task.get('custom_name', task.get('name', '')))
        name_entry = tk.Entry(dialog, textvariable=name_var, bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('body_medium'), relief='solid', borderwidth=1, highlightbackground=COLORS['border_color'])
        name_entry.pack(fill='x', padx=15, pady=5)
        execute_once_var = tk.BooleanVar(value=task.get('execute_once', False))
        execute_once_check = tk.Checkbutton(dialog, text='仅执行一次（在多轮循环中只执行一次）', variable=execute_once_var, bg=COLORS['surface_container_low'], fg=COLORS['text_primary'], font=get_font('body_small'), selectcolor=COLORS['surface_container_low'], activebackground=COLORS['surface_container'], relief='solid', borderwidth=1)
        execute_once_check.pack(pady=(5, 10), padx=15, anchor=tk.W)
        if variables:
            var_label = tk.Label(dialog, text='任务变量', bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('title_small', bold=True))
            var_label.pack(pady=(10, 5), padx=15, anchor=tk.W)
            variables_frame = tk.Frame(dialog, bg=COLORS['surface'])
            variables_frame.pack(fill='both', expand=True, padx=15, pady=5)
            variable_entries = {}
            cascade_widgets = {}

            def extract_option_value(opt):
                if isinstance(opt, dict):
                    return opt.get('value', '')
                return opt

            def extract_option_label(opt):
                if isinstance(opt, dict):
                    return opt.get('label', opt.get('value', ''))
                return opt

            def should_show_cascade_var(var_def, parent_values):
                depends_on = var_def.get('depends_on')
                if not depends_on:
                    return True
                parent_var = depends_on.get('variable')
                trigger_values = depends_on.get('values', [])
                if parent_var in parent_values:
                    parent_value = parent_values.get(parent_var, '')
                    return parent_value in trigger_values
                return False

            def update_cascade_visibility():
                current_values = {}
                for v_name, (v_var, v_type) in variable_entries.items():
                    current_values[v_name] = v_var.get()
                for v_name, widget_info in cascade_widgets.items():
                    var_def = widget_info['var_def']
                    frame = widget_info['frame']
                    if should_show_cascade_var(var_def, current_values):
                        frame.pack(fill='x', pady=4)
                    else:
                        frame.pack_forget()
            var_dependencies = {}
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
                is_cascade = var_type == 'cascade_select' or depends_on is not None
                if is_cascade:
                    cascade_widgets[var_name] = {'frame': var_frame, 'var_def': var_def}
                    parent_values = {}
                    for v_name, (v_var, v_type) in variable_entries.items():
                        parent_values[v_name] = v_var.get()
                    if should_show_cascade_var(var_def, parent_values):
                        var_frame.pack(fill='x', pady=4)
                else:
                    var_frame.pack(fill='x', pady=4)
                display_name = var_name
                if is_cascade:
                    display_name = f'  └─ {var_name}'
                name_lbl = tk.Label(var_frame, text=f'{display_name}:', bg=COLORS['surface'], fg=COLORS['text_secondary'], font=get_font('body_small'))
                name_lbl.pack(side=tk.LEFT)
                if var_type == 'bool':
                    var_var = tk.BooleanVar(value=bool(current_value))
                    var_entry = tk.Checkbutton(var_frame, variable=var_var, bg=COLORS['surface_container_low'], selectcolor=COLORS['surface_container_low'], relief='solid', borderwidth=1)
                    var_entry.pack(side=tk.RIGHT)
                elif var_type == 'int':
                    var_var = tk.StringVar(value=str(current_value))
                    var_entry = tk.Entry(var_frame, textvariable=var_var, width=10, bg=COLORS['surface'], fg=COLORS['text_primary'], relief='solid', borderwidth=1)
                    var_entry.pack(side=tk.RIGHT)
                elif var_type in ('select', 'cascade_select') and var_options:
                    option_values = [extract_option_value(opt) for opt in var_options]
                    option_labels = [extract_option_label(opt) for opt in var_options]
                    if current_value not in option_values:
                        current_value = option_values[0] if option_values else var_default
                    var_var = tk.StringVar(value=str(current_value))
                    var_entry = ttk.Combobox(var_frame, textvariable=var_var, values=option_labels, width=15, state='readonly')
                    var_entry.pack(side=tk.RIGHT)
                    variable_entries[var_name + '_label_map'] = (dict(zip(option_labels, option_values)), 'label_map')
                    if var_name in var_dependencies:

                        def on_parent_change(event, vn=var_name):
                            dialog.after(10, update_cascade_visibility)
                        var_entry.bind('<<ComboboxSelected>>', on_parent_change)
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
                if var_type == 'label_map':
                    continue
                value = var_var.get()
                label_map_key = var_name + '_label_map'
                if label_map_key in variable_entries:
                    label_map, _ = variable_entries[label_map_key]
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
            self.log_callback(f"任务 '{new_name}' 已更新", 'task', 'INFO')
            dialog.destroy()

        def on_cancel():
            dialog.destroy()
        btn_frame = tk.Frame(dialog, bg=COLORS['surface'])
        btn_frame.pack(pady=15, fill='x', padx=15)
        save_btn = tk.Button(btn_frame, text='保存', command=on_save, bg=COLORS['surface_container_low'], fg=COLORS['text_primary'], font=get_font('body_medium', bold=True), relief='solid', borderwidth=1, padx=20, pady=8, cursor='hand2')
        save_btn.pack(side=tk.RIGHT, padx=(5, 0))
        self._bind_hover_effect(save_btn, COLORS['surface_container_low'], COLORS['surface_container'], COLORS['text_primary'], COLORS['text_primary'])
        cancel_btn = tk.Button(btn_frame, text='取消', command=on_cancel, bg=COLORS['surface_container_low'], fg=COLORS['text_primary'], font=get_font('body_medium'), relief='solid', borderwidth=1, highlightbackground=COLORS['border_color'], padx=20, pady=8, cursor='hand2')
        cancel_btn.pack(side=tk.RIGHT)
        self._bind_hover_effect(cancel_btn, COLORS['surface_container_low'], COLORS['surface_container'], COLORS['text_primary'], COLORS['text_primary'])

    def show_edit_task_dialog(self):
        if self.selected_task_index < 0:
            messagebox.showwarning('警告', '请先选择一个任务')
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
        dialog.title('设置任务')
        dialog.geometry('450x400')
        dialog.transient(self.parent_frame.winfo_toplevel())
        dialog.grab_set()
        dialog.configure(bg=COLORS['surface'])
        name_label = tk.Label(dialog, text='任务名称', bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('title_small', bold=True))
        name_label.pack(pady=(15, 5), padx=15, anchor=tk.W)
        name_var = tk.StringVar(value=task.get('custom_name', task.get('name', '')))
        name_entry = tk.Entry(dialog, textvariable=name_var, bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('body_medium'), relief='solid', borderwidth=1, highlightbackground=COLORS['border_color'])
        name_entry.pack(fill='x', padx=15, pady=5)
        execute_once_var = tk.BooleanVar(value=task.get('execute_once', False))
        execute_once_check = tk.Checkbutton(dialog, text='仅执行一次（在多轮循环中只执行一次）', variable=execute_once_var, bg=COLORS['surface_container_low'], fg=COLORS['text_primary'], font=get_font('body_small'), selectcolor=COLORS['surface_container_low'], activebackground=COLORS['surface_container'], relief='solid', borderwidth=1)
        execute_once_check.pack(pady=(5, 10), padx=15, anchor=tk.W)
        if variables:
            var_label = tk.Label(dialog, text='任务变量', bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('title_small', bold=True))
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
            self.update_queue_display()
            self.log_callback(f"任务 '{new_name}' 已更新", 'task', 'INFO')
            dialog.destroy()

        def on_cancel():
            dialog.destroy()
        btn_frame = tk.Frame(dialog, bg=COLORS['surface'])
        btn_frame.pack(pady=15, fill='x', padx=15)
        save_btn = tk.Button(btn_frame, text='保存', command=on_save, bg=COLORS['surface_container_low'], fg=COLORS['text_primary'], font=get_font('body_medium', bold=True), relief='solid', borderwidth=1, padx=20, pady=8, cursor='hand2')
        save_btn.pack(side=tk.RIGHT, padx=(5, 0))
        self._bind_hover_effect(save_btn, COLORS['surface_container_low'], COLORS['surface_container'], COLORS['text_primary'], COLORS['text_primary'])
        cancel_btn = tk.Button(btn_frame, text='取消', command=on_cancel, bg=COLORS['surface_container_low'], fg=COLORS['text_primary'], font=get_font('body_medium'), relief='solid', borderwidth=1, highlightbackground=COLORS['border_color'], padx=20, pady=8, cursor='hand2')
        cancel_btn.pack(side=tk.RIGHT)
        self._bind_hover_effect(cancel_btn, COLORS['surface_container_low'], COLORS['surface_container'], COLORS['text_primary'], COLORS['text_primary'])

    def sync_all_tasks_definitions_from_server(self) -> bool:
        if not self.execution_manager.auth_manager.get_login_status():
            return False
        if not self.execution_manager.communicator:
            self.log_callback('通信模块未初始化', 'task', 'ERROR')
            return False
        queue_info = self.task_queue_manager.get_queue_info()
        task_ids = [task.get('id', '') for task in queue_info['tasks'] if task.get('id')]
        if not task_ids:
            return True
        try:
            response = self.execution_manager.communicator.send_request('sync_all_tasks_definitions', {'task_ids': task_ids})
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
                self.log_callback(f'启动时同步完成: {updated_count}个任务已更新', 'task', 'INFO')
                return True
            else:
                error_msg = response.get('message', '未知错误') if response else '无响应'
                self.log_callback(f'批量同步任务定义失败: {error_msg}', 'task', 'ERROR')
                return False
        except Exception as e:
            self.log_callback(f'批量同步任务定义异常: {e}', 'task', 'ERROR')
            return False

    def get_task_definition_from_server(self, task_id: str):
        if not self.execution_manager.auth_manager.get_login_status():
            return None
        if not self.execution_manager.communicator:
            self.log_callback('通信模块未初始化', 'task', 'ERROR')
            return None
        try:
            response = self.execution_manager.communicator.send_request('get_task_definition', {'task_id': task_id})
            if response and response.get('status') == 'success':
                task = response.get('task')
                self.log_callback(f"成功获取任务 '{task_id}' 的最新定义", 'task', 'INFO')
                return task
            else:
                error_msg = response.get('message', '未知错误') if response else '无响应'
                self.log_callback(f'获取任务定义失败: {error_msg}', 'task', 'ERROR')
                return None
        except Exception as e:
            self.log_callback(f'获取任务定义异常: {e}', 'task', 'ERROR')
            return None

    def get_available_tasks_from_server(self):
        if not self.execution_manager.auth_manager.get_login_status():
            return []
        if not self.execution_manager.communicator:
            self.log_callback('通信模块未初始化', 'task', 'ERROR')
            return []
        try:
            response = self.execution_manager.communicator.send_request('get_default_tasks', {})
            if response and response.get('status') == 'success':
                tasks = response.get('tasks', [])
                visible_tasks = [task for task in tasks if task.get('visible', True)]
                self.log_callback(f'成功从服务器获取 {len(visible_tasks)} 个可用任务', 'task', 'INFO')
                return visible_tasks
            else:
                error_msg = response.get('message', '未知错误') if response else '无响应'
                self.log_callback(f'获取可用任务失败: {error_msg}', 'task', 'ERROR')
                return []
        except Exception as e:
            self.log_callback(f'获取可用任务异常: {e}', 'task', 'ERROR')
            return []

    def add_task_to_queue(self, task_template=None):
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
            self.log_callback(f"已添加任务 '{new_task['name']}' 到队列", 'task', 'INFO')
            self.task_queue_manager.save_task_queue()

    def on_execution_count_changed(self):
        try:
            count = self.execution_count_var.get()
            self.task_queue_manager.set_execution_count(count)
            self.log_callback(f'执行次数设置为: {count}', 'execution', 'INFO')
        except tk.TclError:
            pass

    def on_infinite_loop_changed(self):
        is_infinite = self.infinite_loop_var.get()
        if is_infinite:
            self.execution_count_entry.config(state='disabled')
            self.task_queue_manager.set_execution_count(-1)
            self.log_callback('已启用持续循环模式', 'execution', 'INFO')
        else:
            self.execution_count_entry.config(state='normal')
            count = self.execution_count_var.get()
            self.task_queue_manager.set_execution_count(count)
            self.log_callback(f'执行次数设置为: {count}', 'execution', 'INFO')

    def start_llm_execution(self):
        main_gui = None
        if hasattr(self.parent_frame, 'winfo_toplevel'):
            root = self.parent_frame.winfo_toplevel()
            if hasattr(root, 'gui_manager'):
                main_gui = root.gui_manager
        preview_update_callback = None
        if main_gui and hasattr(main_gui, 'on_preview_update'):
            preview_update_callback = main_gui.on_preview_update
        success, message = self.execution_manager.start_execution(self.log_callback, self.update_ui_callback, preview_update_callback)
        if not success:
            messagebox.showwarning('警告', message)
        else:
            self.llm_start_btn.config(state='disabled')
            self.llm_stop_btn.config(state='normal')

    def stop_llm_execution(self):
        self.execution_manager.stop_execution()
        self.llm_start_btn.config(state='normal')
        self.llm_stop_btn.config(state='disabled')
        self.log_callback('执行已停止', 'execution', 'INFO')

    def update_ui_callback(self, event_type, data):
        if event_type == 'stop_execution':
            self.llm_start_btn.config(state='normal')
            self.llm_stop_btn.config(state='disabled')

    def delete_selected_task(self):
        if self.selected_task_index < 0:
            messagebox.showwarning('警告', '请先选择一个任务')
            return
        task_index = self.selected_task_index
        queue_info = self.task_queue_manager.get_queue_info()
        if task_index < len(queue_info['tasks']):
            task_name = queue_info['tasks'][task_index].get('name', '未知任务')
        else:
            task_name = '未知任务'
        confirm = messagebox.askyesno('确认删除', f"确定要删除任务 '{task_name}' 吗？\n此操作无法撤销！")
        if confirm:
            removed_task = self.task_queue_manager.remove_task(task_index)
            if removed_task:
                self.selected_task_index = -1
                self.update_queue_display()
                self.log_callback(f"任务 '{removed_task['name']}' 已从队列中删除", 'task', 'INFO')
                self.task_queue_manager.save_task_queue()

    def _create_tooltip(self, widget, text):
        tooltip_window = None

        def show_tooltip(event):
            nonlocal tooltip_window
            if tooltip_window:
                return
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + widget.winfo_height() + 5
            tooltip_window = tk.Toplevel(widget)
            tooltip_window.wm_overrideredirect(True)
            tooltip_window.wm_geometry(f'+{x}+{y}')
            label = tk.Label(tooltip_window, text=text, bg=COLORS['surface_container_high'], fg=COLORS['text_primary'], font=get_font('body_small'), relief='solid', borderwidth=1, padx=8, pady=4)
            label.pack()

        def hide_tooltip(event):
            nonlocal tooltip_window
            if tooltip_window:
                tooltip_window.destroy()
                tooltip_window = None
        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)