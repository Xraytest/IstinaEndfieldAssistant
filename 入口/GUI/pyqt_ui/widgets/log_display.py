"""
日志显示组件
使用 QTextEdit 显示日志，支持不同日志级别的颜色区分和自动滚动
"""

from typing import Optional
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QLabel,
    QComboBox,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QTextCursor, QColor, QFont, QTextCharFormat

# 支持两种导入方式
try:
    from ..theme.theme_manager import ThemeManager
except ImportError:
    import sys
    import os
    # 计算项目根目录路径
    current_file = os.path.abspath(__file__)
    widgets_dir = os.path.dirname(current_file)
    pyqt_ui_dir = os.path.dirname(widgets_dir)
    gui_dir = os.path.dirname(pyqt_ui_dir)
    entry_dir = os.path.dirname(gui_dir)
    istina_dir = os.path.dirname(entry_dir)
    project_root = os.path.dirname(istina_dir)
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if istina_dir not in sys.path:
        sys.path.insert(0, istina_dir)
    
    from IstinaEndfieldAssistant.入口.GUI.pyqt_ui.theme.theme_manager import ThemeManager


class LogDisplayWidget(QWidget):
    """
    日志显示组件
    
    功能：
    - 使用 QTextEdit 显示日志
    - 支持不同日志级别的颜色区分（INFO/WARNING/ERROR）
    - 自动滚动到最新日志
    - 支持日志搜索/过滤
    
    提供 append_log(message, level) 方法
    """
    
    # 日志级别常量
    LEVEL_DEBUG = "DEBUG"
    LEVEL_INFO = "INFO"
    LEVEL_WARNING = "WARNING"
    LEVEL_ERROR = "ERROR"
    LEVEL_CRITICAL = "CRITICAL"
    
    # 自定义信号
    log_cleared = pyqtSignal()
    search_performed = pyqtSignal(str, int)  # 搜索文本, 结果数量
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        max_lines: int = 10000,
        auto_scroll: bool = True,
        show_timestamp: bool = True,
        show_filter: bool = True
    ) -> None:
        """
        初始化日志显示组件
        
        Args:
            parent: 父控件
            max_lines: 最大日志行数（超出后自动清理旧日志）
            auto_scroll: 是否自动滚动到最新日志
            show_timestamp: 是否显示时间戳
            show_filter: 是否显示过滤工具栏
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._max_lines = max_lines
        self._auto_scroll = auto_scroll
        self._show_timestamp = show_timestamp
        self._show_filter = show_filter
        self._current_filter_level: Optional[str] = None
        self._log_count: int = 0
        
        self._setup_ui()
        self._setup_style()
    
    def _setup_ui(self) -> None:
        """设置UI结构"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm'),
            self._theme.get_spacing('padding_sm')
        )
        main_layout.setSpacing(self._theme.get_spacing('sm'))
        
        # 工具栏（过滤和搜索）
        if self._show_filter:
            toolbar_frame = QFrame()
            toolbar_layout = QHBoxLayout(toolbar_frame)
            toolbar_layout.setContentsMargins(0, 0, 0, 0)
            toolbar_layout.setSpacing(self._theme.get_spacing('sm'))
            
            # 日志级别过滤
            filter_label = QLabel("级别:")
            filter_label.setProperty("variant", "secondary")
            toolbar_layout.addWidget(filter_label)
            
            self._level_combo = QComboBox()
            self._level_combo.addItem("全部", None)
            self._level_combo.addItem("DEBUG", self.LEVEL_DEBUG)
            self._level_combo.addItem("INFO", self.LEVEL_INFO)
            self._level_combo.addItem("WARNING", self.LEVEL_WARNING)
            self._level_combo.addItem("ERROR", self.LEVEL_ERROR)
            self._level_combo.addItem("CRITICAL", self.LEVEL_CRITICAL)
            self._level_combo.setFixedWidth(100)
            self._level_combo.currentIndexChanged.connect(self._on_level_changed)
            toolbar_layout.addWidget(self._level_combo)
            
            toolbar_layout.addSpacing(self._theme.get_spacing('lg'))
            
            # 搜索框
            search_label = QLabel("搜索:")
            search_label.setProperty("variant", "secondary")
            toolbar_layout.addWidget(search_label)
            
            self._search_input = QLineEdit()
            self._search_input.setPlaceholderText("输入搜索关键词...")
            self._search_input.setFixedWidth(200)
            self._search_input.returnPressed.connect(self._on_search)
            toolbar_layout.addWidget(self._search_input)
            
            search_btn = QPushButton("搜索")
            search_btn.setProperty("variant", "secondary")
            search_btn.setFixedHeight(28)
            search_btn.clicked.connect(self._on_search)
            toolbar_layout.addWidget(search_btn)
            
            toolbar_layout.addStretch()
            
            # 清除按钮
            clear_btn = QPushButton("清除")
            clear_btn.setProperty("variant", "danger")
            clear_btn.setFixedHeight(28)
            clear_btn.clicked.connect(self.clear_logs)
            toolbar_layout.addWidget(clear_btn)
            
            main_layout.addWidget(toolbar_frame)
        
        # 日志计数显示
        count_frame = QFrame()
        count_layout = QHBoxLayout(count_frame)
        count_layout.setContentsMargins(0, 0, 0, 0)
        
        self._count_label = QLabel("日志: 0 行")
        self._count_label.setProperty("variant", "muted")
        count_layout.addWidget(self._count_label)
        
        count_layout.addStretch()
        main_layout.addWidget(count_frame)
        
        # 日志显示区域
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._log_text.setMinimumHeight(200)
        main_layout.addWidget(self._log_text, 1)
    
    def _setup_style(self) -> None:
        """设置样式"""
        c = self._theme.colors
        r = self._theme.get_corner_radius('sm')
        
        # 日志文本区域样式
        self._log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c['log_bg']};
                color: {c['text_primary']};
                border: 1px solid {c['border_color']};
                border-radius: {r}px;
                padding: {self._theme.get_spacing('padding_sm')}px;
                font-family: '{self._theme.get_mono_font_family()}';
                font-size: {self._theme.get_font_size('body_small')}px;
            }}
        """)
    
    def _get_level_color(self, level: str) -> str:
        """获取日志级别对应的颜色"""
        colors = {
            self.LEVEL_DEBUG: self._theme.get_color('text_muted'),
            self.LEVEL_INFO: self._theme.get_color('info'),
            self.LEVEL_WARNING: self._theme.get_color('warning'),
            self.LEVEL_ERROR: self._theme.get_color('danger'),
            self.LEVEL_CRITICAL: self._theme.get_color('danger_light'),
        }
        return colors.get(level, self._theme.get_color('text_primary'))
    
    def _get_level_prefix(self, level: str) -> str:
        """获取日志级别前缀"""
        prefixes = {
            self.LEVEL_DEBUG: "[D]",
            self.LEVEL_INFO: "[I]",
            self.LEVEL_WARNING: "[W]",
            self.LEVEL_ERROR: "[E]",
            self.LEVEL_CRITICAL: "[C]",
        }
        return prefixes.get(level, "[?]")
    
    def _on_level_changed(self, index: int) -> None:
        """日志级别过滤改变"""
        level_data = self._level_combo.itemData(index)
        self._current_filter_level = level_data
        
        # 重新应用过滤（这里简化处理，实际可能需要存储原始日志）
        # 暂时不实现历史日志过滤，只过滤新日志
    
    def _on_search(self) -> None:
        """搜索日志"""
        search_text = self._search_input.text().strip()
        if not search_text:
            return
        
        # 使用 QTextEdit 的查找功能
        cursor = self._log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        
        found_count = 0
        self._log_text.moveCursor(QTextCursor.MoveOperation.Start)
        
        # 查找所有匹配
        while self._log_text.find(search_text):
            found_count += 1
        
        # 高亮第一个匹配
        self._log_text.moveCursor(QTextCursor.MoveOperation.Start)
        self._log_text.find(search_text)
        
        self.search_performed.emit(search_text, found_count)
    
    def _trim_old_logs(self) -> None:
        """清理超出限制的旧日志"""
        if self._log_count <= self._max_lines:
            return
        
        # 计算需要删除的行数
        lines_to_remove = self._log_count - self._max_lines
        
        # 移动光标到文档开头
        cursor = self._log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        
        # 选中并删除多余的行
        for _ in range(lines_to_remove):
            cursor.movePosition(
                QTextCursor.MoveOperation.Down,
                QTextCursor.MoveMode.KeepAnchor
            )
        cursor.removeSelectedText()
        
        self._log_count = self._max_lines
    
    def _update_count_label(self) -> None:
        """更新日志计数显示"""
        self._count_label.setText(f"日志: {self._log_count} 行")
    
    # === 公共方法 ===
    
    def append_log(
        self,
        message: str,
        level: str = LEVEL_INFO,
        source: Optional[str] = None
    ) -> None:
        """
        添加日志
        
        Args:
            message: 日志内容
            level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
            source: 日志来源（可选）
        """
        # 如果设置了级别过滤，且当前级别不符合，则跳过
        if self._current_filter_level and level != self._current_filter_level:
            return
        
        # 构建日志文本
        timestamp = datetime.now().strftime("%H:%M:%S") if self._show_timestamp else ""
        level_prefix = self._get_level_prefix(level)
        source_prefix = f"[{source}]" if source else ""
        
        log_text = f"{timestamp} {level_prefix}{source_prefix} {message}"
        
        # 获取颜色
        color = self._get_level_color(level)
        
        # 创建文本格式
        format = QTextCharFormat()
        format.setForeground(QColor(color))
        
        # 获取文本光标
        cursor = self._log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # 如果不是第一行，添加换行
        if self._log_count > 0:
            cursor.insertText("\n")
        
        # 应用格式并插入文本
        cursor.setCharFormat(format)
        cursor.insertText(log_text)
        
        self._log_count += 1
        
        # 自动滚动到底部
        if self._auto_scroll:
            self._log_text.moveCursor(QTextCursor.MoveOperation.End)
            self._log_text.ensureCursorVisible()
        
        # 清理旧日志
        self._trim_old_logs()
        
        # 更新计数
        self._update_count_label()
    
    def append_debug(self, message: str, source: Optional[str] = None) -> None:
        """添加 DEBUG 级别日志"""
        self.append_log(message, self.LEVEL_DEBUG, source)
    
    def append_info(self, message: str, source: Optional[str] = None) -> None:
        """添加 INFO 级别日志"""
        self.append_log(message, self.LEVEL_INFO, source)
    
    def append_warning(self, message: str, source: Optional[str] = None) -> None:
        """添加 WARNING 级别日志"""
        self.append_log(message, self.LEVEL_WARNING, source)
    
    def append_error(self, message: str, source: Optional[str] = None) -> None:
        """添加 ERROR 级别日志"""
        self.append_log(message, self.LEVEL_ERROR, source)
    
    def append_critical(self, message: str, source: Optional[str] = None) -> None:
        """添加 CRITICAL 级别日志"""
        self.append_log(message, self.LEVEL_CRITICAL, source)
    
    def clear_logs(self) -> None:
        """清除所有日志"""
        self._log_text.clear()
        self._log_count = 0
        self._update_count_label()
        self.log_cleared.emit()
    
    def get_log_text(self) -> str:
        """获取所有日志文本"""
        return self._log_text.toPlainText()
    
    def set_max_lines(self, max_lines: int) -> None:
        """设置最大日志行数"""
        self._max_lines = max_lines
        self._trim_old_logs()
    
    def set_auto_scroll(self, auto_scroll: bool) -> None:
        """设置是否自动滚动"""
        self._auto_scroll = auto_scroll
    
    def scroll_to_bottom(self) -> None:
        """滚动到底部"""
        self._log_text.moveCursor(QTextCursor.MoveOperation.End)
        self._log_text.ensureCursorVisible()
    
    def scroll_to_top(self) -> None:
        """滚动到顶部"""
        self._log_text.moveCursor(QTextCursor.MoveOperation.Start)
        self._log_text.ensureCursorVisible()
    
    def get_log_count(self) -> int:
        """获取日志行数"""
        return self._log_count
    
    # === 重写事件处理 ===
    
    def sizeHint(self):
        """建议大小"""
        return self._theme.get_spacing('lg') * 20  # 约 240x200


class SimpleLogDisplay(QWidget):
    """
    简化版日志显示组件
    
    仅包含日志显示区域，无过滤和搜索功能
    """
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        max_lines: int = 10000,
        auto_scroll: bool = True,
        show_timestamp: bool = True
    ) -> None:
        """
        初始化简化版日志显示
        
        Args:
            parent: 父控件
            max_lines: 最大日志行数
            auto_scroll: 是否自动滚动
            show_timestamp: 是否显示时间戳
        """
        super().__init__(parent)
        self._theme = ThemeManager.get_instance()
        self._max_lines = max_lines
        self._auto_scroll = auto_scroll
        self._show_timestamp = show_timestamp
        self._log_count: int = 0
        
        self._setup_ui()
        self._setup_style()
    
    def _setup_ui(self) -> None:
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self._log_text)
    
    def _setup_style(self) -> None:
        """设置样式"""
        c = self._theme.colors
        r = self._theme.get_corner_radius('sm')
        
        self._log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c['log_bg']};
                color: {c['text_primary']};
                border: 1px solid {c['border_color']};
                border-radius: {r}px;
                padding: {self._theme.get_spacing('padding_sm')}px;
                font-family: '{self._theme.get_mono_font_family()}';
                font-size: {self._theme.get_font_size('body_small')}px;
            }}
        """)
    
    def append_log(
        self,
        message: str,
        level: str = LogDisplayWidget.LEVEL_INFO,
        source: Optional[str] = None
    ) -> None:
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S") if self._show_timestamp else ""
        
        level_prefixes = {
            LogDisplayWidget.LEVEL_DEBUG: "[D]",
            LogDisplayWidget.LEVEL_INFO: "[I]",
            LogDisplayWidget.LEVEL_WARNING: "[W]",
            LogDisplayWidget.LEVEL_ERROR: "[E]",
            LogDisplayWidget.LEVEL_CRITICAL: "[C]",
        }
        level_prefix = level_prefixes.get(level, "[?]")
        source_prefix = f"[{source}]" if source else ""
        
        log_text = f"{timestamp} {level_prefix}{source_prefix} {message}"
        
        color_map = {
            LogDisplayWidget.LEVEL_DEBUG: self._theme.get_color('text_muted'),
            LogDisplayWidget.LEVEL_INFO: self._theme.get_color('info'),
            LogDisplayWidget.LEVEL_WARNING: self._theme.get_color('warning'),
            LogDisplayWidget.LEVEL_ERROR: self._theme.get_color('danger'),
            LogDisplayWidget.LEVEL_CRITICAL: self._theme.get_color('danger_light'),
        }
        color = color_map.get(level, self._theme.get_color('text_primary'))
        
        cursor = self._log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        if self._log_count > 0:
            cursor.insertText("\n")
        
        format = QTextCharFormat()
        format.setForeground(QColor(color))
        cursor.setCharFormat(format)
        cursor.insertText(log_text)
        
        self._log_count += 1
        
        if self._auto_scroll:
            self._log_text.moveCursor(QTextCursor.MoveOperation.End)
            self._log_text.ensureCursorVisible()
        
        # 清理旧日志
        if self._log_count > self._max_lines:
            lines_to_remove = self._log_count - self._max_lines
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(lines_to_remove):
                cursor.movePosition(
                    QTextCursor.MoveOperation.Down,
                    QTextCursor.MoveMode.KeepAnchor
                )
            cursor.removeSelectedText()
            self._log_count = self._max_lines
    
    def clear_logs(self) -> None:
        """清除日志"""
        self._log_text.clear()
        self._log_count = 0
    
    def get_log_text(self) -> str:
        """获取日志文本"""
        return self._log_text.toPlainText()