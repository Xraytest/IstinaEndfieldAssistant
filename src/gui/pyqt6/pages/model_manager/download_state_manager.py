"""
下载状态持久化管理模块

管理下载状态的保存和恢复，支持断点续传提示
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class DownloadState:
    """下载状态数据类"""
    model_name: str
    status: str  # "pending", "downloading", "paused", "completed", "failed"
    progress: int  # 0-100
    downloaded_bytes: int
    total_bytes: int
    last_updated: str  # ISO格式时间戳
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DownloadState':
        """从字典创建"""
        return cls(**data)
    
    def is_resumable(self) -> bool:
        """检查是否可恢复"""
        return self.status in ["downloading", "paused"] and self.progress > 0


class DownloadStateManager:
    """
    下载状态管理器
    
    功能：
    - 保存下载状态到本地配置文件
    - 从配置文件恢复下载状态
    - 管理断点续传信息
    - 清理已完成或失败的记录
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化下载状态管理器
        
        Args:
            config_dir: 配置文件目录，默认为用户数据目录
        """
        if config_dir:
            self._config_dir = Path(config_dir)
        else:
            # 使用用户数据目录
            self._config_dir = Path.home() / ".istina" / "download_states"
        
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self._config_dir / "download_states.json"
        self._states: Dict[str, DownloadState] = {}
        
        self._load_states()
    
    def _load_states(self):
        """从文件加载状态"""
        if self._state_file.exists():
            try:
                with open(self._state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for model_name, state_data in data.items():
                        self._states[model_name] = DownloadState.from_dict(state_data)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"加载下载状态失败: {e}")
                self._states = {}
    
    def _save_states(self):
        """保存状态到文件"""
        try:
            data = {
                model_name: state.to_dict()
                for model_name, state in self._states.items()
            }
            with open(self._state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存下载状态失败: {e}")
    
    def get_state(self, model_name: str) -> Optional[DownloadState]:
        """
        获取模型的下载状态
        
        Args:
            model_name: 模型名称
            
        Returns:
            下载状态，如果不存在则返回None
        """
        return self._states.get(model_name)
    
    def update_state(
        self,
        model_name: str,
        status: str,
        progress: int = 0,
        downloaded_bytes: int = 0,
        total_bytes: int = 0,
        error_message: str = ""
    ):
        """
        更新下载状态
        
        Args:
            model_name: 模型名称
            status: 状态
            progress: 进度 (0-100)
            downloaded_bytes: 已下载字节数
            total_bytes: 总字节数
            error_message: 错误信息
        """
        self._states[model_name] = DownloadState(
            model_name=model_name,
            status=status,
            progress=progress,
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes,
            last_updated=datetime.now().isoformat(),
            error_message=error_message
        )
        self._save_states()
    
    def remove_state(self, model_name: str):
        """
        移除下载状态
        
        Args:
            model_name: 模型名称
        """
        if model_name in self._states:
            del self._states[model_name]
            self._save_states()
    
    def get_resumable_downloads(self) -> List[DownloadState]:
        """
        获取可恢复的下载列表
        
        Returns:
            可恢复的下载状态列表
        """
        return [
            state for state in self._states.values()
            if state.is_resumable()
        ]
    
    def has_resumable_download(self, model_name: str) -> bool:
        """
        检查模型是否有可恢复的下载
        
        Args:
            model_name: 模型名称
            
        Returns:
            是否可恢复
        """
        state = self._states.get(model_name)
        return state is not None and state.is_resumable()
    
    def get_resumable_progress(self, model_name: str) -> int:
        """
        获取可恢复下载的进度
        
        Args:
            model_name: 模型名称
            
        Returns:
            进度百分比，如果没有可恢复下载则返回0
        """
        state = self._states.get(model_name)
        return state.progress if state and state.is_resumable() else 0
    
    def clear_completed(self):
        """清理已完成的下载记录"""
        self._states = {
            model_name: state
            for model_name, state in self._states.items()
            if state.status not in ["completed", "failed"]
        }
        self._save_states()
    
    def clear_all(self):
        """清除所有下载状态"""
        self._states.clear()
        self._save_states()
    
    def get_all_states(self) -> Dict[str, DownloadState]:
        """获取所有下载状态"""
        return self._states.copy()
    
    def mark_downloading(self, model_name: str, total_bytes: int = 0):
        """标记为下载中"""
        self.update_state(
            model_name=model_name,
            status="downloading",
            total_bytes=total_bytes
        )
    
    def mark_paused(self, model_name: str, progress: int, downloaded_bytes: int):
        """标记为暂停"""
        state = self._states.get(model_name)
        total_bytes = state.total_bytes if state else 0
        self.update_state(
            model_name=model_name,
            status="paused",
            progress=progress,
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes
        )
    
    def mark_completed(self, model_name: str):
        """标记为已完成"""
        self.update_state(
            model_name=model_name,
            status="completed",
            progress=100
        )
    
    def mark_failed(self, model_name: str, error_message: str):
        """标记为失败"""
        state = self._states.get(model_name)
        progress = state.progress if state else 0
        downloaded_bytes = state.downloaded_bytes if state else 0
        total_bytes = state.total_bytes if state else 0
        self.update_state(
            model_name=model_name,
            status="failed",
            progress=progress,
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes,
            error_message=error_message
        )
    
    def update_progress(self, model_name: str, progress: int, downloaded_bytes: int):
        """更新下载进度"""
        state = self._states.get(model_name)
        if state:
            self.update_state(
                model_name=model_name,
                status="downloading",
                progress=progress,
                downloaded_bytes=downloaded_bytes,
                total_bytes=state.total_bytes
            )
