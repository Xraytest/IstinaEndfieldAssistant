import subprocess
import os
import time
import json
from typing import List, Dict, Optional, Tuple
from .logger import get_logger, LogCategory, LogLevel

class ADBDeviceManager:

    def __init__(self, adb_path: Optional[str]=None, timeout: int=10):
        if adb_path is None:
            import os
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.adb_path = os.path.join(current_dir, '3rd-part', 'ADB', 'adb.exe')
            if not os.path.exists(self.adb_path):
                self.adb_path = 'adb'
        else:
            self.adb_path = adb_path
        self.timeout = timeout
        self.devices_cache: Dict[str, Dict] = {}
        self.last_scan_time: float = 0
        self.scan_interval: int = 5
        self.logger = get_logger()

    def _run_adb_command(self, args: List[str]) -> Tuple[bool, str]:
        start_time = time.time()
        command_str = ' '.join(args)
        try:
            cmd = [self.adb_path] + args
            self.logger.debug(LogCategory.ADB, f'执行ADB命令: {command_str}')
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=self.timeout)
            duration_ms = (time.time() - start_time) * 1000
            self.logger.log_performance('adb_command', duration_ms, command=command_str)
            if result.returncode == 0:
                self.logger.debug(LogCategory.ADB, f'ADB命令执行完成: {command_str}', return_code=result.returncode, duration_ms=round(duration_ms, 3))
                return (True, result.stdout.strip())
            else:
                stderr = result.stderr.strip() if result.stderr else ''
                self.logger.exception(LogCategory.ADB, f'ADB命令执行异常: {command_str}', return_code=result.returncode, stderr=stderr)
                return (False, stderr)
        except subprocess.TimeoutExpired:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.exception(LogCategory.ADB, f'ADB命令执行超时: {command_str}', timeout_seconds=self.timeout, duration_ms=round(duration_ms, 3))
            return (False, f'ADB命令超时 ({self.timeout}秒)')
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.exception(LogCategory.ADB, f'ADB命令执行异常: {command_str}', exception_type=type(e).__name__, duration_ms=round(duration_ms, 3), exc_info=True)
            return (False, f'ADB命令执行异常: {str(e)}')

    def start_server(self) -> bool:
        self.logger.info(LogCategory.ADB, '启动ADB服务器')
        success, output = self._run_adb_command(['start-server'])
        if success:
            self.logger.info(LogCategory.ADB, 'ADB服务器启动完成')
        else:
            self.logger.exception(LogCategory.ADB, 'ADB服务器启动异常')
        return success

    def kill_server(self) -> bool:
        self.logger.info(LogCategory.ADB, '停止ADB服务器')
        success, output = self._run_adb_command(['kill-server'])
        if success:
            self.logger.info(LogCategory.ADB, 'ADB服务器停止完成')
        else:
            self.logger.exception(LogCategory.ADB, 'ADB服务器停止异常')
        return success

    def get_devices(self, force_refresh: bool=False) -> List[Dict]:
        current_time = time.time()
        if not force_refresh and current_time - self.last_scan_time < self.scan_interval:
            self.logger.debug(LogCategory.ADB, '使用缓存的设备列表', cached_count=len(self.devices_cache))
            return list(self.devices_cache.values())
        self.logger.info(LogCategory.ADB, '扫描设备列表')
        start_time = time.time()
        success, output = self._run_adb_command(['devices', '-l'])
        if not success:
            self.logger.exception(LogCategory.ADB, '设备列表扫描异常')
            return []
        devices = []
        lines = output.split('\n')
        for line in lines[1:]:
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    serial = parts[0]
                    if serial and (not serial.startswith('*')) and (serial != 'List'):
                        state = parts[1]
                        if state in ['device', 'offline', 'unauthorized']:
                            device_info = {'serial': serial, 'state': state, 'model': '', 'product': '', 'transport_id': ''}
                            for part in parts[2:]:
                                if part.startswith('model:'):
                                    device_info['model'] = part[6:]
                                elif part.startswith('product:'):
                                    device_info['product'] = part[8:]
                                elif part.startswith('transport_id:'):
                                    device_info['transport_id'] = part[13:]
                            devices.append(device_info)
                            self.devices_cache[serial] = device_info
                            self.logger.debug(LogCategory.ADB, '发现设备', serial=serial, state=state)
        self.last_scan_time = current_time
        scan_duration = (time.time() - start_time) * 1000
        self.logger.info(LogCategory.ADB, '设备列表扫描完成', device_count=len(devices), duration_ms=round(scan_duration, 3))
        return devices

    def connect_device(self, device_serial: str) -> bool:
        self.logger.info(LogCategory.ADB, '连接设备', device_serial=device_serial)
        devices = self.get_devices()
        device_exists = any((d['serial'] == device_serial for d in devices))
        if not device_exists:
            self.logger.warning(LogCategory.ADB, '设备不存在', device_serial=device_serial)
            return False
        success, _ = self._run_adb_command(['-s', device_serial, 'shell', 'echo', 'connected'])
        if success:
            self.logger.info(LogCategory.ADB, '设备连接完成', device_serial=device_serial)
        else:
            self.logger.exception(LogCategory.ADB, '设备连接异常', device_serial=device_serial)
        return success

    def connect_device_manual(self, device_serial: str) -> bool:
        self.logger.info(LogCategory.ADB, '手动连接设备', device_serial=device_serial)
        if ':' in device_serial and self._is_network_address(device_serial):
            self.logger.debug(LogCategory.ADB, '检测到网络地址', address=device_serial)
            connect_success, _ = self._run_adb_command(['connect', device_serial])
            if not connect_success:
                self.logger.exception(LogCategory.ADB, '网络连接建立异常', address=device_serial)
                return False
        success, _ = self._run_adb_command(['-s', device_serial, 'shell', 'echo', 'connected'])
        if success:
            self.logger.info(LogCategory.ADB, '设备连接完成', device_serial=device_serial)
            self.get_devices(force_refresh=True)
        else:
            self.logger.exception(LogCategory.ADB, '设备连接异常', device_serial=device_serial)
        return success

    def _is_network_address(self, address: str) -> bool:
        import re
        pattern = '^[a-zA-Z0-9.-]+:\\d+$'
        if ':' not in address:
            return False
        is_valid = bool(re.match(pattern, address))
        if is_valid:
            try:
                port = int(address.split(':')[-1])
                if 1 <= port <= 65535:
                    self.logger.debug(LogCategory.ADB, f'有效的网络地址: {address}')
                    return True
                else:
                    self.logger.debug(LogCategory.ADB, f'端口号超出范围: {address}')
            except ValueError:
                self.logger.debug(LogCategory.ADB, f'端口号格式错误: {address}')
        return False

    def disconnect_device(self, device_serial: str) -> bool:
        self.logger.info(LogCategory.ADB, '断开设备连接', device_serial=device_serial)
        success, _ = self._run_adb_command(['disconnect', device_serial])
        if device_serial in self.devices_cache:
            del self.devices_cache[device_serial]
        if success:
            self.logger.info(LogCategory.ADB, '设备断开完成', device_serial=device_serial)
        else:
            self.logger.exception(LogCategory.ADB, '设备断开异常', device_serial=device_serial)
        return success

    def get_device_resolution(self, device_serial: str) -> Optional[Tuple[int, int]]:
        self.logger.debug(LogCategory.ADB, '获取设备分辨率', device_serial=device_serial)
        success, output = self._run_adb_command(['-s', device_serial, 'shell', 'wm', 'size'])
        if not success:
            self.logger.exception(LogCategory.ADB, '获取设备分辨率异常', device_serial=device_serial)
            return None
        try:
            size_str = output.split(':')[-1].strip()
            width, height = map(int, size_str.split('x'))
            self.logger.debug(LogCategory.ADB, '设备分辨率获取完成', device_serial=device_serial, resolution=f'{width}x{height}')
            return (width, height)
        except (ValueError, IndexError) as e:
            self.logger.exception(LogCategory.ADB, '设备分辨率解析异常', device_serial=device_serial, output=output, exc_info=True)
            return None

    def is_device_online(self, device_serial: str) -> bool:
        devices = self.get_devices()
        for device in devices:
            if device['serial'] == device_serial and device['state'] == 'device':
                self.logger.debug(LogCategory.ADB, '设备在线状态检查', device_serial=device_serial, status='online')
                return True
        self.logger.debug(LogCategory.ADB, '设备在线状态检查', device_serial=device_serial, status='offline')
        return False

    def get_device_model(self, device_serial: str) -> str:
        self.logger.debug(LogCategory.ADB, '获取设备型号', device_serial=device_serial)
        success, model = self._run_adb_command(['-s', device_serial, 'shell', 'getprop', 'ro.product.model'])
        if success:
            model_str = model.strip()
            self.logger.debug(LogCategory.ADB, '设备型号获取完成', device_serial=device_serial, model=model_str)
            return model_str
        else:
            self.logger.exception(LogCategory.ADB, '获取设备型号异常', device_serial=device_serial)
            return ''

    def get_device_android_version(self, device_serial: str) -> str:
        self.logger.debug(LogCategory.ADB, '获取Android版本', device_serial=device_serial)
        success, version = self._run_adb_command(['-s', device_serial, 'shell', 'getprop', 'ro.build.version.release'])
        if success:
            version_str = version.strip()
            self.logger.debug(LogCategory.ADB, 'Android版本获取完成', device_serial=device_serial, version=version_str)
            return version_str
        else:
            self.logger.exception(LogCategory.ADB, '获取Android版本异常', device_serial=device_serial)
            return ''