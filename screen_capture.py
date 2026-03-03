"""
屏幕捕获模块 - 负责设备屏幕截图和图像处理
"""
import base64
import io
import sys
import os
import subprocess
import time
from typing import Optional

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from adb_manager import ADBDeviceManager
from logger import get_logger, LogCategory, LogLevel

try:
    from PIL import Image
except ImportError:
    print("警告: PIL库未安装，屏幕捕获功能将不可用")
    Image = None

class ScreenCapture:
    """屏幕捕获器"""
    
    def __init__(self, adb_manager: ADBDeviceManager, max_size: int = 1024):
        """
        初始化屏幕捕获器
        
        Args:
            adb_manager: ADB设备管理器实例
            max_size: 图像最大尺寸（像素）
        """
        self.adb_manager = adb_manager
        self.max_size = max_size
        self.logger = get_logger()
        self.last_image_size = None  # 存储最后一次处理的图像尺寸
        self.last_capture_time = 0   # 上次截图时间戳
        self.min_interval = 1.0      # 最小截图间隔（秒）
        
    def capture_screen(self, device_serial: str) -> Optional[bytes]:
        """
        捕获设备屏幕截图
        
        Args:
            device_serial: 设备序列号
            
        Returns:
            Base64编码的图像数据或None
        """
        if Image is None:
            self.logger.exception(LogCategory.MAIN, "PIL库未初始化")
            return None
        
        current_time = time.time()
        # 检查截图间隔
        time_since_last = current_time - self.last_capture_time
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            self.logger.debug(LogCategory.MAIN, f"截图间隔不足，等待 {wait_time:.3f} 秒",
                           device_serial=device_serial)
            time.sleep(wait_time)
            current_time = time.time()
        
        start_time = current_time
        self.logger.debug(LogCategory.MAIN, "开始屏幕捕获", device_serial=device_serial)
            
        # 执行ADB截图命令
        try:
            cmd = [self.adb_manager.adb_path, "-s", device_serial, "exec-out", "screencap", "-p"]
            self.logger.debug(LogCategory.MAIN, "执行ADB截图命令", device_serial=device_serial)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self.adb_manager.timeout
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            if result.returncode != 0:
                self.logger.exception(LogCategory.MAIN, "ADB截图命令执行异常",
                                   device_serial=device_serial, return_code=result.returncode)
                return None
                
            # 直接使用原始PNG数据，不要进行任何文本处理
            png_data = result.stdout
            png_size = len(png_data)
            self.logger.debug(LogCategory.MAIN, "PNG数据获取完成",
                           device_serial=device_serial, size_bytes=png_size)
            
            # 验证PNG数据完整性（可选的安全检查）
            if not png_data.startswith(b'\x89PNG\r\n\x1a\n'):
                self.logger.exception(LogCategory.MAIN, "PNG数据完整性验证异常",
                                   device_serial=device_serial, size_bytes=png_size)
                return None
                
            # 处理图像
            image = Image.open(io.BytesIO(png_data))
            original_size = image.size
            processed_image = self._process_image(image)
            processed_size = processed_image.size

            # 存储实际发送给服务端的图像尺寸
            self.last_image_size = processed_size

            self.logger.debug(LogCategory.MAIN, "图像处理完成",
                           device_serial=device_serial,
                           original_size=f"{original_size[0]}x{original_size[1]}",
                           processed_size=f"{processed_size[0]}x{processed_size[1]}",
                           format="PNG")
            
            # 转换为Base64
            base64_data = self._image_to_base64(processed_image)
            total_duration_ms = (time.time() - start_time) * 1000
            
            self.logger.info(LogCategory.MAIN, "屏幕捕获完成",
                           device_serial=device_serial,
                           png_size_bytes=png_size,
                           base64_length=len(base64_data),
                           total_duration_ms=round(total_duration_ms, 3))
            
            self.logger.log_performance("screen_capture", total_duration_ms,
                                      device_serial=device_serial)
            
            # 更新最后截图时间（截图完成后的时间，确保延时从上次截图完成后开始计时）
            self.last_capture_time = time.time()
            
            return base64_data
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.exception(LogCategory.MAIN, "屏幕捕获异常",
                               device_serial=device_serial,
                               exception_type=type(e).__name__,
                               duration_ms=round(duration_ms, 3),
                               exc_info=True)
            return None
            
    def _process_image(self, image):
        """
        处理图像 - 调整大小和质量
        
        Args:
            image: 原始PIL图像
            
        Returns:
            处理后的PIL图像
        """
        start_time = time.time()
        original_size = image.size
        
        # 调整图像大小
        if max(image.size) > self.max_size:
            ratio = self.max_size / max(image.size)
            new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
            # 使用简单的resize，避免版本兼容性问题
            image = image.resize(new_size)
            self.logger.debug(LogCategory.MAIN, "图像尺寸调整",
                           original_size=f"{original_size[0]}x{original_size[1]}",
                           new_size=f"{new_size[0]}x{new_size[1]}")
        
        duration_ms = (time.time() - start_time) * 1000
        self.logger.log_performance("image_process", duration_ms)
            
        # 转换为RGB（如果需要）
        if image.mode != 'RGB':
            image = image.convert('RGB')
            
        return image
        
    def _image_to_base64(self, image) -> bytes:
        """
        将PIL图像转换为Base64编码的PNG（无损压缩）
        
        Args:
            image: PIL图像
            
        Returns:
            Base64编码的字节数据
        """
        start_time = time.time()
        
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        png_data = buffer.getvalue()
        base64_data = base64.b64encode(png_data)
        
        duration_ms = (time.time() - start_time) * 1000
        self.logger.log_performance("image_to_base64", duration_ms, format="PNG")
        
        return base64_data
        
    def get_device_info(self, device_serial: str) -> dict:
        """
        获取设备信息

        Args:
            device_serial: 设备序列号

        Returns:
            包含分辨率、型号和图像尺寸的字典
        """
        self.logger.debug(LogCategory.MAIN, "获取设备信息", device_serial=device_serial)
        resolution = self.adb_manager.get_device_resolution(device_serial)
        model = self.adb_manager.get_device_model(device_serial)

        device_info = {
            'resolution': list(resolution) if resolution else [0, 0],
            'model': model,
            'image_size': list(self.last_image_size) if self.last_image_size else None
        }

        self.logger.debug(LogCategory.MAIN, "设备信息获取完成",
                        device_serial=device_serial,
                        resolution=device_info['resolution'],
                        model=model,
                        image_size=device_info['image_size'])

        return device_info