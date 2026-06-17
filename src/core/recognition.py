"""
RecognitionEngine - 视觉识别引擎

为 HighPrecisionPageAnalyzer 提供底层视觉识别能力：
- TemplateMatch: 模板匹配 (cv2.matchTemplate)
- ColorMatch: HSV 颜色轮廓检测
"""

import cv2
import numpy as np
import os
from typing import Tuple, Dict, Any, Optional


class RecognitionEngine:
    """视觉识别引擎"""
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        初始化识别引擎
        
        Args:
            template_dir: 模板图片根目录，默认使用项目 assets/resource_adb/image
        """
        # 计算项目根目录 (当前文件在 src/core/)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.dirname(current_dir)
        project_root = os.path.dirname(src_dir)
        # MaaEnd-2 在 IstinaAI 根目录下
        istina_root = os.path.dirname(project_root)
        
        if template_dir is None:
            self.template_dir = os.path.join(
                istina_root, 
                "sample_program", 
                "MaaEnd-2", 
                "assets", 
                "resource_adb", 
                "image"
            )
        else:
            self.template_dir = template_dir
    
    def recognize(self, img: np.ndarray, config: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        执行识别
        
        Args:
            img: 输入图像 (numpy array)
            config: 识别配置，包含 type 字段
            
        Returns:
            (success: bool, detail: dict)
        """
        rec_type = config.get("type", "")
        
        if rec_type == "TemplateMatch":
            return self._template_match(img, config)
        elif rec_type == "ColorMatch":
            return self._color_match(img, config)
        else:
            return False, {"error": f"Unknown recognition type: {rec_type}"}
    
    def _template_match(self, img: np.ndarray, config: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        模板匹配
        
        Args:
            img: 输入图像
            config: 配置 {
                "type": "TemplateMatch",
                "template": "Common/Button/CancelButtonType1.png",
                "roi": [x, y, w, h],  # 可选，搜索区域
                "threshold": 0.7      # 匹配阈值
            }
            
        Returns:
            (True, {"location": [x, y], "score": 0.95}) 或 (False, {})
        """
        # 加载模板
        template_path = config.get("template", "")
        full_path = os.path.join(self.template_dir, template_path)
        
        if not os.path.exists(full_path):
            return False, {"error": f"Template not found: {full_path}"}
        
        template = cv2.imread(full_path)
        if template is None:
            return False, {"error": f"Failed to load template: {full_path}"}
        
        # 应用 ROI (可选)
        search_img = img
        roi = config.get("roi")
        if roi and len(roi) == 4:
            x, y, w, h = roi
            # 边界检查
            x = max(0, x)
            y = max(0, y)
            w = min(w, img.shape[1] - x)
            h = min(h, img.shape[0] - y)
            search_img = img[y:y+h, x:x+w]
        
        # 执行模板匹配
        result = cv2.matchTemplate(search_img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        threshold = config.get("threshold", 0.7)
        
        if max_val >= threshold:
            # 计算全局坐标
            if roi and len(roi) == 4:
                global_x = roi[0] + max_loc[0]
                global_y = roi[1] + max_loc[1]
            else:
                global_x = max_loc[0]
                global_y = max_loc[1]
            
            return True, {
                "location": [global_x, global_y],
                "score": float(max_val),
                "template_size": [template.shape[1], template.shape[0]]
            }
        
        return False, {}
    
    def _color_match(self, img: np.ndarray, config: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        HSV 颜色轮廓检测
        
        Args:
            img: 输入图像 (BGR)
            config: 配置 {
                "type": "ColorMatch",
                "roi": [x, y, w, h],
                "lower": [h, s, v],      # HSV 下限
                "upper": [h, s, v],     # HSV 上限
                "min_area": 50,         # 最小轮廓面积
                "min_contours": 1       # 最少轮廓数
            }
            
        Returns:
            (True, {"contours": 5, "locations": [[x1,y1], [x2,y2]]}) 或 (False, {})
        """
        # 转换到 HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 应用 ROI (可选)
        search_img = hsv
        roi = config.get("roi")
        if roi and len(roi) == 4:
            x, y, w, h = roi
            x = max(0, x)
            y = max(0, y)
            w = min(w, hsv.shape[1] - x)
            h = min(h, hsv.shape[0] - y)
            search_img = hsv[y:y+h, x:x+w]
        
        # HSV 阈值
        lower = np.array(config.get("lower", [0, 0, 0]))
        upper = np.array(config.get("upper", [180, 255, 255]))
        mask = cv2.inRange(search_img, lower, upper)
        
        # 形态学操作 (去噪)
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 过滤轮廓
        min_area = config.get("min_area", 10)
        valid_contours = []
        locations = []
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= min_area:
                valid_contours.append(cnt)
                # 计算轮廓中心
                M = cv2.moments(cnt)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    # 转换为全局坐标
                    if roi and len(roi) == 4:
                        cx += roi[0]
                        cy += roi[1]
                    locations.append([cx, cy])
        
        min_contours = config.get("min_contours", 1)
        
        if len(valid_contours) >= min_contours:
            return True, {
                "contours": len(valid_contours),
                "locations": locations,
                "total_area": sum(cv2.contourArea(c) for c in valid_contours)
            }
        
        return False, {}


# 测试
if __name__ == "__main__":
    import sys
    
    # 测试模板路径
    engine = RecognitionEngine()
    print(f"Template directory: {engine.template_dir}")
    print(f"Directory exists: {os.path.exists(engine.template_dir)}")
    
    # 列出可用模板
    button_dir = os.path.join(engine.template_dir, "Common", "Button")
    if os.path.exists(button_dir):
        print(f"\nAvailable button templates:")
        for f in sorted(os.listdir(button_dir))[:10]:
            print(f"  - {f}")
    
    scene_dir = os.path.join(engine.template_dir, "SceneManager")
    if os.path.exists(scene_dir):
        print(f"\nAvailable scene templates:")
        for f in sorted(os.listdir(scene_dir))[:10]:
            print(f"  - {f}")
