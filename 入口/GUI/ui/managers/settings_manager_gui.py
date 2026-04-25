"""设置管理GUI模块 - 处理版本信息和更新的UI逻辑"""
import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
import subprocess
import shutil
import sys
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable

# 导入communicator模块
from core.communication.communicator import ClientCommunicator

# 导入GPU检测模块
try:
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.gpu_checker import GPUChecker
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.model_manager import ModelManager
except ImportError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.gpu_checker import GPUChecker
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.model_manager import ModelManager


class SettingsManagerGUI:
    """设置管理GUI类
    
    功能：
    - 版本信息和更新管理
    - 本地推理设置管理
    - 缓存设置管理
    - GPU检测和设备要求检查
    """
    
    # 硬件加速选项
    HARDWARE_ACCEL_OPTIONS = ["auto", "enabled", "disabled"]
    
    def __init__(self, parent_frame, config, log_callback, client_main_ref=None):
        self.parent_frame = parent_frame
        self.config = config
        self.log_callback = log_callback
        self.client_main_ref = client_main_ref  # 引用主客户端实例
        
        # UI组件引用
        self.current_version_label = None
        self.latest_version_label = None
        self.update_status_label = None
        self.update_btn = None
        
        # 本地推理相关
        self._gpu_checker: Optional[GPUChecker] = None
        self._model_manager: Optional[ModelManager] = None
        self._gpu_info: Optional[Dict[str, Any]] = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置设置页面UI"""
        # 触控设置区域
        touch_frame = ttk.LabelFrame(self.parent_frame, text="触控设置", padding="15")
        touch_frame.pack(fill='x', pady=(0, 20))
        
        # 触控方式选择
        touch_method_frame = ttk.Frame(touch_frame)
        touch_method_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(touch_method_frame, text="触控方式:", style='Header.TLabel').pack(side=tk.LEFT)
        
        self.touch_method_var = tk.StringVar()
        touch_method_options = ["maatouch", "pc_foreground"]  # 移除minitouch，添加PC-前台
        self.touch_method_combo = ttk.Combobox(
            touch_method_frame,
            textvariable=self.touch_method_var,
            values=touch_method_options,
            state="readonly",
            width=20
        )
        self.touch_method_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        # 设置当前值
        current_touch_method = self.config.get('touch', {}).get('touch_method', 'maatouch')
        self.touch_method_var.set(current_touch_method)
        
        # 失败时停止执行 - 强制启用，不显示UI选项
        self.fail_on_error_var = tk.BooleanVar(value=True)
        
        # 保存按钮
        save_btn = ttk.Button(touch_frame, text="保存设置", command=self.save_touch_settings, style='Primary.TButton')
        save_btn.pack(side=tk.LEFT, pady=(10, 0))
        
        # 分隔线
        ttk.Separator(self.parent_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # 版本信息区域
        version_frame = ttk.LabelFrame(self.parent_frame, text="版本信息", padding="15")
        version_frame.pack(fill='x', pady=(0, 20))
        
        # 当前版本
        current_version_frame = ttk.Frame(version_frame)
        current_version_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(current_version_frame, text="当前版本:", style='Header.TLabel').pack(side=tk.LEFT)
        self.current_version_label = ttk.Label(current_version_frame, text="加载中...", style='Muted.TLabel')
        self.current_version_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 最新版本
        latest_version_frame = ttk.Frame(version_frame)
        latest_version_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(latest_version_frame, text="最新版本:", style='Header.TLabel').pack(side=tk.LEFT)
        self.latest_version_label = ttk.Label(latest_version_frame, text="检查中...", style='Muted.TLabel')
        self.latest_version_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 更新状态
        self.update_status_label = ttk.Label(version_frame, text="", style='Muted.TLabel')
        self.update_status_label.pack(fill='x', pady=(5, 10))
        
        # 检查更新按钮
        check_update_btn = ttk.Button(version_frame, text="检查更新", command=self.check_for_updates, style='Outline.TButton')
        check_update_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 更新按钮
        self.update_btn = ttk.Button(version_frame, text="更新到最新版本", command=self.update_client, state='disabled', style='Primary.TButton')
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
                    # 更新窗口标题显示新版本
                    if self.client_main_ref and hasattr(self.client_main_ref, 'set_latest_version'):
                        self.client_main_ref.set_latest_version(latest_version)
                else:
                    self.update_status_label.config(text="已是最新版本", foreground='gray')
                    self.update_btn.config(state='disabled')
                    # 更新窗口标题（无新版本）
                    if self.client_main_ref and hasattr(self.client_main_ref, 'set_latest_version'):
                        self.client_main_ref.set_latest_version(None)
            else:
                error_msg = response.get('message', '未知错误') if response else '连接服务器失败'
                self.update_status_label.config(text=f"检查失败: {error_msg}", foreground='red')
                    
        except Exception as e:
            self.update_status_label.config(text=f"检查失败: {str(e)}", foreground='red')
            self.log_callback(f"检查更新失败: {e}", "version", "ERROR")
            # 网络错误时直接退出客户端
            messagebox.showerror("网络连接失败", "无法连接到更新服务器，请检查网络连接后重试。")
            # 使用destroy()立即关闭窗口，避免重复提示
            self.parent_frame.winfo_toplevel().destroy()
            
    def update_client(self):
        """更新客户端"""
        if messagebox.askyesno("确认更新", "确定要更新到最新版本吗？这将覆盖本地文件！"):
            # 在新线程中执行更新
            update_thread = threading.Thread(target=self._update_client_thread, daemon=True)
            update_thread.start()
            
    def _update_client_thread(self):
        """在新线程中执行更新"""
        try:
            # 在主线程中更新UI状态
            self.parent_frame.after(0, lambda: self.update_status_label.config(text="正在更新...", foreground='blue'))
            self.parent_frame.after(0, lambda: self.update_btn.config(state='disabled'))
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
                    
                    # 更新UI
                    self.parent_frame.after(0, lambda: self.update_status_label.config(text="更新成功！正在重启客户端...", foreground='green'))
                    self.parent_frame.after(0, lambda: self.current_version_label.config(text=latest_version))
                    self.parent_frame.after(0, lambda: messagebox.showinfo("更新成功", "客户端已更新到最新版本！\n客户端将自动重启。"))
                else:
                    self.parent_frame.after(0, lambda: self.update_status_label.config(text="更新完成，但版本信息未更新", foreground='orange'))
                    self.parent_frame.after(0, lambda: messagebox.showinfo("更新完成", "客户端已更新！\n客户端将自动重启。"))
                
                # 重启客户端
                self.parent_frame.after(2000, self._restart_client)
                    
            else:
                # 恢复备份
                if os.path.exists(backup_dir):
                    shutil.rmtree(current_dir)
                    shutil.move(backup_dir, current_dir)
                
                error_msg = result.stderr if result.stderr else result.stdout
                self.parent_frame.after(0, lambda: self.update_status_label.config(text=f"更新失败: {error_msg}", foreground='red'))
                self.parent_frame.after(0, lambda: messagebox.showerror("更新失败", f"更新过程中发生错误:\n{error_msg}"))
                    
        except Exception as e:
            self.parent_frame.after(0, lambda: self.update_status_label.config(text=f"更新失败: {str(e)}", foreground='red'))
            self.log_callback(f"更新失败: {e}", "version", "ERROR")
            self.parent_frame.after(0, lambda: messagebox.showerror("更新失败", f"更新过程中发生错误:\n{str(e)}"))
            
    def _restart_client(self):
        """重启客户端"""
        try:
            # 获取当前Python可执行文件路径
            python_exe = sys.executable
            # 获取当前脚本路径
            client_main_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client_main.py")
            
            # 启动新的客户端实例
            subprocess.Popen([python_exe, client_main_path], cwd=os.path.dirname(client_main_path))
            
            # 关闭当前客户端
            self.parent_frame.winfo_toplevel().quit()
        except Exception as e:
            self.log_callback(f"重启客户端失败: {e}", "version", "ERROR")
            messagebox.showerror("重启失败", f"重启客户端时发生错误:\n{str(e)}\n请手动重启客户端。")
            
    def save_touch_settings(self):
        """保存触控设置"""
        try:
            # 更新配置
            if 'touch' not in self.config:
                self.config['touch'] = {}
            
            self.config['touch']['touch_method'] = self.touch_method_var.get()
            self.config['touch']['fail_on_error'] = self.fail_on_error_var.get()
            
            # 保存到文件
            config_path = os.path.join(os.path.dirname(__file__), "..", "config", "client_config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            # 显示成功消息
            messagebox.showinfo("设置已保存", "触控设置已成功保存！\n更改将在下次启动时生效。")
            self.log_callback("触控设置已保存", "settings", "INFO")
            
        except Exception as e:
            self.log_callback(f"保存触控设置失败: {e}", "settings", "ERROR")
            messagebox.showerror("保存失败", f"保存触控设置时发生错误:\n{str(e)}")
    
    # === 本地推理设置管理 ===
    
    def get_local_inference_config(self) -> Dict[str, Any]:
        """获取本地推理配置"""
        return self.config.get('inference', {})
    
    def set_local_inference_enabled(self, enabled: bool) -> bool:
        """设置本地推理启用状态"""
        try:
            if 'inference' not in self.config:
                self.config['inference'] = {}
            
            self.config['inference']['local_inference_enabled'] = enabled
            # 同时更新local.enabled保持兼容
            if 'local' not in self.config['inference']:
                self.config['inference']['local'] = {}
            self.config['inference']['local']['enabled'] = enabled
            
            self._save_config()
            self.log_callback(f"本地推理已{'启用' if enabled else '禁用'}", "settings", "INFO")
            return True
        except Exception as e:
            self.log_callback(f"设置本地推理失败: {e}", "settings", "ERROR")
            return False
    
    def get_hardware_acceleration(self) -> str:
        """获取硬件加速设置"""
        return self.config.get('inference', {}).get('hardware_acceleration', 'auto')
    
    def set_hardware_acceleration(self, mode: str) -> bool:
        """设置硬件加速模式"""
        try:
            if mode not in self.HARDWARE_ACCEL_OPTIONS:
                raise ValueError(f"无效的硬件加速模式: {mode}")
            
            if 'inference' not in self.config:
                self.config['inference'] = {}
            
            self.config['inference']['hardware_acceleration'] = mode
            self._save_config()
            self.log_callback(f"硬件加速设置为: {mode}", "settings", "INFO")
            return True
        except Exception as e:
            self.log_callback(f"设置硬件加速失败: {e}", "settings", "ERROR")
            return False
    
    # === 缓存设置管理 ===
    
    def get_cache_config(self) -> Dict[str, Any]:
        """获取缓存配置"""
        return self.config.get('inference', {}).get('cache_settings', {
            'enabled': True,
            'max_size_mb': 2048,
            'ttl_hours': 24
        })
    
    def set_cache_enabled(self, enabled: bool) -> bool:
        """设置缓存启用状态"""
        try:
            if 'inference' not in self.config:
                self.config['inference'] = {}
            if 'cache_settings' not in self.config['inference']:
                self.config['inference']['cache_settings'] = {}
            
            self.config['inference']['cache_settings']['enabled'] = enabled
            self._save_config()
            self.log_callback(f"缓存已{'启用' if enabled else '禁用'}", "settings", "INFO")
            return True
        except Exception as e:
            self.log_callback(f"设置缓存状态失败: {e}", "settings", "ERROR")
            return False
    
    def set_cache_max_size(self, max_size_mb: int) -> bool:
        """设置缓存最大大小（MB）"""
        try:
            if max_size_mb < 100:
                raise ValueError("缓存大小不能小于100MB")
            
            if 'inference' not in self.config:
                self.config['inference'] = {}
            if 'cache_settings' not in self.config['inference']:
                self.config['inference']['cache_settings'] = {}
            
            self.config['inference']['cache_settings']['max_size_mb'] = max_size_mb
            self._save_config()
            self.log_callback(f"缓存最大大小设置为: {max_size_mb}MB", "settings", "INFO")
            return True
        except Exception as e:
            self.log_callback(f"设置缓存大小失败: {e}", "settings", "ERROR")
            return False
    
    def set_cache_ttl(self, ttl_hours: int) -> bool:
        """设置缓存过期时间（小时）"""
        try:
            if ttl_hours < 1:
                raise ValueError("缓存过期时间不能小于1小时")
            
            if 'inference' not in self.config:
                self.config['inference'] = {}
            if 'cache_settings' not in self.config['inference']:
                self.config['inference']['cache_settings'] = {}
            
            self.config['inference']['cache_settings']['ttl_hours'] = ttl_hours
            self._save_config()
            self.log_callback(f"缓存过期时间设置为: {ttl_hours}小时", "settings", "INFO")
            return True
        except Exception as e:
            self.log_callback(f"设置缓存过期时间失败: {e}", "settings", "ERROR")
            return False
    
    def save_cache_settings(self, enabled: bool, max_size_mb: int, ttl_hours: int) -> bool:
        """保存所有缓存设置"""
        try:
            if 'inference' not in self.config:
                self.config['inference'] = {}
            
            self.config['inference']['cache_settings'] = {
                'enabled': enabled,
                'max_size_mb': max_size_mb,
                'ttl_hours': ttl_hours
            }
            
            self._save_config()
            self.log_callback("缓存设置已保存", "settings", "INFO")
            return True
        except Exception as e:
            self.log_callback(f"保存缓存设置失败: {e}", "settings", "ERROR")
            return False
    
    # === GPU检测和设备要求检查 ===
    
    def check_gpu_requirements(self) -> Dict[str, Any]:
        """检查GPU是否满足本地推理要求"""
        try:
            if self._gpu_checker is None:
                self._gpu_checker = GPUChecker()
            
            result = self._gpu_checker.check_gpu_availability()
            self._gpu_info = result
            
            # 更新配置中的GPU信息
            if 'gpu' not in self.config:
                self.config['gpu'] = {}
            
            self.config['gpu'].update({
                'checked': True,
                'cuda_available': result.get('cuda_available', False),
                'cuda_version': result.get('cuda_version', ''),
                'driver_version': result.get('driver_version', ''),
                'gpu_count': result.get('gpu_count', 0),
                'gpus': result.get('gpus', []),
                'meets_requirements': result.get('meets_requirements', False),
                'recommended_model': result.get('recommended_model')
            })
            
            self._save_config()
            
            self.log_callback(
                f"GPU检测完成: {result.get('gpu_count', 0)}个GPU, "
                f"满足要求: {result.get('meets_requirements', False)}",
                "settings", "INFO"
            )
            
            return result
        except Exception as e:
            self.log_callback(f"GPU检测失败: {e}", "settings", "ERROR")
            return {
                'available': False,
                'meets_requirements': False,
                'error': str(e)
            }
    
    def get_gpu_info(self) -> Optional[Dict[str, Any]]:
        """获取GPU信息"""
        if self._gpu_info is None:
            # 尝试从配置中读取
            gpu_config = self.config.get('gpu', {})
            if gpu_config.get('checked'):
                self._gpu_info = gpu_config
        return self._gpu_info
    
    def meets_gpu_requirements(self) -> bool:
        """检查是否满足GPU要求"""
        gpu_info = self.get_gpu_info()
        if gpu_info is None:
            gpu_info = self.check_gpu_requirements()
        return gpu_info.get('meets_requirements', False)
    
    def get_recommended_model(self) -> Optional[str]:
        """获取推荐的模型"""
        gpu_info = self.get_gpu_info()
        if gpu_info is None:
            gpu_info = self.check_gpu_requirements()
        return gpu_info.get('recommended_model')
    
    # === 模型管理 ===
    
    def get_model_manager(self) -> ModelManager:
        """获取模型管理器实例"""
        if self._model_manager is None:
            models_dir = self.config.get('model', {}).get('models_dir', 'models')
            self._model_manager = ModelManager(models_dir=models_dir)
        return self._model_manager
    
    def get_available_models(self) -> list:
        """获取所有可用模型列表"""
        try:
            manager = self.get_model_manager()
            models = manager.get_all_models()
            return [model.to_dict() for model in models]
        except Exception as e:
            self.log_callback(f"获取模型列表失败: {e}", "settings", "ERROR")
            return []
    
    def get_downloaded_models(self) -> list:
        """获取已下载的模型列表"""
        try:
            manager = self.get_model_manager()
            models = manager.get_available_models()
            return [model.to_dict() for model in models]
        except Exception as e:
            self.log_callback(f"获取已下载模型列表失败: {e}", "settings", "ERROR")
            return []
    
    def download_model(self, model_name: str, progress_callback: Optional[Callable] = None) -> bool:
        """下载指定模型"""
        try:
            manager = self.get_model_manager()
            result = manager.download_model(model_name, progress_callback)
            if result:
                self.log_callback(f"模型 {model_name} 下载成功", "settings", "INFO")
                return True
            else:
                self.log_callback(f"模型 {model_name} 下载失败", "settings", "ERROR")
                return False
        except Exception as e:
            self.log_callback(f"下载模型失败: {e}", "settings", "ERROR")
            return False
    
    def delete_model(self, model_name: str) -> bool:
        """删除指定模型"""
        try:
            manager = self.get_model_manager()
            result = manager.delete_model(model_name)
            if result:
                self.log_callback(f"模型 {model_name} 已删除", "settings", "INFO")
                return True
            else:
                self.log_callback(f"删除模型 {model_name} 失败", "settings", "ERROR")
                return False
        except Exception as e:
            self.log_callback(f"删除模型失败: {e}", "settings", "ERROR")
            return False
    
    def get_model_disk_usage(self) -> Dict[str, Any]:
        """获取模型磁盘使用情况"""
        try:
            manager = self.get_model_manager()
            return manager.get_disk_usage()
        except Exception as e:
            self.log_callback(f"获取磁盘使用情况失败: {e}", "settings", "ERROR")
            return {'total_size_gb': 0, 'model_count': 0, 'models': {}}
    
    # === 配置保存辅助方法 ===
    
    def _save_config(self) -> bool:
        """保存配置到文件"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "client_config.json")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.log_callback(f"保存配置失败: {e}", "settings", "ERROR")
            return False