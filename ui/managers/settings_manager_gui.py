import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
import subprocess
import shutil
import sys
import threading
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from core.communication.communicator import ClientCommunicator
from ui.theme import COLORS, get_font

class SettingsManagerGUI:

    def __init__(self, parent_frame, config, log_callback, client_main_ref=None):
        self.parent_frame = parent_frame
        self.config = config
        self.log_callback = log_callback
        self.client_main_ref = client_main_ref
        self.current_version_label = None
        self.latest_version_label = None
        self.update_status_label = None
        self.update_btn = None
        self.setup_ui()

    def setup_ui(self):
        main_container = tk.Frame(self.parent_frame, bg=COLORS['surface'])
        main_container.pack(fill='both', expand=True, padx=15, pady=15)
        version_frame = tk.Frame(main_container, bg=COLORS['surface'], highlightbackground=COLORS['border_color'], highlightthickness=1)
        version_frame.pack(fill='x', pady=(0, 15))
        version_header = tk.Frame(version_frame, bg=COLORS['surface'], height=40)
        version_header.pack(fill='x')
        version_header.pack_propagate(False)
        version_title = tk.Label(version_header, text='版本信息', bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('title_medium', bold=True), anchor=tk.W)
        version_title.pack(side=tk.LEFT, fill='y', padx=15, pady=10)
        version_content = tk.Frame(version_frame, bg=COLORS['surface'])
        version_content.pack(fill='x', padx=15, pady=15)
        current_version_frame = tk.Frame(version_content, bg=COLORS['surface'])
        current_version_frame.pack(fill='x', pady=(0, 10))
        current_label = tk.Label(current_version_frame, text='当前版本:', bg=COLORS['surface'], fg=COLORS['text_secondary'], font=get_font('body_medium'))
        current_label.pack(side=tk.LEFT)
        self.current_version_label = tk.Label(current_version_frame, text='加载中...', bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('body_medium', bold=True))
        self.current_version_label.pack(side=tk.LEFT, padx=(10, 0))
        latest_version_frame = tk.Frame(version_content, bg=COLORS['surface'])
        latest_version_frame.pack(fill='x', pady=(0, 10))
        latest_label = tk.Label(latest_version_frame, text='最新版本:', bg=COLORS['surface'], fg=COLORS['text_secondary'], font=get_font('body_medium'))
        latest_label.pack(side=tk.LEFT)
        self.latest_version_label = tk.Label(latest_version_frame, text='检查中...', bg=COLORS['surface'], fg=COLORS['text_primary'], font=get_font('body_medium', bold=True))
        self.latest_version_label.pack(side=tk.LEFT, padx=(10, 0))
        self.update_status_label = tk.Label(version_content, text='', bg=COLORS['surface'], fg=COLORS['text_secondary'], font=get_font('body_small'))
        self.update_status_label.pack(fill='x', pady=(5, 10))
        version_btn_frame = tk.Frame(version_content, bg=COLORS['surface'])
        version_btn_frame.pack(fill='x')
        check_update_btn = tk.Button(version_btn_frame, text='🔍 检查更新', command=self.check_for_updates, bg=COLORS['surface_container_low'], fg=COLORS['text_primary'], font=get_font('body_medium'), relief='solid', borderwidth=1, highlightbackground=COLORS['border_color'], padx=15, pady=6, cursor='hand2')
        check_update_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.update_btn = tk.Button(version_btn_frame, text='⬆ 更新到最新版本', command=self.update_client, state='disabled', bg=COLORS['surface_container_low'], fg=COLORS['text_primary'], font=get_font('body_medium', bold=True), relief='solid', borderwidth=1, padx=15, pady=6, cursor='hand2')
        self.update_btn.pack(side=tk.LEFT)
        self.load_local_version()
        self.check_for_updates()

    def load_local_version(self):
        try:
            ver_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'ver.json')
            if os.path.exists(ver_file):
                with open(ver_file, 'r', encoding='utf-8') as f:
                    ver_data = json.load(f)
                version = ver_data.get('version', 'unknown')
                self.current_version_label.config(text=version)
                return version
            else:
                ver_data = {'version': 'alpha_0.0.1'}
                os.makedirs(os.path.dirname(ver_file), exist_ok=True)
                with open(ver_file, 'w', encoding='utf-8') as f:
                    json.dump(ver_data, f, indent=2)
                self.current_version_label.config(text='alpha_0.0.1')
                return 'alpha_0.0.1'
        except Exception as e:
            self.log_callback(f'加载本地版本失败: {e}', 'version', 'ERROR')
            self.current_version_label.config(text='未知')
            return 'unknown'

    def check_for_updates(self):
        try:
            server_host = self.config['server']['host']
            tcp_port = self.config['server']['port']
            password = self.config.get('communication', {}).get('password', 'default_password')
            self.update_status_label.config(text='正在检查更新...', fg=COLORS['info'])
            self.parent_frame.update()
            communicator = ClientCommunicator(server_host, tcp_port, password, timeout=10)
            response = communicator.send_request('check_version', {})
            if response and response.get('status') == 'success':
                latest_version = response.get('data', {}).get('version', 'unknown')
                self.latest_version_label.config(text=latest_version)
                current_version = self.load_local_version()
                if current_version != 'unknown' and latest_version != 'unknown' and (current_version != latest_version):
                    self.update_status_label.config(text='发现新版本！', fg=COLORS['success'])
                    self.update_btn.config(state='normal')
                    if self.client_main_ref and hasattr(self.client_main_ref, 'set_latest_version'):
                        self.client_main_ref.set_latest_version(latest_version)
                else:
                    self.update_status_label.config(text='已是最新版本', fg=COLORS['text_secondary'])
                    self.update_btn.config(state='disabled')
                    if self.client_main_ref and hasattr(self.client_main_ref, 'set_latest_version'):
                        self.client_main_ref.set_latest_version(None)
            else:
                error_msg = response.get('message', '未知错误') if response else '连接服务器失败'
                self.update_status_label.config(text=f'检查失败: {error_msg}', fg=COLORS['danger'])
        except Exception as e:
            self.update_status_label.config(text=f'检查失败: {str(e)}', fg=COLORS['danger'])
            self.log_callback(f'检查更新失败: {e}', 'version', 'ERROR')
            messagebox.showerror('网络连接失败', '无法连接到更新服务器，请检查网络连接后重试。')
            self.parent_frame.winfo_toplevel().destroy()

    def update_client(self):
        if messagebox.askyesno('确认更新', '确定要更新到最新版本吗？这将覆盖本地文件！'):
            update_thread = threading.Thread(target=self._update_client_thread, daemon=True)
            update_thread.start()

    def _update_client_thread(self):
        try:
            self.parent_frame.after(0, lambda: self.update_status_label.config(text='正在更新...', fg=COLORS['info']))
            self.parent_frame.after(0, lambda: self.update_btn.config(state='disabled'))
            self.parent_frame.update()
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            backup_dir = os.path.join(current_dir, 'backup_before_update')
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            shutil.copytree(current_dir, backup_dir)
            git_path = self.config.get('git', {}).get('path', 'git')
            if not os.path.exists(git_path):
                git_path = 'git'
            temp_dir = os.path.join(current_dir, 'temp_update')
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            cmd = [git_path, 'clone', 'https://github.com/Xraytest/IstinaEndfieldAssistant.git', temp_dir]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=current_dir, timeout=300)
            if result.returncode == 0:
                for item in os.listdir(temp_dir):
                    src_path = os.path.join(temp_dir, item)
                    dst_path = os.path.join(current_dir, item)
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
                shutil.rmtree(temp_dir)
                ver_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'ver.json')
                latest_version = self.latest_version_label.cget('text')
                if latest_version and latest_version != '检查中...':
                    with open(ver_file, 'w', encoding='utf-8') as f:
                        json.dump({'version': latest_version}, f, indent=2)
                    self.parent_frame.after(0, lambda: self.update_status_label.config(text='更新成功！正在重启客户端...', fg=COLORS['success']))
                    self.parent_frame.after(0, lambda: self.current_version_label.config(text=latest_version))
                    self.parent_frame.after(0, lambda: messagebox.showinfo('更新成功', '客户端已更新到最新版本！\n客户端将自动重启。'))
                else:
                    self.parent_frame.after(0, lambda: self.update_status_label.config(text='更新完成，但版本信息未更新', fg=COLORS['warning']))
                    self.parent_frame.after(0, lambda: messagebox.showinfo('更新完成', '客户端已更新！\n客户端将自动重启。'))
                self.parent_frame.after(2000, self._restart_client)
            else:
                if os.path.exists(backup_dir):
                    shutil.rmtree(current_dir)
                    shutil.move(backup_dir, current_dir)
                error_msg = result.stderr if result.stderr else result.stdout
                self.parent_frame.after(0, lambda: self.update_status_label.config(text=f'更新失败: {error_msg}', fg=COLORS['danger']))
                self.parent_frame.after(0, lambda: messagebox.showerror('更新失败', f'更新过程中发生错误:\n{error_msg}'))
        except Exception as e:
            self.parent_frame.after(0, lambda: self.update_status_label.config(text=f'更新失败: {str(e)}', fg=COLORS['danger']))
            self.log_callback(f'更新失败: {e}', 'version', 'ERROR')
            self.parent_frame.after(0, lambda: messagebox.showerror('更新失败', f'更新过程中发生错误:\n{str(e)}'))

    def _restart_client(self):
        try:
            python_exe = sys.executable
            client_main_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'client_main.py')
            subprocess.Popen([python_exe, client_main_path], cwd=os.path.dirname(client_main_path))
            self.parent_frame.winfo_toplevel().quit()
        except Exception as e:
            self.log_callback(f'重启客户端失败: {e}', 'version', 'ERROR')
            messagebox.showerror('重启失败', f'重启客户端时发生错误:\n{str(e)}\n请手动重启客户端。')