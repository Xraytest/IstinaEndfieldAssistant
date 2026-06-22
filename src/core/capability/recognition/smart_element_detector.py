#!/usr/bin/env python3
"""
智能元素检测器 - OCR + 模板匹配融合，返回带坐标的元素列表

设计目标：
1. OCR 返回文字元素及其坐标
2. 模板匹配返回 UI 图标及其坐标
3. LLM 根据元素列表自主决定操作位置（而非硬编码坐标）
4. 3CUI 坐标作为降级备选
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import json

from utils.paths import ensure_src_path, get_project_root
ensure_src_path(__file__)


@dataclass
class Element:
    """UI 元素数据类"""
    element_type: str  # "text" | "icon" | "button"
    name: str  # 元素名称（OCR 文本或图标 ID）
    x: int  # 中心点 X
    y: int  # 中心点 Y
    width: int  # 宽度
    height: int  # 高度
    confidence: float  # 置信度 0-1
    metadata: Dict = None  # 额外信息
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x, self.y)


class SmartElementDetector:
    """智能元素检测器 - 融合 OCR 和模板匹配"""
    
    def __init__(self, maafw_executor=None, assets_dir: str = None):
        self.maafw_executor = maafw_executor
        self.assets_dir = Path(assets_dir) if assets_dir else Path(get_project_root()) / "assets"
        
        # 加载 UI 元素模板配置
        self.ui_templates = self._load_ui_templates()
        
        # 常用 UI 元素定义（3CUI 坐标作为降级）
        self.ui_elements_3cui = {
            "quest_icon": {"name": "任务图标", "fallback_coords": [860, 80]},
            "event_icon": {"name": "活动图标", "fallback_coords": [928, 53]},
            "menu_icon": {"name": "菜单图标", "fallback_coords": [1392, 79]},
            "claim_button": {"name": "领取按钮", "fallback_coords": [810, 900]},
            "daily_tab": {"name": "每日标签", "fallback_coords": [600, 300]},
            "weekly_tab": {"name": "周常标签", "fallback_coords": [810, 300]},
        }
    
    def _load_ui_templates(self) -> Dict:
        """加载 UI 元素模板配置"""
        template_config_path = self.assets_dir / "ui_templates.json"
        if template_config_path.exists():
            with open(template_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def detect_all_elements(self, img: np.ndarray, roi: List[int] = None) -> List[Element]:
        """
        检测画面中所有 UI 元素
        
        Args:
            img: 屏幕截图 (BGR)
            roi: 检测区域 [x, y, w, h]，None 表示全屏
            
        Returns:
            元素列表
        """
        elements = []
        
        # 1. OCR 文字识别
        if self.maafw_executor:
            ocr_elements = self._detect_text_elements(img, roi)
            elements.extend(ocr_elements)
        
        # 2. 模板匹配图标识别
        template_elements = self._detect_icon_elements(img, roi)
        elements.extend(template_elements)
        
        return elements
    
    def _detect_text_elements(self, img: np.ndarray, roi: List[int] = None) -> List[Element]:
        """OCR 文字检测"""
        if self.maafw_executor is None:
            return []
        
        try:
            # 调用 MaaFw OCR
            ocr_results = self.maafw_executor.ocr(
                controller_id="default",
                roi=roi
            )
            
            elements = []
            for item in ocr_results:
                text = item.get("text", "").strip()
                box = item.get("box", [0, 0, 0, 0])
                score = item.get("score", 0.0)
                
                if not text or score < 0.3:
                    continue
                
                x, y, w, h = box
                cx, cy = x + w // 2, y + h // 2
                
                elements.append(Element(
                    element_type="text",
                    name=text,
                    x=cx,
                    cy=cy,
                    width=w,
                    height=h,
                    confidence=score,
                    metadata={"box": box}
                ))
            
            return elements
        except Exception as e:
            print(f"[OCR] 检测失败：{e}")
            return []
    
    def _detect_icon_elements(self, img: np.ndarray, roi: List[int] = None) -> List[Element]:
        """模板匹配图标检测"""
        elements = []
        
        for icon_id, template_info in self.ui_templates.items():
            template_path = template_info.get("template", "")
            if not Path(template_path).exists():
                continue
            
            template = cv2.imread(str(template_path))
            if template is None:
                continue
            
            # 模板匹配
            result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
            threshold = template_info.get("threshold", 0.8)
            locations = np.where(result >= threshold)
            
            if len(locations[0]) > 0:
                # 取最高匹配点
                max_pos = np.unravel_index(np.argmax(result), result.shape)
                y, x = max_pos[0], max_pos[1]
                h, w, _ = template.shape
                
                elements.append(Element(
                    element_type="icon",
                    name=icon_id,
                    x=x + w // 2,
                    y=y + h // 2,
                    width=w,
                    height=h,
                    confidence=result[max_pos],
                    metadata={"template": template_path}
                ))
        
        return elements
    
    def find_element_by_name(self, elements: List[Element], name_keywords: List[str]) -> Optional[Element]:
        """根据关键词查找元素"""
        for elem in elements:
            for keyword in name_keywords:
                if keyword in elem.name:
                    return elem
        return None
    
    def build_llm_context(self, elements: List[Element], task_description: str) -> str:
        """
        构建 LLM 上下文，包含元素坐标信息
        
        Args:
            elements: 检测到的元素列表
            task_description: 任务描述
            
        Returns:
            LLM 提示词
        """
        # 元素列表
        element_list = []
        for i, elem in enumerate(elements):
            element_list.append(
                f"{i+1}. [{elem.element_type}] {elem.name} "
                f"位置：({elem.x}, {elem.y}) "
                f"大小：{elem.width}x{elem.height} "
                f"置信度：{elem.confidence:.2f}"
            )
        
        prompt = f"""
任务：{task_description}

检测到以下 UI 元素（带坐标）：
{chr(10).join(element_list)}

请根据元素信息，决定下一步操作：
1. 如果需要点击某个元素，返回该元素的中心坐标
2. 如果需要滑动，返回起始和结束坐标
3. 如果未找到目标元素，使用备选坐标（见下方）

备选坐标（仅在元素检测失败时使用）：
"""
        
        # 添加备选坐标
        for elem_id, elem_info in self.ui_elements_3cui.items():
            coords = elem_info["fallback_coords"]
            prompt += f"- {elem_info['name']} ({elem_id}): ({coords[0]}, {coords[1]})\n"
        
        prompt += """
请返回 JSON 格式：
{
    "action": "tap|swipe|back|wait",
    "target_element": "元素名称或 null",
    "coords": [x, y],  // 点击坐标
    "reason": "决策原因"
}
"""
        return prompt
    
    def get_element_or_fallback(self, elements: List[Element], ui_element_id: str) -> Tuple[int, int]:
        """
        获取元素坐标，如果未检测到则返回备选坐标
        
        Args:
            elements: 检测到的元素列表
            ui_element_id: UI 元素 ID（如 "quest_icon"）
            
        Returns:
            (x, y) 坐标
        """
        # 尝试从检测到的元素中查找
        elem_info = self.ui_elements_3cui.get(ui_element_id, {})
        target_name = elem_info.get("name", ui_element_id)
        
        # 查找匹配的元素
        for elem in elements:
            if target_name in elem.name or ui_element_id in elem.name:
                return elem.center
        
        # 未找到，返回备选坐标
        fallback = elem_info.get("fallback_coords", [540, 360])
        return (fallback[0], fallback[1])


# ═══════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    # 示例用法
    detector = SmartElementDetector()
    
    # 模拟元素列表
    mock_elements = [
        Element("text", "每日任务", 100, 200, 100, 40, 0.95),
        Element("text", "领取", 800, 900, 80, 40, 0.90),
        Element("icon", "quest_icon", 860, 80, 50, 50, 0.85),
    ]
    
    # 构建 LLM 上下文
    prompt = detector.build_llm_context(mock_elements, "打开每日任务面板并领取奖励")
    print(prompt)
    
    # 获取元素坐标（带备选）
    coords = detector.get_element_or_fallback(mock_elements, "quest_icon")
    print(f"\n任务图标坐标：{coords}")
