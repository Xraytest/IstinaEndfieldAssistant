"""
Material Design 3 主题管理器
基于原有 theme.py 的设计规范，使用 QSS 实现 PyQt6 主题系统
"""

from typing import Dict, Optional, Any
from PyQt6.QtWidgets import QApplication


# ============================================================================
# 颜色定义 - Material Design 3 颜色体系
# ============================================================================

COLORS: Dict[str, str] = {
    # === 主色调系统 (Primary) ===
    'primary': '#4361ee',
    'primary_hover': '#3a56d4',
    'primary_light': '#6b83f2',
    'primary_lighter': '#94a5f5',
    'primary_light_container': '#e0e7ff',
    'primary_dark': '#2d4bcc',
    'primary_darker': '#2237a0',
    'primary_dark_container': '#1a2768',
    'on_primary': '#ffffff',
    'on_primary_container': '#1a2768',

    # === 次级色系统 (Secondary) ===
    'secondary': '#7209b7',
    'secondary_light': '#9b3fd4',
    'secondary_dark': '#5a0792',
    'secondary_container': '#f3e5f9',
    'on_secondary': '#ffffff',
    'on_secondary_container': '#3a0055',

    # === 第三色系统 (Tertiary) ===
    'tertiary': '#00bfa5',
    'tertiary_light': '#5df2dc',
    'tertiary_dark': '#008c7a',
    'tertiary_container': '#e0f7fa',
    'on_tertiary': '#ffffff',
    'on_tertiary_container': '#00201c',

    # === 语义颜色 ===
    'success': '#2ecc71',
    'success_light': '#58d68d',
    'success_dark': '#27ae60',
    'success_container': '#e8f8f0',
    'on_success': '#ffffff',

    'warning': '#f39c12',
    'warning_light': '#f5b041',
    'warning_dark': '#d68910',
    'warning_container': '#fef9e7',
    'on_warning': '#1a1c1b',

    'danger': '#e74c3c',
    'danger_light': '#ec7063',
    'danger_dark': '#c0392b',
    'danger_container': '#fdedec',
    'on_danger': '#ffffff',

    'info': '#3498db',
    'info_light': '#5dade2',
    'info_dark': '#2980b9',
    'info_container': '#ebf5fb',
    'on_info': '#ffffff',

    # === 背景色系统 (深色主题 Surface) ===
    'bg_primary': '#1c1c1e',
    'bg_secondary': '#2c2c2e',
    'bg_tertiary': '#3a3a3c',
    'bg_card': '#2c2c2e',
    'bg_elevated': '#3a3a3c',
    'surface': '#1c1c1e',
    'surface_dim': '#141416',
    'surface_bright': '#3a3a3c',
    'surface_container_lowest': '#0f0f11',
    'surface_container_low': '#1c1c1e',
    'surface_container': '#2c2c2e',
    'surface_container_high': '#363638',
    'surface_container_highest': '#3a3a3c',
    'on_surface': '#ffffff',
    'on_surface_variant': '#b0b0b0',

    # === 文字颜色 ===
    'text_primary': '#ffffff',
    'text_secondary': '#b0b0b0',
    'text_tertiary': '#8a8a8a',
    'text_muted': '#666666',
    'text_disabled': '#4a4a4a',

    # === 边框和分割线 ===
    'border_color': '#48484a',
    'border_light': '#636366',
    'divider_color': '#38383a',
    'outline': '#636366',
    'outline_variant': '#48484a',

    # === 特殊用途 ===
    'canvas_bg': '#141416',
    'log_bg': '#141416',
    'selection_bg': '#4361ee',
    'hover_bg': '#3a3a3c',
    'inverse_surface': '#e0e0e0',
    'inverse_on_surface': '#1c1c1e',
    'inverse_primary': '#6b83f2',

    # === 阴影颜色 ===
    'shadow': 'rgba(0, 0, 0, 0.3)',
    'shadow_light': 'rgba(0, 0, 0, 0.15)',
}

# 用户层级颜色
TIER_COLORS: Dict[str, str] = {
    'free': COLORS['text_muted'],
    'prime': COLORS['success'],
    'plus': COLORS['warning'],
    'pro': COLORS['danger'],
}


# ============================================================================
# 字体定义 - Material Design 3 排版规范（优化紧凑版）
# ============================================================================

FONTS: Dict[str, str] = {
    'family': 'Microsoft YaHei UI',
    'family_fallback': 'Segoe UI',
    'family_mono': 'Consolas',
    'family_display': 'Microsoft YaHei UI',
}

FONT_SIZES: Dict[str, int] = {
    'display_large': 45,
    'display_medium': 36,
    'display_small': 28,
    'headline_large': 26,
    'headline_medium': 22,
    'headline_small': 18,
    'title_large': 16,
    'title_medium': 13,
    'title_small': 12,
    'body_large': 13,
    'body_medium': 12,
    'body_small': 11,
    'label_large': 12,
    'label_medium': 11,
    'label_small': 10,
    # 兼容旧系统
    'size_small': 11,
    'size_base': 12,
    'size_medium': 12,
    'size_large': 13,
    'size_xlarge': 16,
    'size_title': 18,
    'size_header': 22,
}

FONT_WEIGHTS: Dict[str, int] = {
    'thin': 100,
    'extra_light': 200,
    'light': 300,
    'regular': 400,
    'medium': 500,
    'semi_bold': 600,
    'bold': 700,
    'extra_bold': 800,
    'black': 900,
}


# ============================================================================
# 间距定义 - Material Design 3 间距系统（紧凑版）
# ============================================================================

SPACING_UNIT = 4

SPACING: Dict[str, int] = {
    'none': 0,
    'xxxs': 1,
    'xxs': 2,
    'xs': 3,
    'sm': 6,
    'md': 8,
    'lg': 12,
    'xl': 16,
    'xxl': 20,
    'xxxl': 24,
    'component': 6,
    'section': 12,
    'container': 16,
    'padding_xs': 3,
    'padding_sm': 6,
    'padding_md': 8,
    'padding_lg': 12,
    'padding_xl': 16,
    'margin_xs': 3,
    'margin_sm': 6,
    'margin_md': 8,
    'margin_lg': 12,
    'margin_xl': 16,
    'icon_text': 6,
    'button_padding_h': 16,
    'button_padding_v': 6,
    'input_padding_h': 10,
    'input_padding_v': 6,
    'card_padding': 12,
    'list_item_padding': 8,
    'dialog_padding': 16,
}


# ============================================================================
# 圆角定义 - Material Design 3 形状系统
# ============================================================================

CORNER_RADIUS: Dict[str, int] = {
    'none': 0,
    'xs': 4,
    'sm': 8,
    'md': 12,
    'lg': 16,
    'xl': 20,
    'xxl': 28,
    'full': 9999,
    'button': 20,
    'button_sm': 8,
    'button_lg': 24,
    'card': 12,
    'card_lg': 16,
    'input': 4,
    'input_outlined': 4,
    'input_filled': 8,
    'dialog': 28,
    'chip': 8,
    'badge': 9999,
    'fab': 16,
    'menu': 8,
    'tooltip': 4,
    'snackbar': 8,
}


# ============================================================================
# 阴影定义 - Material Design 3 阴影系统
# ============================================================================

ELEVATION: Dict[str, int] = {
    'level_0': 0,
    'level_1': 1,
    'level_2': 2,
    'level_3': 3,
    'level_4': 4,
    'level_5': 5,
    'card': 1,
    'card_hover': 2,
    'button': 0,
    'button_floating': 3,
    'menu': 2,
    'dialog': 3,
    'drawer': 4,
    'modal': 5,
}


# ============================================================================
# 动画时间定义
# ============================================================================

DURATION: Dict[str, int] = {
    'instant': 0,
    'fast': 100,
    'normal': 200,
    'slow': 300,
    'slower': 400,
    'hover': 150,
    'press': 100,
    'fade': 200,
    'slide': 300,
    'expand': 250,
    'dialog': 280,
    'snackbar': 250,
}


# ============================================================================
# 动画配置
# ============================================================================

ANIMATION_CONFIG: Dict[str, Any] = {
    'enabled': True,
    'duration_fast': 150,
    'duration_normal': 250,
    'duration_slow': 400,
    'easing_curve': 'OutCubic',
    'fade_enabled': True,
    'slide_enabled': True,
    'scale_enabled': True,
    'hover_enabled': True,
}


class ThemeManager:
    """
    Material Design 3 主题管理器
    
    提供颜色、字体、间距等设计规范常量，
    以及 QSS 样式表生成和应用功能。
    新增动画配置支持。
    """
    
    _instance: Optional['ThemeManager'] = None
    
    def __new__(cls) -> 'ThemeManager':
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        """初始化主题管理器"""
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True
        self._colors = COLORS
        self._fonts = FONTS
        self._font_sizes = FONT_SIZES
        self._font_weights = FONT_WEIGHTS
        self._spacing = SPACING
        self._corner_radius = CORNER_RADIUS
        self._elevation = ELEVATION
        self._duration = DURATION
        self._animation_config = ANIMATION_CONFIG.copy()
    
    # === 属性访问器 ===
    
    @property
    def colors(self) -> Dict[str, str]:
        """获取颜色字典"""
        return self._colors
    
    @property
    def fonts(self) -> Dict[str, str]:
        """获取字体配置"""
        return self._fonts
    
    @property
    def font_sizes(self) -> Dict[str, int]:
        """获取字号配置"""
        return self._font_sizes
    
    @property
    def font_weights(self) -> Dict[str, int]:
        """获取字重配置"""
        return self._font_weights
    
    @property
    def spacing(self) -> Dict[str, int]:
        """获取间距配置"""
        return self._spacing
    
    @property
    def corner_radius(self) -> Dict[str, int]:
        """获取圆角配置"""
        return self._corner_radius
    
    @property
    def elevation(self) -> Dict[str, int]:
        """获取阴影层级配置"""
        return self._elevation
    
    @property
    def duration(self) -> Dict[str, int]:
        """获取动画时长配置"""
        return self._duration
    
    @property
    def animation_config(self) -> Dict[str, Any]:
        """获取动画配置"""
        return self._animation_config
    
    # === 动画配置方法 ===
    
    def is_animation_enabled(self) -> bool:
        """检查动画是否启用"""
        return self._animation_config.get('enabled', True)
    
    def set_animation_enabled(self, enabled: bool) -> None:
        """设置动画启用状态"""
        self._animation_config['enabled'] = enabled
    
    def get_animation_duration(self, key: str = 'normal') -> int:
        """获取动画时长"""
        duration_key = f'duration_{key}'
        return self._animation_config.get(duration_key, self._duration.get(key, 250))
    
    def set_animation_duration(self, key: str, duration: int) -> None:
        """设置动画时长"""
        self._animation_config[f'duration_{key}'] = duration
    
    # === 便捷访问方法 ===
    
    def get_color(self, key: str) -> str:
        """获取指定颜色"""
        return self._colors.get(key, '#000000')
    
    def get_font_size(self, key: str) -> int:
        """获取指定字号"""
        return self._font_sizes.get(key, 12)
    
    def get_spacing(self, key: str) -> int:
        """获取指定间距"""
        return self._spacing.get(key, 0)
    
    def get_corner_radius(self, key: str) -> int:
        """获取指定圆角"""
        return self._corner_radius.get(key, 0)
    
    def get_font_family(self) -> str:
        """获取主字体族"""
        return self._fonts['family']
    
    def get_mono_font_family(self) -> str:
        """获取等宽字体族"""
        return self._fonts['family_mono']
    
    # === QSS 样式生成 ===
    
    def get_stylesheet(self) -> str:
        """
        生成完整的 QSS 样式表
        
        Returns:
            str: Material Design 3 风格的 QSS 样式表
        """
        try:
            return self._build_stylesheet()
        except Exception as e:
            # 如果构建样式表失败，记录错误并返回空样式表
            import logging
            logging.getLogger(__name__).error(f"构建样式表失败: {e}")
            return ""
    
    def _build_stylesheet(self) -> str:
        """构建完整的 QSS 样式表"""
        c = self._colors
        f = self._fonts
        fs = self._font_sizes
        s = self._spacing
        r = self._corner_radius
        
        stylesheet = """
/* ============================================================================
 * Material Design 3 主题 - PyQt6 QSS 样式表
 * ============================================================================ */

/* === 全局样式 === */
QWidget {
    font-family: '%s';
    font-size: %dpx;
    color: %s;
    background-color: %s;
}

QMainWindow {
    background-color: %s;
}

/* === 按钮样式 === */
QPushButton {
    background-color: %s;
    color: %s;
    border: none;
    border-radius: %dpx;
    padding: %dpx %dpx;
    font-size: %dpx;
    font-weight: %d;
    min-height: 32px;
}

QPushButton:hover {
    background-color: %s;
}

QPushButton:pressed {
    background-color: %s;
}

QPushButton:disabled {
    background-color: %s;
    color: %s;
}

/* 主要按钮 */
QPushButton[variant="primary"] {
    background-color: %s;
    color: %s;
}

QPushButton[variant="primary"]:hover {
    background-color: %s;
}

QPushButton[variant="primary"]:pressed {
    background-color: %s;
}

/* 次级按钮 */
QPushButton[variant="secondary"] {
    background-color: transparent;
    color: %s;
    border: 1px solid %s;
}

QPushButton[variant="secondary"]:hover {
    background-color: rgba(67, 97, 238, 0.08);
}

/* 文本按钮 */
QPushButton[variant="text"] {
    background-color: transparent;
    color: %s;
    border: none;
}

QPushButton[variant="text"]:hover {
    background-color: rgba(67, 97, 238, 0.08);
}

/* 危险按钮 */
QPushButton[variant="danger"] {
    background-color: %s;
    color: %s;
}

QPushButton[variant="danger"]:hover {
    background-color: %s;
}

/* === 标签样式 === */
QLabel {
    color: %s;
    background-color: transparent;
    border: none;
}

QLabel[variant="title"] {
    font-size: %dpx;
    font-weight: %d;
    color: %s;
}

QLabel[variant="secondary"] {
    color: %s;
}

QLabel[variant="muted"] {
    color: %s;
}

/* === 输入框样式 === */
QLineEdit {
    background-color: %s;
    color: %s;
    border: 1px solid %s;
    border-radius: %dpx;
    padding: %dpx %dpx;
    font-size: %dpx;
    min-height: 32px;
}

QLineEdit:hover {
    border-color: %s;
}

QLineEdit:focus {
    border-color: %s;
    border-width: 2px;
}

QLineEdit:disabled {
    background-color: %s;
    color: %s;
}

/* === 下拉框样式 === */
QComboBox {
    background-color: %s;
    color: %s;
    border: 1px solid %s;
    border-radius: %dpx;
    padding: %dpx %dpx;
    font-size: %dpx;
    min-height: 32px;
}

QComboBox:hover {
    border-color: %s;
}

QComboBox:focus {
    border-color: %s;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
    padding-right: 8px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid %s;
    width: 0;
    height: 0;
}

QComboBox QAbstractItemView {
    background-color: %s;
    color: %s;
    border: 1px solid %s;
    border-radius: %dpx;
    selection-background-color: %s;
    selection-color: %s;
    padding: 4px;
}

/* === 数值调节框样式 === */
QSpinBox {
    background-color: %s;
    color: %s;
    border: 1px solid %s;
    border-radius: %dpx;
    padding: %dpx %dpx;
    font-size: %dpx;
    min-height: 32px;
}

QSpinBox:hover {
    border-color: %s;
}

QSpinBox:focus {
    border-color: %s;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: %s;
    border: none;
    width: 20px;
    subcontrol-position: right;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: %s;
}

QSpinBox::up-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 6px solid %s;
    width: 0;
    height: 0;
}

QSpinBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid %s;
    width: 0;
    height: 0;
}

/* === 复选框样式 === */
QCheckBox {
    color: %s;
    spacing: %dpx;
    font-size: %dpx;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid %s;
    background-color: transparent;
}

QCheckBox::indicator:hover {
    border-color: %s;
}

QCheckBox::indicator:checked {
    background-color: %s;
    border-color: %s;
}

QCheckBox::indicator:disabled {
    border-color: %s;
    background-color: %s;
}

/* === 标签页样式 === */
QTabWidget::pane {
    background-color: %s;
    border: 1px solid %s;
    border-radius: %dpx;
    top: -1px;
}

QTabBar::tab {
    background-color: %s;
    color: %s;
    border: none;
    border-bottom: 2px solid transparent;
    padding: %dpx %dpx;
    font-size: %dpx;
    min-width: 80px;
}

QTabBar::tab:hover {
    background-color: %s;
}

QTabBar::tab:selected {
    color: %s;
    border-bottom: 2px solid %s;
}

/* === 分割器样式 === */
QSplitter::handle {
    background-color: %s;
}

QSplitter::handle:horizontal {
    width: 1px;
}

QSplitter::handle:vertical {
    height: 1px;
}

/* === 滚动条样式 === */
QScrollBar:vertical {
    background-color: %s;
    width: 8px;
    border-radius: 4px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: %s;
    border-radius: 4px;
    min-height: 32px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: %s;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background-color: transparent;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background-color: transparent;
}

QScrollBar:horizontal {
    background-color: %s;
    height: 8px;
    border-radius: 4px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: %s;
    border-radius: 4px;
    min-width: 32px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: %s;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
    background-color: transparent;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background-color: transparent;
}

/* === 列表视图样式 === */
QListWidget {
    background-color: %s;
    color: %s;
    border: 1px solid %s;
    border-radius: %dpx;
    padding: %dpx;
    font-size: %dpx;
}

QListWidget::item {
    background-color: transparent;
    padding: %dpx;
    border-radius: %dpx;
}

QListWidget::item:hover {
    background-color: %s;
}

QListWidget::item:selected {
    background-color: %s;
    color: %s;
}

QListWidget::item:selected:!active {
    background-color: rgba(67, 97, 238, 0.12);
}

/* === 表格视图样式 === */
QTableWidget, QTableView {
    background-color: %s;
    color: %s;
    border: 1px solid %s;
    border-radius: %dpx;
    gridline-color: %s;
    font-size: %dpx;
}

QTableWidget::item, QTableView::item {
    padding: %dpx;
    border: none;
}

QTableWidget::item:hover, QTableView::item:hover {
    background-color: %s;
}

QTableWidget::item:selected, QTableView::item:selected {
    background-color: %s;
    color: %s;
}

QHeaderView::section {
    background-color: %s;
    color: %s;
    border: none;
    border-bottom: 1px solid %s;
    padding: %dpx;
    font-size: %dpx;
    font-weight: %d;
}

/* === 树形视图样式 === */
QTreeWidget, QTreeView {
    background-color: %s;
    color: %s;
    border: 1px solid %s;
    border-radius: %dpx;
    font-size: %dpx;
}

QTreeWidget::item, QTreeView::item {
    padding: %dpx;
    border-radius: %dpx;
}

QTreeWidget::item:hover, QTreeView::item:hover {
    background-color: %s;
}

QTreeWidget::item:selected, QTreeView::item:selected {
    background-color: %s;
    color: %s;
}

/* === 分组框样式 === */
QGroupBox {
    background-color: %s;
    color: %s;
    border: 1px solid %s;
    border-radius: %dpx;
    font-size: %dpx;
    padding-top: %dpx;
    margin-top: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: %dpx;
    padding: 0 %dpx;
    color: %s;
    font-weight: %d;
}

/* === 进度条样式 === */
QProgressBar {
    background-color: %s;
    border: none;
    border-radius: %dpx;
    height: 8px;
    text-align: center;
    color: %s;
}

QProgressBar::chunk {
    background-color: %s;
    border-radius: %dpx;
}

/* === 文本编辑框样式 === */
QTextEdit, QPlainTextEdit {
    background-color: %s;
    color: %s;
    border: 1px solid %s;
    border-radius: %dpx;
    padding: %dpx;
    font-size: %dpx;
    font-family: '%s';
}

QTextEdit:focus, QPlainTextEdit:focus {
    border-color: %s;
}

/* === 菜单样式 === */
QMenu {
    background-color: %s;
    color: %s;
    border: 1px solid %s;
    border-radius: %dpx;
    padding: 4px;
}

QMenu::item {
    padding: %dpx %dpx;
    border-radius: %dpx;
}

QMenu::item:selected {
    background-color: %s;
}

QMenu::separator {
    height: 1px;
    background-color: %s;
    margin: 4px 8px;
}

/* === 工具提示样式 === */
QToolTip {
    background-color: %s;
    color: %s;
    border: 1px solid %s;
    border-radius: %dpx;
    padding: %dpx %dpx;
    font-size: %dpx;
}

/* === 对话框样式 === */
QDialog {
    background-color: %s;
}

/* === 卡片容器样式 === */
QWidget[class="card"] {
    background-color: %s;
    border: 1px solid %s;
    border-radius: %dpx;
    padding: %dpx;
}

QWidget[class="card"] > QWidget {
    background-color: transparent;
}

QWidget[class="card"]:hover {
    border-color: %s;
}

QWidget[class="cardElevated"] {
    background-color: %s;
    border: none;
    border-radius: %dpx;
    padding: %dpx;
}

QWidget[class="cardElevated"] > QWidget {
    background-color: transparent;
}

QWidget[class="cardOutlined"] {
    background-color: %s;
    border: 1px solid %s;
    border-radius: %dpx;
    padding: %dpx;
}

QWidget[class="cardOutlined"] > QWidget {
    background-color: transparent;
}

/* === 内容区域样式 === */
QWidget[class="contentArea"] {
    background-color: %s;
}

/* === 导航栏样式 === */
QWidget[class="navigationBar"] {
    background-color: %s;
    border-right: 1px solid %s;
}

QPushButton[class="navButton"] {
    background-color: transparent;
    color: %s;
    border: none;
    border-radius: %dpx;
    padding: %dpx;
    text-align: left;
    min-height: 40px;
}

QPushButton[class="navButton"]:hover {
    background-color: %s;
}

QPushButton[class="navButton"]:checked, QPushButton[class="navButton"][selected="true"] {
    background-color: rgba(67, 97, 238, 0.12);
    color: %s;
    border-left: 3px solid %s;
}

/* === 状态栏样式 === */
QStatusBar {
    background-color: %s;
    color: %s;
    border-top: 1px solid %s;
    font-size: %dpx;
}

QStatusBar::item {
    border: none;
}

/* === 堆叠控件样式 === */
QStackedWidget {
    background-color: %s;
}

QStackedWidget > QWidget {
    background-color: %s;
}

/* === 滚动区域样式 === */
QScrollArea {
    background-color: %s;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: %s;
}

/* === 分割线样式 === */
QFrame[frameShape="4"] { /* HLine */
    background-color: %s;
    max-height: 1px;
    border: none;
}

QFrame[frameShape="5"] { /* VLine */
    background-color: %s;
    max-width: 1px;
    border: none;
}
""" % (
            # 全局样式
            f['family'], fs['size_base'], c['text_primary'], c['surface'],
            c['surface'],
            
            # 按钮样式
            c['primary'], c['on_primary'], r['button_sm'], s['button_padding_v'], s['button_padding_h'],
            fs['label_large'], FONT_WEIGHTS['medium'],
            c['primary_hover'],
            c['primary_dark'],
            c['surface_container_high'], c['text_disabled'],
            
            # 主要按钮
            c['primary'], c['on_primary'],
            c['primary_hover'],
            c['primary_dark'],
            
            # 次级按钮
            c['primary'], c['primary'],
            
            # 文本按钮
            c['primary'],
            
            # 危险按钮
            c['danger'], c['on_danger'],
            c['danger_dark'],
            
            # 标签样式
            c['text_primary'],
            fs['title_large'], FONT_WEIGHTS['semi_bold'], c['text_primary'],
            c['text_secondary'],
            c['text_muted'],
            
            # 输入框样式
            c['surface_container'], c['text_primary'], c['outline_variant'],
            r['input'], s['input_padding_v'], s['input_padding_h'], fs['size_base'],
            c['outline'],
            c['primary'],
            c['surface_container_high'], c['text_disabled'],
            
            # 下拉框样式
            c['surface_container'], c['text_primary'], c['outline_variant'],
            r['input'], s['input_padding_v'], s['input_padding_h'], fs['size_base'],
            c['outline'],
            c['primary'],
            c['text_secondary'],
            c['surface_container'], c['text_primary'], c['outline_variant'],
            r['sm'], c['selection_bg'], c['on_primary'],
            
            # 数值调节框样式
            c['surface_container'], c['text_primary'], c['outline_variant'],
            r['input'], s['input_padding_v'], s['input_padding_h'], fs['size_base'],
            c['outline'],
            c['primary'],
            c['surface_container'],
            c['hover_bg'],
            c['text_primary'],
            c['text_primary'],
            
            # 复选框样式
            c['text_primary'], s['icon_text'], fs['size_base'],
            c['outline'],
            c['primary'],
            c['primary'], c['primary'],
            c['text_disabled'], c['surface_container'],
            
            # 标签页样式
            c['surface'], c['outline_variant'], r['sm'],
            c['surface_container'], c['text_secondary'],
            s['padding_sm'], s['padding_xl'], fs['label_large'],
            c['hover_bg'],
            c['primary'], c['primary'],
            
            # 分割器样式
            c['divider_color'],
            
            # 滚动条样式 - 垂直
            c['surface_dim'],
            c['outline_variant'],
            c['outline'],
            
            # 滚动条样式 - 水平
            c['surface_dim'],
            c['outline_variant'],
            c['outline'],
            
            # 列表视图样式
            c['surface'], c['text_primary'], c['outline_variant'],
            r['sm'], s['padding_sm'], fs['size_base'],
            s['list_item_padding'], r['xs'],
            c['hover_bg'],
            c['selection_bg'], c['on_primary'],
            
            # 表格视图样式
            c['surface'], c['text_primary'], c['outline_variant'],
            r['sm'], c['divider_color'], fs['size_base'],
            s['padding_sm'],
            c['hover_bg'],
            c['selection_bg'], c['on_primary'],
            c['surface_container'], c['text_primary'], c['outline_variant'],
            s['padding_sm'], fs['label_large'], FONT_WEIGHTS['medium'],
            
            # 树形视图样式
            c['surface'], c['text_primary'], c['outline_variant'],
            r['sm'], fs['size_base'],
            s['list_item_padding'], r['xs'],
            c['hover_bg'],
            c['selection_bg'], c['on_primary'],
            
            # 分组框样式
            c['surface_container'], c['text_primary'], c['outline_variant'],
            r['sm'], fs['size_base'], s['padding_xl'],
            s['padding_sm'], s['padding_sm'], c['primary'], FONT_WEIGHTS['semi_bold'],
            
            # 进度条样式
            c['surface_container'], r['full'], c['text_primary'],
            c['primary'], r['full'],
            
            # 文本编辑框样式
            c['log_bg'], c['text_primary'], c['outline_variant'],
            r['sm'], s['padding_sm'], fs['size_base'], f['family_mono'],
            c['primary'],
            
            # 菜单样式
            c['surface_container'], c['text_primary'], c['outline_variant'],
            r['menu'],
            s['padding_sm'], s['padding_xl'], r['xs'],
            c['hover_bg'],
            c['divider_color'],
            
            # 工具提示样式
            c['inverse_surface'], c['inverse_on_surface'], c['outline_variant'],
            r['tooltip'], s['padding_sm'], s['padding_md'], fs['label_medium'],
            
            # 对话框样式
            c['surface'],
            
            # 卡片容器样式
            c['surface_container'], c['outline_variant'],
            r['card'], s['card_padding'],
            c['outline'],
            c['surface_container_high'],
            r['card_lg'], s['card_padding'],
            c['surface'], c['outline_variant'],
            r['card'], s['card_padding'],
            
            # 内容区域样式
            c['surface'],
            
            # 导航栏样式
            c['surface_dim'], c['outline_variant'],
            c['text_secondary'],
            r['xs'], s['padding_md'],
            c['hover_bg'],
            c['primary'], c['primary'],
            
            # 状态栏样式
            c['surface_dim'], c['text_secondary'], c['outline_variant'],
            fs['label_medium'],
            
            # 堆叠控件样式
            c['surface'],
            c['surface'],
            
            # 滚动区域样式
            c['surface'],
            c['surface'],
            
            # 分割线样式
            c['divider_color'],
            c['divider_color'],
        )
        
        return stylesheet
    
    def apply_theme(self, app: QApplication) -> None:
        """
        应用主题到 QApplication
        
        Args:
            app: QApplication 实例
        """
        try:
            stylesheet = self.get_stylesheet()
            app.setStyleSheet(stylesheet)
        except Exception as e:
            # 如果样式表应用失败，记录错误但不中断程序
            import logging
            logging.getLogger(__name__).error(f"应用主题失败: {e}")
            # 使用空样式表作为回退
            app.setStyleSheet("")
    
    @classmethod
    def get_instance(cls) -> 'ThemeManager':
        """获取主题管理器单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


# 便捷函数
def get_theme() -> ThemeManager:
    """获取主题管理器实例"""
    return ThemeManager.get_instance()


def apply_theme(app: QApplication) -> None:
    """应用主题到 QApplication"""
    ThemeManager.get_instance().apply_theme(app)


def get_stylesheet() -> str:
    """获取完整 QSS 样式表"""
    return ThemeManager.get_instance().get_stylesheet()