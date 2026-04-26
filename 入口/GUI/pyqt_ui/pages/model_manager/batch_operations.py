"""
批量操作管理模块

提供批量下载、删除等操作的管理
"""

from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum, auto

from PyQt6.QtCore import QObject, pyqtSignal, QThread

# 支持两种导入方式
try:
    from .....安卓相关.core.local_inference.model_manager import ModelManager, ModelInfo
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
    
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.model_manager import ModelManager, ModelInfo


class BatchOperationType(Enum):
    """批量操作类型"""
    DOWNLOAD = auto()   # 批量下载
    DELETE = auto()     # 批量删除


@dataclass
class BatchOperationItem:
    """批量操作项"""
    model_name: str
    operation: BatchOperationType
    status: str = "pending"  # pending, running, success, failed, cancelled
    progress: int = 0
    message: str = ""


class BatchDownloadWorker(QThread):
    """批量下载工作线程"""
    
    item_progress_signal = pyqtSignal(str, int, str)  # model_name, progress, message
    item_finished_signal = pyqtSignal(str, bool, str)  # model_name, success, message
    all_finished_signal = pyqtSignal(bool, int, int)   # all_success, success_count, total_count
    
    def __init__(
        self,
        model_names: List[str],
        model_manager: ModelManager,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self._model_names = model_names
        self._model_manager = model_manager
        self._cancelled = False
        self._current_model: Optional[str] = None
    
    def run(self):
        """执行批量下载"""
        success_count = 0
        total_count = len(self._model_names)
        all_success = True
        
        for model_name in self._model_names:
            if self._cancelled:
                self.item_finished_signal.emit(model_name, False, "已取消")
                all_success = False
                continue
            
            self._current_model = model_name
            self.item_progress_signal.emit(model_name, 0, "开始下载...")
            
            try:
                def progress_callback(percentage: int, message: str):
                    if not self._cancelled:
                        self.item_progress_signal.emit(model_name, percentage, message)
                
                result = self._model_manager.download_model(model_name, progress_callback)
                
                if self._cancelled:
                    self.item_finished_signal.emit(model_name, False, "已取消")
                    all_success = False
                elif result:
                    self.item_finished_signal.emit(model_name, True, "下载完成")
                    success_count += 1
                else:
                    self.item_finished_signal.emit(model_name, False, "下载失败")
                    all_success = False
                    
            except Exception as e:
                self.item_finished_signal.emit(model_name, False, str(e))
                all_success = False
        
        self._current_model = None
        self.all_finished_signal.emit(all_success, success_count, total_count)
    
    def cancel(self):
        """取消批量下载"""
        self._cancelled = True


class BatchDeleteWorker(QThread):
    """批量删除工作线程"""
    
    item_finished_signal = pyqtSignal(str, bool, str)  # model_name, success, message
    all_finished_signal = pyqtSignal(bool, int, int)   # all_success, success_count, total_count
    
    def __init__(
        self,
        model_names: List[str],
        model_manager: ModelManager,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self._model_names = model_names
        self._model_manager = model_manager
    
    def run(self):
        """执行批量删除"""
        success_count = 0
        total_count = len(self._model_names)
        all_success = True
        
        for model_name in self._model_names:
            try:
                result = self._model_manager.delete_model(model_name)
                if result:
                    self.item_finished_signal.emit(model_name, True, "删除成功")
                    success_count += 1
                else:
                    self.item_finished_signal.emit(model_name, False, "删除失败")
                    all_success = False
            except Exception as e:
                self.item_finished_signal.emit(model_name, False, str(e))
                all_success = False
        
        self.all_finished_signal.emit(all_success, success_count, total_count)


class BatchOperationManager(QObject):
    """
    批量操作管理器
    
    功能：
    - 管理批量操作项
    - 执行批量下载
    - 执行批量删除
    - 跟踪操作进度
    - 提供操作结果
    """
    
    # 信号
    operation_started = pyqtSignal(BatchOperationType, int)  # 操作类型，项目数量
    operation_progress = pyqtSignal(str, int, str)  # model_name, progress, message
    operation_item_finished = pyqtSignal(str, bool, str)  # model_name, success, message
    operation_finished = pyqtSignal(bool, int, int)  # all_success, success_count, total_count
    operation_cancelled = pyqtSignal()
    
    def __init__(self, model_manager: ModelManager, parent: Optional[QObject] = None):
        """
        初始化批量操作管理器
        
        Args:
            model_manager: 模型管理器实例
            parent: 父对象
        """
        super().__init__(parent)
        self._model_manager = model_manager
        self._items: Dict[str, BatchOperationItem] = {}
        self._current_worker: Optional[QThread] = None
        self._is_running = False
    
    def prepare_batch_download(self, models: List[ModelInfo]) -> List[str]:
        """
        准备批量下载
        
        Args:
            models: 模型列表
            
        Returns:
            可下载的模型名称列表
        """
        download_list = []
        self._items.clear()
        
        for model in models:
            if not model.is_downloaded:
                download_list.append(model.name)
                self._items[model.name] = BatchOperationItem(
                    model_name=model.name,
                    operation=BatchOperationType.DOWNLOAD
                )
        
        return download_list
    
    def prepare_batch_delete(self, models: List[ModelInfo]) -> List[str]:
        """
        准备批量删除
        
        Args:
            models: 模型列表
            
        Returns:
            可删除的模型名称列表
        """
        delete_list = []
        self._items.clear()
        
        for model in models:
            if model.is_downloaded:
                delete_list.append(model.name)
                self._items[model.name] = BatchOperationItem(
                    model_name=model.name,
                    operation=BatchOperationType.DELETE
                )
        
        return delete_list
    
    def start_batch_download(self, model_names: List[str]) -> bool:
        """
        开始批量下载
        
        Args:
            model_names: 要下载的模型名称列表
            
        Returns:
            是否成功启动
        """
        if self._is_running:
            return False
        
        if not model_names:
            return False
        
        self._is_running = True
        self.operation_started.emit(BatchOperationType.DOWNLOAD, len(model_names))
        
        self._current_worker = BatchDownloadWorker(
            model_names,
            self._model_manager,
            self
        )
        self._current_worker.item_progress_signal.connect(self._on_item_progress)
        self._current_worker.item_finished_signal.connect(self._on_item_finished)
        self._current_worker.all_finished_signal.connect(self._on_all_finished)
        self._current_worker.start()
        
        return True
    
    def start_batch_delete(self, model_names: List[str]) -> bool:
        """
        开始批量删除
        
        Args:
            model_names: 要删除的模型名称列表
            
        Returns:
            是否成功启动
        """
        if self._is_running:
            return False
        
        if not model_names:
            return False
        
        self._is_running = True
        self.operation_started.emit(BatchOperationType.DELETE, len(model_names))
        
        self._current_worker = BatchDeleteWorker(
            model_names,
            self._model_manager,
            self
        )
        self._current_worker.item_finished_signal.connect(self._on_item_finished)
        self._current_worker.all_finished_signal.connect(self._on_all_finished)
        self._current_worker.start()
        
        return True
    
    def cancel_operation(self):
        """取消当前操作"""
        if self._current_worker and isinstance(self._current_worker, BatchDownloadWorker):
            self._current_worker.cancel()
            self.operation_cancelled.emit()
    
    def is_running(self) -> bool:
        """检查是否有操作正在进行"""
        return self._is_running
    
    def get_items(self) -> Dict[str, BatchOperationItem]:
        """获取所有操作项"""
        return self._items.copy()
    
    def get_item_status(self, model_name: str) -> Optional[str]:
        """获取指定模型的操作状态"""
        item = self._items.get(model_name)
        return item.status if item else None
    
    def _on_item_progress(self, model_name: str, progress: int, message: str):
        """处理单项进度更新"""
        if model_name in self._items:
            self._items[model_name].progress = progress
            self._items[model_name].message = message
            self._items[model_name].status = "running"
        self.operation_progress.emit(model_name, progress, message)
    
    def _on_item_finished(self, model_name: str, success: bool, message: str):
        """处理单项完成"""
        if model_name in self._items:
            self._items[model_name].status = "success" if success else "failed"
            self._items[model_name].message = message
        self.operation_item_finished.emit(model_name, success, message)
    
    def _on_all_finished(self, all_success: bool, success_count: int, total_count: int):
        """处理全部完成"""
        self._is_running = False
        self._current_worker = None
        self.operation_finished.emit(all_success, success_count, total_count)
    
    def cleanup(self):
        """清理资源"""
        if self._current_worker and self._current_worker.isRunning():
            if isinstance(self._current_worker, BatchDownloadWorker):
                self._current_worker.cancel()
            self._current_worker.terminate()
            self._current_worker.wait()
        self._current_worker = None
        self._is_running = False
