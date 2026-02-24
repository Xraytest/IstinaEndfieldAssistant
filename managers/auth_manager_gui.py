"""认证管理GUI模块 - 处理登录/注册相关的UI逻辑"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import json


class AuthManagerGUI:
    """认证管理GUI类"""
    
    def __init__(self, parent, auth_manager, on_login_success=None):
        self.parent = parent
        self.auth_manager = auth_manager
        self.on_login_success = on_login_success
        
    def show_login_or_register_dialog(self):
        """显示登录或注册选择对话框 - 不登录则退出"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("账户认证")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # 处理窗口关闭事件，使其与取消按钮行为一致
        def on_close():
            # 不登录注册，直接退出客户端
            dialog.destroy()
            self.parent.quit()
            
        dialog.protocol("WM_DELETE_WINDOW", on_close)
        
        ttk.Label(dialog, text="请选择操作:", font=('Arial', 12, 'bold')).pack(pady=20)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        def on_register():
            dialog.destroy()
            self.show_register_dialog()
            
        def on_login():
            dialog.destroy()
            self.show_login_dialog()
            
        def on_cancel():
            # 不登录注册，直接退出客户端
            dialog.destroy()
            self.parent.quit()
            
        ttk.Button(btn_frame, text="注册", command=on_register, style='Action.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="登入", command=on_login, style='Action.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
    def show_register_dialog(self):
        """显示注册对话框"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("注册")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # 处理窗口关闭事件，使其与取消按钮行为一致
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        
        ttk.Label(dialog, text="请输入用户名:", font=('Arial', 10)).pack(pady=10)
        
        username_var = tk.StringVar()
        username_entry = ttk.Entry(dialog, textvariable=username_var, width=30)
        username_entry.pack(pady=5)
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
                # 检查是否为网络错误
                if error_msg and ("网络连接异常" in error_msg or "网络错误" in error_msg):
                    messagebox.showerror("网络连接失败", "无法连接到服务器，请检查网络连接后重试。")
                    # 网络错误时直接退出客户端
                    dialog.destroy()
                    self.parent.destroy()
                    return
                else:
                    error_display = error_msg if error_msg else "注册失败，请重试。"
                    messagebox.showerror("注册失败", f"注册失败: {error_display}")
                
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="注册", command=on_submit, style='Action.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
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
                        # 检查是否为网络错误
                        if "网络连接异常" in error_msg or "网络错误" in error_msg:
                            messagebox.showerror("网络连接失败", "无法连接到服务器，请检查网络连接后重试。")
                            # 网络错误时直接退出客户端
                            self.parent.destroy()
                            return
                        # 如果是用户不存在或密钥错误，删除文件
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