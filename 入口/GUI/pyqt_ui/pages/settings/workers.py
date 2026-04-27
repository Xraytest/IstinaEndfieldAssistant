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
        # 不在主线程创建 GPUChecker，避免 NVML 初始化导致栈损坏
        # GPUChecker 会在 run() 方法中（工作线程）延迟创建
        self._checker: Optional[GPUChecker] = None
        self._cancelled = False
    
    def run(self) -> None:
        """执行GPU检测"""
        # 检查是否已被取消
        if self._cancelled or self.isInterruptionRequested():
            self.error_signal.emit("检测已取消")
            return
        
        # 在工作线程中创建 GPUChecker，避免主线程栈损坏
        try:
            self._checker = GPUChecker()
        except Exception as e:
            self.error_signal.emit(f"GPUChecker初始化失败: {str(e)}")
            return
            
        try:
            result = self._checker.check_gpu_availability()
            # 发送结果前再次检查是否被取消
            if not self._cancelled and not self.isInterruptionRequested():
                self.finished_signal.emit(result)
        except Exception as e:
            if not self._cancelled and not self.isInterruptionRequested():
                self.error_signal.emit(str(e))
    
    def cancel(self) -> None:
        """取消检测"""
        self._cancelled = True
        self.requestInterruption()


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
