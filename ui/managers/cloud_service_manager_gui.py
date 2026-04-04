import tkinter as tk
from tkinter import ttk, messagebox
from ..theme import get_tier_color, COLORS, get_font

class CloudServiceManagerGUI:

    def __init__(self, parent_frame, auth_manager, log_callback):
        self.parent_frame = parent_frame
        self.auth_manager = auth_manager
        self.log_callback = log_callback
        self.username_label = None
        self.tier_label = None
        self.daily_quota_label = None
        self.weekly_quota_label = None
        self.monthly_quota_label = None
        self.token_label = None
        self.expiry_label = None
        self.setup_ui()

    def setup_ui(self):
        main_container = tk.Frame(self.parent_frame, bg=COLORS['surface'])
        main_container.pack(fill='both', expand=True, padx=15, pady=15)
        user_info_frame = tk.Frame(main_container, bg=COLORS['surface'], highlightbackground=COLORS['border_color'], highlightthickness=1)
        user_info_frame.pack(fill='x', pady=(0, 15))
        header_frame = tk.Frame(user_info_frame, bg=COLORS['surface'], height=40)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        title_label = tk.Label(header_frame, text='👤 用户信息', bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('title_medium', bold=True), anchor=tk.W)
        title_label.pack(side=tk.LEFT, fill='y', padx=15, pady=10)
        content_frame = tk.Frame(user_info_frame, bg=COLORS['surface'])
        content_frame.pack(fill='x', padx=15, pady=15)
        self.username_label = tk.Label(content_frame, text='用户名: 未登录', bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('body_medium', bold=True), anchor=tk.W)
        self.username_label.pack(fill='x', pady=(0, 8))
        self.tier_label = tk.Label(content_frame, text='用户层级: -', bg=COLORS['surface'], fg=COLORS['text_secondary'], font=get_font('body_medium'), anchor=tk.W)
        self.tier_label.pack(fill='x', pady=(0, 15))
        separator = tk.Frame(content_frame, bg=COLORS['border_color'], height=1)
        separator.pack(fill='x', pady=(0, 15))
        quota_title = tk.Label(content_frame, text='📊 配额使用情况', bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('title_small', bold=True), anchor=tk.W)
        quota_title.pack(fill='x', pady=(0, 10))
        self.daily_quota_label = tk.Label(content_frame, text='每日配额: -/-', bg=COLORS['surface'], fg=COLORS['text_secondary'], font=get_font('body_medium'), anchor=tk.W)
        self.daily_quota_label.pack(fill='x', pady=(0, 5))
        self.weekly_quota_label = tk.Label(content_frame, text='每周配额: -/-', bg=COLORS['surface'], fg=COLORS['text_secondary'], font=get_font('body_medium'), anchor=tk.W)
        self.weekly_quota_label.pack(fill='x', pady=(0, 5))
        self.monthly_quota_label = tk.Label(content_frame, text='每月配额: -/-', bg=COLORS['surface'], fg=COLORS['text_secondary'], font=get_font('body_medium'), anchor=tk.W)
        self.monthly_quota_label.pack(fill='x', pady=(0, 15))
        self.token_label = tk.Label(content_frame, text='Token用量: -', bg=COLORS['surface'], fg=COLORS['text_secondary'], font=get_font('body_medium'), anchor=tk.W)
        self.token_label.pack(fill='x', pady=(0, 10))
        self.expiry_label = tk.Label(content_frame, text='', bg=COLORS['surface'], fg=COLORS['warning'], font=get_font('body_small'), anchor=tk.W)
        self.expiry_label.pack(fill='x', pady=(0, 10))
        refresh_btn = tk.Button(content_frame, text='🔄 刷新信息', command=self.refresh_user_info, bg=COLORS['surface_container_low'], fg=COLORS['text_primary'], font=get_font('body_medium', bold=True), relief='solid', borderwidth=1, padx=20, pady=8, cursor='hand2')
        refresh_btn.pack(anchor=tk.W, pady=(10, 0))
        self.update_user_info_display()

    def refresh_user_info(self):
        if not self.auth_manager.get_login_status():
            messagebox.showwarning('未登录', '请先登录后再查看云服务信息')
            return
        try:
            user_info = self.auth_manager.get_user_info()
            if user_info:
                self.update_user_info_display(user_info)
                self.log_callback('用户信息已刷新', 'cloud', 'INFO')
            else:
                self.log_callback('无法获取用户信息', 'cloud', 'ERROR')
                messagebox.showerror('错误', '无法获取用户信息，请检查网络连接')
        except Exception as e:
            self.log_callback(f'刷新用户信息失败: {e}', 'cloud', 'ERROR')
            messagebox.showerror('错误', f'刷新用户信息失败: {str(e)}')

    def update_user_info_display(self, user_info=None):
        if not self.auth_manager.get_login_status():
            self.username_label.config(text='用户名: 未登录')
            self.tier_label.config(text='用户层级: -')
            self.daily_quota_label.config(text='每日配额: -/-')
            self.weekly_quota_label.config(text='每周配额: -/-')
            self.monthly_quota_label.config(text='每月配额: -/-')
            self.token_label.config(text='Token用量: -')
            self.expiry_label.config(text='')
            return
        if user_info is None:
            self.username_label.config(text=f'用户名: {self.auth_manager.get_user_id()}')
            self.tier_label.config(text='用户层级: 加载中...')
            self.daily_quota_label.config(text='每日配额: 加载中...')
            self.weekly_quota_label.config(text='每周配额: 加载中...')
            self.monthly_quota_label.config(text='每月配额: 加载中...')
            self.token_label.config(text='Token用量: 加载中...')
            self.expiry_label.config(text='')
            return
        self.username_label.config(text=f"用户名: {user_info.get('user_id', '未知')}")
        tier = user_info.get('tier', 'free')
        tier_names = {'free': '免费用户', 'prime': 'Prime用户', 'plus': 'Plus用户', 'pro': '专业用户'}
        tier_display = tier_names.get(tier, tier)
        self.tier_label.config(text=f'用户层级: {tier_display}')
        tier_color = get_tier_color(tier)
        self.tier_label.config(fg=tier_color)
        quota_used = user_info.get('quota_used', 0)
        quota_daily = user_info.get('quota_daily', 1000)
        self.daily_quota_label.config(text=f'每日配额: {quota_used}/{quota_daily}')
        quota_weekly = user_info.get('quota_weekly', 6000)
        self.weekly_quota_label.config(text=f'每周配额: 0/{quota_weekly}')
        quota_monthly = user_info.get('quota_monthly', 15000)
        self.monthly_quota_label.config(text=f'每月配额: 0/{quota_monthly}')
        total_tokens = user_info.get('total_tokens_used', 0)
        self.token_label.config(text=f'Token用量: {total_tokens}')
        premium_until = user_info.get('premium_until', 0)
        if premium_until > 0:
            from datetime import datetime
            expiry_date = datetime.fromtimestamp(premium_until)
            self.expiry_label.config(text=f"⏰ 高级权限到期: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.expiry_label.config(text='')