"""
触控执行模块 - 负责执行服务端返回的触控指令
"""
import subprocess
import sys
import os
import time
from typing import Dict, List, Any

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from adb_manager import ADBDeviceManager
from logger import get_logger, LogCategory

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
        self.logger = get_logger()
        
    def execute_touch_actions(self, device_serial: str, touch_actions: List[Dict]) -> bool:
        """
        执行触控动作列表
        
        Args:
            device_serial: 设备序列号
            touch_actions: 触控动作列表
            
        Returns:
            所有动作是否执行成功
        """
        self.logger.info(LogCategory.MAIN, "开始执行触控动作列表",
                        device_serial=device_serial, action_count=len(touch_actions))
        
        start_time = time.time()
        success = True
        failed_actions = []
        
        for index, action in enumerate(touch_actions):
            action_type = action.get('action', 'unknown')
            self.logger.debug(LogCategory.MAIN, "执行触控动作",
                            device_serial=device_serial, index=index, action_type=action_type)
            
            if not self._execute_single_action(device_serial, action):
                success = False
                failed_actions.append(index)
                self.logger.exception(LogCategory.MAIN, "触控动作执行异常",
                                   device_serial=device_serial, index=index, action_type=action_type)
        
        duration_ms = (time.time() - start_time) * 1000
        self.logger.info(LogCategory.MAIN, "触控动作列表执行完成",
                        device_serial=device_serial,
                        total_count=len(touch_actions),
                        success_count=len(touch_actions) - len(failed_actions),
                        failed_count=len(failed_actions),
                        failed_indices=failed_actions if failed_actions else None,
                        duration_ms=round(duration_ms, 3))
        
        self.logger.log_performance("touch_actions", duration_ms,
                                  device_serial=device_serial, count=len(touch_actions))
        
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
        
        self.logger.debug(LogCategory.MAIN, "解析触控动作",
                        device_serial=device_serial, action_type=action_type)
        
        # 定义需要坐标的动作类型
        actions_requiring_coordinates = ['click', 'long_press', 'swipe', 'drag']
        
        # 对于需要坐标的动作，检查坐标
        if action_type in actions_requiring_coordinates:
            if not coordinates or len(coordinates) != 2:
                self.logger.warning(LogCategory.MAIN, "触控动作坐标异常",
                                  device_serial=device_serial, action_type=action_type, coordinates=coordinates)
                return False
        
        # 应用坐标抖动（对于需要坐标的动作）
        x, y = None, None
        if action_type in actions_requiring_coordinates and coordinates:
            x, y = self._apply_jitter(coordinates[0], coordinates[1])
            self.logger.debug(LogCategory.MAIN, "坐标抖动应用完成",
                            device_serial=device_serial,
                            original=f"({coordinates[0]:.3f}, {coordinates[1]:.3f})",
                            jittered=f"({x}, {y})")
        
        result = False
        if action_type == 'click':
            result = self._click(device_serial, x, y)
        elif action_type == 'long_press':
            duration_ms = action.get('parameters', {}).get('duration', 500)
            result = self._long_press(device_serial, x, y, duration_ms)
        elif action_type == 'swipe':
            end_coords = action.get('parameters', {}).get('end_coordinates', [])
            if len(end_coords) == 2:
                end_x, end_y = self._apply_jitter(end_coords[0], end_coords[1])
                duration = action.get('parameters', {}).get('duration', 300)
                result = self._swipe(device_serial, x, y, end_x, end_y, duration)
        elif action_type == 'drag':
            start_coords = action.get('coordinates', [])
            end_coords = action.get('parameters', {}).get('end_coordinates', [])
            if len(start_coords) == 2 and len(end_coords) == 2:
                start_x, start_y = self._apply_jitter(start_coords[0], start_coords[1])
                end_x, end_y = self._apply_jitter(end_coords[0], end_coords[1])
                duration = action.get('parameters', {}).get('duration', 500)
                result = self._swipe(device_serial, start_x, start_y, end_x, end_y, duration)
        elif action_type == 'open_app':
            app_name = action.get('parameters', {}).get('app_name', '')
            result = self._open_app(device_serial, app_name)
        elif action_type == 'system_button':
            button_name = action.get('parameters', {}).get('button', 'back')
            result = self._press_system_button(device_serial, button_name)
        elif action_type == 'type_text':
            text = action.get('parameters', {}).get('text', '')
            result = self._input_text(device_serial, text)
        elif action_type == 'input':
            text = action.get('parameters', {}).get('text', '')
            result = self._input_text(device_serial, text)
        elif action_type == 'key':
            key_code = action.get('parameters', {}).get('key_code')
            result = self._press_key(device_serial, key_code)
        elif action_type == 'wait':
            duration_ms = action.get('parameters', {}).get('duration', 1000)
            time.sleep(duration_ms / 1000.0)
            self.logger.debug(LogCategory.MAIN, "等待动作执行完成",
                            device_serial=device_serial, duration_ms=duration_ms)
            result = True
        elif action_type == 'terminate':
            self.logger.debug(LogCategory.MAIN, "终止任务动作", device_serial=device_serial)
            result = True
        elif action_type == 'answer':
            self.logger.debug(LogCategory.MAIN, "回答问题动作", device_serial=device_serial)
            result = True
        else:
            self.logger.warning(LogCategory.MAIN, "未知触控动作类型",
                              device_serial=device_serial, action_type=action_type)
            
        return result
        
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
            self.logger.debug(LogCategory.MAIN, "使用默认分辨率进行坐标转换",
                            resolution="1080x1920")
            return (int(x * 1080), int(y * 1920))
            
        resolution = self.adb_manager.get_device_resolution(self.current_device)
        if not resolution:
            self.logger.debug(LogCategory.MAIN, "使用默认分辨率进行坐标转换",
                            device_serial=self.current_device, resolution="1080x1920")
            return (int(x * 1080), int(y * 1920))
            
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
        self.logger.debug(LogCategory.MAIN, "执行点击操作",
                        device_serial=device_serial, coordinates=f"({x}, {y})")
        cmd = ["-s", device_serial, "shell", "input", "tap", str(x), str(y)]
        success, _ = self.adb_manager._run_adb_command(cmd)
        if success:
            self.logger.debug(LogCategory.MAIN, "点击操作执行完成",
                            device_serial=device_serial, coordinates=f"({x}, {y})")
        else:
            self.logger.exception(LogCategory.MAIN, "点击操作执行异常",
                               device_serial=device_serial, coordinates=f"({x}, {y})")
        return success
        
    def _swipe(self, device_serial: str, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """执行滑动操作"""
        self.logger.debug(LogCategory.MAIN, "执行滑动操作",
                        device_serial=device_serial,
                        start=f"({x1}, {y1})", end=f"({x2}, {y2})", duration_ms=duration)
        cmd = ["-s", device_serial, "shell", "input", "swipe",
               str(x1), str(y1), str(x2), str(y2), str(duration)]
        success, _ = self.adb_manager._run_adb_command(cmd)
        if success:
            self.logger.debug(LogCategory.MAIN, "滑动操作执行完成",
                            device_serial=device_serial, duration_ms=duration)
        else:
            self.logger.exception(LogCategory.MAIN, "滑动操作执行异常",
                               device_serial=device_serial, duration_ms=duration)
        return success
        
    def _input_text(self, device_serial: str, text: str) -> bool:
        """执行文本输入操作"""
        if not text:
            self.logger.debug(LogCategory.MAIN, "文本输入为空，跳过", device_serial=device_serial)
            return True
            
        text_length = len(text)
        self.logger.debug(LogCategory.MAIN, "执行文本输入操作",
                        device_serial=device_serial, text_length=text_length)
        
        # 转义特殊字符
        escaped_text = text.replace(" ", "%s")
        cmd = ["-s", device_serial, "shell", "input", "text", escaped_text]
        success, _ = self.adb_manager._run_adb_command(cmd)
        if success:
            self.logger.debug(LogCategory.MAIN, "文本输入执行完成",
                            device_serial=device_serial, text_length=text_length)
        else:
            self.logger.exception(LogCategory.MAIN, "文本输入执行异常",
                               device_serial=device_serial, text_length=text_length)
        return success
        
    def _press_key(self, device_serial: str, key_code: str) -> bool:
        """执行按键操作"""
        if not key_code:
            self.logger.warning(LogCategory.MAIN, "按键代码为空", device_serial=device_serial)
            return False
            
        self.logger.debug(LogCategory.MAIN, "执行按键操作",
                        device_serial=device_serial, key_code=key_code)
        cmd = ["-s", device_serial, "shell", "input", "keyevent", key_code]
        success, _ = self.adb_manager._run_adb_command(cmd)
        if success:
            self.logger.debug(LogCategory.MAIN, "按键操作执行完成",
                            device_serial=device_serial, key_code=key_code)
        else:
            self.logger.exception(LogCategory.MAIN, "按键操作执行异常",
                               device_serial=device_serial, key_code=key_code)
        return success
        
    def set_current_device(self, device_serial: str):
        """设置当前设备（用于坐标转换）"""
        self.logger.debug(LogCategory.MAIN, "设置当前设备", device_serial=device_serial)
        self.current_device = device_serial
        
    def _long_press(self, device_serial: str, x: int, y: int, duration_ms: int = 500) -> bool:
        """执行长按操作"""
        self.logger.debug(LogCategory.MAIN, "执行长按操作",
                        device_serial=device_serial, coordinates=f"({x}, {y})", duration_ms=duration_ms)
        # 使用swipe命令模拟长按，起始和结束坐标相同
        cmd = ["-s", device_serial, "shell", "input", "swipe",
               str(x), str(y), str(x), str(y), str(duration_ms)]
        success, _ = self.adb_manager._run_adb_command(cmd)
        if success:
            self.logger.debug(LogCategory.MAIN, "长按操作执行完成",
                            device_serial=device_serial, duration_ms=duration_ms)
        else:
            self.logger.exception(LogCategory.MAIN, "长按操作执行异常",
                               device_serial=device_serial, duration_ms=duration_ms)
        return success
        
    def _open_app(self, device_serial: str, app_name: str) -> bool:
        """执行打开应用操作"""
        if not app_name:
            self.logger.warning(LogCategory.MAIN, "应用名称为空", device_serial=device_serial)
            return False
        
        self.logger.debug(LogCategory.MAIN, "执行打开应用操作",
                        device_serial=device_serial, app_name=app_name)
        # 使用monkey命令启动应用
        cmd = ["-s", device_serial, "shell", "monkey", "-p", app_name, "-c", "android.intent.category.LAUNCHER", "1"]
        success, _ = self.adb_manager._run_adb_command(cmd)
        if success:
            self.logger.debug(LogCategory.MAIN, "打开应用操作执行完成",
                            device_serial=device_serial, app_name=app_name)
        else:
            self.logger.exception(LogCategory.MAIN, "打开应用操作执行异常",
                               device_serial=device_serial, app_name=app_name)
        return success
        
    def _press_system_button(self, device_serial: str, button_name: str) -> bool:
        """执行系统按钮操作"""
        if not button_name:
            self.logger.warning(LogCategory.MAIN, "系统按钮名称为空", device_serial=device_serial)
            return False
        
        self.logger.debug(LogCategory.MAIN, "执行系统按钮操作",
                        device_serial=device_serial, button_name=button_name)
        
        # 系统按钮对应的keycode
        button_keycodes = {
            'back': '4',
            'home': '3',
            'menu': '82',
            'enter': '66'
        }
        
        key_code = button_keycodes.get(button_name.lower())
        if not key_code:
            self.logger.warning(LogCategory.MAIN, "未知系统按钮",
                              device_serial=device_serial, button_name=button_name)
            return False
        
        return self._press_key(device_serial, key_code)