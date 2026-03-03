"""
触控执行模块 - 基于MaaTouch方案的触控执行器
MAA风格安全机制：
1. 滑动模拟点击（Slide-to-Tap）
2. 随机坐标抖动
3. 随机操作延迟
4. 归一化坐标系统 [0, 1]
"""
import subprocess
import sys
import os
import time
import random
import socket
import struct
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from adb_manager import ADBDeviceManager
from logger import get_logger, LogCategory


class TouchMethod(Enum):
    """触控方法枚举"""
    ADB_INPUT = "adb_input"          # 基础方案
    MINITOUCH = "minitouch"          # 高精度方案
    MAATOUCH = "maatouch"            # MAA兼容方案


@dataclass
class MaaTouchConfig:
    """MAA风格触控配置"""
    # 核心安全参数（MAA标准）
    press_duration_ms: int = 50      # 按压持续时间（MAA推荐50ms）
    press_jitter_px: int = 2         # 按压抖动范围（像素）
    swipe_delay_min_ms: int = 100    # 滑动后最小延迟
    swipe_delay_max_ms: int = 300    # 滑动后最大延迟
    
    # 坐标系统
    use_normalized_coords: bool = True  # 使用归一化坐标 [0, 1]
    
    # 触控方法
    touch_method: TouchMethod = TouchMethod.ADB_INPUT
    
    # 高级参数
    enable_swipe_with_pause: bool = False  # 启用滑动暂停检测
    swipe_interval_ms: int = 2            # 滑动插值间隔（MAA标准2ms）
    
    # 二进制文件路径
    minitouch_binary_path: str = "client/3rd-part/maatouch/minitouch"
    maatouch_binary_path: str = "client/3rd-part/maatouch/minitouch"


class TouchExecutor:
    """触控执行器 - 基于MaaTouch方案的安全触控"""
    
    def __init__(self, adb_manager: ADBDeviceManager, config: Optional[MaaTouchConfig] = None):
        """
        初始化触控执行器
        
        Args:
            adb_manager: ADB设备管理器实例
            config: MAA风格触控配置
        """
        self.adb_manager = adb_manager
        self.config = config or MaaTouchConfig()
        self.cached_resolution = {}  # 分辨率缓存
        self.logger = get_logger()
        
        # Minitouch/MaaTouch相关
        self.touch_server_process = None
        self.touch_socket = None
        self.touch_server_available = False
        
        self.logger.info(LogCategory.MAIN, "触控执行器初始化完成",
                        method=self.config.touch_method.value,
                        press_duration_ms=self.config.press_duration_ms,
                        jitter_px=self.config.press_jitter_px,
                        normalized_coords=self.config.use_normalized_coords)
        
    # ===== 核心安全机制（MAA风格） =====
    def safe_press(self, device_serial: str, x: int, y: int,
                   purpose: str = "点击") -> bool:
        """
        安全按压 - MAA风格滑动模拟点击
        
        核心机制：
        1. 起点 = 目标点 + 随机偏移
        2. 终点 = 目标点
        3. 使用50ms快速滑动（MAA标准）
        4. 操作后添加随机延迟（100-300ms）
        
        Args:
            device_serial: 设备序列号
            x: 目标X坐标（像素）
            y: 目标Y坐标（像素）
            purpose: 操作目的说明
            
        Returns:
            操作是否成功
        """
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
        
        # 记录日志
        self.logger.info(LogCategory.MAIN,
                        f"👆 MAA安全按压 ({start_x},{start_y})→({end_x},{end_y}) "
                        f"duration={self.config.press_duration_ms}ms | "
                        f"抖动±{jitter} | purpose={purpose}")
        
        # 执行滑动（MAA标准50ms）
        success = self._swipe(device_serial, start_x, start_y, end_x, end_y,
                            self.config.press_duration_ms)
        
        # MAA风格：操作后添加随机延迟
        if success:
            delay = random.uniform(self.config.swipe_delay_min_ms,
                                 self.config.swipe_delay_max_ms)
            time.sleep(delay / 1000)
            self.logger.debug(LogCategory.MAIN,
                            f"MAA延迟: {delay:.1f}ms")
        
        return success
    
    def safe_swipe(self, device_serial: str, x1: int, y1: int,
                   x2: int, y2: int, duration: int = 300,
                   purpose: str = "滑动") -> bool:
        """
        安全滑动 - MAA风格带抖动的滑动操作
        
        Args:
            device_serial: 设备序列号
            x1: 起始X坐标（像素）
            y1: 起始Y坐标（像素）
            x2: 结束X坐标（像素）
            y2: 结束Y坐标（像素）
            duration: 滑动持续时间（毫秒）
            purpose: 操作目的说明
            
        Returns:
            操作是否成功
        """
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
        
        # 记录日志
        self.logger.info(LogCategory.MAIN,
                        f"👆 MAA安全滑动 ({start_x},{start_y})→({end_x},{end_y}) "
                        f"duration={duration}ms | "
                        f"抖动±{jitter} | purpose={purpose}")
        
        success = self._swipe(device_serial, start_x, start_y, end_x, end_y, duration)
        
        # MAA风格：操作后添加随机延迟
        if success:
            delay = random.uniform(self.config.swipe_delay_min_ms,
                                 self.config.swipe_delay_max_ms)
            time.sleep(delay / 1000)
            self.logger.debug(LogCategory.MAIN,
                            f"MAA延迟: {delay:.1f}ms")
        
        return success
    
    def safe_long_press(self, device_serial: str, x: int, y: int,
                        duration_ms: int = 500, purpose: str = "长按") -> bool:
        """
        安全长按 - MAA风格通过滑动模拟长按
        
        Args:
            device_serial: 设备序列号
            x: 目标X坐标（像素）
            y: 目标Y坐标（像素）
            duration_ms: 长按持续时间（毫秒）
            purpose: 操作目的说明
            
        Returns:
            操作是否成功
        """
        # 应用MAA风格抖动
        jitter = self.config.press_jitter_px
        jitter_x = random.randint(-jitter, jitter)
        jitter_y = random.randint(-jitter, jitter)
        
        start_x = x + jitter_x
        start_y = y + jitter_y
        end_x = x
        end_y = y
        
        # 记录日志
        self.logger.info(LogCategory.MAIN,
                        f"👆 MAA安全长按 ({start_x},{start_y})→({end_x},{end_y}) "
                        f"duration={duration_ms}ms | "
                        f"抖动±{jitter} | purpose={purpose}")
        
        success = self._swipe(device_serial, start_x, start_y, end_x, end_y, duration_ms)
        
        # MAA风格：操作后添加随机延迟
        if success:
            delay = random.uniform(self.config.swipe_delay_min_ms,
                                 self.config.swipe_delay_max_ms)
            time.sleep(delay / 1000)
            self.logger.debug(LogCategory.MAIN,
                            f"MAA延迟: {delay:.1f}ms")
        
        return success
    
    # ===== 坐标转换系统（MAA风格归一化坐标） =====
    def _convert_coordinates(self, device_serial: str, x, y) -> tuple:
        """
        坐标转换 - 支持归一化坐标和像素坐标
        
        支持格式：
        1. 归一化坐标 [0, 1] → 转换为像素坐标
        2. 像素坐标 → 验证范围后使用
        
        Args:
            device_serial: 设备序列号
            x: X坐标（归一化 [0,1] 或 像素）
            y: Y坐标（归一化 [0,1] 或 像素）
            
        Returns:
            (device_x, device_y) 像素坐标元组
        """
        # 获取设备分辨率
        resolution = self._get_device_resolution(device_serial)
        if not resolution:
            resolution = (1080, 1920)  # 默认值
        
        width, height = resolution
        
        # 判断坐标类型
        if self.config.use_normalized_coords and 0 <= x <= 1 and 0 <= y <= 1:
            # 归一化坐标 [0, 1] → 像素坐标
            device_x = int(x * width)
            device_y = int(y * height)
            self.logger.debug(LogCategory.MAIN,
                            f"归一化坐标转换: ({x:.3f},{y:.3f}) → ({device_x},{device_y})")
        else:
            # 像素坐标验证
            device_x = int(x)
            device_y = int(y)
            self.logger.debug(LogCategory.MAIN,
                            f"像素坐标验证: ({x},{y}) → ({device_x},{device_y})")
        
        # 自动修正超出范围的坐标
        device_x = max(0, min(device_x, width - 1))
        device_y = max(0, min(device_y, height - 1))
        
        return (device_x, device_y)
    
    def _to_pixel_coords(self, device_serial: str, norm_x: float, norm_y: float) -> Tuple[int, int]:
        """
        归一化坐标 [0,1] 转换为像素坐标
        
        Args:
            device_serial: 设备序列号
            norm_x: 归一化X坐标 [0, 1]
            norm_y: 归一化Y坐标 [0, 1]
            
        Returns:
            (pixel_x, pixel_y) 像素坐标元组
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
        
        return (pixel_x, pixel_y)
    
    def _get_device_resolution(self, device_serial: str) -> Optional[Tuple[int, int]]:
        """
        获取设备分辨率 - 多级备份机制
        
        优先级：
        1. cached_resolution（内存缓存）
        2. adb_get_resolution()（wm命令）
        3. 截图法获取
        4. 根据设备名猜测
        5. 默认值：1080x1920
        
        Args:
            device_serial: 设备序列号
            
        Returns:
            (width, height) 分辨率元组或None
        """
        # 1. 检查缓存
        if device_serial in self.cached_resolution:
            return self.cached_resolution[device_serial]
        
        # 2. 通过 wm size 获取
        resolution = self._get_resolution_via_wm(device_serial)
        if resolution:
            self.cached_resolution[device_serial] = resolution
            return resolution
        
        # 3. 通过截图法获取
        resolution = self._get_resolution_via_screenshot(device_serial)
        if resolution:
            self.cached_resolution[device_serial] = resolution
            return resolution
        
        # 4. 根据设备名猜测
        resolution = self._guess_resolution_by_model(device_serial)
        if resolution:
            self.cached_resolution[device_serial] = resolution
            return resolution
        
        # 5. 返回默认值
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
                                f"通过wm size获取分辨率: {width}x{height}")
                return (width, height)
            except Exception as e:
                self.logger.debug(LogCategory.MAIN,
                                f"解析wm size输出失败: {e}")
        return None
    
    def _get_resolution_via_screenshot(self, device_serial: str) -> Optional[Tuple[int, int]]:
        """通过截图获取分辨率（使用 dumpsys window windows）"""
        success, output = self.adb_manager._run_adb_command([
            "-s", device_serial, "shell", "dumpsys", "window", "windows"
        ])
        if success:
            try:
                # 查找 mUnrestrictedScreen 属性
                for line in output.split('\n'):
                    if 'mUnrestrictedScreen' in line:
                        # 格式: mUnrestrictedScreen=(0,0) 1080x2400
                        parts = line.split()
                        for part in parts:
                            if 'x' in part and part.replace('x', '').isdigit():
                                width, height = map(int, part.split('x'))
                                self.logger.debug(LogCategory.MAIN,
                                                f"通过dumpsys获取分辨率: {width}x{height}")
                                return (width, height)
            except Exception as e:
                self.logger.debug(LogCategory.MAIN,
                                f"解析dumpsys输出失败: {e}")
        return None
    
    def _guess_resolution_by_model(self, device_serial: str) -> Optional[Tuple[int, int]]:
        """根据设备名猜测分辨率"""
        model = self.adb_manager.get_device_model(device_serial)
        # 常见机型映射表
        model_resolution_map = {
            "Pixel 6": (1080, 2400),
            "Pixel 6 Pro": (1440, 3120),
            "Pixel 7": (1080, 2400),
            "Pixel 7 Pro": (1440, 3120),
            "Pixel 8": (1080, 2400),
            "Pixel 8 Pro": (1440, 3120),
            "Samsung S21": (1080, 2400),
            "Samsung S21+": (1080, 2400),
            "Samsung S21 Ultra": (1440, 3200),
            "Samsung S22": (1080, 2400),
            "Samsung S22+": (1080, 2400),
            "Samsung S22 Ultra": (1440, 3088),
            "Samsung S23": (1080, 2340),
            "Samsung S23+": (1080, 2340),
            "Samsung S23 Ultra": (1440, 3120),
            "Xiaomi 12": (1080, 2400),
            "Xiaomi 12 Pro": (1440, 3200),
            "Xiaomi 13": (1080, 2400),
            "Xiaomi 13 Pro": (1440, 3200),
            "OnePlus 10 Pro": (1440, 3216),
            "OnePlus 11": (1440, 3216),
            "Redmi Note 12": (1080, 2400),
            "Redmi Note 12 Pro": (1080, 2460),
        }
        resolution = model_resolution_map.get(model)
        if resolution:
            self.logger.debug(LogCategory.MAIN,
                            f"根据设备名猜测分辨率: {model} → {resolution[0]}x{resolution[1]}")
        return resolution
    
    def clear_resolution_cache(self, device_serial: Optional[str] = None):
        """
        清除分辨率缓存
        
        Args:
            device_serial: 指定设备序列号，如果为None则清除所有缓存
        """
        if device_serial:
            if device_serial in self.cached_resolution:
                del self.cached_resolution[device_serial]
                self.logger.debug(LogCategory.MAIN,
                                f"清除设备分辨率缓存: {device_serial}")
        else:
            self.cached_resolution.clear()
            self.logger.debug(LogCategory.MAIN, "清除所有分辨率缓存")
    
    # ===== 底层触控操作（支持多种触控方法） =====
    def _swipe(self, device_serial: str, x1: int, y1: int,
               x2: int, y2: int, duration: int) -> bool:
        """
        执行滑动操作 - 根据配置选择触控方法
        
        支持的触控方法：
        - ADB Input: 基础方案，兼容性最好
        - Minitouch: 高精度方案（需要root或临时root）
        - MaaTouch: MAA兼容方案（需要临时root）
        
        Args:
            device_serial: 设备序列号
            x1: 起始X坐标
            y1: 起始Y坐标
            x2: 结束X坐标
            y2: 结束Y坐标
            duration: 持续时间（毫秒）
            
        Returns:
            操作是否成功
        """
        method = self.config.touch_method
        
        if method == TouchMethod.MINITOUCH:
            return self._swipe_minitouch(device_serial, x1, y1, x2, y2, duration)
        elif method == TouchMethod.MAATOUCH:
            return self._swipe_maatouch(device_serial, x1, y1, x2, y2, duration)
        else:  # TouchMethod.ADB_INPUT
            return self._swipe_adb_input(device_serial, x1, y1, x2, y2, duration)
    
    def _swipe_adb_input(self, device_serial: str, x1: int, y1: int,
                        x2: int, y2: int, duration: int) -> bool:
        """
        使用ADB shell input swipe执行滑动（基础方案）
        
        命令格式：
        adb -s <device> shell input swipe <sx> <sy> <ex> <ey> <duration>
        
        Args:
            device_serial: 设备序列号
            x1: 起始X坐标
            y1: 起始Y坐标
            x2: 结束X坐标
            y2: 结束Y坐标
            duration: 持续时间（毫秒）
            
        Returns:
            操作是否成功
        """
        cmd = ["-s", device_serial, "shell", "input", "swipe",
               str(x1), str(y1), str(x2), str(y2), str(duration)]
        success, _ = self.adb_manager._run_adb_command(cmd)
        if success:
            self.logger.debug(LogCategory.MAIN,
                            f"ADB Input滑动执行成功: ({x1},{y1})→({x2},{y2})")
        else:
            self.logger.exception(LogCategory.MAIN,
                            f"ADB Input滑动执行失败")
        return success
    
    def _swipe_minitouch(self, device_serial: str, x1: int, y1: int,
                        x2: int, y2: int, duration: int) -> bool:
        """
        使用Minitouch执行滑动（高精度方案）
        
        Minitouch协议格式：
        v <max_x> <max_y> <max_pressure>
        c
        d <slot> <x> <y> <pressure>
        m <slot> <x> <y> <pressure>
        u <slot>
        c
        
        Args:
            device_serial: 设备序列号
            x1: 起始X坐标
            y1: 起始Y坐标
            x2: 结束X坐标
            y2: 结束Y坐标
            duration: 持续时间（毫秒）
            
        Returns:
            操作是否成功
        """
        # 确保minitouch服务已启动
        if not self._ensure_minitouch(device_serial):
            self.logger.warning(LogCategory.MAIN,
                              "Minitouch不可用，回退到ADB Input")
            return self._swipe_adb_input(device_serial, x1, y1, x2, y2, duration)
        
        try:
            # 获取设备分辨率用于归一化
            resolution = self._get_device_resolution(device_serial)
            if not resolution:
                resolution = (1080, 1920)
            
            max_x, max_y = resolution
            
            # 发送minitouch协议命令
            # 下按
            self._send_minitouch_command(f"d 0 {x1} {y1} 50")
            time.sleep(0.001)
            
            # 移动到终点
            self._send_minitouch_command(f"m 0 {x2} {y2} 50")
            time.sleep(duration / 1000)
            
            # 抬起
            self._send_minitouch_command("u 0")
            self._send_minitouch_command("c")
            
            self.logger.debug(LogCategory.MAIN,
                            f"Minitouch滑动执行成功: ({x1},{y1})→({x2},{y2})")
            return True
        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"Minitouch滑动执行失败: {e}")
            # 回退到ADB Input
            return self._swipe_adb_input(device_serial, x1, y1, x2, y2, duration)
    
    def _swipe_maatouch(self, device_serial: str, x1: int, y1: int,
                       x2: int, y2: int, duration: int) -> bool:
        """
        使用MaaTouch执行滑动（MAA兼容方案）
        
        MaaTouch协议格式：
        contact <slot> <action> <x> <y> <pressure>
        
        Args:
            device_serial: 设备序列号
            x1: 起始X坐标
            y1: 起始Y坐标
            x2: 结束X坐标
            y2: 结束Y坐标
            duration: 持续时间（毫秒）
            
        Returns:
            操作是否成功
        """
        # 确保maatouch服务已启动
        if not self._ensure_maatouch(device_serial):
            self.logger.warning(LogCategory.MAIN,
                              "MaaTouch不可用，回退到ADB Input")
            return self._swipe_adb_input(device_serial, x1, y1, x2, y2, duration)
        
        try:
            # 获取设备分辨率用于归一化
            resolution = self._get_device_resolution(device_serial)
            if not resolution:
                resolution = (1080, 1920)
            
            max_x, max_y = resolution
            
            # 发送maatouch协议命令
            # 下按
            self._send_maatouch_command(f"contact 0 d {x1} {y1} 50")
            time.sleep(0.001)
            
            # 移动到终点
            self._send_maatouch_command(f"contact 0 m {x2} {y2} 50")
            time.sleep(duration / 1000)
            
            # 抬起
            self._send_maatouch_command("contact 0 u 0 0 0")
            
            self.logger.debug(LogCategory.MAIN,
                            f"MaaTouch滑动执行成功: ({x1},{y1})→({x2},{y2})")
            return True
        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"MaaTouch滑动执行失败: {e}")
            # 回退到ADB Input
            return self._swipe_adb_input(device_serial, x1, y1, x2, y2, duration)
    
    # ===== Minitouch/MaaTouch服务管理 =====
    def _ensure_minitouch(self, device_serial: str) -> bool:
        """
        确保minitouch服务已启动

        Args:
            device_serial: 设备序列号

        Returns:
            是否成功启动
        """
        # 检查服务是否已启动
        if self.touch_server_available:
            return True

        # 获取minitouch二进制路径
        binary_path = self.config.minitouch_binary_path
        if not os.path.exists(binary_path):
            self.logger.warning(LogCategory.MAIN,
                              f"Minitouch二进制文件不存在: {binary_path}")
            return False

        # 推送二进制文件到设备
        device_path = "/data/local/tmp/minitouch"
        self.logger.info(LogCategory.MAIN,
                        f"推送minitouch到设备: {device_serial}")

        cmd = ["-s", device_serial, "push", binary_path, device_path]
        success, output = self.adb_manager._run_adb_command(cmd)
        if not success:
            self.logger.exception(LogCategory.MAIN,
                                f"推送minitouch失败: {output}")
            return False

        # 设置执行权限
        cmd = ["-s", device_serial, "shell", "chmod", "755", device_path]
        self.adb_manager._run_adb_command(cmd)

        # 建立端口转发
        self.logger.info(LogCategory.MAIN,
                        f"建立端口转发: {device_serial}")
        cmd = ["-s", device_serial, "forward", "tcp:1717", "tcp:1717"]
        self.adb_manager._run_adb_command(cmd)

        # 启动minitouch服务 - 使用 Popen 启动后台进程，不等待结束
        self.logger.info(LogCategory.MAIN,
                        f"启动minitouch服务: {device_serial}")

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
                            f"Minitouch服务进程启动成功, PID: {self.touch_server_process.pid}")
        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"启动minitouch服务进程失败: {e}")
            return False

        # 等待服务启动
        time.sleep(0.5)

        # 建立TCP连接
        try:
            self.touch_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.touch_socket.settimeout(5.0)
            self.touch_socket.connect(("127.0.0.1", 1717))
            self.logger.info(LogCategory.MAIN,
                            "Minitouch TCP连接建立成功")
            self.touch_server_available = True
            return True
        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"Minitouch TCP连接失败: {e}")
            # 清理失败的进程
            if self.touch_server_process:
                try:
                    self.touch_server_process.terminate()
                    self.touch_server_process.wait(timeout=1)
                except:
                    pass
                self.touch_server_process = None
            return False
    
    def _get_device_abi(self, device_serial: str) -> str:
        """获取设备 CPU 架构"""
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
        """
        确保maatouch服务已启动

        Args:
            device_serial: 设备序列号

        Returns:
            是否成功启动
        """
        # 检查服务是否已启动
        if self.touch_server_available:
            return True

        # 获取设备架构
        device_abi = self._get_device_abi(device_serial)
        self.logger.info(LogCategory.MAIN, f"检测到设备架构: {device_abi}", device_serial=device_serial)

        # 根据设备架构选择正确的二进制文件（优先使用架构特定的二进制）
        arch_binary_path = os.path.join(os.path.dirname(__file__), "device_control_system", "minitouch_resources", device_abi, "minitouch")
        if os.path.exists(arch_binary_path):
            binary_path = arch_binary_path
        else:
            binary_path = self.config.maatouch_binary_path

        self.logger.info(LogCategory.MAIN, f"使用 MaaTouch 二进制: {binary_path}", arch=device_abi)

        if not os.path.exists(binary_path):
            self.logger.warning(LogCategory.MAIN,
                              f"MaaTouch二进制文件不存在: {binary_path}")
            return False

        # 推送二进制文件到设备
        device_path = "/data/local/tmp/maatouch"
        self.logger.info(LogCategory.MAIN,
                        f"推送maatouch到设备: {device_serial}")

        cmd = ["-s", device_serial, "push", binary_path, device_path]
        success, output = self.adb_manager._run_adb_command(cmd)
        if not success:
            self.logger.exception(LogCategory.MAIN,
                                f"推送maatouch失败: {output}")
            return False

        # 设置执行权限
        cmd = ["-s", device_serial, "shell", "chmod", "755", device_path]
        self.adb_manager._run_adb_command(cmd)

        # 建立端口转发
        self.logger.info(LogCategory.MAIN,
                        f"建立端口转发: {device_serial}")
        cmd = ["-s", device_serial, "forward", "tcp:1717", "tcp:1717"]
        self.adb_manager._run_adb_command(cmd)

        # 启动maatouch服务 - 使用 Popen 启动后台进程，不等待结束
        self.logger.info(LogCategory.MAIN,
                        f"启动maatouch服务: {device_serial}")

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
                            f"MaaTouch服务进程启动成功, PID: {self.touch_server_process.pid}")
        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"启动maatouch服务进程失败: {e}")
            return False

        # 等待服务启动
        time.sleep(0.5)

        # 建立TCP连接
        try:
            self.touch_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.touch_socket.settimeout(5.0)
            self.touch_socket.connect(("127.0.0.1", 1717))
            self.logger.info(LogCategory.MAIN,
                            "MaaTouch TCP连接建立成功")
            self.touch_server_available = True
            return True
        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"MaaTouch TCP连接失败: {e}")
            # 清理失败的进程
            if self.touch_server_process:
                try:
                    self.touch_server_process.terminate()
                    self.touch_server_process.wait(timeout=1)
                except:
                    pass
                self.touch_server_process = None
            return False
    
    def _send_minitouch_command(self, command: str):
        """
        发送minitouch协议命令
        
        Minitouch协议格式：
        v <max_x> <max_y> <max_pressure>
        c
        d <slot> <x> <y> <pressure>
        m <slot> <x> <y> <pressure>
        u <slot>
        c
        
        Args:
            command: 协议命令
        """
        if not self.touch_socket:
            raise RuntimeError("Minitouch TCP连接未建立")
        
        try:
            # 发送协议命令
            self.touch_socket.sendall((command + "\n").encode('utf-8'))
            self.logger.debug(LogCategory.MAIN,
                            f"发送minitouch命令: {command.strip()}")
        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"发送minitouch命令失败: {e}")
            raise
    
    def _send_maatouch_command(self, command: str):
        """
        发送maatouch协议命令
        
        MaaTouch协议格式（与minitouch类似）：
        v <max_x> <max_y> <max_pressure>
        c
        d <slot> <x> <y> <pressure>
        m <slot> <x> <y> <pressure>
        u <slot>
        c
        
        Args:
            command: 协议命令
        """
        if not self.touch_socket:
            raise RuntimeError("MaaTouch TCP连接未建立")
        
        try:
            # 发送协议命令
            self.touch_socket.sendall((command + "\n").encode('utf-8'))
            self.logger.debug(LogCategory.MAIN,
                            f"发送maatouch命令: {command.strip()}")
        except Exception as e:
            self.logger.exception(LogCategory.MAIN,
                                f"发送maatouch命令失败: {e}")
            raise
    
    def _release_touch_server(self, device_serial: str):
        """
        释放触控服务资源

        Args:
            device_serial: 设备序列号
        """
        # 关闭TCP连接
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
        if self.config.touch_method == TouchMethod.MINITOUCH:
            cmd = ["-s", device_serial, "shell", "pkill", "-9", "minitouch"]
        elif self.config.touch_method == TouchMethod.MAATOUCH:
            cmd = ["-s", device_serial, "shell", "pkill", "-9", "maatouch"]
        else:
            return

        self.adb_manager._run_adb_command(cmd)
        self.logger.info(LogCategory.MAIN,
                        f"清理触控服务: {self.config.touch_method.value}")
    
    def __del__(self):
        """析构函数 - 清理资源"""
        self._release_touch_server("default")
    
    def _input_text(self, device_serial: str, text: str) -> bool:
        """
        执行文本输入操作
        
        Args:
            device_serial: 设备序列号
            text: 要输入的文本
            
        Returns:
            操作是否成功
        """
        if not text:
            self.logger.debug(LogCategory.MAIN, "文本输入为空，跳过")
            return True
        
        # 转义特殊字符
        escaped_text = text.replace(" ", "%s")
        cmd = ["-s", device_serial, "shell", "input", "text", escaped_text]
        success, _ = self.adb_manager._run_adb_command(cmd)
        if success:
            self.logger.debug(LogCategory.MAIN,
                            f"文本输入执行成功: {len(text)}字符")
        else:
            self.logger.exception(LogCategory.MAIN,
                                f"文本输入执行失败")
        return success
    
    def _press_key(self, device_serial: str, key_code: str) -> bool:
        """
        执行按键操作
        
        Args:
            device_serial: 设备序列号
            key_code: 按键代码
            
        Returns:
            操作是否成功
        """
        if not key_code:
            self.logger.warning(LogCategory.MAIN, "按键代码为空")
            return False
        
        cmd = ["-s", device_serial, "shell", "input", "keyevent", str(key_code)]
        success, _ = self.adb_manager._run_adb_command(cmd)
        if success:
            self.logger.debug(LogCategory.MAIN,
                            f"按键操作执行成功: {key_code}")
        else:
            self.logger.exception(LogCategory.MAIN,
                                f"按键操作执行失败: {key_code}")
        return success
    
    # ===== 统一工具执行入口（MAA风格） =====
    def execute_tool_call(self, device_serial: str, action: str,
                         params: Dict) -> bool:
        """
        统一工具执行入口 - 支持MAA风格触控指令
        
        支持的工具（新格式）：
        - safe_press: 安全按压（MAA风格滑动模拟点击）
        - safe_swipe: 安全滑动
        - safe_long_press: 安全长按
        - wait: 等待
        - input_text: 文本输入
        - press_key: 按键操作
        - system_button: 系统按钮
        
        支持的动作（旧格式兼容）：
        - click: 点击（映射到 safe_press）
        - swipe: 滑动（映射到 safe_swipe）
        - long_press: 长按（映射到 safe_long_press）
        - drag: 拖拽（映射到 safe_swipe）
        - type_text: 文本输入（映射到 input_text）
        - input: 文本输入（映射到 input_text）
        - key: 按键（映射到 press_key）
        - open_app: 打开应用
        - terminate: 终止任务
        - answer: 回答问题
        
        MAA风格触控指令格式：
        {
            "action_type": "click|long_press|swipe|drag",
            "coordinates": {
                "start": [0.5, 0.5],  # 归一化坐标 [0, 1]
                "end": [0.5, 0.6]     # 滑动终点坐标
            },
            "parameters": {
                "duration": 100,      # 毫秒
                "jitter": 2           # 坐标抖动范围（像素）
            }
        }
        
        Args:
            device_serial: 设备序列号
            action: 工具类型
            params: 工具参数
            
        Returns:
            操作是否成功
        """
        self.logger.debug(LogCategory.MAIN,
                        f"执行工具调用: {action}")
        
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
            
            # MAA风格：归一化坐标
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
            
            # 执行MAA风格安全按压
            return self.safe_press(device_serial, device_x, device_y, purpose)
        
        elif mapped_action == "safe_swipe" or action == "swipe" or action == "drag":
            coordinates = params.get("coordinates", {})
            
            # MAA风格：归一化坐标
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
            
            return self.safe_swipe(device_serial, start_x, start_y,
                                  end_x, end_y, duration, purpose)
        
        elif mapped_action == "safe_long_press" or action == "long_press":
            coordinates = params.get("coordinates", {})
            
            # MAA风格：归一化坐标
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
            
            return self.safe_long_press(device_serial, device_x, device_y,
                                       duration_ms, purpose)
        
        elif action == "wait":
            duration_ms = params.get("duration", 1000)
            time.sleep(duration_ms / 1000.0)
            self.logger.debug(LogCategory.MAIN,
                            f"等待完成: {duration_ms}ms")
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
                             f"未知工具类型: {action}")
            return False
    
    def _open_app(self, device_serial: str, app_name: str) -> bool:
        """
        执行打开应用操作
        
        Args:
            device_serial: 设备序列号
            app_name: 应用包名
            
        Returns:
            操作是否成功
        """
        if not app_name:
            self.logger.warning(LogCategory.MAIN, "应用名称为空")
            return False
        
        self.logger.debug(LogCategory.MAIN, "执行打开应用操作", app_name=app_name)
        # 使用monkey命令启动应用
        cmd = ["-s", device_serial, "shell", "monkey", "-p", app_name,
               "-c", "android.intent.category.LAUNCHER", "1"]
        success, _ = self.adb_manager._run_adb_command(cmd)
        if success:
            self.logger.debug(LogCategory.MAIN, "打开应用操作执行完成", app_name=app_name)
        else:
            self.logger.exception(LogCategory.MAIN, "打开应用操作执行失败", app_name=app_name)
        return success
    
    def _press_system_button(self, device_serial: str, button_name: str) -> bool:
        """
        执行系统按钮操作
        
        Args:
            device_serial: 设备序列号
            button_name: 按钮名称 (back/home/menu/enter)
            
        Returns:
            操作是否成功
        """
        if not button_name:
            self.logger.warning(LogCategory.MAIN, "系统按钮名称为空")
            return False
        
        # 系统按钮对应的keycode
        button_keycodes = {
            'back': '4',
            'home': '3',
            'menu': '82',
            'enter': '66'
        }
        
        key_code = button_keycodes.get(button_name.lower())
        if not key_code:
            self.logger.warning(LogCategory.MAIN,
                              f"未知系统按钮: {button_name}")
            return False
        
        return self._press_key(device_serial, key_code)