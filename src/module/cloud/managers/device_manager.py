"""设备管理业务逻辑组件"""
import os
import json
import re

from module.utils.paths import get_cache_dir


class DeviceManager:
    """设备管理业务逻辑类"""
    
    def __init__(self, adb_manager, config):
        self.adb_manager = adb_manager
        self.config = config
        self.current_device = None
        self.last_connected_device = self._load_last_connected_device()
        
    def _load_last_connected_device(self):
        """加载上次连接的设备"""
        cache_dir = get_cache_dir()
        device_cache_file = os.path.join(cache_dir, "last_device.json")
        
        if os.path.exists(device_cache_file):
            with open(device_cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('last_device')
        return None
        
    def _save_last_connected_device(self, device_serial):
        """保存上次连接的设备"""
        cache_dir = get_cache_dir()
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        device_cache_file = os.path.join(cache_dir, "last_device.json")
        with open(device_cache_file, 'w', encoding='utf-8') as f:
            json.dump({'last_device': device_serial}, f)
            
    def scan_devices(self):
        """扫描设备"""
        if not self.adb_manager:
            return []
            
        devices = self.adb_manager.get_devices()
        return devices
        
    def connect_device(self, device_serial):
        """
        连接设备
        不管设备是否在可用列表中都会尝试连接，除非 connect 报错设备不存在
        """
        return self.connect_device_manual(device_serial)
        
    def connect_device_manual(self, device_serial):
        """
        手动连接设备（支持网络设备地址如 127.0.0.1:5555）
        即使设备不在当前可用列表中也会尝试连接
        """
        if not self.adb_manager:
            return False

        is_network_device = bool(re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', device_serial))

        if is_network_device:
            try:
                connect_success = self.adb_manager.connect_device(device_serial)
                if connect_success:
                    self.current_device = device_serial
                    self._save_last_connected_device(device_serial)
                    return True
            except Exception as e:
                print(f"网络设备连接失败：{e}")

        devices = self.adb_manager.get_devices()
        device_in_list = any(d.serial == device_serial for d in devices)

        if device_in_list:
            self.current_device = device_serial
            self._save_last_connected_device(device_serial)
            return True
        elif is_network_device:
            devices = self.adb_manager.get_devices()
            for d in devices:
                if device_serial in d.serial or d.serial in device_serial:
                    self.current_device = d.serial
                    self._save_last_connected_device(d.serial)
                    return True

        return False
        
    def disconnect_device(self):
        """断开设备连接"""
        if not self.current_device:
            return False
            
        if self.adb_manager:
            try:
                self.adb_manager.disconnect_device(self.current_device)
            except Exception as e:
                print(f"断开设备连接失败：{e}")
                
        self.current_device = None
        return True
        
    def get_current_device(self):
        """获取当前连接的设备"""
        return self.current_device
        
    def get_last_connected_device(self):
        """获取上次连接的设备"""
        return self.last_connected_device
