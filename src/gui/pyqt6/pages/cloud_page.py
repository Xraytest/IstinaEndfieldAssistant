"""服务端模型标签管理页面 - Endfield 终端风格
从服务端获取可用模型标签，配置各模式使用的模型标签"""

import os
import json
from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QScrollArea, QTextEdit, QMessageBox,
    QComboBox, QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from core.foundation.utils.paths import get_project_root

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
    QComboBox::down-arrow {
        image: none; border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid rgba(24, 209, 255, 0.50);
        width: 0; height: 0;
    }
    QComboBox QAbstractItemView {
        background-color: rgba(12, 12, 20, 0.95);
        color: #e8e8ee;
        border: 1px solid rgba(24, 209, 255, 0.15);
        selection-background-color: rgba(24, 209, 255, 0.15);
    }
"""


class CloudPage(QWidget):
    """服务端模型标签管理页面"""

    config_changed = pyqtSignal(dict)

    def __init__(self, communicator=None, agent_executor=None, parent=None, config=None):
        super().__init__(parent)
        self.communicator = communicator
        self.agent_executor = agent_executor
        self._config = config or {}
        self._model_tags: List[Dict[str, Any]] = []
        self._sync_status = "unknown"

        self._setup_ui()
        QTimer.singleShot(300, self._fetch_model_tags)

    def _get_cache_dir(self) -> str:
        root = get_project_root()
        cache = os.path.join(root, "cache")
        os.makedirs(cache, exist_ok=True)
        return cache

    def _load_tag_config(self) -> dict:
        path = os.path.join(self._get_cache_dir(), "model_tag.json")
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_tag_config(self, data: dict):
        path = os.path.join(self._get_cache_dir(), "model_tag.json")
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        header = QHBoxLayout()
        title = QLabel("// 云端模型配置")
        title.setStyleSheet(HEADER_STYLE)
        header.addWidget(title)
        header.addStretch()

        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.setFixedSize(100, 32)
        self._refresh_btn.setStyleSheet(BTN_DEFAULT)
        self._refresh_btn.clicked.connect(self._fetch_model_tags)
        header.addWidget(self._refresh_btn)

        self._apply_btn = QPushButton("应用")
        self._apply_btn.setFixedSize(100, 32)
        self._apply_btn.setStyleSheet(BTN_ACTIVE)
        self._apply_btn.clicked.connect(self._apply_config)
        header.addWidget(self._apply_btn)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(16)

        # ======== 1. 服务端可用模型标签 ========
        server_card = self._make_card("服务端可用模型标签")
        self._server_layout = QVBoxLayout()
        server_card.layout().addLayout(self._server_layout)
        self._server_status = QLabel("加载中...")
        self._server_status.setStyleSheet(VAL_STYLE)
        self._server_layout.addWidget(self._server_status)
        scroll_layout.addWidget(server_card)

        # ======== 2. 模式标签配置 ========
        config_card = self._make_card("模式标签配置")
        self._config_layout = QVBoxLayout()
        config_card.layout().addLayout(self._config_layout)

        # 标准推理
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("标准推理:"))
        row1.itemAt(0).widget().setStyleSheet(INFO_STYLE)
        self._std_tag_combo = QComboBox()
        self._std_tag_combo.setMinimumWidth(200)
        self._std_tag_combo.setStyleSheet(COMBO_STYLE)
        row1.addWidget(self._std_tag_combo)
        row1.addStretch()
        self._config_layout.addLayout(row1)

        # PRTS 全智能
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("PRTS 全智能:"))
        row2.itemAt(0).widget().setStyleSheet(INFO_STYLE)
        self._prts_tag_combo = QComboBox()
        self._prts_tag_combo.setMinimumWidth(200)
        self._prts_tag_combo.setStyleSheet(COMBO_STYLE)
        row2.addWidget(self._prts_tag_combo)
        row2.addStretch()
        self._config_layout.addLayout(row2)

        scroll_layout.addWidget(config_card)

        # ======== 3. 状态信息 ========
        status_card = self._make_card("同步状态")
        self._status_layout = QVBoxLayout()
        status_card.layout().addLayout(self._status_layout)
        self._sync_label = QLabel("未同步")
        self._sync_label.setStyleSheet(VAL_STYLE)
        self._status_layout.addWidget(self._sync_label)
        scroll_layout.addWidget(status_card)

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

    def _fetch_model_tags(self):
        """从服务端获取可用模型标签"""
        if not self.communicator:
            self._server_status.setText("通信器未初始化")
            self._server_status.setStyleSheet(RED_STYLE)
            self._sync_label.setText("无法连接服务端")
            self._sync_label.setStyleSheet(RED_STYLE)
            return

        session_id = getattr(getattr(self, 'agent_executor', None), 'session_id', None) or ''
        try:
            response = self.communicator.get_available_models(session_id)
        except Exception as e:
            self._server_status.setText(f"获取失败: {e}")
            self._server_status.setStyleSheet(RED_STYLE)
            self._sync_label.setText("获取失败")
            self._sync_label.setStyleSheet(RED_STYLE)
            return

        if response and response.get('status') == 'success':
            models = response.get('models', [])
            self._model_tags = models
            self._update_server_display(models)
            self._update_combo_boxes(models)
            self._sync_label.setText("已从服务端获取最新模型标签")
            self._sync_label.setStyleSheet(GREEN_STYLE)
        else:
            error_msg = response.get('message', '无响应') if response else '无响应'
            self._server_status.setText(f"获取失败: {error_msg}")
            self._server_status.setStyleSheet(RED_STYLE)

    def _update_server_display(self, models: List[Dict[str, Any]]):
        """更新服务端模型标签显示区域"""
        self._clear_layout(self._server_layout)
        if not models:
            status = QLabel("服务端未返回可用模型标签")
            status.setStyleSheet(VAL_STYLE)
            self._server_layout.addWidget(status)
            return

        for m in models:
            name = m.get('name', '?')
            tier = m.get('tier', '?')
            provider_count = m.get('provider_count', 0)
            row = QHBoxLayout()
            tag_label = QLabel(f"> {name}")
            tag_label.setStyleSheet(BLUE_STYLE)
            row.addWidget(tag_label)
            info_label = QLabel(f"tier={tier}  providers={provider_count}")
            info_label.setStyleSheet(INFO_STYLE)
            row.addWidget(info_label)
            row.addStretch()
            self._server_layout.addLayout(row)

    def _update_combo_boxes(self, models: List[Dict[str, Any]]):
        """更新下拉框内容"""
        names = [m.get('name', '') for m in models if m.get('name')]
        if not names:
            names = ["exploration_deep", "exploration_fast", "standard", "premium"]

        tag_config = self._load_tag_config()

        # 标准推理组合框
        current_std = tag_config.get("standard_reasoning", names[0] if names else "exploration_deep")
        self._std_tag_combo.clear()
        self._std_tag_combo.addItems(names)
        if current_std in names:
            self._std_tag_combo.setCurrentText(current_std)

        # PRTS 全智能组合框
        current_prts = tag_config.get("prts_full_intelligence", names[0] if names else "exploration_deep")
        self._prts_tag_combo.clear()
        self._prts_tag_combo.addItems(names)
        if current_prts in names:
            self._prts_tag_combo.setCurrentText(current_prts)

    def _apply_config(self):
        """应用并保存配置"""
        std_tag = self._std_tag_combo.currentText()
        prts_tag = self._prts_tag_combo.currentText()

        data = {
            "standard_reasoning": std_tag,
            "prts_full_intelligence": prts_tag,
        }
        self._save_tag_config(data)

        # 通知 agent_executor
        if self.agent_executor:
            self.agent_executor.model_tag = std_tag

        self._sync_label.setText(f"配置已保存 | 标准推理: {std_tag} | PRTS: {prts_tag}")
        self._sync_label.setStyleSheet(BLUE_STYLE)
        self.config_changed.emit(data)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def set_communicator(self, communicator):
        self.communicator = communicator

    def set_agent_executor(self, agent_executor):
        self.agent_executor = agent_executor