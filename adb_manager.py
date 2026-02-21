"""
ADB设备管理器 - 负责ADB连接、设备发现和状态监控
"""
import subprocess
import os
import time
import json
from typing import List, Dict, Optional, Tuple

class ADBDeviceManager:
    """ADB设备管理器"""
    
    def __init__(self, adb_path: Optional[str] = None, timeout: int = 10):
        """
        初始化ADB设备管理器
        
        Args:
            adb_path: ADB可执行文件路径，如果为None则使用系统PATH中的adb
            timeout: ADB操作超时时间（秒）
        """
        self.adb_path = adb_path or "adb"
        self.timeout = timeout
        self.devices_cache = {}
        self.last_scan_time = 0
        self.scan_interval = 5  # 设备扫描间隔（秒）
        
    def _run_adb_command(self, args: List[str]) -> Tuple[bool, str]:
        """
        执行ADB命令
        
        Args:
            args: ADB命令参数列表
            
        Returns:
            (success, output) 元组
        """
        try:
            cmd = [self.adb_path] + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, f"ADB命令超时 ({self.timeout}秒)"
        except Exception as e:
            return False, f"ADB命令执行异常: {str(e)}"
            
    def start_server(self) -> bool:
        """启动ADB服务器"""
        success, output = self._run_adb_command(["start-server"])
        return success
        
    def kill_server(self) -> bool:
        """停止ADB服务器"""
        success, output = self._run_adb_command(["kill-server"])
        return success
        
    def get_devices(self, force_refresh: bool = False) -> List[Dict]:
        """
        获取连接的设备列表
        
        Args:
            force_refresh: 是否强制刷新设备列表
            
        Returns:
            设备信息列表，每个设备包含serial、state、model等信息
        """
        current_time = time.time()
        if not force_refresh and current_time - self.last_scan_time < self.scan_interval:
            return list(self.devices_cache.values())
            
        success, output = self._run_adb_command(["devices", "-l"])
        if not success:
            return []
            
        devices = []
        lines = output.split('\n')
        for line in lines[1:]:  # 跳过第一行标题
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    serial = parts[0]
                    # 检查是否是有效的设备序列号（不是空格或特殊字符）
                    if serial and not serial.startswith('*') and serial != 'List':
                        state = parts[1]
                        # 只处理有效的设备状态
                        if state in ['device', 'offline', 'unauthorized']:
                            device_info = {
                                'serial': serial,
                                'state': state,
                                'model': '',
                                'product': '',
                                'transport_id': ''
                            }
                            
                            # 解析额外信息
                            for part in parts[2:]:
                                if part.startswith('model:'):
                                    device_info['model'] = part[6:]
                                elif part.startswith('product:'):
                                    device_info['product'] = part[8:]
                                elif part.startswith('transport_id:'):
                                    device_info['transport_id'] = part[13:]
                                    
                            devices.append(device_info)
                            self.devices_cache[serial] = device_info
                    
        self.last_scan_time = current_time
        return devices
        
    def connect_device(self, device_serial: str) -> bool:
        """
        连接指定设备
        
        Args:
            device_serial: 设备序列号
            
        Returns:
            连接是否成功
        """
        # 验证设备是否存在
        devices = self.get_devices()
        device_exists = any(d['serial'] == device_serial for d in devices)
        if not device_exists:
            return False
            
        # 尝试向设备发送命令验证连接
        success, _ = self._run_adb_command(["-s", device_serial, "shell", "echo", "connected"])
        return success
        
    def disconnect_device(self, device_serial: str) -> bool:
        """
        断开设备连接（对于网络设备）
        
        Args:
            device_serial: 设备序列号
            
        Returns:
            操作是否成功
        """
        success, _ = self._run_adb_command(["disconnect", device_serial])
        if device_serial in self.devices_cache:
            del self.devices_cache[device_serial]
        return success
        
    def get_device_resolution(self, device_serial: str) -> Optional[Tuple[int, int]]:
        """
        获取设备屏幕分辨率
        
        Args:
            device_serial: 设备序列号
            
        Returns:
            (width, height) 元组或None
        """
        success, output = self._run_adb_command([
            "-s", device_serial, "shell", "wm", "size"
        ])
        if not success:
            return None
            
        # 解析输出: "Physical size: 1080x1920"
        try:
            size_str = output.split(':')[-1].strip()
            width, height = map(int, size_str.split('x'))
            return (width, height)
        except (ValueError, IndexError):
            return None
            
    def is_device_online(self, device_serial: str) -> bool:
        """
        检查设备是否在线
        
        Args:
            device_serial: 设备序列号
            
        Returns:
            设备是否在线
        """
        devices = self.get_devices()
        for device in devices:
            if device['serial'] == device_serial and device['state'] == 'device':
                return True
        return False
        
    def get_device_model(self, device_serial: str) -> str:
        """
        获取设备型号
        
        Args:
            device_serial: 设备序列号
            
        Returns:
            设备型号字符串
        """
        success, model = self._run_adb_command([
            "-s", device_serial, "shell", "getprop", "ro.product.model"
        ])
        if success:
            return model.strip()
        return ""
        
    def get_device_android_version(self, device_serial: str) -> str:
        """
        获取Android版本
        
        Args:
            device_serial: 设备序列号
            
        Returns:
            Android版本字符串
        """
        success, version = self._run_adb_command([
            "-s", device_serial, "shell", "getprop", "ro.build.version.release"
        ])
        if success:
            return version.strip()
        return ""