"""
截图记录器 - 记录运行时的设备截图

功能：
- 每秒缓存一张被控设备图像
- 保存到 cache/screencap 目录
- 支持启动/停止记录
- 记录截图统计信息
"""
import os
import time
import threading
from datetime import datetime
from typing import Optional, Callable, Any
from PIL import Image
import io


class ScreencapRecorder:
    """截图记录器"""
    
    def __init__(self, cache_dir: str = "cache/screencap"):
        """
        初始化截图记录器
        
        Args:
            cache_dir: 截图保存目录
        """
        self._cache_dir = cache_dir
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._screencap_count = 0
        self._last_screencap_time = 0.0
        self._lock = threading.Lock()
        self._capture_callback: Optional[Callable[[], Any]] = None
        
        # 确保目录存在
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self) -> None:
        """确保缓存目录存在"""
        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir, exist_ok=True)
    
    def start(self, capture_callback: Callable[[], Any]) -> None:
        """
        开始记录截图
        
        Args:
            capture_callback: 截图回调函数，返回 numpy 数组或 PIL Image
        """
        if self._running:
            return
        
        self._capture_callback = capture_callback
        self._running = True
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        """停止记录截图"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
    
    def _record_loop(self) -> None:
        """截图记录循环"""
        while self._running:
            current_time = time.time()
            
            # 检查是否间隔 1 秒
            if current_time - self._last_screencap_time >= 1.0:
                try:
                    if self._capture_callback:
                        image_data = self._capture_callback()
                        if image_data is not None:
                            self._save_screencap(image_data)
                            self._last_screencap_time = current_time
                except Exception as e:
                    # 记录失败不中断循环
                    pass
            
            # 等待 100ms 后再次检查
            time.sleep(0.1)
    
    def _save_screencap(self, image_data: Any) -> None:
        """
        保存截图
        
        Args:
            image_data: 图像数据（numpy 数组或 PIL Image 或 bytes）
        """
        try:
            # 生成文件名：timestamp 格式
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 保留毫秒
            filename = f"screencap_{timestamp}.png"
            filepath = os.path.join(self._cache_dir, filename)
            
            # 转换并保存图像
            if isinstance(image_data, bytes):
                # bytes 格式（通常是 PNG/JPEG 编码）
                image = Image.open(io.BytesIO(image_data))
            elif hasattr(image_data, 'mode'):
                # PIL Image 格式
                image = image_data
            else:
                # 假设是 numpy 数组
                import numpy as np
                if isinstance(image_data, np.ndarray):
                    image = Image.fromarray(image_data)
                else:
                    return
            
            # 保存为 PNG
            image.save(filepath, 'PNG')
            
            # 更新计数
            with self._lock:
                self._screencap_count += 1
                
        except Exception as e:
            # 保存失败，静默处理
            pass
    
    def get_screencap_count(self) -> int:
        """获取已记录的截图数量"""
        with self._lock:
            return self._screencap_count
    
    def is_recording(self) -> bool:
        """是否正在记录"""
        return self._running
    
    def reset_count(self) -> None:
        """重置计数"""
        with self._lock:
            self._screencap_count = 0
    
    def get_cache_dir(self) -> str:
        """获取缓存目录"""
        return self._cache_dir
    
    def clear_cache(self) -> int:
        """
        清空缓存目录
        
        Returns:
            删除的文件数量
        """
        deleted_count = 0
        if os.path.exists(self._cache_dir):
            for filename in os.listdir(self._cache_dir):
                if filename.startswith("screencap_") and filename.endswith(".png"):
                    filepath = os.path.join(self._cache_dir, filename)
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                    except OSError:
                        pass
        return deleted_count
