"""
输入验证器模块

提供用于设置页面的输入验证功能
"""

from typing import Optional
from pathlib import Path
from PyQt6.QtGui import QValidator
from PyQt6.QtCore import QObject


class PathValidator(QValidator):
    """路径验证器 - 验证路径是否存在"""
    
    def __init__(
        self,
        parent: Optional[QObject] = None,
        must_exist: bool = False,
        allow_file: bool = True,
        allow_dir: bool = True
    ) -> None:
        super().__init__(parent)
        self._must_exist = must_exist
        self._allow_file = allow_file
        self._allow_dir = allow_dir
    
    def validate(self, input_str: str, pos: int) -> tuple:
        """
        验证输入路径
        
        Returns:
            (State, str, int) 元组
        """
        if not input_str:
            return (QValidator.State.Intermediate, input_str, pos)
        
        path = Path(input_str)
        
        # 检查路径是否存在
        if self._must_exist and not path.exists():
            return (QValidator.State.Invalid, input_str, pos)
        
        # 检查路径类型
        if path.exists():
            if path.is_file() and not self._allow_file:
                return (QValidator.State.Invalid, input_str, pos)
            if path.is_dir() and not self._allow_dir:
                return (QValidator.State.Invalid, input_str, pos)
        
        return (QValidator.State.Acceptable, input_str, pos)
    
    def fixup(self, input_str: str) -> str:
        """自动修复路径"""
        # 规范化路径分隔符
        return input_str.replace('\\', '/').strip()


class RangeValidator(QValidator):
    """范围验证器 - 验证数值是否在指定范围内"""
    
    def __init__(
        self,
        min_value: int,
        max_value: int,
        parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        self._min = min_value
        self._max = max_value
    
    def validate(self, input_str: str, pos: int) -> tuple:
        """
        验证输入数值
        
        Returns:
            (State, str, int) 元组
        """
        if not input_str:
            return (QValidator.State.Intermediate, input_str, pos)
        
        try:
            value = int(input_str)
            if value < self._min:
                return (QValidator.State.Intermediate, input_str, pos)
            elif value > self._max:
                return (QValidator.State.Invalid, input_str, pos)
            else:
                return (QValidator.State.Acceptable, input_str, pos)
        except ValueError:
            return (QValidator.State.Invalid, input_str, pos)
    
    def fixup(self, input_str: str) -> str:
        """自动修复数值"""
        try:
            value = int(input_str)
            if value < self._min:
                return str(self._min)
            elif value > self._max:
                return str(self._max)
            return str(value)
        except ValueError:
            return str(self._min)


class CacheSizeValidator(RangeValidator):
    """缓存大小验证器 - 100MB 到 10GB"""
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(100, 10240, parent)


class CacheTTLValidator(RangeValidator):
    """缓存过期时间验证器 - 1小时到7天(168小时)"""
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(1, 168, parent)


# 验证器工厂函数
def create_path_validator(
    must_exist: bool = False,
    allow_file: bool = True,
    allow_dir: bool = True,
    parent: Optional[QObject] = None
) -> PathValidator:
    """创建路径验证器"""
    return PathValidator(must_exist, allow_file, allow_dir, parent)


def create_range_validator(
    min_value: int,
    max_value: int,
    parent: Optional[QObject] = None
) -> RangeValidator:
    """创建范围验证器"""
    return RangeValidator(min_value, max_value, parent)
