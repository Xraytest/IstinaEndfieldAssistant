"""云服务管理GUI模块 - 处理用户信息和配额显示的UI逻辑"""
import tkinter as tk
from tkinter import ttk, messagebox
from client.ui.theme import get_tier_color, get_status_color


class CloudServiceManagerGUI:
    """云服务管理GUI类"""
    
    def __init__(self, parent_frame, auth_manager, log_callback):
        self.parent_frame = parent_frame
        self.auth_manager = auth_manager
        self.log_callback = log_callback
        
        # UI组件引用
        self.username_label = None
        self.tier_label = None
        self.daily_quota_label = None
        self.weekly_quota_label = None
        self.monthly_quota_label = None
        self.token_label = None
        self.expiry_label = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置云服务页面UI"""
        # 用户信息区域
        user_info_frame = ttk.LabelFrame(self.parent_frame, text="用户信息", padding="15")
        user_info_frame.pack(fill='x', pady=(0, 20))
        
        # 用户名
        self.username_label = ttk.Label(user_info_frame, text="用户名: 未登录", style='Header.TLabel')
        self.username_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 用户层级
        self.tier_label = ttk.Label(user_info_frame, text="用户层级: -", style='Muted.TLabel')
        self.tier_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 配额使用情况 - 每日
        self.daily_quota_label = ttk.Label(user_info_frame, text="每日配额: -/-", style='Muted.TLabel')
        self.daily_quota_label.pack(anchor=tk.W, pady=(0, 2))
        
        # 配额使用情况 - 每周
        self.weekly_quota_label = ttk.Label(user_info_frame, text="每周配额: -/-", style='Muted.TLabel')
        self.weekly_quota_label.pack(anchor=tk.W, pady=(0, 2))
        
        # 配额使用情况 - 每月
        self.monthly_quota_label = ttk.Label(user_info_frame, text="每月配额: -/-", style='Muted.TLabel')
        self.monthly_quota_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Token用量统计
        self.token_label = ttk.Label(user_info_frame, text="Token用量: -", style='Muted.TLabel')
        self.token_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 到期时间（仅高层级用户显示）
        self.expiry_label = ttk.Label(user_info_frame, text="", style='Danger.TLabel')
        self.expiry_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 刷新按钮
        refresh_btn = ttk.Button(user_info_frame, text="🔄 刷新信息", command=self.refresh_user_info, style='Outline.TButton')
        refresh_btn.pack(anchor=tk.W, pady=(10, 0))
        
        # 初始化用户信息显示
        self.update_user_info_display()
        
    def refresh_user_info(self):
        """刷新用户信息"""
        if not self.auth_manager.get_login_status():
            messagebox.showwarning("未登录", "请先登录后再查看云服务信息")
            return
            
        try:
            user_info = self.auth_manager.get_user_info()
            if user_info:
                self.update_user_info_display(user_info)
                self.log_callback("用户信息已刷新", "cloud", "INFO")
            else:
                self.log_callback("无法获取用户信息", "cloud", "ERROR")
                messagebox.showerror("错误", "无法获取用户信息，请检查网络连接")
                
        except Exception as e:
            self.log_callback(f"刷新用户信息失败: {e}", "cloud", "ERROR")
            messagebox.showerror("错误", f"刷新用户信息失败: {str(e)}")
            
    def update_user_info_display(self, user_info=None):
        """更新用户信息显示"""
        if not self.auth_manager.get_login_status():
            self.username_label.config(text="用户名: 未登录")
            self.tier_label.config(text="用户层级: -")
            self.daily_quota_label.config(text="每日配额: -/-")
            self.weekly_quota_label.config(text="每周配额: -/-")
            self.monthly_quota_label.config(text="每月配额: -/-")
            self.token_label.config(text="Token用量: -")
            self.expiry_label.config(text="")
            return

        if user_info is None:
            # 显示基本登录信息
            self.username_label.config(text=f"用户名: {self.auth_manager.get_user_id()}")
            self.tier_label.config(text="用户层级: 加载中...")
            self.daily_quota_label.config(text="每日配额: 加载中...")
            self.weekly_quota_label.config(text="每周配额: 加载中...")
            self.monthly_quota_label.config(text="每月配额: 加载中...")
            self.token_label.config(text="Token用量: 加载中...")
            self.expiry_label.config(text="")
            return

        # 更新用户名
        self.username_label.config(text=f"用户名: {user_info.get('user_id', '未知')}")

        # 更新用户层级
        tier = user_info.get('tier', 'free')
        tier_names = {
            'free': '免费用户',
            'prime': 'Prime用户',
            'plus': 'Plus用户',
            'pro': '专业用户'
        }
        tier_display = tier_names.get(tier, tier)
        self.tier_label.config(text=f"用户层级: {tier_display}")

        # 根据用户层级设置颜色
        tier_color = get_tier_color(tier)
        self.tier_label.config(foreground=tier_color)

        # 更新每日配额使用情况
        quota_used = user_info.get('quota_used', 0)
        quota_daily = user_info.get('quota_daily', 1000)  # 使用正确的默认值1000
        self.daily_quota_label.config(text=f"每日配额: {quota_used}/{quota_daily}")

        # 更新每周配额使用情况（目前服务器不跟踪周/月使用量，只显示配额上限）
        quota_weekly = user_info.get('quota_weekly', 6000)
        self.weekly_quota_label.config(text=f"每周配额: 0/{quota_weekly}")

        # 更新每月配额使用情况
        quota_monthly = user_info.get('quota_monthly', 15000)
        self.monthly_quota_label.config(text=f"每月配额: 0/{quota_monthly}")

        # 更新Token用量
        total_tokens = user_info.get('total_tokens_used', 0)
        self.token_label.config(text=f"Token用量: {total_tokens}")

        # 更新到期时间（仅高层级用户）
        premium_until = user_info.get('premium_until', 0)
        if premium_until > 0:
            from datetime import datetime
            expiry_date = datetime.fromtimestamp(premium_until)
            self.expiry_label.config(text=f"高级权限到期: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.expiry_label.config(text="")