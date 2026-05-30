"""Standard Reasoning page - select and execute standard flow tasks"""
import os
import json
from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QScrollArea, QTextEdit, QMessageBox,
    QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal

INFO_STYLE = "color: #9090a8; font-size: 12px; font-family: Consolas; padding: 3px 0;"
VAL_STYLE = "color: #e8e8ee; font-size: 12px; font-family: Consolas; padding: 3px 0;"
GREEN_STYLE = "color: #00ffa2; font-size: 12px; font-family: Consolas; padding: 3px 0;"
RED_STYLE = "color: #ff3355; font-size: 12px; font-family: Consolas; padding: 3px 0;"
BLUE_STYLE = "color: #18d1ff; font-size: 12px; font-family: Consolas; padding: 3px 0;"
HEADER_STYLE = "color: #18d1ff; font-size: 14px; font-family: Consolas; font-weight: bold; letter-spacing: 1px; padding: 4px 0;"

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
BTN_STOP = """
    QPushButton {
        background-color: rgba(255, 51, 85, 0.12);
        color: #ff3355;
        border: 1px solid rgba(255, 51, 85, 0.40);
        border-radius: 4px;
        font-size: 11px; font-family: Consolas; font-weight: bold; letter-spacing: 1px;
    }
    QPushButton:hover { background-color: rgba(255, 51, 85, 0.25); }
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
COMBO_STYLE = """
    QComboBox {
        background-color: rgba(10, 10, 15, 0.80);
        color: #e8e8ee;
        border: 1px solid rgba(24, 209, 255, 0.15);
        border-radius: 4px;
        padding: 8px 12px; font-size: 12px; font-family: Consolas;
        min-height: 36px;
    }
    QComboBox:hover { border-color: rgba(24, 209, 255, 0.35); }
    QComboBox::drop-down { border: none; width: 28px; }
    QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid rgba(24, 209, 255, 0.50); width: 0; height: 0; }
    QComboBox QAbstractItemView {
        background-color: rgba(12, 12, 20, 0.95);
        color: #e8e8ee;
        border: 1px solid rgba(24, 209, 255, 0.15);
        selection-background-color: rgba(24, 209, 255, 0.15);
    }
"""
CHECK_STYLE = """
    QCheckBox { color: #e8e8ee; font-size: 12px; font-family: Consolas; spacing: 8px; }
    QCheckBox::indicator {
        width: 16px; height: 16px; border-radius: 2px;
        border: 1px solid rgba(24, 209, 255, 0.30);
        background-color: transparent;
    }
    QCheckBox::indicator:checked { background-color: #18d1ff; border-color: #18d1ff; }
    QCheckBox::indicator:hover { border-color: #18d1ff; }
"""


class StandardReasoningPage(QWidget):
    """Standard Reasoning - select and execute standard flow tasks"""

    model_tag_changed = pyqtSignal(str)

    def __init__(self, communicator=None, agent_executor=None, parent=None,
                 screen_capture=None, touch_executor=None, config=None):
        super().__init__(parent)
        self.communicator = communicator
        self.agent_executor = agent_executor
        self.screen_capture = screen_capture
        self.touch_executor = touch_executor
        self._config = config or {}
        self._selected_model_tag = self._load_model_tag()
        self._flow_checkboxes: Dict[str, QCheckBox] = {}
        self._setup_ui()

    def _get_cache_dir(self) -> str:
        current = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current))))
        cache = os.path.join(root, "cache")
        os.makedirs(cache, exist_ok=True)
        return cache

    def _load_model_tag(self) -> str:
        path = os.path.join(self._get_cache_dir(), "model_tag.json")
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            return data.get("standard_reasoning", "exploration_deep")
        except:
            return "exploration_deep"

    def _save_model_tag(self, tag: str):
        path = os.path.join(self._get_cache_dir(), "model_tag.json")
        try:
            data = {}
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
            data["standard_reasoning"] = tag
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        except:
            pass

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("// STANDARD REASONING")
        title.setStyleSheet(HEADER_STYLE)
        header.addWidget(title)
        header.addStretch()

        header.addWidget(QLabel("Model Tag:"))
        header.itemAt(header.count() - 1).widget().setStyleSheet(INFO_STYLE)
        self._model_tag_combo = QComboBox()
        self._model_tag_combo.setMinimumWidth(180)
        self._model_tag_combo.setStyleSheet(COMBO_STYLE)
        self._model_tag_combo.addItems(["exploration_deep", "exploration_fast", "standard", "premium"])
        self._model_tag_combo.setCurrentText(self._selected_model_tag)
        self._model_tag_combo.currentTextChanged.connect(self._on_model_tag_changed)
        header.addWidget(self._model_tag_combo)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(16)

        # Standard Flow Selection
        flow_card = self._make_card("STANDARD FLOWS")
        flow_layout = QVBoxLayout()
        flow_card.layout().addLayout(flow_layout)

        flow_list = QWidget()
        flow_list_layout = QVBoxLayout(flow_list)
        flow_list_layout.setSpacing(4)
        standard_flows = [
            "daily_quest", "weekly_quest", "resource_collection", "base_management",
            "character_ascension", "weapon_crafting", "event_rewards",
        ]
        for flow_id in standard_flows:
            cb = QCheckBox(flow_id.replace("_", " ").title())
            cb.setStyleSheet(CHECK_STYLE)
            self._flow_checkboxes[flow_id] = cb
            flow_list_layout.addWidget(cb)
        flow_layout.addWidget(flow_list)

        btn_row = QHBoxLayout()
        self._execute_btn = QPushButton("EXECUTE SELECTED")
        self._execute_btn.setFixedSize(160, 32)
        self._execute_btn.setStyleSheet(BTN_ACTIVE)
        self._execute_btn.clicked.connect(self._execute_selected_flows)
        btn_row.addWidget(self._execute_btn)

        self._exec_stop_btn = QPushButton("STOP")
        self._exec_stop_btn.setFixedSize(80, 32)
        self._exec_stop_btn.setStyleSheet(BTN_STOP)
        self._exec_stop_btn.setEnabled(False)
        self._exec_stop_btn.clicked.connect(self._stop_execution)
        btn_row.addWidget(self._exec_stop_btn)
        btn_row.addStretch()
        flow_layout.addLayout(btn_row)

        self._flow_status = QLabel("Ready")
        self._flow_status.setStyleSheet(VAL_STYLE)
        flow_layout.addWidget(self._flow_status)
        scroll_layout.addWidget(flow_card)

        # Execution Log
        log_card = self._make_card("EXECUTION LOG")
        log_layout_inner = QVBoxLayout()
        log_card.layout().addLayout(log_layout_inner)
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(200)
        self._log_text.setStyleSheet("""
            QTextEdit {
                background-color: rgba(10, 10, 15, 0.90);
                color: #e0e0e8;
                border: 1px solid rgba(24, 209, 255, 0.10);
                border-radius: 4px;
                font-size: 11px; font-family: Consolas;
                padding: 8px;
            }
        """)
        log_layout_inner.addWidget(self._log_text)
        scroll_layout.addWidget(log_card)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

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

    def _on_model_tag_changed(self, tag: str):
        self._selected_model_tag = tag
        self._save_model_tag(tag)
        self.model_tag_changed.emit(tag)

    def _execute_selected_flows(self):
        selected = [fid for fid, cb in self._flow_checkboxes.items() if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, "No Flow Selected", "Select at least one standard flow to execute.")
            return
        if not self.agent_executor:
            QMessageBox.warning(self, "Agent Not Ready", "Agent executor not initialized.")
            return
        self._log(f"Executing flows: {', '.join(selected)}")
        self._execute_btn.setEnabled(False)
        self._exec_stop_btn.setEnabled(True)
        self._flow_status.setText("RUNNING")
        for flow_id in selected:
            if not self._exec_stop_btn.isEnabled():
                break
            self._log(f"[{flow_id}] Starting...")
            result = self.agent_executor.send_instruction(f"Execute standard flow: {flow_id}")
            if result.get("status") == "success":
                self._log(f"[{flow_id}] Completed")
            else:
                self._log(f"[{flow_id}] Failed: {result.get('message', 'Unknown')}")
        self._execute_btn.setEnabled(True)
        self._exec_stop_btn.setEnabled(False)
        self._flow_status.setText("All flows completed.")

    def _stop_execution(self):
        self._exec_stop_btn.setEnabled(False)
        self._log("Execution stopped by user.")

    def _log(self, text: str):
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._log_text.append(f"[{ts}] {text}")

    def set_communicator(self, communicator):
        self.communicator = communicator

    def set_agent_executor(self, agent_executor):
        self.agent_executor = agent_executor

    def set_screen_capture(self, screen_capture):
        self.screen_capture = screen_capture

    def set_touch_executor(self, touch_executor):
        self.touch_executor = touch_executor

    def get_model_tag(self) -> str:
        return self._selected_model_tag