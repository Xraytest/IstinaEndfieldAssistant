"""
MaaFramework Android触控适配器
基于MaaFramework的AdbController实现Android设备触控
优先使用Pipeline方式执行任务

注意：MaaFramework通过pip安装（pip install MaaFw），导入名为 maa
"""
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from core.logger import get_logger, LogCategory, LogLevel

# 尝试导入MaaFramework（pip install MaaFw，导入名 maa）
MAAFW_AVAILABLE = False

try:
    from maa import Library
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.controller import AdbController
    from maa.toolkit import Toolkit
    from maa.define import MaaAdbScreencapMethodEnum, MaaAdbInputMethodEnum
    from maa.event_sink import NotificationType
    # 新版本5.10.0在导入maa时已自动初始化Library
    MAAFW_AVAILABLE = True
except ImportError:
    # 定义占位类型
    Tasker = None
    Resource = None
    AdbController = None
    print("警告: MaaFramework库未安装，触控功能将不可用。请使用 pip install MaaFw 安装")


@dataclass
class MaaFwTouchConfig:
    """MaaFramework触控配置"""
    adb_path: str = ""
    address: str = ""
    screencap_methods: int = 0  # MaaAdbScreencapMethodEnum.Default
    input_methods: int = 0  # MaaAdbInputMethodEnum.Default
    config: Dict = None
    
    # 触控参数
    press_duration_ms: int = 50
    press_jitter_px: int = 2
    swipe_delay_min_ms: int = 100
    swipe_delay_max_ms: int = 300
    use_normalized_coords: bool = True
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}


class MaaFwTouchExecutor:
    """
    MaaFramework触控执行器
    
    基于MaaFramework的AdbController实现，优先使用Pipeline执行任务
    """
    
    def __init__(self, config: MaaFwTouchConfig):
        """
        初始化触控执行器
        
        Args:
            config: MaaFramework触控配置
        """
        self.config = config
        self.logger = get_logger()
        
        # MaaFramework组件
        self._library_loaded = False
        self._resource: Optional[Resource] = None
        self._controller: Optional[AdbController] = None
        self._tasker: Optional[Tasker] = None
        
        # 设备状态
        self._connected = False
        self._resolution: Tuple[int, int] = (0, 0)
        self._uuid = ""
        
    def _load_library(self, lib_path: Optional[str] = None) -> bool:
        """
        加载MaaFramework动态库
        
        注意：MaaFw 5.10.0+ 在导入maa时已自动初始化Library，
        使用包内bin目录的二进制文件。
        此方法主要用于检查库是否可用，以及可选的自定义路径初始化。
        
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
        连接Android设备
        
        Returns:
            bool: 是否连接成功
        """
        if not self._load_library():
            return False
        
        try:
            # 初始化Toolkit配置（可选）
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            config_dir = os.path.join(project_root, "IstinaEndfieldAssistant", "config")
            maa_option_path = os.path.join(config_dir, "maa_option.json")
            
            if os.path.exists(maa_option_path):
                Toolkit.init_option(Path(config_dir))
                self.logger.debug(LogCategory.MAIN, "MaaToolkit配置初始化完成")
            
            # 创建资源
            self._resource = Resource()
            self.logger.debug(LogCategory.MAIN, "Resource创建完成")
            
            # 创建ADB控制器
            self._controller = AdbController(
                adb_path=Path(self.config.adb_path),
                address=self.config.address,
                screencap_methods=self.config.screencap_methods,
                input_methods=self.config.input_methods,
                config=self.config.config
            )
            self.logger.debug(LogCategory.MAIN, "AdbController创建完成",
                             adb_path=self.config.adb_path,
                             address=self.config.address)
            
            # 连接设备
            job = self._controller.post_connection()
            job.wait()
            
            if not job.succeeded:
                self.logger.exception(LogCategory.MAIN, "ADB控制器连接失败")
                return False
            
            # 获取设备信息
            self._uuid = self._controller.uuid
            cached_image = self._controller.cached_image
            if cached_image is not None:
                self._resolution = (cached_image.shape[1], cached_image.shape[0])
            
            # 创建Tasker并绑定
            self._tasker = Tasker()
            if not self._tasker.bind(self._resource, self._controller):
                self.logger.exception(LogCategory.MAIN, "Tasker绑定失败")
                return False
            
            self._connected = True
            self.logger.info(LogCategory.MAIN, "Android设备连接成功",
                            uuid=self._uuid,
                            resolution=f"{self._resolution[0]}x{self._resolution[1]}")
            return True
            
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "Android设备连接异常", error=str(e))
            return False
    
    def disconnect(self) -> bool:
        """
        断开设备连接
        
        Returns:
            bool: 是否断开成功
        """
        try:
            self._connected = False
            self._tasker = None
            self._controller = None
            self._resource = None
            self.logger.info(LogCategory.MAIN, "Android设备已断开")
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
            self.logger.exception(LogCategory.MAIN, "设备未连接，无法加载Pipeline")
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
        
        通过Pipeline JSON定义执行复杂任务，比单次控制更高效
        
        Args:
            entry: 任务入口名称
            pipeline_override: 动态覆盖配置
        
        Returns:
            bool: 是否执行成功
        """
        if not self._connected or not self._tasker:
            self.logger.exception(LogCategory.MAIN, "设备未连接，无法执行Pipeline任务")
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
            self.logger.exception(LogCategory.MAIN, "设备未连接")
            return False
        
        try:
            result = self._resource.override_pipeline(pipeline_override)
            if result:
                self.logger.debug(LogCategory.MAIN, "Pipeline覆盖成功")
            return result
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
            self.logger.exception(LogCategory.MAIN, "设备未连接")
            return False
        
        try:
            # 应用抖动（如果配置启用）
            if self.config.press_jitter_px > 0:
                import random
                x += random.randint(-self.config.press_jitter_px, self.config.press_jitter_px)
                y += random.randint(-self.config.press_jitter_px, self.config.press_jitter_px)
            
            job = self._controller.post_click(x, y)
            job.wait()
            
            # 添加按压延时
            if self.config.press_duration_ms > 0:
                time.sleep(self.config.press_duration_ms / 1000.0)
            
            if job.succeeded:
                self.logger.debug(LogCategory.MAIN, "点击执行成功", x=x, y=y)
                return True
            else:
                self.logger.exception(LogCategory.MAIN, "点击执行失败", x=x, y=y)
                return False
                
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
            self.logger.exception(LogCategory.MAIN, "设备未连接")
            return False
        
        try:
            # 应用滑动延时随机化
            if self.config.swipe_delay_min_ms > 0 and self.config.swipe_delay_max_ms > 0:
                import random
                actual_duration = random.randint(
                    max(duration, self.config.swipe_delay_min_ms),
                    duration + self.config.swipe_delay_max_ms
                )
            else:
                actual_duration = duration
            
            job = self._controller.post_swipe(x1, y1, x2, y2, actual_duration)
            job.wait()
            
            if job.succeeded:
                self.logger.debug(LogCategory.MAIN, "滑动执行成功",
                                x1=x1, y1=y1, x2=x2, y2=y2, duration=actual_duration)
                return True
            else:
                self.logger.exception(LogCategory.MAIN, "滑动执行失败",
                                x1=x1, y1=y1, x2=x2, y2=y2)
                return False
                
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
            self.logger.exception(LogCategory.MAIN, "设备未连接")
            return False
        
        try:
            # 应用抖动
            if self.config.press_jitter_px > 0:
                import random
                x += random.randint(-self.config.press_jitter_px, self.config.press_jitter_px)
                y += random.randint(-self.config.press_jitter_px, self.config.press_jitter_px)
            
            # 使用touch_down + touch_up实现长按
            job = self._controller.post_touch_down(x, y)
            job.wait()
            
            if not job.succeeded:
                return False
            
            # 等待
            time.sleep(duration / 1000.0)
            
            # 抬起
            job = self._controller.post_touch_up()
            job.wait()
            
            if job.succeeded:
                self.logger.debug(LogCategory.MAIN, "长按执行成功", x=x, y=y, duration=duration)
                return True
            else:
                self.logger.exception(LogCategory.MAIN, "长按执行失败", x=x, y=y)
                return False
                
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
            self.logger.exception(LogCategory.MAIN, "设备未连接")
            return None
        
        try:
            job = self._controller.post_screencap()
            job.wait()
            
            if job.succeeded:
                return self._controller.cached_image
            else:
                self.logger.warning(LogCategory.MAIN, "截图失败")
                return None
                
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "截图异常", error=str(e))
            return None
    
    def get_resolution(self) -> Tuple[int, int]:
        """
        获取设备分辨率
        
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
    
    def start_app(self, package_name: str) -> bool:
        """
        启动应用
        
        Args:
            package_name: 应用包名
        
        Returns:
            bool: 是否启动成功
        """
        if not self._connected or not self._controller:
            return False
        
        try:
            job = self._controller.post_start_app(package_name)
            job.wait()
            return job.succeeded
        except:
            return False
    
    def stop_app(self, package_name: str) -> bool:
        """
        关闭应用
        
        Args:
            package_name: 应用包名
        
        Returns:
            bool: 是否关闭成功
        """
        if not self._connected or not self._controller:
            return False
        
        try:
            job = self._controller.post_stop_app(package_name)
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
        """获取Tasker实例（用于Pipeline任务）"""
        return self._tasker
    
    @property
    def resource(self) -> Optional[Resource]:
        """获取Resource实例（用于加载Pipeline）"""
        return self._resource
    
    @property
    def controller(self) -> Optional[AdbController]:
        """获取Controller实例（用于单次控制）"""
        return self._controller