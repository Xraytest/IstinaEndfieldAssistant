"""设备管理业务逻辑组件"""
import os
import json
import re
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
        cache_dir = "cache"
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
        cache_dir = "cache"
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
            
        devices = self.adb_manager.get_devices()
        return devices
        
    def connect_device(self, device_serial):
        """
        连接设备
        不管设备是否在可用列表中都会尝试连接，除非connect报错设备不存在
        """
        # 使用手动连接逻辑，它支持设备不在列表中的情况
        return self.connect_device_manual(device_serial)
        
    def connect_device_manual(self, device_serial):
        """
        手动连接设备（支持网络设备地址如 127.0.0.1:5555）
        即使设备不在当前可用列表中也会尝试连接
        """
        if not self.adb_manager:
            return False

        # 检查是否是网络设备地址 (IP:PORT 格式)
        is_network_device = bool(re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', device_serial))

        if is_network_device:
            # 对于网络设备，先尝试使用 adb connect 命令连接
            try:
                connect_success = self.adb_manager.connect_device(device_serial)
                if connect_success:
                    self.current_device = device_serial
                    self._save_last_connected_device(device_serial)
                    return True
            except Exception as e:
                print(f"网络设备连接失败: {e}")

        # 对于USB设备或网络设备连接后，执行标准连接流程
        # 先检查设备是否已在列表中（可能刚连接成功）
        devices = self.adb_manager.get_devices()
        device_in_list = any(d.serial == device_serial for d in devices)

        if device_in_list:
            # 设备在列表中，标记为当前设备
            self.current_device = device_serial
            self._save_last_connected_device(device_serial)
            return True
        elif is_network_device:
            # 网络设备尝试连接后仍不在列表中，但可能已建立连接
            # 某些情况下设备需要重新扫描才能显示
            # 再次扫描设备列表
            devices = self.adb_manager.get_devices()
            for d in devices:
                # 网络设备可能在连接后显示为不同的序列号
                if device_serial in d.serial or d.serial in device_serial:
                    self.current_device = d.serial
                    self._save_last_connected_device(d.serial)
                    return True

            # 如果还是找不到，尝试直接使用设备地址作为当前设备
            # 这需要调用方在后续操作中能够处理可能的连接失败
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
        cache_dir = "cache"
        device_cache_file = os.path.join(cache_dir, "last_device.json")
        if os.path.exists(device_cache_file):
            try:
                os.remove(device_cache_file)
            except Exception as e:
                print(f"清除设备缓存失败: {e}")