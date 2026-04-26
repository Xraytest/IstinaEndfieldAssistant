"""
模型过滤和排序模块

提供搜索和排序功能
"""

from enum import Enum, auto
from typing import List, Callable, Optional
from dataclasses import dataclass

# 支持两种导入方式
try:
    from .....安卓相关.core.local_inference.model_manager import ModelInfo
except ImportError:
    import sys
    import os
    current_file = os.path.abspath(__file__)
    model_manager_dir = os.path.dirname(current_file)
    pages_dir = os.path.dirname(model_manager_dir)
    pyqt_ui_dir = os.path.dirname(pages_dir)
    gui_dir = os.path.dirname(pyqt_ui_dir)
    entry_dir = os.path.dirname(gui_dir)
    istina_dir = os.path.dirname(entry_dir)
    project_root = os.path.dirname(istina_dir)
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if istina_dir not in sys.path:
        sys.path.insert(0, istina_dir)
    
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.model_manager import ModelInfo


class SortOrder(Enum):
    """排序方式枚举"""
    NAME_ASC = auto()           # 名称 A-Z
    NAME_DESC = auto()          # 名称 Z-A
    SIZE_ASC = auto()           # 大小 小到大
    SIZE_DESC = auto()          # 大小 大到小
    DOWNLOADED_FIRST = auto()   # 已下载优先
    NOT_DOWNLOADED_FIRST = auto()  # 未下载优先
    RECOMMENDED_FIRST = auto()  # 推荐优先


@dataclass
class FilterCriteria:
    """过滤条件数据类"""
    search_text: str = ""                    # 搜索文本
    show_downloaded: bool = True             # 显示已下载
    show_not_downloaded: bool = True         # 显示未下载
    min_size_gb: Optional[float] = None      # 最小大小
    max_size_gb: Optional[float] = None      # 最大大小


class ModelFilter:
    """
    模型过滤器
    
    功能：
    - 按名称搜索
    - 按描述搜索
    - 按下载状态过滤
    - 按大小范围过滤
    - 多种排序方式
    """
    
    def __init__(self):
        """初始化过滤器"""
        self._criteria = FilterCriteria()
        self._sort_order = SortOrder.NAME_ASC
        self._recommended_model: Optional[str] = None
    
    def set_criteria(self, criteria: FilterCriteria):
        """设置过滤条件"""
        self._criteria = criteria
    
    def get_criteria(self) -> FilterCriteria:
        """获取当前过滤条件"""
        return self._criteria
    
    def set_search_text(self, text: str):
        """设置搜索文本"""
        self._criteria.search_text = text.lower().strip()
    
    def set_sort_order(self, order: SortOrder):
        """设置排序方式"""
        self._sort_order = order
    
    def get_sort_order(self) -> SortOrder:
        """获取当前排序方式"""
        return self._sort_order
    
    def set_recommended_model(self, model_name: Optional[str]):
        """设置推荐模型名称"""
        self._recommended_model = model_name
    
    def filter_models(self, models: List[ModelInfo]) -> List[ModelInfo]:
        """
        过滤模型列表
        
        Args:
            models: 原始模型列表
            
        Returns:
            过滤后的模型列表
        """
        result = []
        
        for model in models:
            # 按下载状态过滤
            if model.is_downloaded and not self._criteria.show_downloaded:
                continue
            if not model.is_downloaded and not self._criteria.show_not_downloaded:
                continue
            
            # 按大小范围过滤
            if self._criteria.min_size_gb is not None:
                if model.size_gb < self._criteria.min_size_gb:
                    continue
            if self._criteria.max_size_gb is not None:
                if model.size_gb > self._criteria.max_size_gb:
                    continue
            
            # 按搜索文本过滤
            if self._criteria.search_text:
                search_lower = self._criteria.search_text.lower()
                name_match = search_lower in model.name.lower()
                desc_match = search_lower in model.description.lower()
                
                if not name_match and not desc_match:
                    continue
            
            result.append(model)
        
        return result
    
    def sort_models(self, models: List[ModelInfo]) -> List[ModelInfo]:
        """
        排序模型列表
        
        Args:
            models: 模型列表
            
        Returns:
            排序后的模型列表
        """
        result = list(models)  # 创建副本
        
        if self._sort_order == SortOrder.NAME_ASC:
            result.sort(key=lambda m: m.name.lower())
        elif self._sort_order == SortOrder.NAME_DESC:
            result.sort(key=lambda m: m.name.lower(), reverse=True)
        elif self._sort_order == SortOrder.SIZE_ASC:
            result.sort(key=lambda m: m.size_gb)
        elif self._sort_order == SortOrder.SIZE_DESC:
            result.sort(key=lambda m: m.size_gb, reverse=True)
        elif self._sort_order == SortOrder.DOWNLOADED_FIRST:
            result.sort(key=lambda m: (not m.is_downloaded, m.name.lower()))
        elif self._sort_order == SortOrder.NOT_DOWNLOADED_FIRST:
            result.sort(key=lambda m: (m.is_downloaded, m.name.lower()))
        elif self._sort_order == SortOrder.RECOMMENDED_FIRST:
            if self._recommended_model:
                result.sort(key=lambda m: (
                    m.name != self._recommended_model,
                    not m.is_downloaded,
                    m.name.lower()
                ))
            else:
                result.sort(key=lambda m: (not m.is_downloaded, m.name.lower()))
        
        return result
    
    def apply(self, models: List[ModelInfo]) -> List[ModelInfo]:
        """
        应用过滤和排序
        
        Args:
            models: 原始模型列表
            
        Returns:
            过滤并排序后的模型列表
        """
        filtered = self.filter_models(models)
        return self.sort_models(filtered)
    
    @staticmethod
    def get_sort_order_display_name(order: SortOrder) -> str:
        """获取排序方式的显示名称"""
        names = {
            SortOrder.NAME_ASC: "名称 (A-Z)",
            SortOrder.NAME_DESC: "名称 (Z-A)",
            SortOrder.SIZE_ASC: "大小 (小到大)",
            SortOrder.SIZE_DESC: "大小 (大到小)",
            SortOrder.DOWNLOADED_FIRST: "已下载优先",
            SortOrder.NOT_DOWNLOADED_FIRST: "未下载优先",
            SortOrder.RECOMMENDED_FIRST: "推荐优先",
        }
        return names.get(order, "未知")
    
    @staticmethod
    def get_all_sort_orders() -> List[SortOrder]:
        """获取所有排序方式"""
        return [
            SortOrder.NAME_ASC,
            SortOrder.NAME_DESC,
            SortOrder.SIZE_ASC,
            SortOrder.SIZE_DESC,
            SortOrder.DOWNLOADED_FIRST,
            SortOrder.NOT_DOWNLOADED_FIRST,
            SortOrder.RECOMMENDED_FIRST,
        ]
