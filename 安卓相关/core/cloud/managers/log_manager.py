"""日志管理业务逻辑组件"""
from datetime import datetime
import tkinter as tk

class LogManager:
    """日志管理业务逻辑类"""
    
    def __init__(self, log_text_widget, status_bar):
        self.log_text_widget = log_text_widget
        self.status_bar = status_bar
        
    def log_message(self, message, category="general", level="INFO"):
        """记录日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{category.upper()}] {level}: {message}"
        
        # 更新日志文本控件
        if self.log_text_widget:
            self.log_text_widget.insert(tk.END, log_entry + "\n")
            self.log_text_widget.see(tk.END)
            
        # 更新状态栏
        if self.status_bar:
            self.status_bar.config(text=message)
            
        # 打印到控制台（用于调试）
        print(log_entry)
        
    def clear_log(self):
        """清空日志"""
        if self.log_text_widget:
            self.log_text_widget.delete(1.0, tk.END)