"""
MAA DLL 触控适配器 - 使用 MaaTouch 方案执行触控操作
"""
import sys
import os
import json
import ctypes
import time
import socket
import random
import subprocess
from typing import Dict, Optional, Tuple
from enum import IntEnum, auto, unique

# 添加当前目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 添加 maa_integration 到路径
maa_integration_path = os.path.join(current_dir, 'maa_integration')
if maa_integration_path not in sys.path:
    sys.path.insert(0, maa_integration_path)

from ..logger import get_logger, LogCategory


try:
    from maa_integration.asst import Asst
    from maa_integration.asst.utils import JSON, InstanceOptionType, StaticOptionType
    MAA_AVAILABLE = True
except ImportError as e:
    MAA_AVAILABLE = False
    Asst = None
    InstanceOptionType = None
    StaticOptionType = None
    JSON = None
    print(f"MAA DLL not available: {e}")


class TouchMethod:
    """触控方法枚举（兼容旧版）"""
    ADB_INPUT = "adb_input"
    MINITOUCH = "minitouch"
    MAATOUCH = "maatouch"
    
    def __init__(self, value: str = "adb_input"):
        self.value = value
    
    def __str__(self):
        return self.value
    
    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        if isinstance(other, TouchMethod):
            return self.value == other.value
        return False


class MaaTouchConfig:
    """触控配置（兼容旧版）"""
    def __init__(
        self,
        press_duration_ms: int = 50,
        press_jitter_px: int = 2,
        swipe_delay_min_ms: int = 100,
        swipe_delay_max_ms: int = 300,
        use_normalized_coords: bool = True,
        touch_method: str = TouchMethod.MAATOUCH,
        enable_swipe_with_pause: bool = False,
        swipe_interval_ms: int = 2,
        minitouch_binary_path: str = "",
        maatouch_binary_path: str = "",
        fail_on_error: bool = True
    ):
        self.press_duration_ms = press_duration_ms
        self.press_jitter_px = press_jitter_px
        self.swipe_delay_min_ms = swipe_delay_min_ms
        self.swipe_delay_max_ms = swipe_delay_max_ms
        self.use_normalized_coords = use_normalized_coords
        self.touch_method = touch_method
        self.enable_swipe_with_pause = enable_swipe_with_pause
        self.swipe_interval_ms = swipe_interval_ms
        self.minitouch_binary_path = minitouch_binary_path
        self.maatouch_binary_path = maatouch_binary_path
        self.fail_on_error = fail_on_error


class TouchExecutor:
    """
    触控执行器 - 使用 MaaTouch 方案执行触控操作
    
    """
    
    def __init__(self, adb_manager, config: Optional[MaaTouchConfig] = None):
        """初始化触控执行器"""
        self.adb_manager = adb_manager
        self.config = config or MaaTouchConfig()
        self.cached_resolution = {}
        self.logger = get_logger()

        # MaaTouch TCP 连接
        self.touch_socket = None
        self.touch_server_available = False
        self.touch_server_process = None  # 后台服务进程

        self.logger.info(LogCategory.MAIN, "触控执行器初始化完成（使用 MaaTouch）",
                        method=self.config.touch_method.value if hasattr(self.config.touch_method, 'value') else self.config.touch_method,
                        normalized_coords=self.config.use_normalized_coords)
    
    def _convert_coordinates(self, device_serial: str, x, y) -> tuple:
        """坐标转换"""
        resolution = self._get_device_resolution(device_serial)
        if not resolution:
            resolution = (1080, 1920)
        
        width, height = resolution
        
        # 判断坐标类型
        if self.config.use_normalized_coords and 0 <= x <= 1 and 0 <= y <= 1:
            # 归一化坐标 [0, 1] → 像素坐标
            device_x = int(x * width)
            device_y = int(y * height)
            self.logger.debug(LogCategory.MAIN,
                            f"归一化坐标转换：({x:.3f},{y:.3f}) → ({device_x},{device_y})")
        else:
            # 像素坐标验证
            device_x = int(x)
            device_y = int(y)
            self.logger.debug(LogCategory.MAIN,
                            f"像素坐标验证：({x},{y}) → ({device_x},{device_y})")
        
        # 自动修正超出范围的坐标
        device_x = max(0, min(device_x, width - 1))
        device_y = max(0, min(device_y, height - 1))
        
        return (device_x, device_y)
    
    def _to_pixel_coords(self, device_serial: str, norm_x: float, norm_y: float) -> Tuple[int, int]:
        """归一化坐标转换为像素坐标"""
        resolution = self._get_device_resolution(device_serial)
        if not resolution:
            resolution = (1080, 1920)
        
        width, height = resolution
        
        pixel_x = int(norm_x * width)
        pixel_y = int(norm_y * height)
        
        # 边界检查
        pixel_x = max(0, min(pixel_x, width - 1))
        pixel_y = max(0, min(pixel_y, height - 1))
        
        return (pixel_x, pixel_y)
    
    def _get_device_resolution(self, device_serial: str) -> Optional[Tuple[int, int]]:
        """获取设备分辨率"""
        # 1. 检查缓存
        if device_serial in self.cached_resolution:
            return self.cached_resolution[device_serial]
        
        # 2. 通过 wm size 获取
        resolution = self._get_resolution_via_wm(device_serial)
        if resolution:
            self.cached_resolution[device_serial] = resolution
            return resolution
        
        # 3. 返回默认值
        return (1080, 1920)
    
    def _get_resolution_via_wm(self, device_serial: str) -> Optional[Tuple[int, int]]:
        """通过 wm size 命令获取分辨率"""
        success, output = self.adb_manager._run_adb_command([
            "-s", device_serial, "shell", "wm", "size"
        ])
        if success and "Physical size:" in output:
            try:
                size_str = output.split(':')[-1].strip()
                width, height = map(int, size_str.split('x'))
                self.logger.debug(LogCategory.MAIN,
                                f"通过 wm size 获取分辨率：{width}x{height}")
                return (width, height)
            except Exception as e:
                self.logger.debug(LogCategory.MAIN,
                                f"解析 wm size 输出失败：{e}")
        return None
    
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
    
    def _get_device_abi(self, device_serial: str) -> str:
        """获取设备架构"""
        # 尝试获取支持的 ABI 列表
        success, output = self.adb_manager._run_adb_command([
            "-s", device_serial, "shell", "getprop", "ro.product.cpu.abilist"
        ])
        
        if success and output.strip():
            abis = [abi.strip() for abi in output.split(',') if abi.strip()]
            supported_archs = ['x86_64', 'x86', 'arm64-v8a', 'armeabi-v7a', 'armeabi']
            for arch in supported_archs:
                if arch in abis:
                    return arch
        
        # 回退到单个 ABI
        success, output = self.adb_manager._run_adb_command([
            "-s", device_serial, "shell", "getprop", "ro.product.cpu.abi"
        ])
        
        if success and output.strip():
            return output.strip()
        
        return 'arm64-v8a'
    
    def _ensure_maatouch(self, device_serial: str) -> bool:
        """确保 MaaTouch 服务已启动"""
        if self.touch_server_available:
            return True

        # 获取设备架构
        device_abi = self._get_device_abi(device_serial)
        self.logger.info(LogCategory.MAIN, f"检测到设备架构: {device_abi}", device_serial=device_serial)

        # 根据设备架构选择正确的二进制文件（优先使用架构特定的二进制）
        arch_binary_path = os.path.join(current_dir, "device_control_system", "minitouch_resources", device_abi, "minitouch")
        if os.path.exists(arch_binary_path):
            binary_path = arch_binary_path
        elif self.config.maatouch_binary_path:
            binary_path = self.config.maatouch_binary_path
        else:
            binary_path = os.path.join(current_dir, "device_control_system", "minitouch_resources", "maatouch", "minitouch")

        if not os.path.exists(binary_path):
            self.logger.warning(LogCategory.MAIN, f"MaaTouch 二进制文件不存在: {binary_path}")
            return False

        self.logger.info(LogCategory.MAIN, f"使用 MaaTouch 二进制: {binary_path}", arch=device_abi)

        # 推送二进制文件到设备
        device_path = "/data/local/tmp/maatouch"
        self.logger.info(LogCategory.MAIN, f"推送 maatouch 到设备: {device_serial}")

        cmd = ["-s", device_serial, "push", binary_path, device_path]
        success, output = self.adb_manager._run_adb_command(cmd)
        if not success:
            self.logger.exception(LogCategory.MAIN, f"推送 maatouch 失败: {output}")
            return False

        # 设置执行权限
        cmd = ["-s", device_serial, "shell", "chmod", "755", device_path]
        self.adb_manager._run_adb_command(cmd)

        # 建立端口转发
        self.logger.info(LogCategory.MAIN, f"建立端口转发: {device_serial}")
        cmd = ["-s", device_serial, "forward", "tcp:1717", "tcp:1717"]
        self.adb_manager._run_adb_command(cmd)

        # 启动 maatouch 服务 - 使用 Popen 启动后台进程，不等待结束
        self.logger.info(LogCategory.MAIN, f"启动 maatouch 服务: {device_serial}")

        # 构建完整的 ADB 命令
        adb_cmd = [self.adb_manager.adb_path, "-s", device_serial, "shell", device_path]

        # 使用 Popen 启动后台进程
        try:
            self.touch_server_process = subprocess.Popen(
                adb_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE
            )
            self.logger.debug(LogCategory.MAIN,
                            f"MaaTouch 服务进程启动成功, PID: {self.touch_server_process.pid}")
        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"启动 maatouch 服务进程失败: {e}")
            return False

        # 等待服务启动
        time.sleep(0.5)

        # 建立 TCP 连接
        try:
            self.touch_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.touch_socket.settimeout(5.0)
            self.touch_socket.connect(("127.0.0.1", 1717))
            self.logger.info(LogCategory.MAIN,
                            "MaaTouch TCP 连接建立成功")
            self.touch_server_available = True
            return True
        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"MaaTouch TCP 连接失败：{e}")
            # 清理失败的进程
            if self.touch_server_process:
                try:
                    self.touch_server_process.terminate()
                    self.touch_server_process.wait(timeout=1)
                except:
                    pass
                self.touch_server_process = None
            return False
    
    def _send_maatouch_command(self, command: str):
        """发送 MaaTouch 协议命令"""
        if not self.touch_socket:
            raise RuntimeError("MaaTouch TCP 连接未建立")
        
        try:
            # 发送协议命令
            self.touch_socket.sendall((command + "\n").encode('utf-8'))
            self.logger.debug(LogCategory.MAIN,
                            f"发送 maatouch 命令：{command.strip()}")
        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"发送 maatouch 命令失败：{e}")
            raise
    
    def _release_touch_server(self, device_serial: str):
        """释放触控服务资源"""
        # 关闭 TCP 连接
        if self.touch_socket:
            try:
                self.touch_socket.close()
            except:
                pass
            self.touch_socket = None

        self.touch_server_available = False

        # 终止后台进程
        if self.touch_server_process:
            try:
                self.touch_server_process.terminate()
                self.touch_server_process.wait(timeout=2)
                self.logger.debug(LogCategory.MAIN,
                                f"触控服务进程已终止, PID: {self.touch_server_process.pid}")
            except subprocess.TimeoutExpired:
                self.touch_server_process.kill()
                self.logger.debug(LogCategory.MAIN,
                                f"触控服务进程强制终止, PID: {self.touch_server_process.pid}")
            except Exception as e:
                self.logger.exception(LogCategory.MAIN,
                                    f"终止触控服务进程失败: {e}")
            finally:
                self.touch_server_process = None

        # 移除端口转发
        cmd = ["-s", device_serial, "forward", "--remove", "tcp:1717"]
        self.adb_manager._run_adb_command(cmd)

        # 清理设备上的服务进程
        cmd = ["-s", device_serial, "shell", "pkill", "-f", "maatouch"]
        self.adb_manager._run_adb_command(cmd)

        self.logger.info(LogCategory.MAIN, "MaaTouch 服务已释放")
    
    def safe_press(self, device_serial: str, x: int, y: int,
                   purpose: str = "点击") -> bool:
        """点击操作"""
        # 确保 MaaTouch 服务已启动
        if not self._ensure_maatouch(device_serial):
            self.logger.error(LogCategory.MAIN, "MaaTouch 服务启动失败")
            return False
        
        # 应用 MAA 风格抖动
        jitter = self.config.press_jitter_px
        jitter_x = random.randint(-jitter, jitter)
        jitter_y = random.randint(-jitter, jitter)
        
        start_x = x + jitter_x
        start_y = y + jitter_y
        end_x = x
        end_y = y
        
        # 确保起点和终点不同（避免滑动距离为 0）
        if start_x == end_x and start_y == end_y:
            # 添加最小偏移（1 像素）
            start_x = max(0, x - 1)
            start_y = y
        
        self.logger.info(LogCategory.MAIN,
                        f"MAA 安全按压 ({start_x},{start_y})→({end_x},{end_y}) "
                        f"duration={self.config.press_duration_ms}ms | "
                        f"抖动±{jitter} | purpose={purpose}")
        
        try:
            # 获取设备分辨率用于归一化
            resolution = self._get_device_resolution(device_serial)
            if not resolution:
                resolution = (1080, 1920)
            
            max_x, max_y = resolution
            
            # 发送 MaaTouch 协议命令
            # 下按
            self._send_maatouch_command(f"contact 0 d {start_x} {start_y} 50")
            time.sleep(0.001)
            
            # 移动到终点
            self._send_maatouch_command(f"contact 0 m {end_x} {end_y} 50")
            time.sleep(self.config.press_duration_ms / 1000)
            
            # 抬起
            self._send_maatouch_command("contact 0 u 0 0 0")
            
            self.logger.info(LogCategory.MAIN,
                            f"MaaTouch 点击执行成功：({end_x},{end_y})")
            
            # MAA 风格：操作后添加随机延迟
            delay = random.uniform(self.config.swipe_delay_min_ms,
                                 self.config.swipe_delay_max_ms)
            time.sleep(delay / 1000)
            
            return True
        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"MaaTouch 点击执行失败：{e}")
            return False
    
    def safe_swipe(self, device_serial: str, x1: int, y1: int,
                   x2: int, y2: int, duration: int = 300,
                   purpose: str = "滑动") -> bool:
        """滑动操作"""
        # 确保 MaaTouch 服务已启动
        if not self._ensure_maatouch(device_serial):
            self.logger.error(LogCategory.MAIN, "MaaTouch 服务启动失败")
            return False
        
        # 边界验证
        resolution = self._get_device_resolution(device_serial)
        if resolution:
            x1 = max(0, min(x1, resolution[0] - 1))
            y1 = max(0, min(y1, resolution[1] - 1))
            x2 = max(0, min(x2, resolution[0] - 1))
            y2 = max(0, min(y2, resolution[1] - 1))
        
        self.logger.info(LogCategory.MAIN,
                        f"滑动 ({x1},{y1})→({x2},{y2}) duration={duration}ms | purpose={purpose}")
        
        try:
            # 获取设备分辨率用于归一化
            resolution = self._get_device_resolution(device_serial)
            if not resolution:
                resolution = (1080, 1920)
            
            max_x, max_y = resolution
            
            # 发送 MaaTouch 协议命令
            # 下按
            self._send_maatouch_command(f"contact 0 d {x1} {y1} 50")
            time.sleep(0.001)
            
            # 移动到终点
            self._send_maatouch_command(f"contact 0 m {x2} {y2} 50")
            time.sleep(duration / 1000)
            
            # 抬起
            self._send_maatouch_command("contact 0 u 0 0 0")
            
            self.logger.info(LogCategory.MAIN,
                            f"MaaTouch 滑动执行成功：({x1},{y1})→({x2},{y2})")
            return True
        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"MaaTouch 滑动执行失败：{e}")
            return False
    
    def safe_long_press(self, device_serial: str, x: int, y: int,
                        duration_ms: int = 500, purpose: str = "长按") -> bool:
        """长按操作"""
        # 确保 MaaTouch 服务已启动
        if not self._ensure_maatouch(device_serial):
            self.logger.error(LogCategory.MAIN, "MaaTouch 服务启动失败")
            return False
        
        self.logger.info(LogCategory.MAIN,
                        f"长按 ({x},{y}) duration={duration_ms}ms | purpose={purpose}")
        
        try:
            # 获取设备分辨率用于归一化
            resolution = self._get_device_resolution(device_serial)
            if not resolution:
                resolution = (1080, 1920)
            
            max_x, max_y = resolution
            
            # 发送 MaaTouch 协议命令
            # 下按
            self._send_maatouch_command(f"contact 0 d {x} {y} 50")
            time.sleep(0.001)
            
            # 保持按压（微小移动避免被识别为点击）
            self._send_maatouch_command(f"contact 0 m {x+1} {y+1} 50")
            time.sleep(duration_ms / 1000)
            
            # 抬起
            self._send_maatouch_command("contact 0 u 0 0 0")
            
            self.logger.info(LogCategory.MAIN,
                            f"MaaTouch 长按执行成功：({x},{y})")
            return True
        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"MaaTouch 长按执行失败：{e}")
            return False
    
    def _input_text(self, device_serial: str, text: str) -> bool:
        """执行文本输入操作"""
        if not text:
            self.logger.debug(LogCategory.MAIN, "文本输入为空，跳过")
            return True
        
        # 转义特殊字符
        escaped_text = text.replace(" ", "%s")
        cmd = ["-s", device_serial, "shell", "input", "text", escaped_text]
        success, _ = self.adb_manager._run_adb_command(cmd)
        if success:
            self.logger.debug(LogCategory.MAIN,
                            f"文本输入执行成功：{len(text)}字符")
        else:
            self.logger.exception(LogCategory.MAIN,
                            f"文本输入执行失败")
        return success
    
    def _press_key(self, device_serial: str, key_code: str) -> bool:
        """执行按键操作"""
        if not key_code:
            self.logger.warning(LogCategory.MAIN, "按键代码为空")
            return False
        
        cmd = ["-s", device_serial, "shell", "input", "keyevent", str(key_code)]
        success, _ = self.adb_manager._run_adb_command(cmd)
        if success:
            self.logger.debug(LogCategory.MAIN,
                            f"按键操作执行成功：{key_code}")
        else:
            self.logger.exception(LogCategory.MAIN,
                            f"按键操作执行失败：{key_code}")
        return success
    
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
        
        self.logger.debug(LogCategory.MAIN, "执行打开应用操作", app_name=app_name)
        # 使用 monkey 命令启动应用
        cmd = ["-s", device_serial, "shell", "monkey", "-p", app_name,
               "-c", "android.intent.category.LAUNCHER", "1"]
        success, _ = self.adb_manager._run_adb_command(cmd)
        if success:
            self.logger.debug(LogCategory.MAIN, "打开应用操作执行完成", app_name=app_name)
        else:
            self.logger.exception(LogCategory.MAIN, "打开应用操作执行失败", app_name=app_name)
        return success
    
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
            # 获取坐标（支持归一化坐标和像素坐标）
            coordinates = params.get("coordinates", {})
            
            # 归一化坐标
            if "start" in coordinates and isinstance(coordinates["start"], list):
                norm_x, norm_y = coordinates["start"]
                # 转换为像素坐标
                device_x, device_y = self._to_pixel_coords(device_serial, norm_x, norm_y)
            else:
                # 兼容旧格式
                x = params.get("x", params.get("coordinates", [0, 0])[0])
                y = params.get("y", params.get("coordinates", [0, 0])[1])
                device_x, device_y = self._convert_coordinates(device_serial, x, y)
            
            purpose = params.get("purpose", "点击")
            
            # 执行点击
            return self.safe_press(device_serial, device_x, device_y, purpose)
        
        elif mapped_action == "safe_swipe" or action == "swipe" or action == "drag":
            coordinates = params.get("coordinates", {})
            
            # 归一化坐标
            if "start" in coordinates and "end" in coordinates:
                start_norm = coordinates["start"]
                end_norm = coordinates["end"]
                # 转换为像素坐标
                start_x, start_y = self._to_pixel_coords(device_serial, start_norm[0], start_norm[1])
                end_x, end_y = self._to_pixel_coords(device_serial, end_norm[0], end_norm[1])
            else:
                # 兼容旧格式
                x1 = params.get("x1", params.get("coordinates", [0, 0])[0])
                y1 = params.get("y1", params.get("coordinates", [0, 0])[1])
                x2 = params.get("x2", params.get("end_coordinates", [0, 0])[0])
                y2 = params.get("y2", params.get("end_coordinates", [0, 0])[1])
                start_x, start_y = self._convert_coordinates(device_serial, x1, y1)
                end_x, end_y = self._convert_coordinates(device_serial, x2, y2)
            
            duration = params.get("duration", params.get("parameters", {}).get("duration", 300))
            purpose = params.get("purpose", "滑动")
            
            return self.safe_swipe(device_serial, start_x, start_y, end_x, end_y, duration, purpose)
        
        elif mapped_action == "safe_long_press" or action == "long_press":
            coordinates = params.get("coordinates", {})
            
            # 归一化坐标
            if "start" in coordinates and isinstance(coordinates["start"], list):
                norm_x, norm_y = coordinates["start"]
                device_x, device_y = self._to_pixel_coords(device_serial, norm_x, norm_y)
            else:
                # 兼容旧格式
                x = params.get("x", params.get("coordinates", [0, 0])[0])
                y = params.get("y", params.get("coordinates", [0, 0])[1])
                device_x, device_y = self._convert_coordinates(device_serial, x, y)
            
            duration_ms = params.get("duration", params.get("parameters", {}).get("duration", 500))
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
            app_name = params.get("app_name", "")
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
