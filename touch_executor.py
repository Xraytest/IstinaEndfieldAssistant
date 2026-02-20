"""
触控执行模块 - 负责执行服务端返回的触控指令
"""
import subprocess
import sys
import os
from typing import Dict, List, Any

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from adb_manager import ADBDeviceManager

class TouchExecutor:
    """触控执行器"""
    
    def __init__(self, adb_manager: ADBDeviceManager, 
                 press_duration_ms: int = 100, 
                 press_jitter_px: int = 2):
        """
        初始化触控执行器
        
        Args:
            adb_manager: ADB设备管理器实例
            press_duration_ms: 触控按压时长（毫秒）
            press_jitter_px: 触控坐标抖动范围（像素）
        """
        self.adb_manager = adb_manager
        self.press_duration_ms = press_duration_ms
        self.press_jitter_px = press_jitter_px
        self.current_device = None
        
    def execute_touch_actions(self, device_serial: str, touch_actions: List[Dict]) -> bool:
        """
        执行触控动作列表
        
        Args:
            device_serial: 设备序列号
            touch_actions: 触控动作列表
            
        Returns:
            所有动作是否执行成功
        """
        success = True
        for action in touch_actions:
            if not self._execute_single_action(device_serial, action):
                success = False
        return success
        
    def _execute_single_action(self, device_serial: str, action: Dict[str, Any]) -> bool:
        """
        执行单个触控动作
        
        Args:
            device_serial: 设备序列号
            action: 触控动作字典
            
        Returns:
            动作是否执行成功
        """
        action_type = action.get('action')
        coordinates = action.get('coordinates', [])
        
        if not coordinates or len(coordinates) != 2:
            return False
            
        # 应用坐标抖动
        x, y = self._apply_jitter(coordinates[0], coordinates[1])
        
        if action_type == 'click':
            return self._click(device_serial, x, y)
        elif action_type == 'swipe':
            end_coords = action.get('parameters', {}).get('end_coordinates', [])
            if len(end_coords) == 2:
                end_x, end_y = self._apply_jitter(end_coords[0], end_coords[1])
                duration = action.get('parameters', {}).get('duration', 300)
                return self._swipe(device_serial, x, y, end_x, end_y, duration)
        elif action_type == 'input':
            text = action.get('parameters', {}).get('text', '')
            return self._input_text(device_serial, text)
        elif action_type == 'key':
            key_code = action.get('parameters', {}).get('key_code')
            return self._press_key(device_serial, key_code)
            
        return False
        
    def _apply_jitter(self, x: float, y: float) -> tuple:
        """
        应用坐标抖动
        
        Args:
            x: X坐标（0.0-1.0归一化坐标）
            y: Y坐标（0.0-1.0归一化坐标）
            
        Returns:
            抖动后的设备坐标元组
        """
        import random
        
        # 获取设备分辨率
        if self.current_device is None:
            return (int(x * 1080), int(y * 1920))  # 默认分辨率
            
        resolution = self.adb_manager.get_device_resolution(self.current_device)
        if not resolution:
            return (int(x * 1080), int(y * 1920))  # 默认分辨率
            
        device_x = int(x * resolution[0])
        device_y = int(y * resolution[1])
        
        # 应用抖动
        jitter_x = random.randint(-self.press_jitter_px, self.press_jitter_px)
        jitter_y = random.randint(-self.press_jitter_px, self.press_jitter_px)
        
        final_x = max(0, min(device_x + jitter_x, resolution[0] - 1))
        final_y = max(0, min(device_y + jitter_y, resolution[1] - 1))
        
        return (final_x, final_y)
        
    def _click(self, device_serial: str, x: int, y: int) -> bool:
        """执行点击操作"""
        cmd = ["-s", device_serial, "shell", "input", "tap", str(x), str(y)]
        success, _ = self.adb_manager._run_adb_command(cmd)
        return success
        
    def _swipe(self, device_serial: str, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """执行滑动操作"""
        cmd = ["-s", device_serial, "shell", "input", "swipe", 
               str(x1), str(y1), str(x2), str(y2), str(duration)]
        success, _ = self.adb_manager._run_adb_command(cmd)
        return success
        
    def _input_text(self, device_serial: str, text: str) -> bool:
        """执行文本输入操作"""
        if not text:
            return True
            
        # 转义特殊字符
        escaped_text = text.replace(" ", "%s")
        cmd = ["-s", device_serial, "shell", "input", "text", escaped_text]
        success, _ = self.adb_manager._run_adb_command(cmd)
        return success
        
    def _press_key(self, device_serial: str, key_code: str) -> bool:
        """执行按键操作"""
        if not key_code:
            return False
            
        cmd = ["-s", device_serial, "shell", "input", "keyevent", key_code]
        success, _ = self.adb_manager._run_adb_command(cmd)
        return success
        
    def set_current_device(self, device_serial: str):
        """设置当前设备（用于坐标转换）"""
        self.current_device = device_serial