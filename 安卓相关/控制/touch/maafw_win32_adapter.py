"""
MaaFramework Win32触控适配器
基于MaaFramework的Win32Controller实现PC窗口触控
优先使用Pipeline方式执行任务

注意：MaaFramework导入名为 maa
"""
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from ctypes import c_void_p
from dataclasses import dataclass

from core.logger import get_logger, LogCategory, LogLevel

# 尝试导入MaaFramework
MAAFW_AVAILABLE = False

try:
    from maa import Library
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.controller import Win32Controller
    from maa.toolkit import Toolkit
    from maa.define import MaaWin32ScreencapMethodEnum, MaaWin32InputMethodEnum
    # 新版本5.10.0在导入maa时已自动初始化Library
    MAAFW_AVAILABLE = True
except ImportError:
    # 定义占位类型
    Tasker = None
    Resource = None
    Win32Controller = None
    print("警告: MaaFramework库未安装，Win32触控功能将不可用。请使用 pip install MaaFw 安装")


@dataclass
class MaaFwWin32Config:
    """MaaFramework Win32触控配置"""
    hwnd: c_void_p = None
    screencap_method: int = 0  # MaaWin32ScreencapMethodEnum.GDI
    input_method: int = 0  # MaaWin32InputMethodEnum.Seize
    
    # 触控参数
    press_duration_ms: int = 50
    swipe_duration_ms: int = 300


class MaaFwWin32Executor:
    """
    MaaFramework Win32触控执行器
    
    基于MaaFramework的Win32Controller实现，优先使用Pipeline执行任务
    """
    
    def __init__(self, config: MaaFwWin32Config):
        """
        初始化Win32触控执行器
        
        Args:
            config: MaaFramework Win32触控配置
        """
        self.config = config
        self.logger = get_logger()
        
        # MaaFramework组件
        self._library_loaded = False
        self._resource: Optional[Resource] = None
        self._controller: Optional[Win32Controller] = None
        self._tasker: Optional[Tasker] = None
        
        # 状态
        self._connected = False
        self._resolution: Tuple[int, int] = (0, 0)
        self._window_title = ""
    
    def _load_library(self, lib_path: Optional[str] = None) -> bool:
        """
        加载MaaFramework动态库
        
        注意：MaaFw 5.10.0+ 在导入maa时已自动初始化Library，
        使用包内bin目录的二进制文件。
        此方法主要用于检查库是否可用。
        
        Args:
            lib_path: 库路径（可选，新版本通常不需要指定）
        
        Returns:
            bool: 是否加载成功
        """
        if not MAAFW_AVAILABLE:
            self.logger.exception(LogCategory.MAIN, "MaaFramework库未安装")
            return False
        
        if self._library_loaded:
            return True
        
        try:
            # 新版本5.10.0+在导入时已自动初始化Library
            # 如果需要自定义路径，可通过环境变量MAAFW_BINARY_PATH设置
            # 这里我们直接标记为已加载，因为导入时已完成初始化
            self._library_loaded = True
            self.logger.info(LogCategory.MAIN, "MaaFramework库已自动初始化（pip安装版本）")
            return True
            
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "MaaFramework库加载失败", error=str(e))
            return False
    
    def connect(self) -> bool:
        """
        连接PC窗口
        
        Returns:
            bool: 是否连接成功
        """
        if not self._load_library():
            return False
        
        try:
            # 初始化Toolkit配置
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            config_dir = os.path.join(project_root, "IstinaEndfieldAssistant", "config")
            
            if os.path.exists(config_dir):
                Toolkit.init_option(Path(config_dir))
            
            # 创建资源
            self._resource = Resource()
            
            # 创建Win32控制器
            self._controller = Win32Controller(
                hwnd=self.config.hwnd,
                screencap_method=self.config.screencap_method,
                input_method=self.config.input_method
            )
            
            # 连接窗口
            job = self._controller.post_connection()
            job.wait()
            
            if not job.succeeded:
                self.logger.exception(LogCategory.MAIN, "Win32控制器连接失败")
                return False
            
            # 获取窗口信息
            cached_image = self._controller.cached_image
            if cached_image is not None:
                self._resolution = (cached_image.shape[1], cached_image.shape[0])
            
            # 创建Tasker并绑定
            self._tasker = Tasker()
            if not self._tasker.bind(self._resource, self._controller):
                self.logger.exception(LogCategory.MAIN, "Tasker绑定失败")
                return False
            
            self._connected = True
            self.logger.info(LogCategory.MAIN, "PC窗口连接成功",
                            hwnd=self.config.hwnd,
                            resolution=f"{self._resolution[0]}x{self._resolution[1]}")
            return True
            
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "PC窗口连接异常", error=str(e))
            return False
    
    def disconnect(self) -> bool:
        """
        断开窗口连接
        
        Returns:
            bool: 是否断开成功
        """
        try:
            self._connected = False
            self._tasker = None
            self._controller = None
            self._resource = None
            self.logger.info(LogCategory.MAIN, "PC窗口已断开")
            return True
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "断开连接异常", error=str(e))
            return False
    
    # ==================== Pipeline优先方法 ====================
    
    def load_pipeline(self, pipeline_path: str) -> bool:
        """
        加载Pipeline资源
        
        Args:
            pipeline_path: Pipeline JSON文件路径或资源目录
        
        Returns:
            bool: 是否加载成功
        """
        if not self._connected or not self._resource:
            self.logger.exception(LogCategory.MAIN, "窗口未连接，无法加载Pipeline")
            return False
        
        try:
            path = Path(pipeline_path)
            job = self._resource.post_bundle(path)
            job.wait()
            
            if job.succeeded:
                self.logger.info(LogCategory.MAIN, "Pipeline资源加载成功", path=pipeline_path)
                return True
            else:
                self.logger.exception(LogCategory.MAIN, "Pipeline资源加载失败", path=pipeline_path)
                return False
                
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "Pipeline加载异常", error=str(e))
            return False
    
    def run_pipeline_task(self, entry: str, pipeline_override: Dict = None) -> bool:
        """
        执行Pipeline任务（推荐方式）
        
        Args:
            entry: 任务入口名称
            pipeline_override: 动态覆盖配置
        
        Returns:
            bool: 是否执行成功
        """
        if not self._connected or not self._tasker:
            self.logger.exception(LogCategory.MAIN, "窗口未连接，无法执行Pipeline任务")
            return False
        
        try:
            job = self._tasker.post_task(entry, pipeline_override or {})
            job.wait()
            
            if job.succeeded:
                self.logger.debug(LogCategory.MAIN, "Pipeline任务执行成功", entry=entry)
                return True
            else:
                self.logger.warning(LogCategory.MAIN, "Pipeline任务执行失败", entry=entry)
                return False
                
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "Pipeline任务执行异常", entry=entry, error=str(e))
            return False
    
    def run_pipeline_sequence(self, tasks: list) -> bool:
        """
        执行Pipeline任务序列
        
        Args:
            tasks: 任务入口列表
        
        Returns:
            bool: 是否全部执行成功
        """
        for task in tasks:
            if not self.run_pipeline_task(task):
                return False
        return True
    
    def override_pipeline(self, pipeline_override: Dict) -> bool:
        """
        动态覆盖Pipeline配置
        
        Args:
            pipeline_override: 覆盖配置字典
        
        Returns:
            bool: 是否覆盖成功
        """
        if not self._connected or not self._resource:
            return False
        
        try:
            return self._resource.override_pipeline(pipeline_override)
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "Pipeline覆盖异常", error=str(e))
            return False
    
    # ==================== 单次控制方法（备用） ====================
    
    def click(self, x: int, y: int) -> bool:
        """
        点击（单次控制，建议优先使用Pipeline）
        
        Args:
            x: x坐标
            y: y坐标
        
        Returns:
            bool: 是否执行成功
        """
        if not self._connected or not self._controller:
            return False
        
        try:
            job = self._controller.post_click(x, y)
            job.wait()
            
            if self.config.press_duration_ms > 0:
                time.sleep(self.config.press_duration_ms / 1000.0)
            
            return job.succeeded
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "点击执行异常", error=str(e))
            return False
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """
        滑动（单次控制，建议优先使用Pipeline）
        
        Args:
            x1: 起点x
            y1: 起点y
            x2: 终点x
            y2: 终点y
            duration: 滑动时长（毫秒）
        
        Returns:
            bool: 是否执行成功
        """
        if not self._connected or not self._controller:
            return False
        
        try:
            job = self._controller.post_swipe(x1, y1, x2, y2, duration)
            job.wait()
            return job.succeeded
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "滑动执行异常", error=str(e))
            return False
    
    def long_press(self, x: int, y: int, duration: int = 1000) -> bool:
        """
        长按（单次控制，建议优先使用Pipeline）
        
        Args:
            x: x坐标
            y: y坐标
            duration: 长按时长（毫秒）
        
        Returns:
            bool: 是否执行成功
        """
        if not self._connected or not self._controller:
            return False
        
        try:
            job = self._controller.post_touch_down(x, y)
            job.wait()
            
            if not job.succeeded:
                return False
            
            time.sleep(duration / 1000.0)
            
            job = self._controller.post_touch_up()
            job.wait()
            return job.succeeded
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "长按执行异常", error=str(e))
            return False
    
    def screencap(self) -> Optional[any]:
        """
        截图
        
        Returns:
            numpy.ndarray: 截图图像（BGR格式）或None
        """
        if not self._connected or not self._controller:
            return None
        
        try:
            job = self._controller.post_screencap()
            job.wait()
            
            if job.succeeded:
                return self._controller.cached_image
            return None
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "截图异常", error=str(e))
            return None
    
    def get_resolution(self) -> Tuple[int, int]:
        """
        获取窗口分辨率
        
        Returns:
            Tuple[int, int]: (width, height)
        """
        if self._resolution == (0, 0) and self._controller:
            try:
                image = self.screencap()
                if image is not None:
                    self._resolution = (image.shape[1], image.shape[0])
            except:
                pass
        return self._resolution
    
    def click_key(self, key: int) -> bool:
        """
        点击按键
        
        Args:
            key: 虚拟键码
        
        Returns:
            bool: 是否执行成功
        """
        if not self._connected or not self._controller:
            return False
        
        try:
            job = self._controller.post_click_key(key)
            job.wait()
            return job.succeeded
        except:
            return False
    
    def scroll(self, dx: int, dy: int) -> bool:
        """
        滚动
        
        Args:
            dx: 水平滚动距离
            dy: 垂直滚动距离
        
        Returns:
            bool: 是否执行成功
        """
        if not self._connected or not self._controller:
            return False
        
        try:
            job = self._controller.post_scroll(dx, dy)
            job.wait()
            return job.succeeded
        except:
            return False
    
    # ==================== 属性访问 ====================
    
    @property
    def connected(self) -> bool:
        """是否已连接"""
        return self._connected
    
    @property
    def tasker(self) -> Optional[Tasker]:
        """获取Tasker实例"""
        return self._tasker
    
    @property
    def resource(self) -> Optional[Resource]:
        """获取Resource实例"""
        return self._resource
    
    @property
    def controller(self) -> Optional[Win32Controller]:
        """获取Controller实例"""
        return self._controller