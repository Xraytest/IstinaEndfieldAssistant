"""
设备录屏记录模块 - 用于调试的运行时录屏功能
录制屏幕并标记触控操作位置
"""
import os
import sys
import time
import threading
import queue
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import io

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from logger import get_logger, LogCategory, LogLevel

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("警告: PIL库未安装，录屏功能将不可用")
    Image = None
    ImageDraw = None
    ImageFont = None

try:
    import cv2
    import numpy as np
except ImportError:
    print("警告: OpenCV库未安装，录屏功能将不可用")
    cv2 = None
    np = None


class TouchEventType(Enum):
    """触控事件类型"""
    CLICK = "click"
    SWIPE = "swipe"
    LONG_PRESS = "long_press"
    DRAG = "drag"


@dataclass
class TouchEvent:
    """触控事件数据"""
    event_type: TouchEventType
    coordinates: List[Tuple[int, int]]  # 点击坐标列表
    timestamp: float  # 相对于录屏开始的时间戳（秒）
    purpose: str = ""
    duration_ms: int = 0  # 持续时间（毫秒）
    visual_duration: float = 1.0  # 视觉标记显示时长（秒）


@dataclass
class ScreenFrame:
    """屏幕帧数据"""
    image_data: bytes  # PNG格式的原始图像数据
    timestamp: float  # 相对于录屏开始的时间戳（秒）


class ScreenRecorder:
    """
    设备录屏记录器

    功能：
    1. 捕获屏幕帧并记录时间戳
    2. 记录触控操作位置和时间
    3. 在帧上绘制点按标识
    4. 导出为视频文件
    """

    def __init__(self,
                 fps: int = 10,
                 show_touch_duration: float = 1.0,
                 touch_marker_color: Tuple[int, int, int] = (255, 0, 0),
                 output_dir: str = None):
        """
        初始化录屏记录器

        Args:
            fps: 录制帧率
            show_touch_duration: 触控标记显示时长（秒）
            touch_marker_color: 触控标记颜色 (R, G, B)
            output_dir: 输出目录，默认为 client_debug/recordings
        """
        self.fps = fps
        self.show_touch_duration = show_touch_duration
        self.touch_marker_color = touch_marker_color
        self.logger = get_logger()

        # 设置输出目录
        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = os.path.join(os.path.dirname(__file__), "recordings")

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

        # 录制状态
        self.is_recording = False
        self.start_time = 0
        self.frames: List[ScreenFrame] = []
        self.touch_events: List[TouchEvent] = []

        # 线程安全
        self.lock = threading.Lock()
        self.frame_queue = queue.Queue(maxsize=100)  # 帧队列
        self.recording_thread = None

        # 触控回调
        self._touch_callback: Optional[Callable] = None

        # 视频写入器
        self._video_writer = None

        self.logger.info(LogCategory.MAIN, "录屏记录器初始化完成",
                        fps=fps, output_dir=self.output_dir)

    def start_recording(self) -> bool:
        """
        开始录制

        Returns:
            是否成功开始录制
        """
        if self.is_recording:
            self.logger.warning(LogCategory.MAIN, "录屏已在进行中")
            return False

        if Image is None or cv2 is None:
            self.logger.error(LogCategory.MAIN, "录屏依赖库未安装（PIL, OpenCV）")
            return False

        with self.lock:
            self.frames.clear()
            self.touch_events.clear()
            self.is_recording = True
            self.start_time = time.time()

        self.logger.info(LogCategory.MAIN, "录屏开始",
                        start_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        return True

    def stop_recording(self) -> Optional[str]:
        """
        停止录制并导出视频

        Returns:
            生成的视频文件路径，失败返回None
        """
        if not self.is_recording:
            self.logger.warning(LogCategory.MAIN, "录屏未在进行中")
            return None

        with self.lock:
            self.is_recording = False

        # 等待帧队列处理完成
        time.sleep(0.5)

        # 生成视频
        video_path = self._export_video()

        self.logger.info(LogCategory.MAIN, "录屏结束",
                        frames_count=len(self.frames),
                        touch_events_count=len(self.touch_events),
                        video_path=video_path)

        return video_path

    def capture_frame(self, image_data: bytes) -> bool:
        """
        捕获一帧屏幕

        Args:
            image_data: PNG格式的图像数据（base64编码或原始字节）

        Returns:
            是否成功捕获
        """
        if not self.is_recording:
            return False

        try:
            # 如果是base64编码，解码
            if isinstance(image_data, str):
                import base64
                image_data = base64.b64decode(image_data)

            # 计算时间戳
            timestamp = time.time() - self.start_time

            # 创建帧数据
            frame = ScreenFrame(
                image_data=image_data,
                timestamp=timestamp
            )

            with self.lock:
                self.frames.append(frame)

            self.logger.debug(LogCategory.MAIN, "帧捕获完成",
                            timestamp=round(timestamp, 3),
                            frame_index=len(self.frames))

            return True

        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "帧捕获异常", exc_info=True)
            return False

    def record_touch_event(self,
                           event_type: TouchEventType,
                           coordinates: List[Tuple[int, int]],
                           purpose: str = "",
                           duration_ms: int = 0) -> bool:
        """
        记录触控事件

        Args:
            event_type: 事件类型
            coordinates: 坐标列表 [(x1, y1), (x2, y2), ...]
            purpose: 操作目的说明
            duration_ms: 持续时间（毫秒）

        Returns:
            是否成功记录
        """
        if not self.is_recording:
            return False

        try:
            timestamp = time.time() - self.start_time

            event = TouchEvent(
                event_type=event_type,
                coordinates=coordinates,
                timestamp=timestamp,
                purpose=purpose,
                duration_ms=duration_ms,
                visual_duration=self.show_touch_duration
            )

            with self.lock:
                self.touch_events.append(event)

            self.logger.info(LogCategory.MAIN, "触控事件记录",
                           event_type=event_type.value,
                           coordinates=coordinates,
                           timestamp=round(timestamp, 3),
                           purpose=purpose)

            return True

        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "触控事件记录异常", exc_info=True)
            return False

    def record_click(self, x: int, y: int, purpose: str = "") -> bool:
        """记录点击事件"""
        return self.record_touch_event(
            TouchEventType.CLICK,
            [(x, y)],
            purpose=purpose
        )

    def record_swipe(self, x1: int, y1: int, x2: int, y2: int,
                     purpose: str = "", duration_ms: int = 300) -> bool:
        """记录滑动事件"""
        return self.record_touch_event(
            TouchEventType.SWIPE,
            [(x1, y1), (x2, y2)],
            purpose=purpose,
            duration_ms=duration_ms
        )

    def record_long_press(self, x: int, y: int,
                          purpose: str = "", duration_ms: int = 500) -> bool:
        """记录长按事件"""
        return self.record_touch_event(
            TouchEventType.LONG_PRESS,
            [(x, y)],
            purpose=purpose,
            duration_ms=duration_ms
        )

    def _export_video(self) -> Optional[str]:
        """
        导出视频文件

        Returns:
            视频文件路径，失败返回None
        """
        if not self.frames:
            self.logger.warning(LogCategory.MAIN, "没有帧数据，跳过视频导出")
            return None

        try:
            # 生成文件名
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_filename = f"recording_{timestamp_str}.mp4"
            video_path = os.path.join(self.output_dir, video_filename)

            # 读取第一帧获取尺寸
            first_frame = self.frames[0]
            image = Image.open(io.BytesIO(first_frame.image_data))
            width, height = image.size

            # 创建视频写入器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(
                video_path,
                fourcc,
                self.fps,
                (width, height)
            )

            if not video_writer.isOpened():
                self.logger.error(LogCategory.MAIN, "无法创建视频写入器")
                return None

            self.logger.info(LogCategory.MAIN, "开始导出视频",
                           frames_count=len(self.frames),
                           resolution=f"{width}x{height}",
                           fps=self.fps)

            # 处理每一帧
            for i, frame in enumerate(self.frames):
                # 解码图像
                image = Image.open(io.BytesIO(frame.image_data))

                # 绘制触控标记
                image = self._draw_touch_markers(image, frame.timestamp)

                # 转换为OpenCV格式
                frame_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

                # 写入视频
                video_writer.write(frame_array)

                # 进度日志
                if (i + 1) % 50 == 0 or i == len(self.frames) - 1:
                    self.logger.debug(LogCategory.MAIN, f"视频导出进度: {i+1}/{len(self.frames)}")

            video_writer.release()

            self.logger.info(LogCategory.MAIN, "视频导出完成",
                           video_path=video_path,
                           duration_seconds=round(self.frames[-1].timestamp, 2))

            return video_path

        except Exception as e:
            self.logger.exception(LogCategory.MAIN, "视频导出异常", exc_info=True)
            return None

    def _draw_touch_markers(self, image: 'Image.Image', current_timestamp: float) -> 'Image.Image':
        """
        在图像上绘制触控标记

        Args:
            image: PIL图像
            current_timestamp: 当前帧的时间戳

        Returns:
            绘制了标记的图像
        """
        if not self.touch_events:
            return image

        # 创建副本以避免修改原图
        image = image.copy()
        draw = ImageDraw.Draw(image)

        # 尝试加载字体
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None

        # 绘制每个仍在显示时间内的触控事件
        for event in self.touch_events:
            # 检查是否在显示时间范围内
            time_elapsed = current_timestamp - event.timestamp
            if time_elapsed < 0 or time_elapsed > event.visual_duration:
                continue

            # 计算透明度（渐隐效果）
            alpha = int(255 * (1 - time_elapsed / event.visual_duration))

            # 根据事件类型绘制不同的标记
            if event.event_type == TouchEventType.CLICK:
                self._draw_click_marker(draw, event, alpha, font)
            elif event.event_type == TouchEventType.SWIPE:
                self._draw_swipe_marker(draw, event, alpha, font)
            elif event.event_type == TouchEventType.LONG_PRESS:
                self._draw_long_press_marker(draw, event, alpha, font)
            elif event.event_type == TouchEventType.DRAG:
                self._draw_drag_marker(draw, event, alpha, font)

        return image

    def _draw_click_marker(self, draw: 'ImageDraw.ImageDraw',
                           event: TouchEvent, alpha: int,
                           font: Optional['ImageFont.FreeTypeFont']):
        """绘制点击标记"""
        if not event.coordinates:
            return

        x, y = event.coordinates[0]
        color = (*self.touch_marker_color, alpha) if len(self.touch_marker_color) == 3 else self.touch_marker_color

        # 绘制圆形标记
        radius = 20
        # 外圈
        draw.ellipse(
            [(x - radius, y - radius), (x + radius, y + radius)],
            outline=color[:3],
            width=3
        )
        # 内圈
        inner_radius = 5
        draw.ellipse(
            [(x - inner_radius, y - inner_radius), (x + inner_radius, y + inner_radius)],
            fill=color[:3]
        )

        # 绘制十字线
        line_length = 30
        draw.line([(x - line_length, y), (x + line_length, y)], fill=color[:3], width=2)
        draw.line([(x, y - line_length), (x, y + line_length)], fill=color[:3], width=2)

        # 绘制标签
        if font and event.purpose:
            label = f"Click: {event.purpose}"
            draw.text((x + 25, y - 10), label, fill=color[:3], font=font)

    def _draw_swipe_marker(self, draw: 'ImageDraw.ImageDraw',
                           event: TouchEvent, alpha: int,
                           font: Optional['ImageFont.FreeTypeFont']):
        """绘制滑动标记"""
        if len(event.coordinates) < 2:
            return

        start_x, start_y = event.coordinates[0]
        end_x, end_y = event.coordinates[1]
        color = self.touch_marker_color

        # 绘制滑动路径
        draw.line(
            [(start_x, start_y), (end_x, end_y)],
            fill=color,
            width=3
        )

        # 绘制箭头
        self._draw_arrow(draw, start_x, start_y, end_x, end_y, color)

        # 绘制起点标记
        draw.ellipse(
            [(start_x - 8, start_y - 8), (start_x + 8, start_y + 8)],
            outline=color,
            width=2
        )

        # 绘制终点标记
        draw.ellipse(
            [(end_x - 5, end_y - 5), (end_x + 5, end_y + 5)],
            fill=color
        )

        # 绘制标签
        if font and event.purpose:
            label = f"Swipe: {event.purpose}"
            draw.text((end_x + 10, end_y - 10), label, fill=color, font=font)

    def _draw_long_press_marker(self, draw: 'ImageDraw.ImageDraw',
                                event: TouchEvent, alpha: int,
                                font: Optional['ImageFont.FreeTypeFont']):
        """绘制长按标记"""
        if not event.coordinates:
            return

        x, y = event.coordinates[0]
        color = self.touch_marker_color

        # 绘制大圆形
        radius = 25
        draw.ellipse(
            [(x - radius, y - radius), (x + radius, y + radius)],
            outline=color,
            width=4
        )

        # 绘制内部填充（半透明效果）
        inner_radius = 15
        draw.ellipse(
            [(x - inner_radius, y - inner_radius), (x + inner_radius, y + inner_radius)],
            outline=color,
            width=2
        )

        # 绘制持续时间标签
        if font:
            label = f"Long: {event.duration_ms}ms"
            draw.text((x + 30, y - 10), label, fill=color, font=font)

    def _draw_drag_marker(self, draw: 'ImageDraw.ImageDraw',
                          event: TouchEvent, alpha: int,
                          font: Optional['ImageFont.FreeTypeFont']):
        """绘制拖拽标记（与滑动类似，但样式不同）"""
        if len(event.coordinates) < 2:
            return

        start_x, start_y = event.coordinates[0]
        end_x, end_y = event.coordinates[1]
        color = (255, 165, 0)  # 橙色

        # 绘制虚线效果（通过绘制多条短线）
        dash_length = 10
        gap_length = 5
        total_length = ((start_x - end_x) ** 2 + (start_y - end_y) ** 2) ** 0.5
        dx = (end_x - start_x) / total_length if total_length > 0 else 0
        dy = (end_y - start_y) / total_length if total_length > 0 else 0

        current_pos = 0
        while current_pos < total_length:
            segment_start_x = start_x + dx * current_pos
            segment_start_y = start_y + dy * current_pos
            segment_end_pos = min(current_pos + dash_length, total_length)
            segment_end_x = start_x + dx * segment_end_pos
            segment_end_y = start_y + dy * segment_end_pos
            draw.line(
                [(segment_start_x, segment_start_y), (segment_end_x, segment_end_y)],
                fill=color,
                width=3
            )
            current_pos += dash_length + gap_length

        # 绘制标记
        draw.rectangle(
            [(start_x - 6, start_y - 6), (start_x + 6, start_y + 6)],
            outline=color,
            width=2
        )
        draw.ellipse(
            [(end_x - 6, end_y - 6), (end_x + 6, end_y + 6)],
            fill=color
        )

        # 绘制标签
        if font and event.purpose:
            label = f"Drag: {event.purpose}"
            draw.text((end_x + 10, end_y - 10), label, fill=color, font=font)

    def _draw_arrow(self, draw: 'ImageDraw.ImageDraw',
                    start_x: float, start_y: float,
                    end_x: float, end_y: float,
                    color: Tuple[int, int, int]):
        """绘制箭头"""
        import math

        # 计算箭头方向
        dx = end_x - start_x
        dy = end_y - start_y
        length = math.sqrt(dx * dx + dy * dy)

        if length < 10:
            return

        # 归一化方向向量
        dx /= length
        dy /= length

        # 箭头大小
        arrow_length = 15
        arrow_width = 8

        # 箭头两侧的点
        arrow_x1 = end_x - arrow_length * dx + arrow_width * dy
        arrow_y1 = end_y - arrow_length * dy - arrow_width * dx
        arrow_x2 = end_x - arrow_length * dx - arrow_width * dy
        arrow_y2 = end_y - arrow_length * dy + arrow_width * dx

        # 绘制箭头三角形
        draw.polygon(
            [(end_x, end_y), (arrow_x1, arrow_y1), (arrow_x2, arrow_y2)],
            fill=color
        )

    def get_recording_status(self) -> Dict:
        """
        获取录制状态

        Returns:
            包含录制状态的字典
        """
        with self.lock:
            return {
                'is_recording': self.is_recording,
                'frames_count': len(self.frames),
                'touch_events_count': len(self.touch_events),
                'duration': time.time() - self.start_time if self.is_recording else 0,
                'output_dir': self.output_dir
            }

    def set_touch_callback(self, callback: Callable):
        """设置触控事件回调函数"""
        self._touch_callback = callback


# 全局录屏记录器实例
_recorder_instance: Optional[ScreenRecorder] = None


def get_recorder() -> Optional[ScreenRecorder]:
    """获取全局录屏记录器实例"""
    global _recorder_instance
    if _recorder_instance is None:
        _recorder_instance = ScreenRecorder()
    return _recorder_instance


def init_recorder(fps: int = 10,
                  show_touch_duration: float = 1.0,
                  output_dir: str = None) -> ScreenRecorder:
    """
    初始化全局录屏记录器

    Args:
        fps: 帧率
        show_touch_duration: 触控标记显示时长
        output_dir: 输出目录

    Returns:
        ScreenRecorder实例
    """
    global _recorder_instance
    _recorder_instance = ScreenRecorder(
        fps=fps,
        show_touch_duration=show_touch_duration,
        output_dir=output_dir
    )
    return _recorder_instance