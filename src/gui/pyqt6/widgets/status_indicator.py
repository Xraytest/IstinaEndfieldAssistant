"""Stub for status indicator - replaced by Agent mode"""

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt


class ConnectionStatusIndicator(QWidget):
    """连接状态指示器 - Agent 模式简化版"""
    
    def __init__(self, connection_type: str = "server", parent=None):
        super().__init__(parent)
        self.connection_type = connection_type
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # 状态点
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #00ffa2; font-size: 10px;")
        layout.addWidget(self.status_dot)
        
        # 状态文本
        self.status_text = QLabel("ONLINE")
        self.status_text.setStyleSheet("color: #00ffa2; font-size: 11px; font-family: Consolas;")
        layout.addWidget(self.status_text)
        
        layout.addStretch()
        
        self.setStyleSheet("background-color: transparent;")
    
    
class StatusIndicatorWidget(QWidget):
    """状态指示器组件 - Agent 模式简化版"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("// STATUS INDICATOR"))
        layout.addStretch()
        self.setStyleSheet("background-color: transparent;")


class DualStatusIndicator(QWidget):
    """双重状态指示器 - Agent 模式简化版"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("// DUAL STATUS"))
        layout.addStretch()
        self.setStyleSheet("background-color: transparent;")