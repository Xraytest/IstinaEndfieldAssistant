#!/usr/bin/env python3
"""
识别引擎 - MaaEnd 式多源融合识别系统

实现 MaaEnd 的核心识别能力：
1. 模板匹配（TemplateMatch）- OpenCV
2. 颜色匹配（ColorMatch）- OpenCV HSV
3. 组合识别（And/Or）
4. OCR 识别 - 通过 MaaFw Pipeline 系统（内建 OCR 引擎）

参考：MaaEnd-2/assets/resource/pipeline/Common/
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import sys


class RecognitionEngine:
    """识别引擎，支持 MaaEnd 式节点识别

    OCR 由 MaaFw Tasker+Resource 管道系统原生处理，无需额外安装。
    本引擎负责：模板匹配、颜色匹配、组合逻辑。
    如需 OCR，使用 MaaFwPipelineOCR 包装类。
    """

    def __init__(self, assets_dir: str = None):
        # recognition_engine.py 在 src/core/recognition/
        # parent → recognition, parent.parent → core, parent.parent.parent → src
        # parent.parent.parent.parent → 项目根目录
        self.assets_dir = Path(assets_dir) if assets_dir else Path(__file__).resolve().parent.parent.parent.parent / "assets"

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
            # OCR 由 MaaFw Pipeline 原生实现，此处为占位
            # 实际使用时应通过 MaaFwPipelineOCR 封装
            return False, {"reason": "OCR requires MaaFw Pipeline (see MaaFwPipelineOCR)"}
        elif isinstance(node_config, str):
            return False, None
        return False, None

    # ── 模板匹配（SIFT 特征匹配，尺度不变）─────────────────

    def _template_match(self, img: np.ndarray, config: Dict[str, Any]) -> Tuple[bool, Any]:
        """SIFT 特征匹配 — 尺度/旋转不变，远超模板匹配

        config: {template: str, roi: [x,y,w,h], threshold: float (最小匹配点数)}
        """
        template_path = config.get("template", "")
        roi = config.get("roi")
        min_matches = config.get("threshold", 10)  # reinterpret as min matches

        if not Path(template_path).is_absolute():
            template_path = self.assets_dir / template_path

        template = cv2.imread(str(template_path))
        if template is None:
            return False, {"error": "template not found"}

        x, y = 0, 0
        if roi:
            rx, ry, rw, rh = roi
            search_img = img[ry:ry+rh, rx:rx+rw]
            x, y = rx, ry
        else:
            search_img = img

        # SIFT 检测器
        sift = cv2.SIFT_create()

        # 转换为灰度
        gray_tmpl = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        gray_src = cv2.cvtColor(search_img, cv2.COLOR_BGR2GRAY)

        kp1, des1 = sift.detectAndCompute(gray_tmpl, None)
        kp2, des2 = sift.detectAndCompute(gray_src, None)

        if des1 is None or des2 is None or len(des1) < 4 or len(des2) < 4:
            return False, {"matches": 0}

        # FLANN 匹配
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        matches = flann.knnMatch(des1, des2, k=2)

        # Lowe's ratio test
        good = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance:
                good.append(m)

        if len(good) >= min_matches:
            # 计算匹配中心位置
            pts = [kp2[m.trainIdx].pt for m in good]
            cx = int(sum(p[0] for p in pts) / len(pts)) + x
            cy = int(sum(p[1] for p in pts) / len(pts)) + y
            return True, {"location": (cx, cy), "matches": len(good)}

        return False, {"matches": len(good)}

    # ── 颜色匹配（轮廓检测，非像素分布）─────────────────────

    def _color_match(self, img: np.ndarray, config: Dict[str, Any]) -> Tuple[bool, Any]:
        """颜色元素检测：在 ROI 内查找至少 min_contours 个指定颜色的连通区域

        config: {roi: [x,y,w,h], lower: [h,s,v], upper: [h,s,v],
                 min_area: int, min_contours: int}
        returns: (bool, {"contours": int})
        """
        roi = config.get("roi")
        lower = np.array(config.get("lower"))
        upper = np.array(config.get("upper"))
        min_area = config.get("min_area", 30)
        min_contours = config.get("min_contours", 1)

        if roi:
            rx, ry, rw, rh = roi
            img_crop = img[ry:ry+rh, rx:rx+rw]
        else:
            img_crop = img

        hsv = cv2.cvtColor(img_crop, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid = [c for c in contours if cv2.contourArea(c) >= min_area]

        return len(valid) >= min_contours, {"contours": len(valid)}

    # ── 组合识别 ───────────────────────────────────────────────

    def _and_recognize(self, img: np.ndarray, config: Dict[str, Any]) -> Tuple[bool, Any]:
        """And：所有子节点都匹配"""
        for node in config.get("nodes", []):
            ok, _ = self.recognize(img, node)
            if not ok:
                return False, None
        return True, None

    def _or_recognize(self, img: np.ndarray, config: Dict[str, Any]) -> Tuple[bool, Any]:
        """Or：任一子节点匹配即成功（短路求值）"""
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
        ocr = MaaFwPipelineOCR(maafw_executor)
        ok, result = ocr.recognize(image, roi, expected_texts)
    """

    def __init__(self, maafw_executor=None):
        """如需使用 MaaFw 管道 OCR，传入已连接的 MaaFwTouchExecutor"""
        self._executor = maafw_executor

    def recognize(self, img: np.ndarray, roi: List[int],
                  expected: List[str]) -> Tuple[bool, Any]:
        """通过 MaaFw Pipeline 执行 OCR

        Args:
            img: BGR 图像
            roi: [x, y, w, h] 识别区域
            expected: 期望匹配的文本列表

        Returns:
            (是否匹配, {"texts": list, "matches": list})
        """
        if self._executor is None:
            return False, {"reason": "MaaFw executor not provided"}
        # MaaFw Pipeline OCR 通过 JSON 配置执行
        # 实际调用由 MaaFw Tasker.run_task() 完成
        return False, {"reason": "Pipeline OCR not yet integrated"}


# ═══════════════════════════════════════════════════════════════
# 预定义状态节点（参考 MaaEnd，适配 OpenCV 实现）
# ═══════════════════════════════════════════════════════════════

PREDEFINED_STATES = {
    # ── 取消按钮（对话框区域 SIFT，阈值=5最小匹配点） ──
    "CancelButton": {
        "type": "Or",
        "nodes": [
            {
                "type": "TemplateMatch",
                "template": "Common/Button/CancelButtonType1.png",
                "roi": [200, 500, 700, 500],
                "threshold": 5
            },
            {
                "type": "TemplateMatch",
                "template": "Common/Button/CancelButtonType2.png",
                "roi": [200, 500, 700, 500],
                "threshold": 5
            }
        ]
    },

    # ── 世界页面（左上角小ROI SIFT） ──
    "InWorld": {
        "type": "Or",
        "nodes": [
            {
                "type": "TemplateMatch",
                "template": "SceneManager/WorldMenu.png",
                "roi": [0, 0, 200, 200],
                "threshold": 5
            },
            {
                "type": "TemplateMatch",
                "template": "Common/Button/RegionalDevelopmentButton.png",
                "roi": [0, 0, 300, 100],
                "threshold": 5
            }
        ]
    },

    # ── 任务图标（右上角ROI，高阈值防误匹配） ──
    "TaskIcon": {
        "type": "TemplateMatch",
        "template": "SceneManager/TaskIcon.png",
        "roi": [700, 30, 300, 150],
        "threshold": 15
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
                "threshold": 5
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
            },
            {
                "type": "OCR",
                "roi": [420, 1820, 450, 100],
                "expected": ["FIELD", "ENDFIELD"]
            }
        ],
        "note": "需要 MaaFw Pipeline OCR 支持"
    },

    # ── 行动手册 ──
    "InOperationalManual": {
        "type": "OCR",
        "roi": [0, 0, 215, 60],
        "expected": ["行动手册", "Operational Manual", "案内所"],
        "note": "需要 MaaFw Pipeline OCR 支持"
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

    from core.adb_utils import ADB

    adb = ADB()
    img_bytes = adb.screencap(dedup=False)

    if img_bytes:
        img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        engine = RecognitionEngine()

        print("\n[测试] 颜色匹配（黄色按钮）...")
        ok, result = engine.recognize(img, {
            "type": "ColorMatch",
            "roi": [0, 0, 1920, 1080],
            "lower": [28, 100, 100],
            "upper": [29, 255, 255],
            "count": 3000
        })
        print(f"  结果：{ok}, {result}")

        print("\n[测试] OCR 识别（需 MaaFw Pipeline）...")
        ok, result = engine.recognize(img, {
            "type": "OCR",
            "roi": [0, 0, 400, 100],
            "expected": ["任务", "日常"]
        })
        print(f"  结果：{ok}, {result}")

        print("\n[完成]")
    else:
        print("[错误] 截图失败")
