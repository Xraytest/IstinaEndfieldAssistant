"""
ADB设备管理器 - 负责ADB连接、设备发现和状态监控
"""
import subprocess
import os
import time
import json
from typing import List, Dict, Optional, Tuple
from logger import get_logger, LogCategory, LogLevel

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
        self.logger = get_logger()
        
    def _run_adb_command(self, args: List[str]) -> Tuple[bool, str]:
        """
        执行ADB命令
        
        Args:
            args: ADB命令参数列表
            
        Returns:
            (success, output) 元组
        """
        start_time = time.time()
        command_str = " ".join(args)
        
        try:
            cmd = [self.adb_path] + args
            self.logger.debug(LogCategory.ADB, f"执行ADB命令: {command_str}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=self.timeout
            )
            
            duration_ms = (time.time() - start_time) * 1000
            self.logger.log_performance("adb_command", duration_ms, command=command_str)
            
            if result.returncode == 0:
                self.logger.debug(LogCategory.ADB, f"ADB命令执行完成: {command_str}",
                                 return_code=result.returncode, duration_ms=round(duration_ms, 3))
                return True, result.stdout.strip()
            else:
                stderr = result.stderr.strip() if result.stderr else ""
                self.logger.exception(LogCategory.ADB, f"ADB命令执行异常: {command_str}",
                                     return_code=result.returncode, stderr=stderr)
                return False, stderr
        except subprocess.TimeoutExpired:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.exception(LogCategory.ADB, f"ADB命令执行超时: {command_str}",
                                 timeout_seconds=self.timeout, duration_ms=round(duration_ms, 3))
            return False, f"ADB命令超时 ({self.timeout}秒)"
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.exception(LogCategory.ADB, f"ADB命令执行异常: {command_str}",
                                 exception_type=type(e).__name__, duration_ms=round(duration_ms, 3), exc_info=True)
            return False, f"ADB命令执行异常: {str(e)}"
            
    def start_server(self) -> bool:
        """启动ADB服务器"""
        self.logger.info(LogCategory.ADB, "启动ADB服务器")
        success, output = self._run_adb_command(["start-server"])
        if success:
            self.logger.info(LogCategory.ADB, "ADB服务器启动完成")
        else:
            self.logger.exception(LogCategory.ADB, "ADB服务器启动异常")
        return success
        
    def kill_server(self) -> bool:
        """停止ADB服务器"""
        self.logger.info(LogCategory.ADB, "停止ADB服务器")
        success, output = self._run_adb_command(["kill-server"])
        if success:
            self.logger.info(LogCategory.ADB, "ADB服务器停止完成")
        else:
            self.logger.exception(LogCategory.ADB, "ADB服务器停止异常")
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
            self.logger.debug(LogCategory.ADB, "使用缓存的设备列表",
                             cached_count=len(self.devices_cache))
            return list(self.devices_cache.values())
        
        self.logger.info(LogCategory.ADB, "扫描设备列表")
        start_time = time.time()
        
        success, output = self._run_adb_command(["devices", "-l"])
        if not success:
            self.logger.exception(LogCategory.ADB, "设备列表扫描异常")
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
                            self.logger.debug(LogCategory.ADB, "发现设备", serial=serial, state=state)
                    
        self.last_scan_time = current_time
        scan_duration = (time.time() - start_time) * 1000
        self.logger.info(LogCategory.ADB, "设备列表扫描完成",
                         device_count=len(devices), duration_ms=round(scan_duration, 3))
        return devices
        
    def connect_device(self, device_serial: str) -> bool:
        """
        连接指定设备
        
        Args:
            device_serial: 设备序列号
            
        Returns:
            连接是否成功
        """
        self.logger.info(LogCategory.ADB, "连接设备", device_serial=device_serial)
        
        # 验证设备是否存在
        devices = self.get_devices()
        device_exists = any(d['serial'] == device_serial for d in devices)
        if not device_exists:
            self.logger.warning(LogCategory.ADB, "设备不存在", device_serial=device_serial)
            return False
            
        # 尝试向设备发送命令验证连接
        success, _ = self._run_adb_command(["-s", device_serial, "shell", "echo", "connected"])
        if success:
            self.logger.info(LogCategory.ADB, "设备连接完成", device_serial=device_serial)
        else:
            self.logger.exception(LogCategory.ADB, "设备连接异常", device_serial=device_serial)
        return success
        
    def connect_device_manual(self, device_serial: str) -> bool:
        """
        手动连接指定设备（不验证设备是否在扫描列表中）
        
        Args:
            device_serial: 设备序列号或网络地址（如 192.168.1.100:5555）
            
        Returns:
            连接是否成功
        """
        self.logger.info(LogCategory.ADB, "手动连接设备", device_serial=device_serial)
        
        # 检测是否为网络地址格式（包含冒号且符合主机:端口格式）
        if ':' in device_serial and self._is_network_address(device_serial):
            self.logger.debug(LogCategory.ADB, "检测到网络地址", address=device_serial)
            # 先执行 adb connect 命令建立网络连接
            connect_success, _ = self._run_adb_command(["connect", device_serial])
            if not connect_success:
                self.logger.exception(LogCategory.ADB, "网络连接建立异常", address=device_serial)
                return False
        
        # 直接尝试连接，不验证设备是否存在
        success, _ = self._run_adb_command(["-s", device_serial, "shell", "echo", "connected"])
        if success:
            self.logger.info(LogCategory.ADB, "设备连接完成", device_serial=device_serial)
            # 如果连接成功，刷新设备列表以包含新设备
            self.get_devices(force_refresh=True)
        else:
            self.logger.exception(LogCategory.ADB, "设备连接异常", device_serial=device_serial)
        return success
    
    def _is_network_address(self, address: str) -> bool:
        """检测是否为有效的网络地址格式（主机:端口）"""
        import re
        # 匹配 主机名:端口 或 IP:端口 格式
        pattern = r'^[a-zA-Z0-9.-]+:\d+$'
        return bool(re.match(pattern, address))
        
    def disconnect_device(self, device_serial: str) -> bool:
        """
        断开设备连接（对于网络设备）
        
        Args:
            device_serial: 设备序列号
            
        Returns:
            操作是否成功
        """
        self.logger.info(LogCategory.ADB, "断开设备连接", device_serial=device_serial)
        success, _ = self._run_adb_command(["disconnect", device_serial])
        if device_serial in self.devices_cache:
            del self.devices_cache[device_serial]
        if success:
            self.logger.info(LogCategory.ADB, "设备断开完成", device_serial=device_serial)
        else:
            self.logger.exception(LogCategory.ADB, "设备断开异常", device_serial=device_serial)
        return success
        
    def get_device_resolution(self, device_serial: str) -> Optional[Tuple[int, int]]:
        """
        获取设备屏幕分辨率
        
        Args:
            device_serial: 设备序列号
            
        Returns:
            (width, height) 元组或None
        """
        self.logger.debug(LogCategory.ADB, "获取设备分辨率", device_serial=device_serial)
        success, output = self._run_adb_command([
            "-s", device_serial, "shell", "wm", "size"
        ])
        if not success:
            self.logger.exception(LogCategory.ADB, "获取设备分辨率异常", device_serial=device_serial)
            return None
            
        # 解析输出: "Physical size: 1080x1920"
        try:
            size_str = output.split(':')[-1].strip()
            width, height = map(int, size_str.split('x'))
            self.logger.debug(LogCategory.ADB, "设备分辨率获取完成",
                           device_serial=device_serial, resolution=f"{width}x{height}")
            return (width, height)
        except (ValueError, IndexError) as e:
            self.logger.exception(LogCategory.ADB, "设备分辨率解析异常",
                                 device_serial=device_serial, output=output, exc_info=True)
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
                self.logger.debug(LogCategory.ADB, "设备在线状态检查",
                                device_serial=device_serial, status="online")
                return True
        self.logger.debug(LogCategory.ADB, "设备在线状态检查",
                        device_serial=device_serial, status="offline")
        return False
        
    def get_device_model(self, device_serial: str) -> str:
        """
        获取设备型号
        
        Args:
            device_serial: 设备序列号
            
        Returns:
            设备型号字符串
        """
        self.logger.debug(LogCategory.ADB, "获取设备型号", device_serial=device_serial)
        success, model = self._run_adb_command([
            "-s", device_serial, "shell", "getprop", "ro.product.model"
        ])
        if success:
            model_str = model.strip()
            self.logger.debug(LogCategory.ADB, "设备型号获取完成",
                           device_serial=device_serial, model=model_str)
            return model_str
        else:
            self.logger.exception(LogCategory.ADB, "获取设备型号异常", device_serial=device_serial)
            return ""
        
    def get_device_android_version(self, device_serial: str) -> str:
        """
        获取Android版本
        
        Args:
            device_serial: 设备序列号
            
        Returns:
            Android版本字符串
        """
        self.logger.debug(LogCategory.ADB, "获取Android版本", device_serial=device_serial)
        success, version = self._run_adb_command([
            "-s", device_serial, "shell", "getprop", "ro.build.version.release"
        ])
        if success:
            version_str = version.strip()
            self.logger.debug(LogCategory.ADB, "Android版本获取完成",
                           device_serial=device_serial, version=version_str)
            return version_str
        else:
            self.logger.exception(LogCategory.ADB, "获取Android版本异常", device_serial=device_serial)
            return ""