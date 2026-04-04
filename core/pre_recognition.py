"""
客户端预识别模块
在发送截图到服务端前，先进行本地元素识别
将识别到的位置信息附加到VLM prompt中，便于正确点击
"""

import base64
import json
import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from io import BytesIO
from PIL import Image, ImageDraw
import threading

# 尝试导入OpenCV
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


@dataclass
class RecognitionResult:
    """识别结果数据类"""
    id: str
    type: str  # template, color, ocr
    found: bool
    box: Optional[Tuple[int, int, int, int]] = None  # (x, y, width, height)
    center: Optional[Tuple[int, int]] = None  # 中心点坐标
    confidence: float = 0.0
    text: Optional[str] = None
    label: str = ""


@dataclass
class PreRecognitionConfig:
    """预识别配置"""
    templates: List[Dict[str, Any]] = field(default_factory=list)
    color_matches: List[Dict[str, Any]] = field(default_factory=list)
    ocr_regions: List[Dict[str, Any]] = field(default_factory=list)


class ClientPreRecognizer:
    """客户端预识别器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, resource_path: str = None, config: Dict = None):
        """
        初始化预识别器
        
        Args:
            resource_path: 资源文件路径（模板图像等）
            config: 配置字典
        """
        self.logger = logging.getLogger("ClientPreRecognizer")
        self.resource_path = resource_path or os.path.join(
            os.path.dirname(__file__), '..', '..', 'resources', 'templates'
        )
        self.config = config or {}
        
        # 默认置信度阈值
        self.confidence_threshold = self.config.get('confidence_threshold', 0.7)
        
        # 模板缓存
        self._template_cache: Dict[str, Any] = {}
        
        # 初始化状态
        self._initialized = CV2_AVAILABLE
        if not CV2_AVAILABLE:
            self.logger.warning("OpenCV不可用，预识别功能受限")
    
    def is_available(self) -> bool:
        """检查预识别器是否可用"""
        return self._initialized
    
    def process_screenshot(
        self, 
        screenshot: Image.Image, 
        config: PreRecognitionConfig
    ) -> Tuple[Image.Image, List[RecognitionResult]]:
        """
        处理截图，执行预识别
        
        Args:
            screenshot: PIL Image对象
            config: 预识别配置
            
        Returns:
            (标注后的图像, 识别结果列表)
        """
        if not self._initialized:
            return screenshot, []
        
        results = []
        annotated_image = screenshot.copy()
        
        # 执行模板匹配
        for template_config in config.templates:
            result = self._match_template(screenshot, template_config)
            if result:
                results.append(result)
        
        # 执行颜色匹配
        for color_config in config.color_matches:
            result = self._match_color(screenshot, color_config)
            if result:
                results.append(result)
        
        # OCR识别（如果有配置）
        for ocr_config in config.ocr_regions:
            result = self._perform_ocr(screenshot, ocr_config)
            if result:
                results.append(result)
        
        # 标注图像
        if results:
            annotated_image = self._annotate_image(screenshot, results)
        
        return annotated_image, results
    
    def process_screenshot_base64(
        self, 
        image_base64: str, 
        config: PreRecognitionConfig
    ) -> Tuple[str, List[RecognitionResult]]:
        """
        处理base64编码的截图
        
        Args:
            image_base64: base64编码的图像
            config: 预识别配置
            
        Returns:
            (标注后图像的base64, 识别结果列表)
        """
        # 解码图像
        if image_base64.startswith('data:image'):
            image_base64 = image_base64.split(',')[1]
        
        image_bytes = base64.b64decode(image_base64)
        screenshot = Image.open(BytesIO(image_bytes))
        
        # 处理
        annotated_image, results = self.process_screenshot(screenshot, config)
        
        # 编码返回
        buffer = BytesIO()
        annotated_image.save(buffer, format='PNG')
        annotated_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return annotated_base64, results
    
    def _match_template(
        self, 
        screenshot: Image.Image, 
        config: Dict[str, Any]
    ) -> Optional[RecognitionResult]:
        """
        模板匹配
        
        Args:
            screenshot: 截图
            config: 模板配置，包含:
                - id: 识别ID
                - template_path: 模板路径
                - threshold: 匹配阈值
                - roi: 感兴趣区域 [x, y, w, h]
                - label: 显示标签
        """
        if not CV2_AVAILABLE:
            return None
        
        template_id = config.get('id', 'unknown')
        template_path = config.get('template_path')
        threshold = config.get('threshold', self.confidence_threshold)
        roi = config.get('roi')
        label = config.get('label', template_id)
        
        if not template_path:
            # 尝试从资源路径查找
            template_name = config.get('template_name')
            if template_name:
                template_path = os.path.join(self.resource_path, template_name)
        
        if not template_path or not os.path.exists(template_path):
            self.logger.debug(f"模板文件不存在: {template_path}")
            return RecognitionResult(
                id=template_id,
                type='template',
                found=False,
                label=label
            )
        
        try:
            # 转换为OpenCV格式
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # 加载模板
            if template_path not in self._template_cache:
                self._template_cache[template_path] = cv2.imread(template_path)
            template = self._template_cache[template_path]
            
            if template is None:
                self.logger.warning(f"无法加载模板: {template_path}")
                return RecognitionResult(
                    id=template_id,
                    type='template',
                    found=False,
                    label=label
                )
            
            # 应用ROI
            x_offset, y_offset = 0, 0
            if roi:
                x, y, w, h = roi
                screenshot_cv = screenshot_cv[y:y+h, x:x+w]
                x_offset, y_offset = x, y
            
            # 检查尺寸
            if template.shape[0] > screenshot_cv.shape[0] or \
               template.shape[1] > screenshot_cv.shape[1]:
                return RecognitionResult(
                    id=template_id,
                    type='template',
                    found=False,
                    label=label
                )
            
            # 模板匹配
            result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                # 计算全局坐标
                template_h, template_w = template.shape[:2]
                global_x = x_offset + max_loc[0]
                global_y = y_offset + max_loc[1]
                center_x = global_x + template_w // 2
                center_y = global_y + template_h // 2
                
                return RecognitionResult(
                    id=template_id,
                    type='template',
                    found=True,
                    box=(global_x, global_y, template_w, template_h),
                    center=(center_x, center_y),
                    confidence=float(max_val),
                    label=label
                )
            
            return RecognitionResult(
                id=template_id,
                type='template',
                found=False,
                label=label
            )
            
        except Exception as e:
            self.logger.error(f"模板匹配失败: {template_id}, error={e}")
            return RecognitionResult(
                id=template_id,
                type='template',
                found=False,
                label=label
            )
    
    def _match_color(
        self, 
        screenshot: Image.Image, 
        config: Dict[str, Any]
    ) -> Optional[RecognitionResult]:
        """
        颜色匹配
        
        Args:
            screenshot: 截图
            config: 颜色配置，包含:
                - id: 识别ID
                - lower: 颜色下限 [B, G, R] 或 [H, S, V]
                - upper: 颜色上限 [B, G, R] 或 [H, S, V]
                - roi: 感兴趣区域
                - min_count: 最小像素数
                - label: 显示标签
        """
        if not CV2_AVAILABLE:
            return None
        
        color_id = config.get('id', 'unknown')
        lower = config.get('lower', [0, 0, 0])
        upper = config.get('upper', [255, 255, 255])
        roi = config.get('roi')
        min_count = config.get('min_count', 10)
        label = config.get('label', color_id)
        
        try:
            # 转换为OpenCV格式
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # 应用ROI
            x_offset, y_offset = 0, 0
            if roi:
                x, y, w, h = roi
                screenshot_cv = screenshot_cv[y:y+h, x:x+w]
                x_offset, y_offset = x, y
            
            # 创建颜色掩码
            lower_np = np.array(lower)
            upper_np = np.array(upper)
            mask = cv2.inRange(screenshot_cv, lower_np, upper_np)
            
            # 查找轮廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # 找到最大轮廓
                largest_contour = max(contours, key=cv2.contourArea)
                area = cv2.contourArea(largest_contour)
                
                if area >= min_count:
                    # 获取边界框
                    x, y, w, h = cv2.boundingRect(largest_contour)
                    global_x = x_offset + x
                    global_y = y_offset + y
                    center_x = global_x + w // 2
                    center_y = global_y + h // 2
                    
                    return RecognitionResult(
                        id=color_id,
                        type='color',
                        found=True,
                        box=(global_x, global_y, w, h),
                        center=(center_x, center_y),
                        confidence=min(area / 1000.0, 1.0),
                        label=label
                    )
            
            return RecognitionResult(
                id=color_id,
                type='color',
                found=False,
                label=label
            )
            
        except Exception as e:
            self.logger.error(f"颜色匹配失败: {color_id}, error={e}")
            return RecognitionResult(
                id=color_id,
                type='color',
                found=False,
                label=label
            )
    
    def _perform_ocr(
        self, 
        screenshot: Image.Image, 
        config: Dict[str, Any]
    ) -> Optional[RecognitionResult]:
        """
        OCR识别（基础实现，需要额外的OCR库）
        
        Args:
            screenshot: 截图
            config: OCR配置
        """
        # OCR需要额外的库支持，这里提供基础框架
        ocr_id = config.get('id', 'unknown')
        label = config.get('label', ocr_id)
        
        # 如果没有OCR库，返回未找到
        return RecognitionResult(
            id=ocr_id,
            type='ocr',
            found=False,
            label=label
        )
    
    def _annotate_image(
        self, 
        screenshot: Image.Image, 
        results: List[RecognitionResult]
    ) -> Image.Image:
        """
        在图像上标注识别结果
        
        Args:
            screenshot: 原始截图
            results: 识别结果列表
            
        Returns:
            标注后的图像
        """
        annotated = screenshot.copy()
        draw = ImageDraw.Draw(annotated)
        
        # 颜色映射
        colors = {
            'template': (0, 255, 0),    # 绿色
            'color': (255, 165, 0),      # 橙色
            'ocr': (0, 128, 255),        # 蓝色
        }
        
        for result in results:
            if result.found and result.box:
                x, y, w, h = result.box
                color = colors.get(result.type, (0, 255, 0))
                
                # 绘制边界框
                draw.rectangle([x, y, x + w, y + h], outline=color, width=2)
                
                # 绘制中心点
                if result.center:
                    cx, cy = result.center
                    draw.ellipse([cx-3, cy-3, cx+3, cy+3], fill=color)
                
                # 绘制标签
                label_text = result.label
                if result.text:
                    label_text = f"{result.label}: {result.text}"
                
                draw.text((x, y - 12), label_text, fill=color)
        
        return annotated
    
    def generate_vlm_context(self, results: List[RecognitionResult]) -> str:
        """
        生成VLM上下文信息
        
        Args:
            results: 识别结果列表
            
        Returns:
            格式化的上下文字符串，供VLM使用
        """
        context_parts = ["【客户端预识别结果】"]
        
        found_items = []
        not_found_items = []
        
        for result in results:
            if result.found:
                item_desc = f"- {result.label}"
                if result.text:
                    item_desc += f": {result.text}"
                if result.center:
                    item_desc += f" (中心坐标: {result.center[0]}, {result.center[1]})"
                if result.box:
                    item_desc += f" [区域: ({result.box[0]}, {result.box[1]}) 大小: {result.box[2]}x{result.box[3]}]"
                item_desc += f" 置信度: {result.confidence:.2f}"
                found_items.append(item_desc)
            else:
                not_found_items.append(f"- {result.label}")
        
        if found_items:
            context_parts.append("\n已识别到的UI元素:")
            context_parts.extend(found_items)
            context_parts.append("\n提示: 点击元素时请使用其中心坐标")
        
        if not_found_items:
            context_parts.append("\n未识别到的元素:")
            context_parts.extend(not_found_items)
        
        return "\n".join(context_parts)
    
    def results_to_dict(self, results: List[RecognitionResult]) -> List[Dict]:
        """将识别结果转换为字典列表"""
        return [
            {
                'id': r.id,
                'type': r.type,
                'found': r.found,
                'box': r.box,
                'center': r.center,
                'confidence': r.confidence,
                'text': r.text,
                'label': r.label
            }
            for r in results
        ]


def create_pre_recognition_config_from_task(task: Dict[str, Any]) -> PreRecognitionConfig:
    """
    从任务配置创建预识别配置
    
    Args:
        task: 任务配置字典
        
    Returns:
        PreRecognitionConfig对象
    """
    pre_recog = task.get('pre_recognition', {})
    
    return PreRecognitionConfig(
        templates=pre_recog.get('templates', []),
        color_matches=pre_recog.get('color_matches', []),
        ocr_regions=pre_recog.get('ocr_regions', [])
    )


# 全局单例
_pre_recognizer_instance: Optional[ClientPreRecognizer] = None


def get_pre_recognizer(resource_path: str = None, config: Dict = None) -> ClientPreRecognizer:
    """
    获取预识别器单例
    
    Args:
        resource_path: 资源路径
        config: 配置字典
        
    Returns:
        ClientPreRecognizer实例
    """
    global _pre_recognizer_instance
    
    if _pre_recognizer_instance is None:
        _pre_recognizer_instance = ClientPreRecognizer(resource_path, config)
    
    return _pre_recognizer_instance