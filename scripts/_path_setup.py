"""Shared path setup for scripts/ directory.

Usage from scripts/*.py:
    from _path_setup import PROJECT_ROOT, SRC_DIR, ensure_path
"""
import sys
from pathlib import Path

# 自举：先添加 src 路径才能导入 utils.paths
_SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from core.foundation.utils.paths import get_project_root, get_src_dir, ensure_src_path

PROJECT_ROOT = Path(get_project_root())
SRC_DIR = Path(get_src_dir())

# DEPRECATED: MODULE_DIR 保留为向后兼容别名，指向 SRC_DIR
# 新代码请使用 from core.{foundation,capability,service}.xxx import YYY
MODULE_DIR = SRC_DIR  # noqa: F811


def ensure_path():
    """确保 src 目录在 sys.path 中"""
    ensure_src_path(__file__)
