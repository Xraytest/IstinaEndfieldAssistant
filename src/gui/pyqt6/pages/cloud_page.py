"""Cloud services page - Endfield terminal style"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class CloudPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("// CLOUD SERVICES TERMINAL")
        label.setStyleSheet("""
            QLabel {
                color: #18d1ff;
                font-size: 14px;
                font-family: Consolas;
                font-weight: bold;
                letter-spacing: 1px;
                padding: 24px;
            }
        """)
        layout.addWidget(label)
        layout.addStretch()