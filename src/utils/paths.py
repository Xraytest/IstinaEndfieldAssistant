"""
统一路径管理工具 - IstinaEndfieldAssistant

提供一致的项目路径计算方法，避免各模块重复实现
"""
import os
import sys
from typing import Optional


def get_project_root(start_file: str = __file__) -> str:
    """
    获取项目根目录（IstinaEndfieldAssistant/）
    
    Args:
        start_file: 起始文件路径，默认为当前文件
        
    Returns:
        项目根目录绝对路径
    """
    # IstinaEndfieldAssistant/src/utils/paths.py → IstinaEndfieldAssistant/
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(start_file))))


def get_src_dir(start_file: str = __file__) -> str:
    """
    获取 src 目录
    
    Args:
        start_file: 起始文件路径
        
    Returns:
        src 目录绝对路径
    """
    return os.path.join(get_project_root(start_file), "src")


def get_config_dir(start_file: str = __file__) -> str:
    """
    获取 config 目录
    
    Args:
        start_file: 起始文件路径
        
    Returns:
        config 目录绝对路径
    """
    return os.path.join(get_project_root(start_file), "config")


def get_cache_dir(start_file: str = __file__) -> str:
    """
    获取 cache 目录
    
    Args:
        start_file: 起始文件路径
        
    Returns:
        cache 目录绝对路径
    """
    return os.path.join(get_project_root(start_file), "cache")


def get_data_dir(start_file: str = __file__) -> str:
    """
    获取 data 目录
    
    Args:
        start_file: 起始文件路径
        
    Returns:
        data 目录绝对路径
    """
    return os.path.join(get_project_root(start_file), "data")


def get_3rd_party_dir(start_file: str = __file__) -> str:
    """
    获取 3rd-party 目录
    
    Args:
        start_file: 起始文件路径
        
    Returns:
        3rd-party 目录绝对路径
    """
    return os.path.join(get_project_root(start_file), "3rd-party")


def get_client_config_path(start_file: str = __file__) -> str:
    """
    获取客户端配置文件路径
    
    Args:
        start_file: 起始文件路径
        
    Returns:
        client_config.json 绝对路径
    """
    return os.path.join(get_config_dir(start_file), "client_config.json")


def ensure_path(path: str, position: int = 0) -> None:
    """
    确保路径在 sys.path 中
    
    Args:
        path: 要添加的路径
        position: 插入位置（0 表示最前面）
    """
    if path not in sys.path:
        sys.path.insert(position, path)
        # print(f"[路径管理] 已添加路径：{path}")


def ensure_src_path(start_file: str = __file__) -> None:
    """
    确保 src 目录在 sys.path 中
    
    Args:
        start_file: 起始文件路径
    """
    ensure_path(get_src_dir(start_file))


def ensure_project_path(start_file: str = __file__) -> None:
    """
    确保项目根目录在 sys.path 中
    
    Args:
        start_file: 起始文件路径
    """
    ensure_path(get_project_root(start_file))


# ==================== 便捷函数 ====================

def get_adb_path(start_file: str = __file__) -> str:
    """
    获取 ADB 可执行文件路径
    
    Args:
        start_file: 起始文件路径
        
    Returns:
        adb.exe 绝对路径
    """
    return os.path.join(get_3rd_party_dir(start_file), "adb", "adb.exe")


def get_git_path(start_file: str = __file__) -> str:
    """
    获取 Git 可执行文件路径
    
    Args:
        start_file: 起始文件路径
        
    Returns:
        git.exe 绝对路径
    """
    return os.path.join(get_3rd_party_dir(start_file), "git", "bin", "git.exe")


def get_standard_flows_config_path(start_file: str = __file__) -> str:
    """
    获取标准流配置文件路径
    
    Args:
        start_file: 起始文件路径
        
    Returns:
        flows_config.json 绝对路径
    """
    return os.path.join(get_config_dir(start_file), "standard_flows", "flows_config.json")


def get_logging_config_path(start_file: str = __file__) -> str:
    """
    获取日志配置文件路径
    
    Args:
        start_file: 起始文件路径
        
    Returns:
        logging_config.json 绝对路径
    """
    return os.path.join(get_config_dir(start_file), "logging_config.json")


# ==================== 测试 ====================

if __name__ == "__main__":
    print("=== 路径管理工具测试 ===\n")
    
    print(f"项目根目录：{get_project_root()}")
    print(f"src 目录：{get_src_dir()}")
    print(f"config 目录：{get_config_dir()}")
    print(f"cache 目录：{get_cache_dir()}")
    print(f"data 目录：{get_data_dir()}")
    print(f"3rd-party 目录：{get_3rd_party_dir()}")
    print(f"\n客户端配置：{get_client_config_path()}")
    print(f"标准流配置：{get_standard_flows_config_path()}")
    print(f"日志配置：{get_logging_config_path()}")
    print(f"\nADB 路径：{get_adb_path()}")
    print(f"Git 路径：{get_git_path()}")
    
    print("\n=== sys.path 测试 ===")
    print(f"添加前 src 在 sys.path: {get_src_dir() in sys.path}")
    ensure_src_path()
    print(f"添加后 src 在 sys.path: {get_src_dir() in sys.path}")
