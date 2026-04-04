"""
MaaFramework Win32触控适配器
直接使用maafw库的Win32Controller，不搬运代码
"""
import sys
import os
import time
import ctypes
from typing import Dict, Optional, Tuple
from maa.controller import Win32Controller
from maa.define import MaaWin32ScreencapMethodEnum, MaaWin32InputMethodEnum
from maa.toolkit import Toolkit

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from ..logger import get_logger, LogCategory


class MaaFwWin32Config:
    """Win32触控配置"""
    
    def __init__(
        self,
        screencap_method: int = MaaWin32ScreencapMethodEnum.DXGI_DesktopDup,
        mouse_method: int = MaaWin32InputMethodEnum.Seize,
        keyboard_method: int = MaaWin32InputMethodEnum.Seize,
        press_duration_ms: int = 50,
        swipe_delay_min_ms: int = 100,
        swipe_delay_max_ms: int = 300,
        fail_on_error: bool = True
    ):
        self.screencap_method = screencap_method
        self.mouse_method = mouse_method
        self.keyboard_method = keyboard_method
        self.press_duration_ms = press_duration_ms
        self.swipe_delay_min_ms = swipe_delay_min_ms
        self.swipe_delay_max_ms = swipe_delay_max_ms
        self.fail_on_error = fail_on_error


class MaaFwWin32Executor:
    """MaaFramework Win32触控执行器 - 直接使用maafw库"""
    
    def __init__(self, config: Optional[MaaFwWin32Config] = None):
        self.config = config or MaaFwWin32Config()
        self.logger = get_logger()
        self.maa_controller: Optional[Win32Controller] = None
        self._hwnd = None
        self._width = 0
        self._height = 0
        self._connected = False
        
        # 初始化Toolkit
        user_path = './'
        Toolkit.init_option(user_path)
        self.logger.info(LogCategory.MAIN, 'MaaFramework Win32触控执行器初始化完成',
            screencap_method=self.config.screencap_method,
            mouse_method=self.config.mouse_method
        )
    
    def _find_window_by_title(self, window_title: str) -> Optional[int]:
        """通过窗口标题查找窗口句柄"""
        user32 = ctypes.windll.user32
        
        # 直接查找
        hwnd = user32.FindWindowW(None, window_title)
        if hwnd:
            return hwnd
        
        # 枚举窗口查找部分匹配
        matching_hwnds = []
        
        def enum_windows_callback(hwnd, _):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value
                if window_title.lower() in title.lower():
                    matching_hwnds.append(hwnd)
            return True
        
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
        
        if matching_hwnds:
            return matching_hwnds[0]
        return None
    
    def connect(self, window_title: str = "Endfield") -> bool:
        """连接到窗口"""
        try:
            # 查找窗口
            hwnd = self._find_window_by_title(window_title)
            if not hwnd:
                self.logger.error(LogCategory.MAIN, f'未找到窗口: {window_title}')
                return False
            
            self._hwnd = hwnd
            self.logger.info(LogCategory.MAIN, f'找到窗口: hwnd={hwnd}, title={window_title}')
            
            # 创建MaaFramework Win32Controller
            self.maa_controller = Win32Controller(
                hWnd=hwnd,
                screencap_method=self.config.screencap_method,
                mouse_method=self.config.mouse_method,
                keyboard_method=self.config.keyboard_method
            )
            
            # 连接
            result = self.maa_controller.post_connection().wait()
            if not result:
                self.logger.error(LogCategory.MAIN, 'MaaFramework Win32Controller连接失败')
                return False
            
            self._connected = True
            
            # 获取窗口尺寸
            self._update_window_size()
            
            self.logger.info(LogCategory.MAIN, f'MaaFramework Win32Controller连接成功',
                window_title=window_title,
                hwnd=hwnd,
                width=self._width,
                height=self._height
            )
            return True
            
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, f'Win32Controller连接异常: {e}')
            return False
    
    def _update_window_size(self):
        """更新窗口尺寸"""
        if not self.maa_controller:
            return
        
        try:
            # 通过截图获取尺寸
            result = self.maa_controller.post_screencap().wait()
            if result:
                image = self.maa_controller.cached_image
                if image is not None:
                    self._height, self._width = image.shape[:2]
                    self.logger.debug(LogCategory.MAIN, f'窗口尺寸: {self._width}x{self._height}')
        except Exception as e:
            self.logger.warning(LogCategory.MAIN, f'获取窗口尺寸失败: {e}')
            # 使用默认值
            self._width = 1920
            self._height = 1080
    
    def screencap(self) -> Optional[bytes]:
        """截图"""
        if not self._connected or not self.maa_controller:
            return None
        
        try:
            result = self.maa_controller.post_screencap().wait()
            if result:
                image = self.maa_controller.cached_image
                if image is not None:
                    # 转换为PNG bytes
                    from PIL import Image
                    import io
                    pil_image = Image.fromarray(image)
                    output_buffer = io.BytesIO()
                    pil_image.save(output_buffer, format='PNG')
                    return output_buffer.getvalue()
            return None
        except Exception as e:
            self.logger.error(LogCategory.MAIN, f'截图失败: {e}')
            return None
    
    def click(self, x: int, y: int) -> bool:
        """点击"""
        if not self._connected or not self.maa_controller:
            self.logger.error(LogCategory.MAIN, 'Win32Controller未连接')
            return False
        
        try:
            result = self.maa_controller.post_click(x, y).wait()
            if result:
                self.logger.debug(LogCategory.MAIN, f'Win32点击成功: ({x}, {y})')
                # 添加延迟
                delay = (self.config.press_duration_ms + 
                         (self.config.swipe_delay_min_ms + self.config.swipe_delay_max_ms) / 2) / 1000
                time.sleep(delay)
                return True
            else:
                self.logger.warning(LogCategory.MAIN, f'Win32点击失败: ({x}, {y})')
                return False
        except Exception as e:
            self.logger.error(LogCategory.MAIN, f'Win32点击异常: {e}')
            return False
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """滑动"""
        if not self._connected or not self.maa_controller:
            self.logger.error(LogCategory.MAIN, 'Win32Controller未连接')
            return False
        
        try:
            result = self.maa_controller.post_swipe(x1, y1, x2, y2, duration).wait()
            if result:
                self.logger.debug(LogCategory.MAIN, f'Win32滑动成功: ({x1},{y1}) -> ({x2},{y2})')
                # 添加延迟
                delay = (self.config.swipe_delay_min_ms + self.config.swipe_delay_max_ms) / 2 / 1000
                time.sleep(delay)
                return True
            else:
                self.logger.warning(LogCategory.MAIN, f'Win32滑动失败: ({x1},{y1}) -> ({x2},{y2})')
                return False
        except Exception as e:
            self.logger.error(LogCategory.MAIN, f'Win32滑动异常: {e}')
            return False
    
    def long_press(self, x: int, y: int, duration: int = 500) -> bool:
        """长按"""
        if not self._connected or not self.maa_controller:
            self.logger.error(LogCategory.MAIN, 'Win32Controller未连接')
            return False
        
        try:
            # 使用touch_down + 等待 + touch_up实现长按
            result = self.maa_controller.post_touch_down(x, y, contact=0).wait()
            if result:
                time.sleep(duration / 1000)
                result = self.maa_controller.post_touch_up(contact=0).wait()
                if result:
                    self.logger.debug(LogCategory.MAIN, f'Win32长按成功: ({x}, {y}), duration={duration}ms')
                    return True
            self.logger.warning(LogCategory.MAIN, f'Win32长按失败: ({x}, {y})')
            return False
        except Exception as e:
            self.logger.error(LogCategory.MAIN, f'Win32长按异常: {e}')
            return False
    
    def press_key(self, key: str) -> bool:
        """按键"""
        if not self._connected or not self.maa_controller:
            self.logger.error(LogCategory.MAIN, 'Win32Controller未连接')
            return False
        
        try:
            # 获取虚拟键码
            key_code = self._get_key_code(key)
            if key_code:
                result = self.maa_controller.post_click_key(key_code).wait()
                if result:
                    self.logger.debug(LogCategory.MAIN, f'Win32按键成功: {key}')
                    return True
            self.logger.warning(LogCategory.MAIN, f'Win32按键失败: {key}')
            return False
        except Exception as e:
            self.logger.error(LogCategory.MAIN, f'Win32按键异常: {e}')
            return False
    
    def _get_key_code(self, key: str) -> int:
        """获取虚拟键码"""
        key_map = {
            'enter': 13,
            'esc': 27,
            'escape': 27,
            'space': 32,
            'tab': 9,
            'backspace': 8,
            'delete': 46,
            'insert': 45,
            'home': 36,
            'end': 35,
            'pageup': 33,
            'pagedown': 34,
            'left': 37,
            'up': 38,
            'right': 39,
            'down': 40,
            'f1': 112,
            'f2': 113,
            'f3': 114,
            'f4': 115,
            'f5': 116,
            'f6': 117,
            'f7': 118,
            'f8': 119,
            'f9': 120,
            'f10': 121,
            'f11': 122,
            'f12': 123,
        }
        
        key_lower = key.lower()
        if key_lower in key_map:
            return key_map[key_lower]
        
        # 单个字符
        if len(key) == 1:
            return ord(key.upper())
        
        return 0
    
    def input_text(self, text: str) -> bool:
        """输入文本"""
        if not self._connected or not self.maa_controller:
            self.logger.error(LogCategory.MAIN, 'Win32Controller未连接')
            return False
        
        try:
            result = self.maa_controller.post_input_text(text).wait()
            if result:
                self.logger.debug(LogCategory.MAIN, f'Win32文本输入成功: {text[:20]}...')
                return True
            self.logger.warning(LogCategory.MAIN, f'Win32文本输入失败')
            return False
        except Exception as e:
            self.logger.error(LogCategory.MAIN, f'Win32文本输入异常: {e}')
            return False
    
    def disconnect(self) -> bool:
        """断开连接"""
        self._connected = False
        self._hwnd = None
        self._width = 0
        self._height = 0
        if self.maa_controller:
            # MaaFramework没有显式的disconnect方法，直接释放引用
            self.maa_controller = None
        self.logger.info(LogCategory.MAIN, 'Win32Controller已断开')
        return True
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self.maa_controller is not None
    
    def get_size(self) -> Tuple[int, int]:
        """获取窗口尺寸"""
        return (self._width, self._height)
    
    def execute_tool_call(self, action: str, params: dict, image_size: Tuple[int, int] = None) -> bool:
        """执行工具调用（统一接口）"""
        self.logger.debug(LogCategory.MAIN, f'执行Win32工具调用: {action}')
        
        action_mapping = {
            'click': 'click',
            'swipe': 'swipe',
            'long_press': 'long_press',
            'drag': 'swipe',
            'key': 'press_key',
            'press_key': 'press_key',
            'type_text': 'input_text',
            'input': 'input_text'
        }
        
        mapped_action = action_mapping.get(action.lower(), action.lower())
        
        # 使用传入的尺寸或自身尺寸
        width, height = image_size if image_size else (self._width, self._height)
        
        if mapped_action == 'click':
            coords = params.get('coordinates', [0.5, 0.5])
            if isinstance(coords, list) and len(coords) >= 2:
                rel_x, rel_y = coords[0], coords[1]
            else:
                rel_x, rel_y = 0.5, 0.5
            
            abs_x = int(rel_x * width)
            abs_y = int(rel_y * height)
            purpose = params.get('purpose', '点击')
            return self.click(abs_x, abs_y)
        
        elif mapped_action == 'swipe':
            coords = params.get('coordinates', {})
            if isinstance(coords, dict):
                start = coords.get('start', [0.3, 0.5])
                end = coords.get('end', [0.7, 0.5])
            else:
                start = params.get('coordinates', [0.3, 0.5])
                end = params.get('end_coordinates', [0.7, 0.5])
            
            x1 = int(start[0] * width)
            y1 = int(start[1] * height)
            x2 = int(end[0] * width)
            y2 = int(end[1] * height)
            duration = params.get('duration', 300)
            purpose = params.get('purpose', '滑动')
            return self.swipe(x1, y1, x2, y2, duration)
        
        elif mapped_action == 'long_press':
            coords = params.get('coordinates', [0.5, 0.5])
            if isinstance(coords, list) and len(coords) >= 2:
                rel_x, rel_y = coords[0], coords[1]
            else:
                rel_x, rel_y = 0.5, 0.5
            
            abs_x = int(rel_x * width)
            abs_y = int(rel_y * height)
            duration = params.get('duration', 500)
            return self.long_press(abs_x, abs_y, duration)
        
        elif mapped_action == 'press_key':
            key = params.get('key', params.get('key_code', ''))
            return self.press_key(str(key))
        
        elif mapped_action == 'input_text':
            text = params.get('text', '')
            return self.input_text(text)
        
        else:
            self.logger.warning(LogCategory.MAIN, f'未知的Win32触控动作: {action}')
            return False


# 创建不同控制方案的预设配置
def create_seize_controller(window_title: str = "Endfield") -> MaaFwWin32Executor:
    """创建前台独占控制器（Seize方式）"""
    config = MaaFwWin32Config(
        screencap_method=MaaWin32ScreencapMethodEnum.DXGI_DesktopDup,
        mouse_method=MaaWin32InputMethodEnum.Seize,
        keyboard_method=MaaWin32InputMethodEnum.Seize
    )
    executor = MaaFwWin32Executor(config)
    executor.connect(window_title)
    return executor


def create_send_message_controller(window_title: str = "Endfield") -> MaaFwWin32Executor:
    """创建后台SendMessage控制器"""
    config = MaaFwWin32Config(
        screencap_method=MaaWin32ScreencapMethodEnum.GDI,
        mouse_method=MaaWin32InputMethodEnum.SendMessage,
        keyboard_method=MaaWin32InputMethodEnum.SendMessage
    )
    executor = MaaFwWin32Executor(config)
    executor.connect(window_title)
    return executor


def create_post_message_controller(window_title: str = "Endfield") -> MaaFwWin32Executor:
    """创建后台PostMessage控制器"""
    config = MaaFwWin32Config(
        screencap_method=MaaWin32ScreencapMethodEnum.GDI,
        mouse_method=MaaWin32InputMethodEnum.PostMessage,
        keyboard_method=MaaWin32InputMethodEnum.PostMessage
    )
    executor = MaaFwWin32Executor(config)
    executor.connect(window_title)
    return executor