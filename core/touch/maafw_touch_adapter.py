"""
MaaFramework (MaaFw) 触控适配器 - 使用 MaaFramework Python 库执行触控操作
"""
import sys
import os
import time
import random
from typing import Dict, Optional, Tuple
from maa.controller import AdbController
from maa.toolkit import Toolkit
from maa.context import Context
from maa.resource import Resource
from maa.tasker import Tasker

from core.logger import get_logger, LogCategory


class MaaFwTouchConfig:
    """MaaFramework 触控配置"""
    def __init__(
        self,
        press_duration_ms: int = 50,
        press_jitter_px: int = 2,
        swipe_delay_min_ms: int = 100,
        swipe_delay_max_ms: int = 300,
        use_normalized_coords: bool = True,
        fail_on_error: bool = True
    ):
        self.press_duration_ms = press_duration_ms
        self.press_jitter_px = press_jitter_px
        self.swipe_delay_min_ms = swipe_delay_min_ms
        self.swipe_delay_max_ms = swipe_delay_max_ms
        self.use_normalized_coords = use_normalized_coords
        self.fail_on_error = fail_on_error


class MaaFwTouchExecutor:
    """
    MaaFramework 触控执行器 - 使用 MaaFramework Python 库执行触控操作

    """

    def __init__(self, adb_manager, config: Optional[MaaFwTouchConfig] = None):
        """初始化 MaaFramework 触控执行器"""
        self.adb_manager = adb_manager  # 保留用于兼容性
        self.config = config or MaaFwTouchConfig()
        self.cached_resolution = {}
        self.logger = get_logger()

        # MaaFramework 相关
        self.maa_controller = None
        self.maa_tasker = None
        self.maa_resource = None
        self.connected_devices = {}  # device_serial -> controller

        # 初始化 MaaFramework - 设置正确的DLL路径
        # DLL文件位于 client/maa_integration 目录
        maa_integration_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "maa_integration")
        if os.path.exists(maa_integration_path):
            Toolkit.init_option(maa_integration_path)
            self.logger.debug(LogCategory.MAIN, f"MaaFramework DLL路径: {maa_integration_path}")
        else:
            # 回退到当前目录
            Toolkit.init_option("./")

        self.logger.info(LogCategory.MAIN, "MaaFramework 触控执行器初始化完成",
                        normalized_coords=self.config.use_normalized_coords)

    def _get_device_resolution(self, device_serial: str) -> Optional[Tuple[int, int]]:
        """获取设备分辨率"""
        # 1. 检查缓存
        if device_serial in self.cached_resolution:
            return self.cached_resolution[device_serial]

        # 2. 尝试从 MaaFramework 控制器获取
        controller = self._get_or_create_controller(device_serial)
        if controller:
            try:
                # 执行一次截图来获取分辨率
                image = controller.post_screencap().wait().get()
                if image is not None:
                    height, width = image.shape[:2]
                    resolution = (width, height)
                    self.cached_resolution[device_serial] = resolution
                    self.logger.debug(LogCategory.MAIN,
                                    f"通过 MaaFramework 获取分辨率：{width}x{height}")
                    return resolution
            except Exception as e:
                self.logger.debug(LogCategory.MAIN,
                                f"通过 MaaFramework 获取分辨率失败：{e}")

        # 3. 回退到 ADB 方法
        if hasattr(self.adb_manager, '_run_adb_command'):
            success, output = self.adb_manager._run_adb_command([
                "-s", device_serial, "shell", "wm", "size"
            ])
            if success and "Physical size:" in output:
                try:
                    size_str = output.split(':')[-1].strip()
                    width, height = map(int, size_str.split('x'))
                    self.cached_resolution[device_serial] = (width, height)
                    self.logger.debug(LogCategory.MAIN,
                                    f"通过 wm size 获取分辨率：{width}x{height}")
                    return (width, height)
                except Exception as e:
                    self.logger.debug(LogCategory.MAIN,
                                    f"解析 wm size 输出失败：{e}")

        # 4. 返回默认值
        return (1080, 1920)

    def _get_or_create_controller(self, device_serial: str) -> Optional[AdbController]:
        """获取或创建 MaaFramework 控制器"""
        if device_serial in self.connected_devices:
            return self.connected_devices[device_serial]

        try:
            # 获取ADB路径
            adb_path = getattr(self.adb_manager, 'adb_path', 'adb')
            
            # 查找 ADB 设备
            adb_devices = Toolkit.find_adb_devices()
            target_device = None

            for device in adb_devices:
                if device.address == device_serial or device_serial in device.address:
                    target_device = device
                    break

            # 基本ADB配置 - 使用简单的JSON对象格式
            # 参考: https://github.com/MaaXYZ/MaaFramework
            import json
            adb_config = {
                "configName": "Default",
                "devices": "[Adb] devices",
                "addressRegex": "([^\\n]+)\\tdevice",
                "connect": "[Adb] connect [AdbSerial]",
                "uuid": "[Adb] -s [AdbSerial] shell settings get secure android_id",
                "screencapRawWithGzip": "[Adb] -s [AdbSerial] exec-out \"screencap | gzip -1\"",
                "screencapEncode": "[Adb] -s [AdbSerial] exec-out screencap -p",
                "click": "[Adb] -s [AdbSerial] shell input tap [x] [y]",
                "swipe": "[Adb] -s [AdbSerial] shell input swipe [x1] [y1] [x2] [y2] [duration]",
                "pressEsc": "[Adb] -s [AdbSerial] shell input keyevent 111"
            }
            config_json = json.dumps(adb_config)

            if not target_device:
                # 如果没找到精确匹配，尝试使用序列号作为地址
                self.logger.warning(LogCategory.MAIN,
                                  f"未找到设备 {device_serial}，尝试直接连接")
                
                from maa.define import MaaAdbScreencapMethodEnum, MaaAdbInputMethodEnum
                # 创建控制器
                controller = AdbController(
                    adb_path=adb_path,
                    address=device_serial,
                    screencap_methods=MaaAdbScreencapMethodEnum.Default,
                    input_methods=MaaAdbInputMethodEnum.Default,
                    config=config_json,
                )
            else:
                # 使用找到的设备信息创建控制器
                controller = AdbController(
                    adb_path=target_device.adb_path,
                    address=target_device.address,
                    screencap_methods=target_device.screencap_methods,
                    input_methods=target_device.input_methods,
                    config=config_json,
                )

            # 连接设备
            self.logger.info(LogCategory.MAIN,
                           f"正在连接设备 {device_serial}")
            connection_result = controller.post_connection().wait()
            if not connection_result:
                self.logger.error(LogCategory.MAIN,
                                f"MaaFramework 连接设备失败：{device_serial}")
                return None

            self.connected_devices[device_serial] = controller
            self.logger.info(LogCategory.MAIN,
                           f"MaaFramework 设备连接成功：{device_serial}")
            return controller

        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"创建 MaaFramework 控制器失败：{e}")
            return None

    def _normalize_to_pixel_coords(self, device_serial: str, norm_x: float, norm_y: float) -> Tuple[int, int]:
        """
        归一化坐标转换为像素坐标

        Args:
            device_serial: 设备序列号
            norm_x: 归一化X坐标 (0.0-1.0)
            norm_y: 归一化Y坐标 (0.0-1.0)

        Returns:
            (pixel_x, pixel_y) 元组
        """
        resolution = self._get_device_resolution(device_serial)
        if not resolution:
            resolution = (1080, 1920)

        width, height = resolution

        pixel_x = int(norm_x * width)
        pixel_y = int(norm_y * height)

        # 边界检查
        pixel_x = max(0, min(pixel_x, width - 1))
        pixel_y = max(0, min(pixel_y, height - 1))

        self.logger.debug(LogCategory.MAIN,
                        f"归一化坐标转换：({norm_x:.3f},{norm_y:.3f}) → ({pixel_x},{pixel_y})")

        return (pixel_x, pixel_y)

    def _validate_pixel_coords(self, device_serial: str, x: int, y: int) -> Tuple[int, int]:
        """
        验证和修正像素坐标，确保在有效范围内

        Args:
            device_serial: 设备序列号
            x: X坐标（像素）
            y: Y坐标（像素）

        Returns:
            修正后的(pixel_x, pixel_y)元组
        """
        resolution = self._get_device_resolution(device_serial)
        if not resolution:
            resolution = (1080, 1920)

        width, height = resolution

        # 自动修正超出范围的坐标
        pixel_x = max(0, min(x, width - 1))
        pixel_y = max(0, min(y, height - 1))

        if (pixel_x, pixel_y) != (x, y):
            self.logger.debug(LogCategory.MAIN,
                            f"坐标修正：({x},{y}) → ({pixel_x},{pixel_y})")

        return (pixel_x, pixel_y)

    def clear_resolution_cache(self, device_serial: Optional[str] = None):
        """清除分辨率缓存"""
        if device_serial:
            if device_serial in self.cached_resolution:
                del self.cached_resolution[device_serial]
                self.logger.debug(LogCategory.MAIN,
                                f"清除设备分辨率缓存：{device_serial}")
        else:
            self.cached_resolution.clear()
            self.logger.debug(LogCategory.MAIN, "清除所有分辨率缓存")

    def safe_press(self, device_serial: str, x: int, y: int,
                   purpose: str = "点击") -> bool:
        """安全按压"""
        # 应用MAA风格抖动
        jitter = self.config.press_jitter_px
        jitter_x = random.randint(-jitter, jitter)
        jitter_y = random.randint(-jitter, jitter)

        start_x = x + jitter_x
        start_y = y + jitter_y
        end_x = x
        end_y = y

        # 确保起点和终点不同（避免滑动距离为0）
        if start_x == end_x and start_y == end_y:
            # 添加最小偏移（1像素）
            start_x = max(0, x - 1)
            start_y = y

        self.logger.info(LogCategory.MAIN,
                        f"MAA安全按压 ({start_x},{start_y})→({end_x},{end_y}) "
                        f"duration={self.config.press_duration_ms}ms | "
                        f"抖动±{jitter} | purpose={purpose}")

        # 执行点击
        controller = self._get_or_create_controller(device_serial)
        if controller:
            try:
                # MaaFramework 的 click 方法
                result = controller.post_click(end_x, end_y).wait()
                if result:
                    self.logger.info(LogCategory.MAIN,
                                    f"MaaFramework 点击执行成功：({end_x},{end_y})")
                else:
                    self.logger.error(LogCategory.MAIN,
                                    f"MaaFramework 点击执行失败，尝试ADB回退")
                    # 回退到ADB命令
                    return self._adb_click(device_serial, end_x, end_y)
            except Exception as e:
                self.logger.warning(LogCategory.MAIN,
                                f"MaaFramework 点击执行异常，尝试ADB回退：{e}")
                return self._adb_click(device_serial, end_x, end_y)
        else:
            # 直接使用ADB命令
            self.logger.info(LogCategory.MAIN, "使用ADB命令执行点击")
            return self._adb_click(device_serial, end_x, end_y)

        # MAA风格：操作后添加随机延迟
        delay = random.uniform(self.config.swipe_delay_min_ms,
                             self.config.swipe_delay_max_ms)
        time.sleep(delay / 1000)
        self.logger.debug(LogCategory.MAIN,
                        f"MAA延迟: {delay:.1f}ms")

        return True

    def _adb_click(self, device_serial: str, x: int, y: int) -> bool:
        """使用ADB命令执行点击（回退方案）"""
        try:
            if hasattr(self.adb_manager, '_run_adb_command'):
                success, output = self.adb_manager._run_adb_command([
                    "-s", device_serial, "shell", "input", "tap", str(x), str(y)
                ])
                if success:
                    self.logger.info(LogCategory.MAIN,
                                    f"ADB点击执行成功：({x},{y})")
                    # 添加延迟
                    delay = random.uniform(self.config.swipe_delay_min_ms,
                                         self.config.swipe_delay_max_ms)
                    time.sleep(delay / 1000)
                    return True
                else:
                    self.logger.error(LogCategory.MAIN,
                                    f"ADB点击执行失败：{output}")
                    return False
            else:
                self.logger.error(LogCategory.MAIN, "ADB管理器不可用")
                return False
        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"ADB点击执行异常：{e}")
            return False

    def _adb_swipe(self, device_serial: str, x1: int, y1: int,
                   x2: int, y2: int, duration: int = 300) -> bool:
        """使用ADB命令执行滑动（回退方案）"""
        try:
            if hasattr(self.adb_manager, '_run_adb_command'):
                success, output = self.adb_manager._run_adb_command([
                    "-s", device_serial, "shell", "input", "swipe",
                    str(x1), str(y1), str(x2), str(y2), str(duration)
                ])
                if success:
                    self.logger.info(LogCategory.MAIN,
                                    f"ADB滑动执行成功：({x1},{y1})->({x2},{y2})")
                    # 添加延迟
                    delay = random.uniform(self.config.swipe_delay_min_ms,
                                         self.config.swipe_delay_max_ms)
                    time.sleep(delay / 1000)
                    return True
                else:
                    self.logger.error(LogCategory.MAIN,
                                    f"ADB滑动执行失败：{output}")
                    return False
            else:
                self.logger.error(LogCategory.MAIN, "ADB管理器不可用")
                return False
        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"ADB滑动执行异常：{e}")
            return False

    def safe_swipe(self, device_serial: str, x1: int, y1: int,
                   x2: int, y2: int, duration: int = 300,
                   purpose: str = "滑动") -> bool:
        """安全滑动"""
        # 应用MAA风格抖动到起点和终点
        jitter = self.config.press_jitter_px
        jitter_x1 = random.randint(-jitter, jitter)
        jitter_y1 = random.randint(-jitter, jitter)
        jitter_x2 = random.randint(-jitter, jitter)
        jitter_y2 = random.randint(-jitter, jitter)

        start_x = x1 + jitter_x1
        start_y = y1 + jitter_y1
        end_x = x2 + jitter_x2
        end_y = y2 + jitter_y2

        # 边界验证
        resolution = self._get_device_resolution(device_serial)
        if resolution:
            start_x = max(0, min(start_x, resolution[0] - 1))
            start_y = max(0, min(start_y, resolution[1] - 1))
            end_x = max(0, min(end_x, resolution[0] - 1))
            end_y = max(0, min(end_y, resolution[1] - 1))

        self.logger.info(LogCategory.MAIN,
                        f"MAA安全滑动 ({start_x},{start_y})→({end_x},{end_y}) "
                        f"duration={duration}ms | "
                        f"抖动±{jitter} | purpose={purpose}")

        # 执行滑动
        controller = self._get_or_create_controller(device_serial)
        if controller:
            try:
                result = controller.post_swipe(start_x, start_y, end_x, end_y, duration).wait()
                if result:
                    self.logger.info(LogCategory.MAIN,
                                    f"MaaFramework 滑动执行成功：({start_x},{start_y})→({end_x},{end_y})")
                else:
                    self.logger.warning(LogCategory.MAIN,
                                    f"MaaFramework 滑动执行失败，尝试ADB回退")
                    return self._adb_swipe(device_serial, start_x, start_y, end_x, end_y, duration)
            except Exception as e:
                self.logger.warning(LogCategory.MAIN,
                                f"MaaFramework 滑动执行异常，尝试ADB回退：{e}")
                return self._adb_swipe(device_serial, start_x, start_y, end_x, end_y, duration)
        else:
            # 直接使用ADB命令
            self.logger.info(LogCategory.MAIN, "使用ADB命令执行滑动")
            return self._adb_swipe(device_serial, start_x, start_y, end_x, end_y, duration)

        # MAA风格：操作后添加随机延迟
        delay = random.uniform(self.config.swipe_delay_min_ms,
                             self.config.swipe_delay_max_ms)
        time.sleep(delay / 1000)
        self.logger.debug(LogCategory.MAIN,
                        f"MAA延迟: {delay:.1f}ms")

        return True

    def safe_long_press(self, device_serial: str, x: int, y: int,
                        duration_ms: int = 500, purpose: str = "长按") -> bool:
        """安全长按"""
        # 应用MAA风格抖动
        jitter = self.config.press_jitter_px
        jitter_x = random.randint(-jitter, jitter)
        jitter_y = random.randint(-jitter, jitter)

        start_x = x + jitter_x
        start_y = y + jitter_y
        end_x = x
        end_y = y

        self.logger.info(LogCategory.MAIN,
                        f"MAA安全长按 ({start_x},{start_y})→({end_x},{end_y}) "
                        f"duration={duration_ms}ms | "
                        f"抖动±{jitter} | purpose={purpose}")

        # 执行长按（使用滑动实现）
        controller = self._get_or_create_controller(device_serial)
        if not controller:
            self.logger.error(LogCategory.MAIN, "无法获取 MaaFramework 控制器")
            return False

        try:
            result = controller.post_swipe(start_x, start_y, end_x, end_y, duration_ms).wait()
            if result:
                self.logger.info(LogCategory.MAIN,
                                f"MaaFramework 长按执行成功：({start_x},{start_y})→({end_x},{end_y})")
            else:
                self.logger.error(LogCategory.MAIN,
                                f"MaaFramework 长按执行失败：({start_x},{start_y})→({end_x},{end_y})")
                return False

        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"MaaFramework 长按执行异常：{e}")
            return False

        # MAA风格：操作后添加随机延迟
        delay = random.uniform(self.config.swipe_delay_min_ms,
                             self.config.swipe_delay_max_ms)
        time.sleep(delay / 1000)
        self.logger.debug(LogCategory.MAIN,
                        f"MAA延迟: {delay:.1f}ms")

        return True

    def _input_text(self, device_serial: str, text: str) -> bool:
        """执行文本输入操作"""
        if not text:
            self.logger.debug(LogCategory.MAIN, "文本输入为空，跳过")
            return True

        controller = self._get_or_create_controller(device_serial)
        if not controller:
            self.logger.error(LogCategory.MAIN, "无法获取 MaaFramework 控制器")
            return False

        try:
            result = controller.post_input_text(text).wait()
            if result:
                self.logger.debug(LogCategory.MAIN,
                                f"文本输入执行成功：{len(text)}字符")
                return True
            else:
                self.logger.error(LogCategory.MAIN,
                                f"文本输入执行失败：{text}")
                return False

        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"文本输入执行异常：{e}")
            return False

    def _press_key(self, device_serial: str, key_code: str) -> bool:
        """执行按键操作"""
        if not key_code:
            self.logger.warning(LogCategory.MAIN, "按键代码为空")
            return False

        # MaaFramework 可能不直接支持按键，回退到 ADB
        if hasattr(self.adb_manager, '_run_adb_command'):
            cmd = ["-s", device_serial, "shell", "input", "keyevent", str(key_code)]
            success, _ = self.adb_manager._run_adb_command(cmd)
            if success:
                self.logger.debug(LogCategory.MAIN,
                                f"按键操作执行成功：{key_code}")
            else:
                self.logger.exception(LogCategory.MAIN,
                                f"按键操作执行失败：{key_code}")
            return success
        else:
            self.logger.warning(LogCategory.MAIN, f"MaaFramework 不支持按键操作：{key_code}")
            return False

    def _press_system_button(self, device_serial: str, button_name: str) -> bool:
        """执行系统按钮操作"""
        button_codes = {
            'back': 4,
            'home': 3,
            'recent': 187
        }

        key_code = button_codes.get(button_name.lower())
        if key_code is None:
            self.logger.warning(LogCategory.MAIN, f"未知系统按钮：{button_name}")
            return False

        return self._press_key(device_serial, str(key_code))

    def _open_app(self, device_serial: str, app_name: str) -> bool:
        """执行打开应用操作"""
        if not app_name:
            self.logger.warning(LogCategory.MAIN, "应用名称为空")
            return False

        # 应用名称到包名的映射表
        app_package_mapping = {
            "明日方舟：终末地": "com.hypergryph.endfield",
            "明日方舟终末地": "com.hypergryph.endfield",
            "终末地": "com.hypergryph.endfield",
            "endfield": "com.hypergryph.endfield",
            "arknights": "com.hypergryph.arknights",
            "明日方舟": "com.hypergryph.arknights",
            "blue archive": "com.nexon.bluearchive",
            "蔚蓝档案": "com.nexon.bluearchive",
        }

        # 获取包名：优先使用映射表，如果app_name看起来像包名则直接使用
        package_name = app_package_mapping.get(app_name, app_name)
        
        # 如果app_name不像是包名（不包含点），尝试通过映射查找
        if '.' not in app_name and app_name not in app_package_mapping:
            self.logger.warning(LogCategory.MAIN, f"未知应用名称: {app_name}, 尝试使用原始名称")
            package_name = app_name

        self.logger.debug(LogCategory.MAIN, "执行打开应用操作",
                         app_name=app_name, package_name=package_name)
        
        # 使用 ADB monkey 命令启动应用
        if hasattr(self.adb_manager, '_run_adb_command'):
            cmd = ["-s", device_serial, "shell", "monkey", "-p", package_name,
                   "-c", "android.intent.category.LAUNCHER", "1"]
            success, _ = self.adb_manager._run_adb_command(cmd)
            if success:
                self.logger.info(LogCategory.MAIN, "打开应用操作执行完成",
                                app_name=app_name, package_name=package_name)
            else:
                self.logger.exception(LogCategory.MAIN, "打开应用操作执行失败",
                                     app_name=app_name, package_name=package_name)
            return success
        else:
            self.logger.warning(LogCategory.MAIN, f"无法打开应用：{app_name}")
            return False

    def execute_tool_call(self, device_serial: str, action: str,
                         params: Dict) -> bool:
        """统一工具执行入口"""
        self.logger.info(LogCategory.MAIN,
                        f"执行工具调用：{action}")

        # 旧格式兼容映射
        action_mapping = {
            'click': 'safe_press',
            'swipe': 'safe_swipe',
            'long_press': 'safe_long_press',
            'drag': 'safe_swipe',
            'type_text': 'input_text',
            'input': 'input_text',
            'key': 'press_key'
        }

        # 映射旧动作类型到新工具类型
        mapped_action = action_mapping.get(action, action)

        if mapped_action == "safe_press" or action == "click":
            # 获取坐标（支持多种格式）
            coordinates = params.get("coordinates")
            device_x, device_y = 0, 0

            # 格式1: 对象格式 {"start": [x, y], "end": [x, y]} - 归一化坐标
            if isinstance(coordinates, dict) and "start" in coordinates and isinstance(coordinates["start"], list):
                norm_x, norm_y = coordinates["start"]
                device_x, device_y = self._normalize_to_pixel_coords(device_serial, norm_x, norm_y)
            # 格式2: 数组格式 [x, y] - 需要判断是归一化坐标还是像素坐标
            elif isinstance(coordinates, list) and len(coordinates) >= 2:
                x, y = coordinates[0], coordinates[1]
                # 判断是否为归一化坐标（值在0-1范围内）
                if x <= 1.0 and y <= 1.0:
                    # 归一化坐标，需要转换
                    device_x, device_y = self._normalize_to_pixel_coords(device_serial, x, y)
                    self.logger.debug(LogCategory.MAIN,
                                    f"检测到归一化坐标 [{x}, {y}]，转换为像素坐标 ({device_x}, {device_y})")
                else:
                    # 像素坐标，直接使用
                    device_x, device_y = self._validate_pixel_coords(device_serial, int(x), int(y))
            # 格式3: 兼容旧格式 - 单独的 x, y 字段
            elif params.get("x") is not None or params.get("y") is not None:
                x = params.get("x", 0)
                y = params.get("y", 0)
                # 判断是否为归一化坐标
                if x <= 1.0 and y <= 1.0:
                    device_x, device_y = self._normalize_to_pixel_coords(device_serial, x, y)
                else:
                    device_x, device_y = self._validate_pixel_coords(device_serial, int(x), int(y))
            # 格式4: coordinates 为 None 但有其他坐标字段
            else:
                # 尝试从 params 中获取
                x = params.get("x", 0)
                y = params.get("y", 0)
                # 判断是否为归一化坐标
                if x <= 1.0 and y <= 1.0:
                    device_x, device_y = self._normalize_to_pixel_coords(device_serial, x, y)
                else:
                    device_x, device_y = self._validate_pixel_coords(device_serial, int(x), int(y))

            purpose = params.get("purpose", "点击")

            # 执行点击
            return self.safe_press(device_serial, device_x, device_y, purpose)

        elif mapped_action == "safe_swipe" or action == "swipe" or action == "drag":
            coordinates = params.get("coordinates")
            end_coordinates = params.get("end_coordinates")
            start_x, start_y, end_x, end_y = 0, 0, 0, 0

            # 格式1: 对象格式 {"start": [x, y], "end": [x, y]} - 归一化坐标
            if isinstance(coordinates, dict) and "start" in coordinates and "end" in coordinates:
                start_norm = coordinates["start"]
                end_norm = coordinates["end"]
                start_x, start_y = self._normalize_to_pixel_coords(device_serial, start_norm[0], start_norm[1])
                end_x, end_y = self._normalize_to_pixel_coords(device_serial, end_norm[0], end_norm[1])
            # 格式2: 数组格式 [x1, y1, x2, y2] - 像素坐标
            elif isinstance(coordinates, list) and len(coordinates) >= 4:
                start_x, start_y = self._validate_pixel_coords(device_serial, int(coordinates[0]), int(coordinates[1]))
                end_x, end_y = self._validate_pixel_coords(device_serial, int(coordinates[2]), int(coordinates[3]))
            # 格式3: coordinates 为起点数组，end_coordinates 为终点数组
            elif isinstance(coordinates, list) and isinstance(end_coordinates, list):
                start_x, start_y = self._validate_pixel_coords(device_serial, int(coordinates[0]), int(coordinates[1]))
                end_x, end_y = self._validate_pixel_coords(device_serial, int(end_coordinates[0]), int(end_coordinates[1]))
            # 格式4: 兼容旧格式 - 单独的 x1, y1, x2, y2 字段
            else:
                x1 = params.get("x1", 0)
                y1 = params.get("y1", 0)
                x2 = params.get("x2", 0)
                y2 = params.get("y2", 0)
                start_x, start_y = self._validate_pixel_coords(device_serial, int(x1), int(y1))
                end_x, end_y = self._validate_pixel_coords(device_serial, int(x2), int(y2))

            duration = params.get("duration", 300)
            purpose = params.get("purpose", "滑动")

            return self.safe_swipe(device_serial, start_x, start_y, end_x, end_y, duration, purpose)

        elif mapped_action == "safe_long_press" or action == "long_press":
            coordinates = params.get("coordinates")
            device_x, device_y = 0, 0

            # 格式1: 对象格式 {"start": [x, y]} - 归一化坐标
            if isinstance(coordinates, dict) and "start" in coordinates and isinstance(coordinates["start"], list):
                norm_x, norm_y = coordinates["start"]
                device_x, device_y = self._normalize_to_pixel_coords(device_serial, norm_x, norm_y)
            # 格式2: 数组格式 [x, y] - 像素坐标
            elif isinstance(coordinates, list) and len(coordinates) >= 2:
                device_x, device_y = self._validate_pixel_coords(device_serial, int(coordinates[0]), int(coordinates[1]))
            # 格式3: 兼容旧格式 - 单独的 x, y 字段
            else:
                x = params.get("x", 0)
                y = params.get("y", 0)
                device_x, device_y = self._validate_pixel_coords(device_serial, int(x), int(y))

            duration_ms = params.get("duration", 500)
            purpose = params.get("purpose", "长按")

            return self.safe_long_press(device_serial, device_x, device_y, duration_ms, purpose)

        elif action == "wait":
            import time
            duration_ms = params.get("duration", 1000)
            time.sleep(duration_ms / 1000.0)
            self.logger.debug(LogCategory.MAIN,
                            f"等待完成：{duration_ms}ms")
            return True

        elif mapped_action == "input_text" or action == "type_text" or action == "input":
            text = params.get("text", "")
            return self._input_text(device_serial, text)

        elif mapped_action == "press_key" or action == "key":
            key_code = params.get("key_code", params.get("key", ""))
            return self._press_key(device_serial, str(key_code))

        elif action == "system_button":
            button_name = params.get("button", "back")
            return self._press_system_button(device_serial, button_name)

        elif action == "open_app":
            # 支持两种参数格式：app_name 或 text
            app_name = params.get("app_name", params.get("text", ""))
            return self._open_app(device_serial, app_name)

        elif action == "terminate":
            self.logger.debug(LogCategory.MAIN, "终止任务动作", device_serial=device_serial)
            return True

        elif action == "answer":
            self.logger.debug(LogCategory.MAIN, "回答问题动作", device_serial=device_serial)
            return True

        else:
            self.logger.warning(LogCategory.MAIN,
                             f"未知工具类型：{action}")
            return False