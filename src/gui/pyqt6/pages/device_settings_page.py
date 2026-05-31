"""Device settings page - Endfield terminal style with scheduled start"""
from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QTimeEdit, QCheckBox, QGroupBox, QMessageBox, QFormLayout
)
from PyQt6.QtCore import pyqtSignal, Qt, QTime
import json
import os

HEADER_STYLE = "color: #18d1ff; font-size: 14px; font-family: Consolas; font-weight: bold; letter-spacing: 1px; padding: 4px 0;"
INFO_STYLE = "color: #9090a8; font-size: 12px; font-family: Consolas; padding: 3px 0;"
VAL_STYLE = "color: #e8e8ee; font-size: 12px; font-family: Consolas; padding: 3px 0;"
GREEN_STYLE = "color: #00ffa2; font-size: 12px; font-family: Consolas; padding: 3px 0;"
RED_STYLE = "color: #ff3355; font-size: 12px; font-family: Consolas; padding: 3px 0;"

BTN_ACTIVE = """
    QPushButton {
        background-color: rgba(0, 255, 162, 0.12);
        color: #00ffa2;
        border: 1px solid rgba(0, 255, 162, 0.40);
        border-radius: 4px;
        font-size: 11px; font-family: Consolas; font-weight: bold; letter-spacing: 1px;
    }
    QPushButton:hover { background-color: rgba(0, 255, 162, 0.25); }
"""
BTN_DEFAULT = """
    QPushButton {
        background-color: rgba(24, 209, 255, 0.10);
        color: #18d1ff;
        border: 1px solid rgba(24, 209, 255, 0.30);
        border-radius: 4px;
        font-size: 11px; font-family: Consolas; font-weight: bold; letter-spacing: 1px;
    }
    QPushButton:hover { background-color: rgba(24, 209, 255, 0.20); }
"""


class DeviceSettingsPage(QWidget):
    """Device settings page with scheduled standard flow start"""
    
    settings_changed = pyqtSignal(dict)
    schedule_changed = pyqtSignal(list)
    
    def __init__(self, device_manager=None, config: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self._config = config or {}
        self._scheduled_tasks: List[Dict[str, Any]] = []
        
        self._setup_ui()
        self._load_scheduled_tasks()
    
    def _get_cache_dir(self) -> str:
        current = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current))))
        cache = os.path.join(root, "cache")
        os.makedirs(cache, exist_ok=True)
        return cache
    
    def _load_scheduled_tasks(self):
        path = os.path.join(self._get_cache_dir(), "scheduled_tasks.json")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self._scheduled_tasks = json.load(f)
            self._update_schedule_table()
        except:
            self._scheduled_tasks = []
    
    def _save_scheduled_tasks(self):
        path = os.path.join(self._get_cache_dir(), "scheduled_tasks.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._scheduled_tasks, f, indent=2, ensure_ascii=False)
            self.schedule_changed.emit(self._scheduled_tasks)
        except Exception as e:
            print(f"Failed to save scheduled tasks: {e}")
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Title
        title = QLabel("// DEVICE SETTINGS")
        title.setStyleSheet(HEADER_STYLE)
        layout.addWidget(title)
        
        # Device Connection Settings
        device_group = self._make_card("DEVICE CONNECTION")
        device_layout = QVBoxLayout()
        
        # Auto-connect checkbox
        self._auto_connect_cb = QCheckBox("AUTO-CONNECT ON STARTUP")
        self._auto_connect_cb.setStyleSheet("""
            QCheckBox {
                color: #e8e8ee; font-size: 12px; font-family: Consolas; spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px; height: 16px; border-radius: 2px;
                border: 1px solid rgba(24, 209, 255, 0.30); background-color: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #18d1ff; border-color: #18d1ff;
            }
        """)
        self._auto_connect_cb.setToolTip("Automatically connect to last device on startup")
        self._auto_connect_cb.stateChanged.connect(self._on_auto_connect_changed)
        device_layout.addWidget(self._auto_connect_cb)
        
        # Last connected device display
        last_device_row = QHBoxLayout()
        last_device_row.addWidget(QLabel("LAST CONNECTED:"))
        last_device_row.itemAt(0).widget().setStyleSheet(INFO_STYLE)
        self._last_device_label = QLabel("NONE")
        self._last_device_label.setStyleSheet(VAL_STYLE)
        last_device_row.addWidget(self._last_device_label)
        last_device_row.addStretch()
        device_layout.addLayout(last_device_row)
        
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)
        
        # Scheduled Standard Flow Start
        schedule_group = self._make_card("SCHEDULED STANDARD FLOW START")
        schedule_layout = QVBoxLayout()
        
        # Schedule table
        self._schedule_table = QTableWidget()
        self._schedule_table.setColumnCount(4)
        self._schedule_table.setHorizontalHeaderLabels(["Time", "Flow Name", "Enabled", "Actions"])
        self._schedule_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._schedule_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._schedule_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._schedule_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._schedule_table.setColumnWidth(0, 100)
        self._schedule_table.setColumnWidth(2, 80)
        self._schedule_table.setColumnWidth(3, 100)
        self._schedule_table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(16, 16, 26, 0.85);
                border: 1px solid rgba(24, 209, 255, 0.10);
                border-radius: 4px;
                color: #e8e8ee; font-size: 12px; font-family: Consolas;
                gridline-color: rgba(24, 209, 255, 0.10);
            }
            QTableWidget::item { padding: 8px; }
            QHeaderView::section {
                background-color: rgba(24, 209, 255, 0.10);
                color: #18d1ff; font-size: 11px; font-weight: bold;
                padding: 8px; border: none;
            }
        """)
        schedule_layout.addWidget(self._schedule_table)
        
        # Add/Remove buttons
        btn_layout = QHBoxLayout()
        self._add_task_btn = QPushButton("ADD TASK")
        self._add_task_btn.setStyleSheet(BTN_ACTIVE)
        self._add_task_btn.clicked.connect(self._add_scheduled_task)
        btn_layout.addWidget(self._add_task_btn)
        
        self._remove_task_btn = QPushButton("REMOVE")
        self._remove_task_btn.setStyleSheet(BTN_DEFAULT)
        self._remove_task_btn.clicked.connect(self._remove_scheduled_task)
        btn_layout.addWidget(self._remove_task_btn)
        
        self._save_schedule_btn = QPushButton("SAVE")
        self._save_schedule_btn.setStyleSheet(BTN_ACTIVE)
        self._save_schedule_btn.clicked.connect(self._save_scheduled_tasks)
        btn_layout.addWidget(self._save_schedule_btn)
        
        btn_layout.addStretch()
        schedule_layout.addLayout(btn_layout)
        
        schedule_group.setLayout(schedule_layout)
        layout.addWidget(schedule_group)
        
        layout.addStretch()
        self._update_device_info()
    
    def _make_card(self, title: str) -> QGroupBox:
        group = QGroupBox()
        group.setStyleSheet("""
            QGroupBox {
                background-color: rgba(16, 16, 26, 0.85);
                border: 1px solid rgba(24, 209, 255, 0.10);
                border-radius: 4px;
                font-size: 13px; font-family: Consolas;
                color: #e8e8ee; font-weight: bold; letter-spacing: 1px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 16px; padding: 0 4px;
            }
        """)
        group.setTitle(title)
        group.setLayout(QVBoxLayout())
        group.layout().setContentsMargins(20, 16, 20, 16)
        group.layout().setSpacing(6)
        return group
    
    def _update_device_info(self):
        if self.device_manager:
            last_device = self.device_manager.get_last_connected_device()
            if last_device:
                self._last_device_label.setText(last_device)
                self._last_device_label.setStyleSheet(GREEN_STYLE)
            else:
                self._last_device_label.setText("NONE")
                self._last_device_label.setStyleSheet(RED_STYLE)
    
    def _on_auto_connect_changed(self, state):
        enabled = state == Qt.CheckState.Checked
        self._config.setdefault('device', {})
        self._config['device']['auto_connect'] = enabled
        self.settings_changed.emit(self._config)
    
    def _update_schedule_table(self):
        self._schedule_table.setRowCount(len(self._scheduled_tasks))
        for i, task in enumerate(self._scheduled_tasks):
            # Time column
            time_item = QTableWidgetItem(task.get('time', '00:00'))
            time_item.setData(Qt.ItemDataRole.EditRole, task.get('time', '00:00'))
            self._schedule_table.setItem(i, 0, time_item)
            
            # Flow name column
            flow_item = QTableWidgetItem(task.get('flow_name', 'standard'))
            flow_item.setData(Qt.ItemDataRole.EditRole, task.get('flow_name', 'standard'))
            self._schedule_table.setItem(i, 1, flow_item)
            
            # Enabled column
            enabled_widget = QCheckBox()
            enabled_widget.setChecked(task.get('enabled', True))
            enabled_widget.stateChanged.connect(lambda s, row=i: self._on_task_enabled_changed(row))
            self._schedule_table.setCellWidget(i, 2, enabled_widget)
            
            # Actions column (empty, handled by remove button)
            pass
    
    def _on_task_enabled_changed(self, row: int):
        if row < len(self._scheduled_tasks):
            checkbox = self._schedule_table.cellWidget(row, 2)
            self._scheduled_tasks[row]['enabled'] = checkbox.isChecked()
    
    def _add_scheduled_task(self):
        new_task = {
            'time': '08:00',
            'flow_name': 'standard',
            'enabled': True
        }
        self._scheduled_tasks.append(new_task)
        self._update_schedule_table()
    
    def _remove_scheduled_task(self):
        current_row = self._schedule_table.currentRow()
        if current_row >= 0 and current_row < len(self._scheduled_tasks):
            self._scheduled_tasks.pop(current_row)
            self._update_schedule_table()
        else:
            QMessageBox.warning(self, "No Selection", "Please select a task to remove.")
    
    def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        return self._scheduled_tasks
    
    def set_device_manager(self, device_manager):
        self.device_manager = device_manager
        self._update_device_info()
