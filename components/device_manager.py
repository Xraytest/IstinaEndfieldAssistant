"""设备管理业务逻辑组件"""
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox

class DeviceManager:
    """设备管理业务逻辑类"""
    
    def __init__(self, adb_manager, config):
        self.adb_manager = adb_manager
        self.config = config
        self.current_device = None
        self.last_connected_device = self._load_last_connected_device()
        
    def _load_last_connected_device(self):
        """加载上次连接的设备"""
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
        device_cache_file = os.path.join(cache_dir, "last_device.json")
        
        if os.path.exists(device_cache_file):
            try:
                with open(device_cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('last_device')
            except Exception as e:
                print(f"加载设备缓存失败: {e}")
        return None
        
    def _save_last_connected_device(self, device_serial):
        """保存上次连接的设备"""
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        device_cache_file = os.path.join(cache_dir, "last_device.json")
        try:
            with open(device_cache_file, 'w', encoding='utf-8') as f:
                json.dump({'last_device': device_serial}, f)
        except Exception as e:
            print(f"保存设备缓存失败: {e}")
            
    def scan_devices(self):
        """扫描设备"""
        if not self.adb_manager:
            return []
            
        devices = self.adb_manager.get_devices(force_refresh=True)
        return devices
        
    def connect_device(self, device_serial):
        """连接设备"""
        if self.adb_manager and self.adb_manager.connect_device(device_serial):
            self.current_device = device_serial
            self._save_last_connected_device(device_serial)
            return True
        return False
        
    def connect_device_manual(self, device_serial):
        """手动连接设备（不验证设备是否存在）"""
        if self.adb_manager and self.adb_manager.connect_device_manual(device_serial):
            self.current_device = device_serial
            self._save_last_connected_device(device_serial)
            return True
        return False
        
    def disconnect_device(self):
        """断开设备连接"""
        self.current_device = None
        
    def get_current_device(self):
        """获取当前连接的设备"""
        return self.current_device
        
    def get_last_connected_device(self):
        """获取上次连接的设备"""
        return self.last_connected_device
        
    def clear_last_connected_device(self):
        """清除上次连接的设备缓存"""
        self.last_connected_device = None
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
        device_cache_file = os.path.join(cache_dir, "last_device.json")
        if os.path.exists(device_cache_file):
            try:
                os.remove(device_cache_file)
            except Exception as e:
                print(f"清除设备缓存失败: {e}")