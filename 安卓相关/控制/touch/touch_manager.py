"""
统一触控管理器 - 使用MaaFramework库管理触控

支持两种触控方式：
1. Android设备: MaaTouch (通过MaaFramework AdbController)
2. PC前台窗口: Win32Controller (通过MaaFramework Win32Controller)
"""
import os
import sys
from typing import Optional, Dict, Any, Tuple
from enum import Enum

from core.logger import get_logger, LogCategory


class TouchDeviceType(Enum):
    """触控设备类型"""
    ANDROID = "android"  # 安卓设备（通过MaaTouch）
    PC = "pc"            # PC前台窗口（通过Win32Controller）


class TouchManager:
    """
    统一触控管理器 - 管理Android和PC两种触控方式
    
    使用MaaFramework库实现触控操作，无需自建协议实现。
    """
    
    def __init__(self):
        """初始化触控管理器"""
        self.logger = get_logger()
        
        # 设备类型和执行器
        self._device_type: Optional[TouchDeviceType] = None
        self._android_executor = None
        self._pc_executor = None
        
        # ADB管理器引用（Android设备需要）
        self._adb_manager = None
        
        self.logger.info(LogCategory.MAIN, "触控管理器初始化完成")
    
    @property
    def device_type(self) -> Optional[TouchDeviceType]:
        """获取当前设备类型"""
        return self._device_type
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接设备"""
        if self._device_type == TouchDeviceType.ANDROID:
            return self._android_executor is not None
        elif self._device_type == TouchDeviceType.PC:
            return self._pc_executor is not None and self._pc_executor._connected
        return False
    
    def connect_android(self, adb_manager, device_serial: str, config: Optional[Dict] = None) -> bool:
        """
        连接Android设备
        
        Args:
            adb_manager: ADB设备管理器实例
            device_serial: 设备序列号
            config: 触控配置（可选）
            
        Returns:
            是否连接成功
        """
        try:
            from .maafw_touch_adapter import MaaFwTouchExecutor, MaaFwTouchConfig
            
            self._adb_manager = adb_manager
            
            # 创建配置
            if config:
                touch_config = MaaFwTouchConfig(
                    press_duration_ms=config.get('press_duration_ms', 50),
                    press_jitter_px=config.get('press_jitter_px', 2),
                    swipe_delay_min_ms=config.get('swipe_delay_min_ms', 100),
                    swipe_delay_max_ms=config.get('swipe_delay_max_ms', 300),
                    use_normalized_coords=config.get('use_normalized_coords', True),
                    fail_on_error=config.get('fail_on_error', True)
                )
            else:
                touch_config = MaaFwTouchConfig()
            
            # 创建执行器
            self._android_executor = MaaFwTouchExecutor(
                adb_manager=adb_manager,
                config=touch_config
            )
            
            self._device_type = TouchDeviceType.ANDROID
            
            self.logger.info(LogCategory.MAIN, "Android设备触控连接成功",
                           device_serial=device_serial,
                           device_type="MaaTouch")
            return True
            
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, f"Android设备触控连接失败: {e}")
            return False
    
    def connect_pc(self, window_title: str = "Endfield", config: Optional[Dict] = None) -> bool:
        """
        连接PC前台窗口
        
        Args:
            window_title: 窗口标题
            config: 触控配置（可选）
            
        Returns:
            是否连接成功
        """
        try:
            from .maafw_win32_adapter import MaaFwWin32Executor, MaaFwWin32Config
            from maa.define import MaaWin32ScreencapMethodEnum, MaaWin32InputMethodEnum
            
            # 创建配置
            if config:
                win32_config = MaaFwWin32Config(
                    screencap_method=config.get('screencap_method', MaaWin32ScreencapMethodEnum.DXGI_DesktopDup),
                    mouse_method=config.get('mouse_method', MaaWin32InputMethodEnum.Seize),
                    keyboard_method=config.get('keyboard_method', MaaWin32InputMethodEnum.Seize),
                    press_duration_ms=config.get('press_duration_ms', 50),
                    swipe_delay_min_ms=config.get('swipe_delay_min_ms', 100),
                    swipe_delay_max_ms=config.get('swipe_delay_max_ms', 300),
                    fail_on_error=config.get('fail_on_error', True)
                )
            else:
                win32_config = MaaFwWin32Config()
            
            # 创建执行器
            self._pc_executor = MaaFwWin32Executor(config=win32_config)
            
            # 连接窗口
            if not self._pc_executor.connect(window_title):
                self.logger.error(LogCategory.MAIN, f"PC窗口连接失败: {window_title}")
                return False
            
            self._device_type = TouchDeviceType.PC
            
            self.logger.info(LogCategory.MAIN, "PC窗口触控连接成功",
                           window_title=window_title,
                           device_type="Win32Controller")
            return True
            
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, f"PC窗口触控连接失败: {e}")
            return False
    
    def disconnect(self) -> None:
        """断开当前设备连接"""
        if self._device_type == TouchDeviceType.ANDROID:
            # Android执行器无需显式断开
            self._android_executor = None
            self._adb_manager = None
            
        elif self._device_type == TouchDeviceType.PC:
            if self._pc_executor:
                # Win32执行器无需显式断开
                self._pc_executor = None
        
        self._device_type = None
        self.logger.info(LogCategory.MAIN, "触控设备已断开")
    
    def safe_press(self, device_serial: str, x: int, y: int, purpose: str = "点击") -> bool:
        """
        安全按压
        
        Args:
            device_serial: 设备序列号（Android设备需要，PC设备可忽略）
            x: X坐标（像素）
            y: Y坐标（像素）
            purpose: 操作目的说明
            
        Returns:
            操作是否成功
        """
        if self._device_type == TouchDeviceType.ANDROID and self._android_executor:
            return self._android_executor.safe_press(device_serial, x, y, purpose)
        elif self._device_type == TouchDeviceType.PC and self._pc_executor:
            return self._pc_executor.click(x, y)
        else:
            self.logger.error(LogCategory.MAIN, "触控设备未连接")
            return False
    
    def safe_swipe(self, device_serial: str, x1: int, y1: int, x2: int, y2: int, 
                   duration: int = 300, purpose: str = "滑动") -> bool:
        """
        安全滑动
        
        Args:
            device_serial: 设备序列号（Android设备需要，PC设备可忽略）
            x1: 起始X坐标
            y1: 起始Y坐标
            x2: 结束X坐标
            y2: 结束Y坐标
            duration: 持续时间（毫秒）
            purpose: 操作目的说明
            
        Returns:
            操作是否成功
        """
        if self._device_type == TouchDeviceType.ANDROID and self._android_executor:
            return self._android_executor.safe_swipe(device_serial, x1, y1, x2, y2, duration, purpose)
        elif self._device_type == TouchDeviceType.PC and self._pc_executor:
            return self._pc_executor.swipe(x1, y1, x2, y2, duration)
        else:
            self.logger.error(LogCategory.MAIN, "触控设备未连接")
            return False
    
    def safe_long_press(self, device_serial: str, x: int, y: int, 
                        duration_ms: int = 500, purpose: str = "长按") -> bool:
        """
        安全长按
        
        Args:
            device_serial: 设备序列号（Android设备需要，PC设备可忽略）
            x: X坐标
            y: Y坐标
            duration_ms: 持续时间（毫秒）
            purpose: 操作目的说明
            
        Returns:
            操作是否成功
        """
        if self._device_type == TouchDeviceType.ANDROID and self._android_executor:
            return self._android_executor.safe_long_press(device_serial, x, y, duration_ms, purpose)
        elif self._device_type == TouchDeviceType.PC and self._pc_executor:
            return self._pc_executor.swipe(x, y, x, y, duration_ms)
        else:
            self.logger.error(LogCategory.MAIN, "触控设备未连接")
            return False
    
    def execute_tool_call(self, device_serial: str, action: str, params: Dict) -> bool:
        """
        统一工具执行入口
        
        Args:
            device_serial: 设备序列号（Android设备需要，PC设备可忽略）
            action: 动作类型
            params: 动作参数
            
        Returns:
            操作是否成功
        """
        if self._device_type == TouchDeviceType.ANDROID and self._android_executor:
            return self._android_executor.execute_tool_call(device_serial, action, params)
        elif self._device_type == TouchDeviceType.PC and self._pc_executor:
            return self._execute_pc_tool_call(action, params)
        else:
            self.logger.error(LogCategory.MAIN, "触控设备未连接")
            return False
    
    def _execute_pc_tool_call(self, action: str, params: Dict) -> bool:
        """执行PC工具调用"""
        import time
        import random
        
        # 动作映射
        action_mapping = {
            'click': 'safe_press',
            'swipe': 'safe_swipe',
            'long_press': 'safe_long_press',
            'drag': 'safe_swipe'
        }
        
        mapped_action = action_mapping.get(action, action)
        
        if mapped_action in ('safe_press', 'click'):
            coordinates = params.get("coordinates")
            x, y = 0, 0
            
            # 格式1: 对象格式 {"start": [x, y]}
            if isinstance(coordinates, dict) and "start" in coordinates:
                x, y = coordinates["start"]
            # 格式2: 数组格式 [x, y]
            elif isinstance(coordinates, list) and len(coordinates) >= 2:
                x, y = coordinates[0], coordinates[1]
            # 格式3: 单独的 x, y 字段
            else:
                x = params.get("x", 0)
                y = params.get("y", 0)
            
            return self._pc_executor.click(int(x), int(y))
        
        elif mapped_action in ('safe_swipe', 'swipe', 'drag'):
            coordinates = params.get("coordinates")
            end_coordinates = params.get("end_coordinates")
            x1, y1, x2, y2 = 0, 0, 0, 0
            
            # 格式1: 对象格式 {"start": [x, y], "end": [x, y]}
            if isinstance(coordinates, dict) and "start" in coordinates and "end" in coordinates:
                x1, y1 = coordinates["start"]
                x2, y2 = coordinates["end"]
            # 格式2: 数组格式 [x1, y1, x2, y2]
            elif isinstance(coordinates, list) and len(coordinates) >= 4:
                x1, y1 = coordinates[0], coordinates[1]
                x2, y2 = coordinates[2], coordinates[3]
            # 格式3: coordinates 为起点，end_coordinates 为终点
            elif isinstance(coordinates, list) and isinstance(end_coordinates, list):
                x1, y1 = coordinates[0], coordinates[1]
                x2, y2 = end_coordinates[0], end_coordinates[1]
            # 格式4: 单独的 x1, y1, x2, y2 字段
            else:
                x1 = params.get("x1", 0)
                y1 = params.get("y1", 0)
                x2 = params.get("x2", 0)
                y2 = params.get("y2", 0)
            
            duration = params.get("duration", 300)
            return self._pc_executor.swipe(int(x1), int(y1), int(x2), int(y2), duration)
        
        elif mapped_action in ('safe_long_press', 'long_press'):
            coordinates = params.get("coordinates")
            x, y = 0, 0
            
            # 格式1: 对象格式 {"start": [x, y]}
            if isinstance(coordinates, dict) and "start" in coordinates:
                x, y = coordinates["start"]
            # 格式2: 数组格式 [x, y]
            elif isinstance(coordinates, list) and len(coordinates) >= 2:
                x, y = coordinates[0], coordinates[1]
            # 格式3: 单独的 x, y 字段
            else:
                x = params.get("x", 0)
                y = params.get("y", 0)
            
            duration_ms = params.get("duration", 500)
            return self._pc_executor.swipe(int(x), int(y), int(x), int(y), duration_ms)
        
        elif action == "wait":
            duration_ms = params.get("duration", 1000)
            time.sleep(duration_ms / 1000.0)
            return True
        
        elif action == "open_app":
            # PC模式打开应用（窗口已固定为Endfield）
            self.logger.info(LogCategory.MAIN, f"PC模式打开应用: {params.get('app_name', 'Endfield')}")
            return True
        
        elif action == "key":
            key_code = params.get("key_code", params.get("key", ""))
            return self._pc_executor.press_key(str(key_code))
        
        else:
            self.logger.warning(LogCategory.MAIN, f"PC不支持的动作: {action}")
            return False
    
    def get_resolution(self, device_serial: str = None) -> Optional[Tuple[int, int]]:
        """
        获取设备分辨率
        
        Args:
            device_serial: 设备序列号（Android设备需要）
            
        Returns:
            (width, height) 元组或 None
        """
        if self._device_type == TouchDeviceType.ANDROID and self._android_executor:
            return self._android_executor._get_device_resolution(device_serial)
        elif self._device_type == TouchDeviceType.PC and self._pc_executor:
            return (self._pc_executor._width, self._pc_executor._height)
        return None
    
    def screencap(self, device_serial: str = None) -> Optional[bytes]:
        """
        截图（仅PC模式支持）
        
        Args:
            device_serial: 设备序列号（Android设备需要）
            
        Returns:
            PNG格式的截图数据
        """
        if self._device_type == TouchDeviceType.PC and self._pc_executor:
            return self._pc_executor.screencap()
        else:
            self.logger.warning(LogCategory.MAIN, "截图仅PC模式支持，Android请使用ScreenCapture")
            return None