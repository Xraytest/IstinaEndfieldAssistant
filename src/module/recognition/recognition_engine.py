#!/usr/bin/env python3
"""
识别引擎 - MaaEnd 式多源融合识别系统

实现 MaaEnd 的核心识别能力：
1. 模板匹配（TemplateMatch）- 掩膜 ZNCC 模板匹配（参考 MaaEnd-2 CoreMatch）
2. 颜色匹配（ColorMatch）- OpenCV HSV 颜色轮廓检测
3. 组合识别（And/Or）
4. OCR 识别 - MaaFw Pipeline 内建 OCR 引擎

参考：MaaEnd-2/assets/resource/pipeline/Common/
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
import os

from module.utils.paths import get_project_root


class RecognitionEngine:
    """识别引擎，支持 MaaEnd 式节点识别

    OCR 通过 MaaFw Pipeline 系统调用（内建 OCR 引擎）。
    本引擎负责：模板匹配、颜色匹配、组合逻辑。
    """

    def __init__(self, assets_dir: str = None):
        self.assets_dir = assets_dir if assets_dir else os.path.join(get_project_root(), "assets")

    # ── 主分发 ─────────────────────────────────────────────────

    def recognize(self, img: np.ndarray, node_config: Dict[str, Any]) -> Tuple[bool, Any]:
        """执行节点识别"""
        node_type = node_config.get("type", "")

        if node_type == "TemplateMatch":
            return self._template_match(img, node_config)
        elif node_type == "ColorMatch":
            return self._color_match(img, node_config)
        elif node_type == "And":
            return self._and_recognize(img, node_config)
        elif node_type == "Or":
            return self._or_recognize(img, node_config)
        elif node_type == "OCR":
            # OCR 通过 MaaFw Pipeline 执行，此处返回提示
            return False, {"reason": "OCR 需通过 MaaFw Pipeline 执行，请使用 Tasker.post_recognition()"}
        elif isinstance(node_config, str):
            return False, None
        return False, None

    # ── 模板匹配（掩膜 ZNCC，参考 MaaEnd-2 CoreMatch）──────────

    @staticmethod
    def _refine_peak_subpixel(result: np.ndarray, max_loc: Tuple[int, int]) -> Tuple[float, float]:
        """抛物线亚像素精化 — 参考 MaaEnd-2 RefinePeakSubpixel"""
        x, y = float(max_loc[0]), float(max_loc[1])
        h, w = result.shape

        if 0 < max_loc[0] < w - 1:
            left = result[max_loc[1], max_loc[0] - 1]
            center = result[max_loc[1], max_loc[0]]
            right = result[max_loc[1], max_loc[0] + 1]
            denom = left - 2.0 * center + right
            if abs(denom) > 1e-12:
                x += 0.5 * (left - right) / denom

        if 0 < max_loc[1] < h - 1:
            top = result[max_loc[1] - 1, max_loc[0]]
            center = result[max_loc[1], max_loc[0]]
            bottom = result[max_loc[1] + 1, max_loc[0]]
            denom = top - 2.0 * center + bottom
            if abs(denom) > 1e-12:
                y += 0.5 * (top - bottom) / denom

        return x, y

    @staticmethod
    def _compute_psr(result: np.ndarray, max_loc: Tuple[int, int], peak_radius: int = 5) -> Tuple[float, float, float]:
        """计算 PSR (Peak to Sidelobe Ratio) 和 delta — 参考 MaaEnd-2 CoreMatch

        返回: (psr, delta, second_score)
        """
        h, w = result.shape
        max_val = result[max_loc[1], max_loc[0]]

        x1 = max(0, max_loc[0] - peak_radius)
        y1 = max(0, max_loc[1] - peak_radius)
        x2 = min(w, max_loc[0] + peak_radius + 1)
        y2 = min(h, max_loc[1] + peak_radius + 1)

        peak_region = result[y1:y2, x1:x2].copy()
        result[y1:y2, x1:x2] = -2.0
        _, second_val, _, _ = cv2.minMaxLoc(result)
        result[y1:y2, x1:x2] = peak_region

        mask = np.ones(result.shape, dtype=np.uint8)
        mask[y1:y2, x1:x2] = 0
        mean, stddev = cv2.meanStdDev(result, mask=mask)

        psr = (max_val - mean[0][0]) / (stddev[0][0] + 1e-6)
        delta = max_val - second_val

        return float(psr), float(delta), float(second_val)

    def _template_match(self, img: np.ndarray, config: Dict[str, Any]) -> Tuple[bool, Any]:
        """掩膜 ZNCC 模板匹配 — 参考 MaaEnd-2 CoreMatch

        核心改进（对比旧 SIFT 方案）：
        1. 使用 Alpha 通道生成权重掩膜，排除透明/背景区域干扰
        2. 对搜索图做高斯模糊预处理
        3. 亚像素精化定位
        4. PSR + Delta 双重验证

        config: {template: str, roi: [x,y,w,h], threshold: float (置信度 0-1, 默认 0.7),
                 blur_size: int (高斯模糊核, 默认 5)}

        返回格式:
        - 成功：(True, {"bbox": [x1, y1, x2, y2], "center": [cx, cy],
                        "score": float, "psr": float, "delta": float})
        - 失败：(False, {"score": float})
        """
        template_path = config.get("template", "")
        roi = config.get("roi")
        threshold = config.get("threshold", 0.7)
        blur_size = config.get("blur_size", 5)

        if not Path(template_path).is_absolute():
            template_path = self.assets_dir / template_path

        template = cv2.imread(str(template_path), cv2.IMREAD_UNCHANGED)
        if template is None:
            return False, {"error": "template not found"}

        x_offset, y_offset = 0, 0
        if roi:
            rx, ry, rw, rh = roi
            search_img = img[ry:ry+rh, rx:rx+rw]
            x_offset, y_offset = rx, ry
        else:
            search_img = img

        # ── 生成权重掩膜 ──
        has_alpha = (template.shape[2] == 4)
        if has_alpha:
            alpha = template[:, :, 3]
            _, mask = cv2.threshold(alpha, 128, 255, cv2.THRESH_BINARY)
            mask = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
            templ_bgr = template[:, :, :3]
        else:
            templ_bgr = template
            mask = np.ones(template.shape[:2], dtype=np.uint8) * 255

        # ── 预处理 ──
        gray_tmpl = cv2.cvtColor(templ_bgr, cv2.COLOR_BGR2GRAY)
        gray_src = cv2.cvtColor(search_img, cv2.COLOR_BGR2GRAY)
        if blur_size > 0:
            gray_src = cv2.GaussianBlur(gray_src, (blur_size, blur_size), 0)

        # 掩膜均值外推：透明区域填充为模板均值，消除边界虚假梯度
        if has_alpha:
            mean_val = cv2.mean(gray_tmpl, mask=mask)[0]
            gray_tmpl_filled = gray_tmpl.copy()
            gray_tmpl_filled[mask == 0] = mean_val
        else:
            gray_tmpl_filled = gray_tmpl

        # ── 执行模板匹配 ──
        try:
            result = cv2.matchTemplate(gray_src, gray_tmpl_filled, cv2.TM_CCOEFF_NORMED, mask=mask)
        except cv2.error:
            result = cv2.matchTemplate(gray_src, gray_tmpl_filled, cv2.TM_CCOEFF_NORMED)

        result = np.nan_to_num(result, nan=-1.0)

        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val < threshold:
            return False, {"score": float(max_val)}

        # ── 亚像素精化 ──
        refined_x, refined_y = self._refine_peak_subpixel(result, max_loc)

        # ── PSR + Delta 验证 ──
        psr, delta, second_score = self._compute_psr(result, max_loc)

        if max_val < 0.8 and (psr < 6.0 or delta < 0.02):
            return False, {"score": float(max_val), "psr": psr, "delta": delta}

        # ── 计算全局坐标 ──
        global_x = refined_x + x_offset
        global_y = refined_y + y_offset
        tw, th = template.shape[1], template.shape[0]
        x1, y1 = int(global_x), int(global_y)
        x2, y2 = int(global_x + tw), int(global_y + th)
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        return True, {
            "bbox": [x1, y1, x2, y2],
            "center": [cx, cy],
            "score": float(max_val),
            "psr": float(psr),
            "delta": float(delta),
            "template_size": [tw, th],
        }

    # ── 颜色匹配（轮廓检测，非像素分布）─────────────────────

    def _color_match(self, img: np.ndarray, config: Dict[str, Any]) -> Tuple[bool, Any]:
        """颜色元素检测：在 ROI 内查找至少 min_contours 个指定颜色的连通区域

        config: {roi: [x,y,w,h], lower: [h,s,v], upper: [h,s,v],
                 min_area: int, min_contours: int}
        
        返回格式:
        - 成功：(True, {"contours": int, "bboxes": [[x1,y1,x2,y2],...], "centers": [[cx,cy],...], "total_area": int})
        - 失败：(False, {"contours": int})
        """
        roi = config.get("roi")
        lower = np.array(config.get("lower"))
        upper = np.array(config.get("upper"))
        min_area = config.get("min_area", 30)
        min_contours = config.get("min_contours", 1)

        x_offset, y_offset = 0, 0
        if roi:
            rx, ry, rw, rh = roi
            img_crop = img[ry:ry+rh, rx:rx+rw]
            x_offset, y_offset = rx, ry
        else:
            img_crop = img

        hsv = cv2.cvtColor(img_crop, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_contours = []
        bboxes = []
        centers = []
        total_area = 0
        
        for c in contours:
            area = cv2.contourArea(c)
            if area >= min_area:
                valid_contours.append(c)
                total_area += area
                
                # 计算边界框
                x, y, w, h = cv2.boundingRect(c)
                # 转换为全局坐标
                global_x1 = x + x_offset
                global_y1 = y + y_offset
                global_x2 = x + w + x_offset
                global_y2 = y + h + y_offset
                bboxes.append([global_x1, global_y1, global_x2, global_y2])
                
                # 计算中心点
                cx = global_x1 + w // 2
                cy = global_y1 + h // 2
                centers.append([cx, cy])

        if len(valid_contours) >= min_contours:
            return True, {
                "contours": len(valid_contours),
                "bboxes": bboxes,
                "centers": centers,
                "total_area": total_area
            }

        return False, {"contours": len(valid_contours)}

    # ── 组合识别 ───────────────────────────────────────────────

    def _and_recognize(self, img: np.ndarray, config: Dict[str, Any]) -> Tuple[bool, Any]:
        """And：所有子节点都匹配，聚合所有 bbox 信息"""
        all_bboxes = []
        all_centers = []
        
        for node in config.get("nodes", []):
            ok, result = self.recognize(img, node)
            if not ok:
                return False, None
            # 聚合 bbox 信息
            if result:
                if "bbox" in result:
                    all_bboxes.append(result["bbox"])
                if "bboxes" in result:
                    all_bboxes.extend(result["bboxes"])
                if "center" in result:
                    all_centers.append(result["center"])
                if "centers" in result:
                    all_centers.extend(result["centers"])
        
        return True, {"bboxes": all_bboxes, "centers": all_centers}

    def _or_recognize(self, img: np.ndarray, config: Dict[str, Any]) -> Tuple[bool, Any]:
        """Or：任一子节点匹配即成功（短路求值），返回第一个匹配的完整信息"""
        for node in config.get("nodes", []):
            ok, result = self.recognize(img, node)
            if ok:
                return True, result
        return False, None


# ═══════════════════════════════════════════════════════════════
# MaaFw Pipeline OCR 封装
# ═══════════════════════════════════════════════════════════════

class MaaFwPipelineOCR:
    """通过 MaaFw Tasker + Resource 管道系统执行 OCR

    用法:
        from maa import Tasker, Resource, Controller
        from maa.pipeline import JRecognitionType, JOCR

        # 创建 Tasker 并绑定 Resource/Controller
        tasker = Tasker()
        resource = Resource()
        controller = Controller()
        tasker.bind(resource, controller)

        # 执行 OCR
        ocr_param = JOCR(
            expected=["领取", "Claim"],
            roi=(0, 0, 1280, 720)
        )
        job = tasker.post_recognition(JRecognitionType.OCR, ocr_param, image)
        detail = job.get()
    """

    @staticmethod
    def create_ocr_param(expected: List[str], roi: Tuple[int, int, int, int] = (0, 0, 0, 0),
                         threshold: float = 0.3) -> Dict[str, Any]:
        """
        创建 OCR 识别参数（JSON 格式，用于 Pipeline 配置）

        Args:
            expected: 期望匹配的文本列表（支持正则表达式）
            roi: 识别区域 (x, y, w, h)
            threshold: 置信度阈值

        Returns:
            OCR 参数字典
        """
        return {
            "type": "OCR",
            "param": {
                "expected": expected,
                "roi": list(roi),
                "threshold": threshold
            }
        }

    @staticmethod
    def doc():
        """返回 MaaFw OCR 使用文档"""
        return """
MaaFw Pipeline OCR 使用指南
==========================

1. 通过 Tasker.post_recognition() 执行 OCR:
   from maa import Tasker, JRecognitionType
   from maa.pipeline import JOCR

   ocr_param = JOCR(
       expected=["领取", "Claim", "(?i)collect"],  # 支持正则
       roi=(0, 0, 1280, 720),
       threshold=0.3
   )
   job = tasker.post_recognition(JRecognitionType.OCR, ocr_param, image)

2. 在 Pipeline JSON 中配置 OCR:
   {
       "CheckClaimButton": {
           "recognition": {
               "type": "OCR",
               "param": {
                   "expected": ["领取", "一键领取", "Claim"],
                   "roi": [950, 60, 330, 640],
                   "threshold": 0.3
               }
           },
           "action": {"type": "Click"}
       }
   }

3. OCR 结果格式（重要：包含完整坐标信息供 LLM 决策）:
   RecognitionDetail(
       hit: bool,                          # 是否匹配期望文本
       box: (x, y, w, h),                  # 匹配位置边界框
       all_results: list[RecognitionResult],  # 所有识别结果
       best_result: RecognitionResult       # 最佳匹配结果
   )
   
   RecognitionResult 包含:
   - text: str              # 识别的文本
   - bbox: [x1, y1, x2, y2] # 文本边界框（全局坐标）
   - center: [cx, cy]       # 文本中心点
   - confidence: float      # 置信度

4. 支持的特性:
   - 多语言自动检测（中文/英文/日文/韩文）
   - 正则表达式匹配（如 (?i) 不区分大小写）
   - ROI 区域识别
   - 置信度阈值过滤
   - 文本排序（Horizontal/Vertical/Area 等）
   - **返回完整坐标信息，LLM 可根据坐标自行决定点击位置**
"""


# ═══════════════════════════════════════════════════════════════
# 预定义状态节点（参考 MaaEnd，适配 OpenCV 实现）
# ═══════════════════════════════════════════════════════════════

PREDEFINED_STATES = {
    # ── 取消按钮（对话框区域掩膜 ZNCC，阈值=0.7） ──
    "CancelButton": {
        "type": "Or",
        "nodes": [
            {
                "type": "TemplateMatch",
                "template": "Common/Button/CancelButtonType1.png",
                "roi": [200, 500, 700, 500],
                "threshold": 0.7
            },
            {
                "type": "TemplateMatch",
                "template": "Common/Button/CancelButtonType2.png",
                "roi": [200, 500, 700, 500],
                "threshold": 0.7
            }
        ]
    },

    # ── 世界页面（左上角小 ROI 掩膜 ZNCC） ──
    "InWorld": {
        "type": "Or",
        "nodes": [
            {
                "type": "TemplateMatch",
                "template": "SceneManager/WorldMenu.png",
                "roi": [0, 0, 200, 200],
                "threshold": 0.65
            },
            {
                "type": "TemplateMatch",
                "template": "Common/Button/RegionalDevelopmentButton.png",
                "roi": [0, 0, 300, 100],
                "threshold": 0.7
            }
        ]
    },

    # ── 任务图标（右上角 ROI，高阈值防误匹配） ──
    "TaskIcon": {
        "type": "TemplateMatch",
        "template": "SceneManager/TaskIcon.png",
        "roi": [700, 30, 300, 150],
        "threshold": 0.85
    },

    # ── 黄色确认按钮（颜色轮廓 + 模板双验证） ──
    "YellowConfirmButton": {
        "type": "And",
        "nodes": [
            {
                "type": "ColorMatch",
                "roi": [200, 500, 700, 500],
                "lower": [28, 100, 100],
                "upper": [29, 255, 255],
                "min_area": 100,
                "min_contours": 1
            },
            {
                "type": "TemplateMatch",
                "template": "Common/Button/YellowConfirmButtonType1.png",
                "roi": [200, 500, 700, 500],
                "threshold": 0.7
            }
        ]
    },

    # ── 菜单列表（颜色验证，OCR 需 MaaFw Pipeline） ──
    "InMenuList": {
        "type": "And",
        "nodes": [
            {
                "type": "ColorMatch",
                "roi": [0, 1760, 200, 200],
                "lower": [90, 35, 35],
                "upper": [191, 83, 85],
                "min_area": 30,
                "min_contours": 2
            }
        ],
        "note": "OCR 部分需通过 MaaFw Pipeline 执行"
    },

    # ── 行动手册（OCR 需 MaaFw Pipeline） ──
    "InOperationalManual": {
        "note": "需通过 MaaFw Pipeline OCR 执行:\n" +
                "  ocr_param = JOCR(expected=['行动手册', 'Operational Manual'], roi=(0, 0, 215, 60))"
    }
}


# ═══════════════════════════════════════════════════════════════
# 测试代码
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from pathlib import Path

    # recognition_engine.py 在 src/core/recognition/
    SRC_DIR = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(SRC_DIR))

    print("=" * 60)
    print("识别引擎测试（MaaFw OCR + OpenCV 模板/颜色匹配）")
    print("=" * 60)

    # 打印 MaaFw OCR 使用文档
    print("\nMaaFw OCR 使用指南:")
    print(MaaFwPipelineOCR.doc())

    # 测试预定义状态
    print("\n预定义状态节点:")
    for name, config in PREDEFINED_STATES.items():
        print(f"  - {name}: {config.get('type', 'N/A')}")

