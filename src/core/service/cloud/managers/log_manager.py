"""日志管理业务逻辑组件"""
from datetime import datetime
from typing import Optional, Callable


class LogManager:
    """日志管理业务逻辑类

    框架无关的日志管理器，通过回调函数与 GUI 框架解耦。
    支持 PyQt6 和 tkinter 两种 GUI 框架。
    """

    def __init__(self, log_callback: Optional[Callable] = None,
                 status_callback: Optional[Callable] = None,
                 clear_callback: Optional[Callable] = None):
        """
        Args:
            log_callback: 日志写入回调，接受 (text: str) 参数
            status_callback: 状态栏更新回调，接受 (text: str) 参数
            clear_callback: 清空日志回调，无参数
        """
        self._log_callback = log_callback
        self._status_callback = status_callback
        self._clear_callback = clear_callback

    def set_log_widget(self, log_text_widget) -> None:
        """设置日志文本控件（兼容 tkinter 和 PyQt6）"""
        import sys
        if 'PyQt6' in sys.modules:
            self._log_callback = lambda text: (
                log_text_widget.insertPlainText(text + "\n")
                if hasattr(log_text_widget, 'insertPlainText')
                else log_text_widget.append(text)
            )
            self._clear_callback = lambda: log_text_widget.clear()
        else:
            import tkinter as tk
            self._log_callback = lambda text: (
                log_text_widget.insert(tk.END, text + "\n"),
                log_text_widget.see(tk.END)
            )
            self._clear_callback = lambda: log_text_widget.delete(1.0, tk.END)

    def set_status_bar(self, status_bar) -> None:
        """设置状态栏控件（兼容 tkinter 和 PyQt6）"""
        import sys
        if 'PyQt6' in sys.modules:
            self._status_callback = lambda text: (
                status_bar.showMessage(text)
                if hasattr(status_bar, 'showMessage')
                else status_bar.setText(text)
            )
        else:
            self._status_callback = lambda text: status_bar.config(text=text)

    def log_message(self, message: str, category: str = "general", level: str = "INFO") -> None:
        """记录日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{category.upper()}] {level}: {message}"

        if self._log_callback:
            try:
                self._log_callback(log_entry)
            except Exception:
                pass

        if self._status_callback:
            try:
                self._status_callback(message)
            except Exception:
                pass

        print(log_entry)

    def clear_log(self) -> None:
        """清空日志"""
        if self._clear_callback:
            try:
                self._clear_callback()
            except Exception:
                pass