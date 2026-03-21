"""认证管理GUI模块 - MAA风格登录/注册对话框"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import json
from ..theme import COLORS, get_font


class AuthManagerGUI:
    """认证管理GUI类 - MAA风格"""
    
    def __init__(self, parent, auth_manager, on_login_success=None):
        self.parent = parent
        self.auth_manager = auth_manager
        self.on_login_success = on_login_success
        
    def show_login_or_register_dialog(self):
        """显示登录或注册选择对话框 - MAA风格"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("账户认证")
        dialog.geometry("320x180")
        dialog.resizable(False, False)
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.configure(bg=COLORS['surface'])
        
        # 处理窗口关闭事件
        def on_close():
            dialog.destroy()
            self.parent.quit()
            
        dialog.protocol("WM_DELETE_WINDOW", on_close)
        
        # 标题
        title_label = tk.Label(
            dialog,
            text="🔐 账户认证",
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('title_medium', bold=True)
        )
        title_label.pack(pady=(20, 15))
        
        # 提示文字
        hint_label = tk.Label(
            dialog,
            text="请选择操作:",
            bg=COLORS['surface'],
            fg=COLORS['text_secondary'],
            font=get_font('body_medium')
        )
        hint_label.pack(pady=(0, 15))
        
        # 按钮区域
        btn_frame = tk.Frame(dialog, bg=COLORS['surface'])
        btn_frame.pack(pady=10)
        
        def on_register():
            dialog.destroy()
            self.show_register_dialog()
            
        def on_login():
            dialog.destroy()
            self.show_login_dialog()
            
        def on_cancel():
            dialog.destroy()
            self.parent.quit()
            
        # 注册按钮 - 浅灰色背景带圆角
        register_btn = tk.Button(
            btn_frame,
            text="注册",
            command=on_register,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_medium', bold=True),
            relief='solid',
            borderwidth=1,
            padx=20,
            pady=8,
            cursor='hand2'
        )
        register_btn.pack(side=tk.LEFT, padx=5)
        
        # 登录按钮 - 浅灰色背景带圆角
        login_btn = tk.Button(
            btn_frame,
            text="登入",
            command=on_login,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_medium', bold=True),
            relief='solid',
            borderwidth=1,
            padx=20,
            pady=8,
            cursor='hand2'
        )
        login_btn.pack(side=tk.LEFT, padx=5)
        
        # 取消按钮 - 浅灰色背景带圆角
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
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
    def show_register_dialog(self):
        """显示注册对话框 - MAA风格"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("注册")
        dialog.geometry("350x200")
        dialog.resizable(False, False)
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.configure(bg=COLORS['surface'])
        
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        
        # 标题
        title_label = tk.Label(
            dialog,
            text="📝 注册新账户",
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('title_medium', bold=True)
        )
        title_label.pack(pady=(20, 15))
        
        # 输入框标签
        input_label = tk.Label(
            dialog,
            text="请输入用户名:",
            bg=COLORS['surface'],
            fg=COLORS['text_secondary'],
            font=get_font('body_medium'),
            anchor=tk.W
        )
        input_label.pack(fill='x', padx=30, pady=(0, 5))
        
        # 输入框
        username_var = tk.StringVar()
        username_entry = tk.Entry(
            dialog,
            textvariable=username_var,
            width=30,
            bg=COLORS['surface'],
            fg=COLORS['text_primary'],
            font=get_font('body_medium'),
            relief='solid',
            borderwidth=1,
            highlightbackground=COLORS['border_color'],
            highlightthickness=1
        )
        username_entry.pack(padx=30, pady=5, fill='x')
        username_entry.focus()
        
        def on_submit():
            username = username_var.get().strip()
            if not username:
                messagebox.showwarning("警告", "请输入有效的用户名")
                return
                
            success, error_msg = self.auth_manager.register_user(username)
            if success:
                dialog.destroy()
                messagebox.showinfo("注册成功", f"{username}注册成功！登入凭证已缓存于本地")
                if self.on_login_success:
                    self.on_login_success()
            else:
                if error_msg and ("网络连接异常" in error_msg or "网络错误" in error_msg):
                    messagebox.showerror("网络连接失败", "无法连接到服务器，请检查网络连接后重试。")
                    dialog.destroy()
                    self.parent.destroy()
                    return
                else:
                    error_display = error_msg if error_msg else "注册失败，请重试。"
                    messagebox.showerror("注册失败", f"注册失败: {error_display}")
                
        # 按钮区域
        btn_frame = tk.Frame(dialog, bg=COLORS['surface'])
        btn_frame.pack(pady=20)
        
        # 注册按钮 - 浅灰色背景带圆角
        submit_btn = tk.Button(
            btn_frame,
            text="注册",
            command=on_submit,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_medium', bold=True),
            relief='solid',
            borderwidth=1,
            padx=25,
            pady=8,
            cursor='hand2'
        )
        submit_btn.pack(side=tk.LEFT, padx=5)
        
        # 取消按钮 - 浅灰色背景带圆角
        cancel_btn = tk.Button(
            btn_frame,
            text="取消",
            command=dialog.destroy,
            bg=COLORS['surface_container_low'],
            fg=COLORS['text_primary'],
            font=get_font('body_medium'),
            relief='solid',
            borderwidth=1,
            highlightbackground=COLORS['border_color'],
            padx=25,
            pady=8,
            cursor='hand2'
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # 绑定回车键
        username_entry.bind('<Return>', lambda e: on_submit())
        
    def show_login_dialog(self):
        """显示登录对话框"""
        def on_select_file():
            file_path = filedialog.askopenfilename(
                title="选择ArkPass文件",
                filetypes=[("ArkPass Files", "*.arkpass"), ("All Files", "*.*")]
            )
            if file_path:
                result = self.auth_manager.login_with_arkpass(file_path)
                if isinstance(result, tuple):
                    success, error_msg = result[:2]
                    if success:
                        messagebox.showinfo("登录成功", "登录成功！")
                        if self.on_login_success:
                            self.on_login_success()
                    else:
                        if "网络连接异常" in error_msg or "网络错误" in error_msg:
                            messagebox.showerror("网络连接失败", "无法连接到服务器，请检查网络连接后重试。")
                            self.parent.destroy()
                            return
                        if len(result) > 2 and result[2] in ['user_not_found', 'invalid_api_key']:
                            try:
                                os.remove(file_path)
                                print(f"已删除无效的ArkPass文件: {file_path}")
                            except Exception as e:
                                print(f"删除ArkPass文件失败: {e}")
                        messagebox.showerror("登录失败", f"登录失败: {error_msg}")
                elif result:
                    messagebox.showinfo("登录成功", "登录成功！")
                    if self.on_login_success:
                        self.on_login_success()
                else:
                    messagebox.showerror("登录失败", "ArkPass文件无效或登录失败。")
                    
        on_select_file()
