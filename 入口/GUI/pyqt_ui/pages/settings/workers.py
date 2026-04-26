"""
工作线程模块

提取公共的GPU检测和模型下载工作线程，供设置页面和对话框复用
"""

from typing import Optional, Dict, Any, Callable
from PyQt6.QtCore import QThread, pyqtSignal

# 导入本地推理模块
try:
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.gpu_checker import GPUChecker
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.model_manager import ModelManager
except ImportError:
    import sys
    import os
    # 计算项目根目录路径
    current_file = os.path.abspath(__file__)
    settings_dir = os.path.dirname(current_file)
    pages_dir = os.path.dirname(settings_dir)
    pyqt_ui_dir = os.path.dirname(pages_dir)
    gui_dir = os.path.dirname(pyqt_ui_dir)
    entry_dir = os.path.dirname(gui_dir)
    istina_dir = os.path.dirname(entry_dir)
    project_root = os.path.dirname(istina_dir)
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if istina_dir not in sys.path:
        sys.path.insert(0, istina_dir)
    
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.gpu_checker import GPUChecker
    from IstinaEndfieldAssistant.安卓相关.core.local_inference.model_manager import ModelManager


class GPUCheckWorker(QThread):
    """GPU检测工作线程"""
    
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    
    def __init__(self, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self._checker: Optional[GPUChecker] = None
        try:
            self._checker = GPUChecker()
        except Exception:
            self._checker = None
    
    def run(self) -> None:
        """执行GPU检测"""
        if self._checker is None:
            self.error_signal.emit("GPUChecker初始化失败")
            return
            
        try:
            result = self._checker.check_gpu_availability()
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))


class ModelDownloadWorker(QThread):
    """模型下载工作线程"""
    
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, model_name: str, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self._model_name = model_name
        self._manager: Optional[ModelManager] = None
        self._cancelled = False
        
        try:
            self._manager = ModelManager()
        except Exception:
            self._manager = None
    
    def run(self) -> None:
        """执行模型下载"""
        if self._manager is None:
            self.finished_signal.emit(False, "ModelManager初始化失败")
            return
            
        try:
            def progress_callback(percentage: int, message: str) -> None:
                if not self._cancelled:
                    self.progress_signal.emit(percentage, message)
            
            result = self._manager.download_model(self._model_name, progress_callback)
            
            if self._cancelled:
                self.finished_signal.emit(False, "下载已取消")
            elif result:
                self.finished_signal.emit(True, "下载完成")
            else:
                self.finished_signal.emit(False, "下载失败")
                
        except Exception as e:
            self.finished_signal.emit(False, str(e))
    
    def cancel(self) -> None:
        """取消下载"""
        self._cancelled = True
