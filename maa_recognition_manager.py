import base64
import json
import os
import sys
from typing import List, Dict, Optional, Tuple
from PIL import Image
from io import BytesIO
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
from maa_integration.asst import Asst
from client.core.logger import get_logger, LogCategory
logger = get_logger()

class MAARecognitionManager:

    def __init__(self, config: dict):
        self.config = config
        self.maa_instance = None
        self.maa_loaded = False
        self.gpu_acceleration = config.get('gpu_acceleration', False)
        self.confidence_threshold = 0.6
        self._init_maa()

    def _init_maa(self):
        try:
            maa_path = os.path.join(os.path.dirname(__file__), 'maa_integration')
            if Asst.load(maa_path):
                self.maa_instance = Asst()
                if self.gpu_acceleration:
                    Asst.set_static_option(0, '1')
                    logger.info(LogCategory.MAIN, 'MAA GPU 推理加速已启用')
                self.maa_loaded = True
                version = self.maa_instance.get_version()
                logger.info(LogCategory.MAIN, f'MAA 已初始化，版本: {version}')
            else:
                logger.warning(LogCategory.MAIN, 'MAA DLL 加载失败，模板匹配功能将不可用')
                self.maa_loaded = False
        except Exception as e:
            logger.exception(LogCategory.MAIN, f'MAA 初始化失败: {e}')
            self.maa_loaded = False

    def detect_auxiliary_info(self, image_base64: str, templates: List[Dict]) -> List[Dict]:
        if not self.maa_loaded or not self.maa_instance:
            logger.debug(LogCategory.MAIN, 'MAA 未初始化，跳过辅助信息检测')
            return []
        try:
            results = []
            image_data = base64.b64decode(image_base64)
            image = Image.open(BytesIO(image_data))
            for template in templates:
                template_name = template.get('name', 'unknown')
                template_path = template.get('image_path')
                roi = template.get('roi')
                method = template.get('method', 'TemplateMatch')
                if not template_path or not os.path.exists(template_path):
                    logger.debug(LogCategory.MAIN, f'模板文件不存在: {template_path}')
                    continue
                try:
                    matches = self._template_match(image, template_path, roi, method)
                    valid_matches = [m for m in matches if m.get('score', 0) >= self.confidence_threshold]
                    results.extend(valid_matches)
                except Exception as e:
                    logger.warning(LogCategory.MAIN, f'模板匹配失败: {template_name}, 错误: {e}')
            logger.debug(LogCategory.MAIN, f'辅助信息检测完成，找到 {len(results)} 个匹配')
            return results
        except Exception as e:
            logger.exception(LogCategory.MAIN, f'辅助信息检测异常: {e}')
            return []

    def _template_match(self, image: Image.Image, template_path: str, roi: Optional[List[int]]=None, method: str='TemplateMatch') -> List[Dict]:
        try:
            template_image = Image.open(template_path)
            template_name = os.path.basename(template_path)
            temp_template_dir = os.path.join(os.path.dirname(__file__), 'maa_integration', 'resource', 'template')
            os.makedirs(temp_template_dir, exist_ok=True)
            temp_template_path = os.path.join(temp_template_dir, template_name)
            template_image.save(temp_template_path)
            recognition_task = {'template': template_name, 'roi': roi if roi else [0, 0, image.width, image.height], 'threshold': self.confidence_threshold, 'method': method}
            matches = self._opencv_template_match(image, template_path, roi)
            return matches
        except Exception as e:
            logger.warning(LogCategory.MAIN, f'模板匹配异常: {e}')
            return []

    def _opencv_template_match(self, image: Image.Image, template_path: str, roi: Optional[List[int]]=None) -> List[Dict]:
        try:
            import cv2
            import numpy as np
            image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            template = cv2.imread(template_path)
            if template is None:
                logger.warning(LogCategory.MAIN, f'无法加载模板图像: {template_path}')
                return []
            if roi:
                x, y, w, h = roi
                image_cv = image_cv[y:y + h, x:x + w]
            else:
                x, y = (0, 0)
            if template.shape[0] > image_cv.shape[0] or template.shape[1] > image_cv.shape[1]:
                logger.debug(LogCategory.MAIN, f'模板大于图像，跳过匹配')
                return []
            result = cv2.matchTemplate(image_cv, template, cv2.TM_CCOEFF_NORMED)
            matches = []
            loc = np.where(result >= self.confidence_threshold)
            template_h, template_w = template.shape[:2]
            for pt in zip(*loc[::-1]):
                match_x, match_y = pt
                score = result[match_y, match_x]
                global_x = x + match_x
                global_y = y + match_y
                center_x = global_x + template_w // 2
                center_y = global_y + template_h // 2
                matches.append({'name': os.path.basename(template_path), 'x': int(center_x), 'y': int(center_y), 'width': int(template_w), 'height': int(template_h), 'score': float(score), 'roi': [int(global_x), int(global_y), int(template_w), int(template_h)]})
            return matches
        except ImportError:
            logger.warning(LogCategory.MAIN, 'OpenCV 未安装，无法执行模板匹配')
            return []
        except Exception as e:
            logger.warning(LogCategory.MAIN, f'OpenCV 模板匹配异常: {e}')
            return []

    def set_gpu_acceleration(self, enabled: bool):
        self.gpu_acceleration = enabled
        if self.maa_loaded and self.maa_instance:
            try:
                Asst.set_static_option(0, '1' if enabled else '0')
                logger.info(LogCategory.MAIN, f"GPU 推理加速已{('启用' if enabled else '禁用')}")
            except Exception as e:
                logger.warning(LogCategory.MAIN, f'设置 GPU 推理加速失败: {e}')

    def is_available(self) -> bool:
        return self.maa_loaded

    def cleanup(self):
        if self.maa_instance:
            try:
                del self.maa_instance
                self.maa_instance = None
                self.maa_loaded = False
                logger.info(LogCategory.MAIN, 'MAA 资源已清理')
            except Exception as e:
                logger.warning(LogCategory.MAIN, f'清理 MAA 资源时出错: {e}')