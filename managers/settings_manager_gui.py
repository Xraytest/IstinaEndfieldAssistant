"""设置管理GUI模块 - 处理版本信息和更新的UI逻辑"""
import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
import subprocess
import shutil
import sys
from pathlib import Path

# 导入communicator模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from communicator import ClientCommunicator


class SettingsManagerGUI:
    """设置管理GUI类"""
    
    def __init__(self, parent_frame, config, log_callback):
        self.parent_frame = parent_frame
        self.config = config
        self.log_callback = log_callback
        
        # UI组件引用
        self.current_version_label = None
        self.latest_version_label = None
        self.update_status_label = None
        self.update_btn = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置设置页面UI"""
        # 版本信息区域
        version_frame = ttk.LabelFrame(self.parent_frame, text="版本信息", padding="15")
        version_frame.pack(fill='x', pady=(0, 20))
        
        # 当前版本
        current_version_frame = ttk.Frame(version_frame)
        current_version_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(current_version_frame, text="当前版本:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.current_version_label = ttk.Label(current_version_frame, text="加载中...", font=('Arial', 10))
        self.current_version_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 最新版本
        latest_version_frame = ttk.Frame(version_frame)
        latest_version_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(latest_version_frame, text="最新版本:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.latest_version_label = ttk.Label(latest_version_frame, text="检查中...", font=('Arial', 10))
        self.latest_version_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 更新状态
        self.update_status_label = ttk.Label(version_frame, text="", foreground='blue', font=('Arial', 9))
        self.update_status_label.pack(fill='x', pady=(5, 10))
        
        # 检查更新按钮
        check_update_btn = ttk.Button(version_frame, text="检查更新", command=self.check_for_updates)
        check_update_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 更新按钮
        self.update_btn = ttk.Button(version_frame, text="更新到最新版本", command=self.update_client, state='disabled')
        self.update_btn.pack(side=tk.LEFT)
        
        # 初始化版本信息
        self.load_local_version()
        self.check_for_updates()
        
    def load_local_version(self):
        """加载本地版本信息"""
        try:
            ver_file = os.path.join(os.path.dirname(__file__), "..", "data", "ver.json")
            if os.path.exists(ver_file):
                with open(ver_file, 'r', encoding='utf-8') as f:
                    ver_data = json.load(f)
                version = ver_data.get('version', 'unknown')
                self.current_version_label.config(text=version)
                return version
            else:
                # 如果文件不存在，创建默认版本文件
                ver_data = {'version': 'alpha_0.0.1'}
                os.makedirs(os.path.dirname(ver_file), exist_ok=True)
                with open(ver_file, 'w', encoding='utf-8') as f:
                    json.dump(ver_data, f, indent=2)
                self.current_version_label.config(text='alpha_0.0.1')
                return 'alpha_0.0.1'
        except Exception as e:
            self.log_callback(f"加载本地版本失败: {e}", "version", "ERROR")
            self.current_version_label.config(text="未知")
            return "unknown"
            
    def check_for_updates(self):
        """检查更新"""
        try:
            # 使用TCP端口连接服务器
            server_host = self.config['server']['host']
            tcp_port = self.config['server']['port']
            password = self.config.get('communication', {}).get('password', 'default_password')
            
            self.update_status_label.config(text="正在检查更新...", foreground='blue')
            self.parent_frame.update()
            
            # 创建TCP通信器并发送请求
            communicator = ClientCommunicator(server_host, tcp_port, password, timeout=10)
            response = communicator.send_request('check_version', {})
            
            if response and response.get('status') == 'success':
                latest_version = response.get('data', {}).get('version', 'unknown')
                self.latest_version_label.config(text=latest_version)
                
                # 比较版本
                current_version = self.load_local_version()
                if current_version != 'unknown' and latest_version != 'unknown' and current_version != latest_version:
                    self.update_status_label.config(text="发现新版本！", foreground='green')
                    self.update_btn.config(state='normal')
                else:
                    self.update_status_label.config(text="已是最新版本", foreground='gray')
                    self.update_btn.config(state='disabled')
            else:
                error_msg = response.get('message', '未知错误') if response else '连接服务器失败'
                self.update_status_label.config(text=f"检查失败: {error_msg}", foreground='red')
                    
        except Exception as e:
            self.update_status_label.config(text=f"检查失败: {str(e)}", foreground='red')
            self.log_callback(f"检查更新失败: {e}", "version", "ERROR")
            # 网络错误时直接退出客户端
            messagebox.showerror("网络连接失败", "无法连接到更新服务器，请检查网络连接后重试。")
            self.parent_frame.winfo_toplevel().quit()
            
    def update_client(self):
        """更新客户端"""
        if messagebox.askyesno("确认更新", "确定要更新到最新版本吗？这将覆盖本地文件！"):
            try:
                self.update_status_label.config(text="正在更新...", foreground='blue')
                self.update_btn.config(state='disabled')
                self.parent_frame.update()
                
                # 获取当前工作目录
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                
                # 备份当前版本（可选）
                backup_dir = os.path.join(current_dir, "backup_before_update")
                if os.path.exists(backup_dir):
                    shutil.rmtree(backup_dir)
                shutil.copytree(current_dir, backup_dir)
                
                # 执行git clone覆盖
                git_path = self.config.get('git', {}).get('path', 'git')
                if not os.path.exists(git_path):
                    git_path = 'git'  # 使用系统git
                
                # 克隆到临时目录
                temp_dir = os.path.join(current_dir, "temp_update")
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                
                cmd = [git_path, "clone", "https://github.com/Xraytest/IstinaEndfieldAssistant.git", temp_dir]
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=current_dir, timeout=300)
                
                if result.returncode == 0:
                    # 复制新文件覆盖旧文件（保留data目录和cache目录）
                    for item in os.listdir(temp_dir):
                        src_path = os.path.join(temp_dir, item)
                        dst_path = os.path.join(current_dir, item)
                        
                        # 跳过data和cache目录
                        if item in ['data', 'cache']:
                            continue
                            
                        if os.path.isdir(src_path):
                            if os.path.exists(dst_path):
                                shutil.rmtree(dst_path)
                            shutil.copytree(src_path, dst_path)
                        else:
                            if os.path.exists(dst_path):
                                os.remove(dst_path)
                            shutil.copy2(src_path, dst_path)
                    
                    # 清理临时目录
                    shutil.rmtree(temp_dir)
                    
                    # 更新版本文件
                    ver_file = os.path.join(os.path.dirname(__file__), "..", "data", "ver.json")
                    latest_version = self.latest_version_label.cget("text")
                    if latest_version and latest_version != "检查中...":
                        with open(ver_file, 'w', encoding='utf-8') as f:
                            json.dump({'version': latest_version}, f, indent=2)
                        
                        self.update_status_label.config(text="更新成功！请重启客户端", foreground='green')
                        self.current_version_label.config(text=latest_version)
                        messagebox.showinfo("更新成功", "客户端已更新到最新版本！\n请重启客户端以应用更改。")
                    else:
                        self.update_status_label.config(text="更新完成，但版本信息未更新", foreground='orange')
                        messagebox.showinfo("更新完成", "客户端已更新！\n请重启客户端以应用更改。")
                        
                else:
                    # 恢复备份
                    if os.path.exists(backup_dir):
                        shutil.rmtree(current_dir)
                        shutil.move(backup_dir, current_dir)
                    
                    error_msg = result.stderr if result.stderr else result.stdout
                    self.update_status_label.config(text=f"更新失败: {error_msg}", foreground='red')
                    messagebox.showerror("更新失败", f"更新过程中发生错误:\n{error_msg}")
                    
            except Exception as e:
                self.update_status_label.config(text=f"更新失败: {str(e)}", foreground='red')
                self.log_callback(f"更新失败: {e}", "version", "ERROR")
                messagebox.showerror("更新失败", f"更新过程中发生错误:\n{str(e)}")