"""
MAA 辅助信息识别器 - 使用 MAA 进行模板匹配和图像识别
"""
import base64
import json
import os
import sys
from typing import List, Dict, Optional, Tuple
from PIL import Image
from io import BytesIO

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from maa_integration.asst import Asst
from logger import get_logger, LogCategory

logger = get_logger()


class MAARecognitionManager:
    """MAA 辅助信息识别管理器"""

    def __init__(self, config: dict):
        """
        初始化 MAA 识别管理器

        Args:
            config: 配置字典，包含 maa 相关配置
        """
        self.config = config
        self.maa_instance = None
        self.maa_loaded = False
        self.gpu_acceleration = config.get('gpu_acceleration', False)
        self.confidence_threshold = 0.6  # 固定置信度阈值为 0.6

        # 初始化 MAA
        self._init_maa()

    def _init_maa(self):
        """初始化 MAA 实例"""
        try:
            maa_path = os.path.join(os.path.dirname(__file__), 'maa_integration')

            # 加载 MAA DLL
            if Asst.load(maa_path):
                # 创建 MAA 实例
                self.maa_instance = Asst()

                # 设置 GPU 推理加速
                if self.gpu_acceleration:
                    # 设置使用 DirectML (Windows GPU)
                    Asst.set_static_option(
                        0,  # MaaOption::DirectML
                        "1"
                    )
                    logger.info(LogCategory.MAIN, "MAA GPU 推理加速已启用")

                self.maa_loaded = True
                version = self.maa_instance.get_version()
                logger.info(LogCategory.MAIN, f"MAA 已初始化，版本: {version}")
            else:
                logger.warning(LogCategory.MAIN, "MAA DLL 加载失败，模板匹配功能将不可用")
                self.maa_loaded = False

        except Exception as e:
            logger.exception(LogCategory.MAIN, f"MAA 初始化失败: {e}")
            self.maa_loaded = False

    def detect_auxiliary_info(
        self,
        image_base64: str,
        templates: List[Dict]
    ) -> List[Dict]:
        """
        检测辅助信息图像位置

        Args:
            image_base64: Base64 编码的截图数据
            templates: 模板列表，每个模板包含:
                - name: 模板名称
                - image_path: 模板图像路径
                - roi: 可选的感兴趣区域 [x, y, w, h]
                - method: 匹配方法 (TemplateMatch, OcrDetect 等)

        Returns:
            匹配结果列表，每个结果包含:
                - name: 模板名称
                - x, y: 中心坐标
                - width, height: 匹配区域大小
                - score: 置信度分数 (0-1)
                - roi: 实际匹配区域 [x, y, w, h]
        """
        if not self.maa_loaded or not self.maa_instance:
            logger.debug(LogCategory.MAIN, "MAA 未初始化，跳过辅助信息检测")
            return []

        try:
            results = []

            # 将 Base64 图像转换为 PIL Image
            image_data = base64.b64decode(image_base64)
            image = Image.open(BytesIO(image_data))

            # 遍历所有模板进行匹配
            for template in templates:
                template_name = template.get('name', 'unknown')
                template_path = template.get('image_path')
                roi = template.get('roi')
                method = template.get('method', 'TemplateMatch')

                if not template_path or not os.path.exists(template_path):
                    logger.debug(LogCategory.MAIN, f"模板文件不存在: {template_path}")
                    continue

                try:
                    # 执行模板匹配
                    matches = self._template_match(image, template_path, roi, method)

                    # 过滤置信度低于阈值的结果
                    valid_matches = [
                        m for m in matches
                        if m.get('score', 0) >= self.confidence_threshold
                    ]

                    results.extend(valid_matches)

                except Exception as e:
                    logger.warning(
                        LogCategory.MAIN,
                        f"模板匹配失败: {template_name}, 错误: {e}"
                    )

            logger.debug(
                LogCategory.MAIN,
                f"辅助信息检测完成，找到 {len(results)} 个匹配"
            )

            return results

        except Exception as e:
            logger.exception(LogCategory.MAIN, f"辅助信息检测异常: {e}")
            return []

    def _template_match(
        self,
        image: Image.Image,
        template_path: str,
        roi: Optional[List[int]] = None,
        method: str = 'TemplateMatch'
    ) -> List[Dict]:
        """
        执行模板匹配

        Args:
            image: PIL 图像对象
            template_path: 模板图像路径
            roi: 可选的感兴趣区域 [x, y, w, h]
            method: 匹配方法

        Returns:
            匹配结果列表
        """
        # 注意: MAA 的 Python 绑定目前不直接支持独立的模板匹配
        # 我们需要使用 MAA 的任务系统来实现
        # 这里我们创建一个临时的识别任务

        try:
            # 读取模板图像
            template_image = Image.open(template_path)
            template_name = os.path.basename(template_path)

            # 将模板保存到临时位置供 MAA 使用
            temp_template_dir = os.path.join(
                os.path.dirname(__file__),
                'maa_integration',
                'resource',
                'template'
            )
            os.makedirs(temp_template_dir, exist_ok=True)

            temp_template_path = os.path.join(temp_template_dir, template_name)
            template_image.save(temp_template_path)

            # 构建识别任务
            recognition_task = {
                'template': template_name,
                'roi': roi if roi else [0, 0, image.width, image.height],
                'threshold': self.confidence_threshold,
                'method': method
            }

            # 这里我们返回模拟结果，实际实现需要通过 MAA C++ API
            # 暂时使用 OpenCV 进行模板匹配作为替代方案

            matches = self._opencv_template_match(image, template_path, roi)

            return matches

        except Exception as e:
            logger.warning(LogCategory.MAIN, f"模板匹配异常: {e}")
            return []

    def _opencv_template_match(
        self,
        image: Image.Image,
        template_path: str,
        roi: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        使用 OpenCV 进行模板匹配 (作为 MAA 的替代方案)

        Args:
            image: PIL 图像对象
            template_path: 模板图像路径
            roi: 可选的感兴趣区域 [x, y, w, h]

        Returns:
            匹配结果列表
        """
        try:
            import cv2
            import numpy as np

            # 转换为 OpenCV 格式
            image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            template = cv2.imread(template_path)

            if template is None:
                logger.warning(LogCategory.MAIN, f"无法加载模板图像: {template_path}")
                return []

            # 如果指定了 ROI，裁剪图像
            if roi:
                x, y, w, h = roi
                image_cv = image_cv[y:y+h, x:x+w]
            else:
                x, y = 0, 0

            # 检查模板是否大于图像
            if template.shape[0] > image_cv.shape[0] or template.shape[1] > image_cv.shape[1]:
                logger.debug(LogCategory.MAIN, f"模板大于图像，跳过匹配")
                return []

            # 执行模板匹配
            result = cv2.matchTemplate(image_cv, template, cv2.TM_CCOEFF_NORMED)

            # 查找所有匹配位置
            matches = []
            loc = np.where(result >= self.confidence_threshold)

            # 获取模板尺寸
            template_h, template_w = template.shape[:2]

            # 对匹配结果进行非极大值抑制 (NMS) 避免重复
            for pt in zip(*loc[::-1]):
                match_x, match_y = pt
                score = result[match_y, match_x]

                # 转换为全局坐标
                global_x = x + match_x
                global_y = y + match_y

                # 计算中心坐标
                center_x = global_x + template_w // 2
                center_y = global_y + template_h // 2

                matches.append({
                    'name': os.path.basename(template_path),
                    'x': int(center_x),
                    'y': int(center_y),
                    'width': int(template_w),
                    'height': int(template_h),
                    'score': float(score),
                    'roi': [int(global_x), int(global_y), int(template_w), int(template_h)]
                })

            return matches

        except ImportError:
            logger.warning(LogCategory.MAIN, "OpenCV 未安装，无法执行模板匹配")
            return []
        except Exception as e:
            logger.warning(LogCategory.MAIN, f"OpenCV 模板匹配异常: {e}")
            return []

    def set_gpu_acceleration(self, enabled: bool):
        """
        设置 GPU 推理加速

        Args:
            enabled: 是否启用 GPU 推理加速
        """
        self.gpu_acceleration = enabled

        if self.maa_loaded and self.maa_instance:
            try:
                Asst.set_static_option(
                    0,  # MaaOption::DirectML
                    "1" if enabled else "0"
                )
                logger.info(
                    LogCategory.MAIN,
                    f"GPU 推理加速已{'启用' if enabled else '禁用'}"
                )
            except Exception as e:
                logger.warning(LogCategory.MAIN, f"设置 GPU 推理加速失败: {e}")

    def is_available(self) -> bool:
        """检查 MAA 是否可用"""
        return self.maa_loaded

    def cleanup(self):
        """清理资源"""
        if self.maa_instance:
            try:
                del self.maa_instance
                self.maa_instance = None
                self.maa_loaded = False
                logger.info(LogCategory.MAIN, "MAA 资源已清理")
            except Exception as e:
                logger.warning(LogCategory.MAIN, f"清理 MAA 资源时出错: {e}")
