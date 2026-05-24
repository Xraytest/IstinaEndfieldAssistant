"""
ReAcrture 客户端主题模块
基于服务端 dashboard.css 的明日方舟风格深色主题
采用 Material Design 3 设计规范
"""

# ============================================================================
# 颜色定义 - Material Design 3 颜色体系
# ============================================================================

# 主色调系统 (Primary) - 保持原有主配色
COLORS = {
    # === 主色调系统 ===
    'primary': '#4361ee',              # 主色 - 蓝色 (保持不变)
    'primary_hover': '#3a56d4',        # 主色悬停
    # 主色浅色变体
    'primary_light': '#6b83f2',        # 主色浅色
    'primary_lighter': '#94a5f5',      # 主色更浅
    'primary_light_container': '#e0e7ff',  # 主色容器 (浅色背景)
    # 主色深色变体
    'primary_dark': '#2d4bcc',         # 主色深色
    'primary_darker': '#2237a0',       # 主色更深
    'primary_dark_container': '#1a2768',   # 主色容器 (深色背景)
    # 主色文字
    'on_primary': '#ffffff',           # 主色上的文字
    'on_primary_container': '#1a2768', # 主色容器上的文字

    # === 次级色系统 (Secondary) ===
    'secondary': '#7209b7',            # 次级色 - 紫色
    # 次级色变体
    'secondary_light': '#9b3fd4',      # 次级色浅色
    'secondary_dark': '#5a0792',       # 次级色深色
    'secondary_container': '#f3e5f9',  # 次级色容器
    # 次级色文字
    'on_secondary': '#ffffff',         # 次级色上的文字
    'on_secondary_container': '#3a0055',  # 次级色容器上的文字

    # === 第三色系统 (Tertiary) ===
    'tertiary': '#00bfa5',             # 第三色 - 青色
    'tertiary_light': '#5df2dc',       # 第三色浅色
    'tertiary_dark': '#008c7a',        # 第三色深色
    'tertiary_container': '#e0f7fa',   # 第三色容器
    'on_tertiary': '#ffffff',          # 第三色上的文字
    'on_tertiary_container': '#00201c',  # 第三色容器上的文字

    # === 语义颜色 ===
    'success': '#2ecc71',              # 成功 - 绿色
    'success_light': '#58d68d',        # 成功浅色
    'success_dark': '#27ae60',         # 成功深色
    'success_container': '#e8f8f0',    # 成功容器
    'on_success': '#ffffff',           # 成功上的文字

    'warning': '#f39c12',              # 警告 - 橙色
    'warning_light': '#f5b041',        # 警告浅色
    'warning_dark': '#d68910',         # 警告深色
    'warning_container': '#fef9e7',    # 警告容器
    'on_warning': '#1a1c1b',           # 警告上的文字

    'danger': '#e74c3c',               # 危险 - 红色
    'danger_light': '#ec7063',         # 危险浅色
    'danger_dark': '#c0392b',          # 危险深色
    'danger_container': '#fdedec',     # 危险容器
    'on_danger': '#ffffff',            # 危险上的文字

    'info': '#3498db',                 # 信息 - 蓝色
    'info_light': '#5dade2',           # 信息浅色
    'info_dark': '#2980b9',            # 信息深色
    'info_container': '#ebf5fb',       # 信息容器
    'on_info': '#ffffff',              # 信息上的文字

    # === 背景色系统 (深色主题 Surface) ===
    'bg_primary': '#1c1c1e',           # 主背景 (Surface)
    'bg_secondary': '#2c2c2e',         # 次级背景 (Surface Container High)
    'bg_tertiary': '#3a3a3c',          # 第三级背景 (Surface Container Highest)
    'bg_card': '#2c2c2e',              # 卡片背景
    'bg_elevated': '#3a3a3c',          # 提升背景 (Surface Elevated)
    # 表面变体
    'surface': '#1c1c1e',              # 表面色
    'surface_dim': '#141416',          # 暗淡表面
    'surface_bright': '#3a3a3c',       # 明亮表面
    'surface_container_lowest': '#0f0f11',  # 最低容器
    'surface_container_low': '#1c1c1e',     # 低容器
    'surface_container': '#2c2c2e',         # 容器
    'surface_container_high': '#363638',    # 高容器
    'surface_container_highest': '#3a3a3c', # 最高容器
    # 表面文字
    'on_surface': '#ffffff',           # 表面上的文字
    'on_surface_variant': '#b0b0b0',   # 表面变体上的文字

    # === 文字颜色 ===
    'text_primary': '#ffffff',         # 主文字
    'text_secondary': '#b0b0b0',       # 次级文字
    'text_tertiary': '#8a8a8a',        # 第三级文字
    'text_muted': '#666666',           # 淡化文字
    'text_disabled': '#4a4a4a',        # 禁用文字

    # === 边框和分割线 ===
    'border_color': '#48484a',         # 边框色
    'border_light': '#636366',         # 浅边框
    'divider_color': '#38383a',        # 分割线
    'outline': '#636366',              # 轮廓色
    'outline_variant': '#48484a',      # 轮廓变体

    # === 状态层颜色 (State Layers) ===
    # 用于悬停、聚焦、按压等状态
    'state_hover': 'rgba(255, 255, 255, 0.08)',    # 悬停状态层
    'state_focus': 'rgba(255, 255, 255, 0.12)',    # 聚焦状态层
    'state_press': 'rgba(255, 255, 255, 0.16)',    # 按压状态层
    'state_drag': 'rgba(255, 255, 255, 0.20)',     # 拖拽状态层
    # 主色状态层
    'primary_state_hover': 'rgba(67, 97, 238, 0.08)',
    'primary_state_focus': 'rgba(67, 97, 238, 0.12)',
    'primary_state_press': 'rgba(67, 97, 238, 0.16)',

    # === 特殊用途 ===
    'canvas_bg': '#141416',            # 画布背景（屏幕预览等）
    'log_bg': '#141416',               # 日志背景
    'selection_bg': '#4361ee',         # 选中背景
    'hover_bg': '#3a3a3c',             # 悬停背景
    'inverse_surface': '#e0e0e0',      # 反转表面
    'inverse_on_surface': '#1c1c1e',   # 反转表面上的文字
    'inverse_primary': '#6b83f2',      # 反转主色

    # === 阴影颜色 ===
    'shadow': 'rgba(0, 0, 0, 0.3)',    # 阴影
    'shadow_light': 'rgba(0, 0, 0, 0.15)',  # 浅阴影
}

# 用户层级颜色
TIER_COLORS = {
    'free': COLORS['text_muted'],
    'prime': COLORS['success'],
    'plus': COLORS['warning'],
    'pro': COLORS['danger'],
}

# ============================================================================
# 字体定义 - Material Design 3 排版规范（优化紧凑版）
# ============================================================================

FONTS = {
    # === 字体族 ===
    'family': 'Microsoft YaHei UI',      # 中文字体 (保持不变)
    'family_fallback': 'Segoe UI',       # 备用字体
    'family_mono': 'Consolas',           # 等宽字体 (代码/日志)
    'family_display': 'Microsoft YaHei UI',  # 展示字体

    # === 字号系统 (Material Design 3 Typography Scale - 紧凑版) ===
    # 展示字号
    'display_large': 45,      # 大展示标题 (原57)
    'display_medium': 36,     # 中展示标题 (原45)
    'display_small': 28,      # 小展示标题 (原36)

    # 标题字号
    'headline_large': 26,     # 大标题 (原32)
    'headline_medium': 22,    # 中标题 (原28)
    'headline_small': 18,     # 小标题 (原24)

    # 标题字号 (Title)
    'title_large': 16,        # 大标题 (原22)
    'title_medium': 13,       # 中标题 (原16)
    'title_small': 12,        # 小标题 (原14)

    # 正文字号
    'body_large': 13,         # 大正文 (原16)
    'body_medium': 12,        # 中正文 (默认) (原14)
    'body_small': 11,         # 小正文 (原12)

    # 标签字号
    'label_large': 12,        # 大标签 (按钮) (原14)
    'label_medium': 11,       # 中标签 (原12)
    'label_small': 10,        # 小标签 (原11)

    # === 兼容旧系统 ===
    'size_small': 11,         # body_small
    'size_base': 12,          # body_medium (默认)
    'size_medium': 12,        # body_medium
    'size_large': 13,         # body_large / title_medium
    'size_xlarge': 16,        # title_large
    'size_title': 18,         # headline_small
    'size_header': 22,        # headline_medium
}

# === 字重定义 ===
FONT_WEIGHTS = {
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

# === 行高定义 ===
LINE_HEIGHTS = {
    'display_large': 64,
    'display_medium': 52,
    'display_small': 44,
    'headline_large': 40,
    'headline_medium': 36,
    'headline_small': 32,
    'title_large': 28,
    'title_medium': 24,
    'title_small': 20,
    'body_large': 24,
    'body_medium': 20,
    'body_small': 16,
    'label_large': 20,
    'label_medium': 16,
    'label_small': 16,
}

# === 字间距定义 ===
LETTER_SPACING = {
    'display_large': -0.25,
    'display_medium': 0,
    'display_small': 0,
    'headline_large': 0,
    'headline_medium': 0,
    'headline_small': 0,
    'title_large': 0,
    'title_medium': 0.15,
    'title_small': 0.1,
    'body_large': 0.5,
    'body_medium': 0.25,
    'body_small': 0.4,
    'label_large': 0.1,
    'label_medium': 0.5,
    'label_small': 0.5,
}

# ============================================================================
# 间距定义 - Material Design 3 间距系统（紧凑版）
# ============================================================================

# 基础间距单位 (4dp)
SPACING_UNIT = 4

# 标准间距
SPACING = {
    # === 基础间距 (4dp 倍数) ===
    'none': 0,
    'xxxs': 1,           # 1px - 极小间距
    'xxs': 2,            # 2px - 超小间距
    'xs': 3,             # 3px - 小间距
    'sm': 6,             # 6dp - 标准小间距
    'md': 8,             # 8dp - 中等间距
    'lg': 12,            # 12dp - 大间距
    'xl': 16,            # 16dp - 超大间距
    'xxl': 20,           # 20dp - 特大间距
    'xxxl': 24,          # 24dp - 巨大间距

    # === 组件间距 ===
    'component': 6,      # 组件内元素间距
    'section': 12,       # 区块间距
    'container': 16,     # 容器间距

    # === 内边距 ===
    'padding_xs': 3,     # 小内边距
    'padding_sm': 6,     # 标准内边距
    'padding_md': 8,     # 中等内边距
    'padding_lg': 12,    # 大内边距
    'padding_xl': 16,    # 超大内边距

    # === 外边距 ===
    'margin_xs': 3,      # 小外边距
    'margin_sm': 6,      # 标准外边距
    'margin_md': 8,      # 中等外边距
    'margin_lg': 12,     # 大外边距
    'margin_xl': 16,     # 超大外边距

    # === 特殊间距 ===
    'icon_text': 6,      # 图标与文字间距
    'button_padding_h': 16,  # 按钮水平内边距
    'button_padding_v': 6,   # 按钮垂直内边距
    'input_padding_h': 10,   # 输入框水平内边距
    'input_padding_v': 6,    # 输入框垂直内边距
    'card_padding': 12,      # 卡片内边距
    'list_item_padding': 8,  # 列表项内边距
    'dialog_padding': 16,    # 对话框内边距
}

# ============================================================================
# 圆角定义 - Material Design 3 形状系统
# ============================================================================

CORNER_RADIUS = {
    # === 标准圆角 ===
    'none': 0,
    'xs': 4,             # 超小圆角
    'sm': 8,             # 小圆角
    'md': 12,            # 中等圆角
    'lg': 16,            # 大圆角
    'xl': 20,            # 超大圆角
    'xxl': 28,           # 特大圆角
    'full': 9999,        # 完全圆形/胶囊形

    # === 组件圆角 ===
    'button': 20,        # 按钮圆角 (胶囊形)
    'button_sm': 8,      # 小按钮圆角
    'button_lg': 24,     # 大按钮圆角
    'card': 12,          # 卡片圆角
    'card_lg': 16,       # 大卡片圆角
    'input': 4,          # 输入框圆角
    'input_outlined': 4, # 轮廓输入框圆角
    'input_filled': 8,   # 填充输入框圆角
    'dialog': 28,        # 对话框圆角
    'chip': 8,           # 标签圆角
    'badge': 9999,       # 徽章圆角 (圆形)
    'fab': 16,           # 悬浮按钮圆角
    'menu': 8,           # 菜单圆角
    'tooltip': 4,        # 提示框圆角
    'snackbar': 8,       # Snackbar圆角
}

# ============================================================================
# 阴影定义 - Material Design 3 阴影系统
# ============================================================================

ELEVATION = {
    # === 阴影层级 (0-5) ===
    'level_0': 0,        # 无阴影
    'level_1': 1,        # 一级阴影 (卡片)
    'level_2': 2,        # 二级阴影 (浮动按钮)
    'level_3': 3,        # 三级阴影 (菜单)
    'level_4': 4,        # 四级阴影 (对话框)
    'level_5': 5,        # 五级阴影 (模态框)

    # === 组件阴影 ===
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

DURATION = {
    # === 标准动画时长 ===
    'instant': 0,
    'fast': 100,         # 快速动画 (ms)
    'normal': 200,       # 标准动画
    'slow': 300,         # 慢速动画
    'slower': 400,       # 更慢动画

    # === 组件动画时长 ===
    'hover': 150,        # 悬停动画
    'press': 100,        # 按压动画
    'fade': 200,         # 淡入淡出
    'slide': 300,        # 滑动动画
    'expand': 250,       # 展开/收起
    'dialog': 280,       # 对话框动画
    'snackbar': 250,     # Snackbar动画
}

# ============================================================================
# 样式配置
# ============================================================================

def get_font(size_key='size_base', bold=False):
    """获取字体配置"""
    size = FONTS.get(size_key, 10)
    weight = 'bold' if bold else 'normal'
    return (FONTS['family'], size, weight)


def get_font_tuple(size_key='size_base', bold=False):
    """获取字体元组（用于ttk样式）"""
    size = FONTS.get(size_key, 10)
    weight = 'bold' if bold else 'normal'
    return (FONTS['family'], size, weight)


# ============================================================================
# ttk 样式配置函数
# ============================================================================

def setup_ttk_styles(style=None):
    """
    配置 ttk 样式

    Args:
        style: ttk.Style 实例，如果为 None 则创建新实例
    """
    import tkinter.ttk as ttk

    if style is None:
        style = ttk.Style()

    # 设置整体主题
    style.theme_use('clam')  # clam 主题支持自定义颜色

    # ----------------------------------------------------------------
    # 通用配置
    # ----------------------------------------------------------------

    # 默认字体
    default_font = get_font_tuple('size_base')
    bold_font = get_font_tuple('size_base', bold=True)

    # ----------------------------------------------------------------
    # Frame 样式 - Material Design 3 表面系统
    # ----------------------------------------------------------------

    # === 基础 Frame ===
    style.configure('TFrame',
        background=COLORS['surface'])

    # === 表面变体 ===
    style.configure('Surface.TFrame',
        background=COLORS['surface'])

    style.configure('SurfaceDim.TFrame',
        background=COLORS['surface_dim'])

    style.configure('SurfaceBright.TFrame',
        background=COLORS['surface_bright'])

    # === 容器表面 ===
    style.configure('SurfaceContainer.TFrame',
        background=COLORS['surface_container'])

    style.configure('SurfaceContainerLow.TFrame',
        background=COLORS['surface_container_low'])

    style.configure('SurfaceContainerHigh.TFrame',
        background=COLORS['surface_container_high'])

    style.configure('SurfaceContainerHighest.TFrame',
        background=COLORS['surface_container_highest'])

    # ----------------------------------------------------------------
    # 卡片样式 - Material Design 3 卡片系统
    # ----------------------------------------------------------------

    # === 基础卡片 ===
    style.configure('Card.TFrame',
        background=COLORS['bg_card'])

    # === 填充卡片 (Filled Card) ===
    style.configure('CardFilled.TFrame',
        background=COLORS['surface_container_high'])

    # === 提升卡片 (Elevated Card) ===
    style.configure('CardElevated.TFrame',
        background=COLORS['surface_container_high'])

    # === 轮廓卡片 (Outlined Card) ===
    style.configure('CardOutlined.TFrame',
        background=COLORS['surface'],
        bordercolor=COLORS['outline_variant'])

    # ----------------------------------------------------------------
    # LabelFrame 样式 - 卡片容器
    # ----------------------------------------------------------------

    # === 基础 LabelFrame ===
    style.configure('TLabelframe',
        background=COLORS['surface'],
        bordercolor=COLORS['outline_variant'],
        relief='flat',
        borderwidth=1)

    style.configure('TLabelframe.Label',
        background=COLORS['surface'],
        foreground=COLORS['primary'],
        font=get_font_tuple('title_medium', bold=True))

    # === 卡片 LabelFrame (带标题的卡片) ===
    style.configure('Card.TLabelframe',
        background=COLORS['surface_container'],
        bordercolor=COLORS['outline_variant'],
        relief='flat',
        borderwidth=1)

    style.configure('Card.TLabelframe.Label',
        background=COLORS['surface_container'],
        foreground=COLORS['primary'],
        font=get_font_tuple('title_medium', bold=True))

    # === 填充卡片 LabelFrame ===
    style.configure('CardFilled.TLabelframe',
        background=COLORS['surface_container_high'],
        bordercolor=COLORS['surface_container_highest'],
        relief='flat',
        borderwidth=0)

    style.configure('CardFilled.TLabelframe.Label',
        background=COLORS['surface_container_high'],
        foreground=COLORS['on_surface'],
        font=get_font_tuple('title_medium', bold=True))

    # === 提升卡片 LabelFrame ===
    style.configure('CardElevated.TLabelframe',
        background=COLORS['surface_container_high'],
        bordercolor=COLORS['surface_container_highest'],
        relief='flat',
        borderwidth=0)

    style.configure('CardElevated.TLabelframe.Label',
        background=COLORS['surface_container_high'],
        foreground=COLORS['primary'],
        font=get_font_tuple('title_medium', bold=True))

    # === 轮廓卡片 LabelFrame ===
    style.configure('CardOutlined.TLabelframe',
        background=COLORS['surface'],
        bordercolor=COLORS['outline'],
        relief='flat',
        borderwidth=1)

    style.configure('CardOutlined.TLabelframe.Label',
        background=COLORS['surface'],
        foreground=COLORS['primary'],
        font=get_font_tuple('title_medium', bold=True))

    # === 紧凑卡片 ===
    style.configure('CardCompact.TLabelframe',
        background=COLORS['surface_container'],
        bordercolor=COLORS['outline_variant'],
        relief='flat',
        borderwidth=1)

    style.configure('CardCompact.TLabelframe.Label',
        background=COLORS['surface_container'],
        foreground=COLORS['primary'],
        font=get_font_tuple('title_small', bold=True))

    # ----------------------------------------------------------------
    # Label 样式
    # ----------------------------------------------------------------
    style.configure('TLabel',
        background=COLORS['bg_primary'],
        foreground=COLORS['text_primary'],
        font=default_font)

    style.configure('Secondary.TLabel',
        background=COLORS['bg_primary'],
        foreground=COLORS['text_secondary'],
        font=default_font)

    style.configure('Muted.TLabel',
        background=COLORS['bg_primary'],
        foreground=COLORS['text_muted'],
        font=get_font_tuple('size_small'))

    style.configure('Title.TLabel',
        background=COLORS['bg_primary'],
        foreground=COLORS['text_primary'],
        font=get_font_tuple('size_title', bold=True))

    style.configure('Header.TLabel',
        background=COLORS['bg_primary'],
        foreground=COLORS['primary'],
        font=get_font_tuple('size_header', bold=True))

    style.configure('Status.TLabel',
        background=COLORS['bg_primary'],
        foreground=COLORS['text_secondary'],
        font=get_font_tuple('size_small'))

    # 成功/警告/危险状态标签
    style.configure('Success.TLabel',
        background=COLORS['bg_primary'],
        foreground=COLORS['success'],
        font=default_font)

    style.configure('Warning.TLabel',
        background=COLORS['bg_primary'],
        foreground=COLORS['warning'],
        font=default_font)

    style.configure('Danger.TLabel',
        background=COLORS['bg_primary'],
        foreground=COLORS['danger'],
        font=default_font)

    # ----------------------------------------------------------------
    # Button 样式 - Material Design 3 按钮系统
    # ----------------------------------------------------------------

    # === 填充按钮 (Filled Button) - 默认样式 ===
    style.configure('TButton',
        background=COLORS['bg_tertiary'],
        foreground=COLORS['text_primary'],
        font=bold_font,
        borderwidth=0,
        focuscolor='none',
        relief='flat',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('TButton',
        background=[('active', COLORS['hover_bg']),
                   ('pressed', COLORS['primary']),
                   ('disabled', COLORS['bg_secondary'])],
        foreground=[('active', COLORS['text_primary']),
                   ('disabled', COLORS['text_disabled'])])

    # === 填充按钮 - 主要 (Filled Button - Primary) ===
    style.configure('Primary.TButton',
        background=COLORS['primary'],
        foreground=COLORS['on_primary'],
        font=bold_font,
        borderwidth=0,
        focuscolor='none',
        relief='flat',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('Primary.TButton',
        background=[('active', COLORS['primary_dark']),
                   ('pressed', COLORS['primary_darker']),
                   ('disabled', COLORS['bg_secondary'])],
        foreground=[('active', COLORS['on_primary']),
                   ('disabled', COLORS['text_disabled'])])

    # === 填充按钮 - 次级 (Filled Button - Secondary) ===
    style.configure('Secondary.TButton',
        background=COLORS['secondary'],
        foreground=COLORS['on_secondary'],
        font=bold_font,
        borderwidth=0,
        focuscolor='none',
        relief='flat',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('Secondary.TButton',
        background=[('active', COLORS['secondary_dark']),
                   ('pressed', COLORS['secondary_dark']),
                   ('disabled', COLORS['bg_secondary'])],
        foreground=[('active', COLORS['on_secondary']),
                   ('disabled', COLORS['text_disabled'])])

    # === 填充按钮 - 成功 (Filled Button - Success) ===
    style.configure('Success.TButton',
        background=COLORS['success'],
        foreground=COLORS['on_success'],
        font=bold_font,
        borderwidth=0,
        focuscolor='none',
        relief='flat',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('Success.TButton',
        background=[('active', COLORS['success_dark']),
                   ('pressed', COLORS['success_dark']),
                   ('disabled', COLORS['bg_secondary'])],
        foreground=[('active', COLORS['on_success']),
                   ('disabled', COLORS['text_disabled'])])

    # === 填充按钮 - 警告 (Filled Button - Warning) ===
    style.configure('Warning.TButton',
        background=COLORS['warning'],
        foreground=COLORS['on_warning'],
        font=bold_font,
        borderwidth=0,
        focuscolor='none',
        relief='flat',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('Warning.TButton',
        background=[('active', COLORS['warning_dark']),
                   ('pressed', COLORS['warning_dark']),
                   ('disabled', COLORS['bg_secondary'])],
        foreground=[('active', COLORS['on_warning']),
                   ('disabled', COLORS['text_disabled'])])

    # === 填充按钮 - 危险 (Filled Button - Danger) ===
    style.configure('Danger.TButton',
        background=COLORS['danger'],
        foreground=COLORS['on_danger'],
        font=bold_font,
        borderwidth=0,
        focuscolor='none',
        relief='flat',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('Danger.TButton',
        background=[('active', COLORS['danger_dark']),
                   ('pressed', COLORS['danger_dark']),
                   ('disabled', COLORS['bg_secondary'])],
        foreground=[('active', COLORS['on_danger']),
                   ('disabled', COLORS['text_disabled'])])

    # === 轮廓按钮 (Outlined Button) ===
    style.configure('Outline.TButton',
        background=COLORS['bg_primary'],
        foreground=COLORS['primary'],
        font=bold_font,
        borderwidth=1,
        focuscolor='none',
        relief='solid',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('Outline.TButton',
        background=[('active', COLORS['primary']),
                   ('pressed', COLORS['primary_dark']),
                   ('disabled', COLORS['bg_primary'])],
        foreground=[('active', COLORS['on_primary']),
                   ('pressed', COLORS['on_primary']),
                   ('disabled', COLORS['text_disabled'])])

    # === 轮廓按钮 - 次级 (Outlined Button - Secondary) ===
    style.configure('OutlineSecondary.TButton',
        background=COLORS['bg_primary'],
        foreground=COLORS['secondary'],
        font=bold_font,
        borderwidth=1,
        focuscolor='none',
        relief='solid',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('OutlineSecondary.TButton',
        background=[('active', COLORS['secondary']),
                   ('pressed', COLORS['secondary_dark']),
                   ('disabled', COLORS['bg_primary'])],
        foreground=[('active', COLORS['on_secondary']),
                   ('pressed', COLORS['on_secondary']),
                   ('disabled', COLORS['text_disabled'])])

    # === 轮廓按钮 - 危险 (Outlined Button - Danger) ===
    style.configure('OutlineDanger.TButton',
        background=COLORS['bg_primary'],
        foreground=COLORS['danger'],
        font=bold_font,
        borderwidth=1,
        focuscolor='none',
        relief='solid',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('OutlineDanger.TButton',
        background=[('active', COLORS['danger']),
                   ('pressed', COLORS['danger_dark']),
                   ('disabled', COLORS['bg_primary'])],
        foreground=[('active', COLORS['on_danger']),
                   ('pressed', COLORS['on_danger']),
                   ('disabled', COLORS['text_disabled'])])

    # === 文本按钮 (Text Button) ===
    style.configure('Text.TButton',
        background=COLORS['bg_primary'],
        foreground=COLORS['primary'],
        font=bold_font,
        borderwidth=0,
        focuscolor='none',
        relief='flat',
        padding=(SPACING['padding_sm'], SPACING['padding_xs']))

    style.map('Text.TButton',
        background=[('active', COLORS['hover_bg']),
                   ('pressed', COLORS['bg_tertiary']),
                   ('disabled', COLORS['bg_primary'])],
        foreground=[('active', COLORS['primary_light']),
                   ('pressed', COLORS['primary']),
                   ('disabled', COLORS['text_disabled'])])

    # === 文本按钮 - 次级 (Text Button - Secondary) ===
    style.configure('TextSecondary.TButton',
        background=COLORS['bg_primary'],
        foreground=COLORS['text_secondary'],
        font=bold_font,
        borderwidth=0,
        focuscolor='none',
        relief='flat',
        padding=(SPACING['padding_sm'], SPACING['padding_xs']))

    style.map('TextSecondary.TButton',
        background=[('active', COLORS['hover_bg']),
                   ('pressed', COLORS['bg_tertiary']),
                   ('disabled', COLORS['bg_primary'])],
        foreground=[('active', COLORS['text_primary']),
                   ('pressed', COLORS['text_primary']),
                   ('disabled', COLORS['text_disabled'])])

    # === 色调按钮 (Tonal Button) ===
    style.configure('Tonal.TButton',
        background=COLORS['primary_dark_container'],
        foreground=COLORS['primary_light'],
        font=bold_font,
        borderwidth=0,
        focuscolor='none',
        relief='flat',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('Tonal.TButton',
        background=[('active', COLORS['primary_darker']),
                   ('pressed', COLORS['primary_darker']),
                   ('disabled', COLORS['bg_secondary'])],
        foreground=[('active', COLORS['primary_lighter']),
                   ('pressed', COLORS['primary_lighter']),
                   ('disabled', COLORS['text_disabled'])])

    # === 色调按钮 - 危险 (Tonal Button - Danger) ===
    style.configure('TonalDanger.TButton',
        background=COLORS['danger_container'],
        foreground=COLORS['danger'],
        font=bold_font,
        borderwidth=0,
        focuscolor='none',
        relief='flat',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('TonalDanger.TButton',
        background=[('active', COLORS['danger_light']),
                   ('pressed', COLORS['danger']),
                   ('disabled', COLORS['bg_secondary'])],
        foreground=[('active', COLORS['on_danger']),
                   ('pressed', COLORS['on_danger']),
                   ('disabled', COLORS['text_disabled'])])

    # === 小型按钮 (Small Button) ===
    style.configure('Small.TButton',
        background=COLORS['bg_tertiary'],
        foreground=COLORS['text_primary'],
        font=get_font_tuple('label_medium', bold=True),
        borderwidth=0,
        focuscolor='none',
        relief='flat',
        padding=(SPACING['padding_sm'], SPACING['padding_xs']))

    style.map('Small.TButton',
        background=[('active', COLORS['hover_bg']),
                   ('pressed', COLORS['primary'])],
        foreground=[('active', COLORS['text_primary'])])

    # === 图标按钮 (Icon Button) ===
    style.configure('Icon.TButton',
        background=COLORS['bg_primary'],
        foreground=COLORS['text_secondary'],
        font=bold_font,
        borderwidth=0,
        focuscolor='none',
        relief='flat',
        padding=SPACING['sm'])

    style.map('Icon.TButton',
        background=[('active', COLORS['hover_bg']),
                   ('pressed', COLORS['bg_tertiary'])],
        foreground=[('active', COLORS['text_primary']),
                   ('pressed', COLORS['primary'])])

    # ----------------------------------------------------------------
    # Entry 样式 - Material Design 3 输入框系统
    # ----------------------------------------------------------------

    # === 填充输入框 (Filled Input) ===
    style.configure('TEntry',
        fieldbackground=COLORS['surface_container_high'],
        foreground=COLORS['on_surface'],
        insertcolor=COLORS['on_surface'],
        bordercolor=COLORS['outline_variant'],
        lightcolor=COLORS['outline_variant'],
        darkcolor=COLORS['outline_variant'],
        padding=(SPACING['input_padding_h'], SPACING['input_padding_v']))

    style.map('TEntry',
        fieldbackground=[('focus', COLORS['surface_container_highest']),
                        ('disabled', COLORS['surface_container'])],
        bordercolor=[('focus', COLORS['primary']),
                    ('disabled', COLORS['outline_variant'])],
        lightcolor=[('focus', COLORS['primary']),
                   ('disabled', COLORS['outline_variant'])],
        darkcolor=[('focus', COLORS['primary']),
                  ('disabled', COLORS['outline_variant'])],
        foreground=[('disabled', COLORS['text_disabled'])])

    # === 轮廓输入框 (Outlined Input) ===
    style.configure('Outlined.TEntry',
        fieldbackground=COLORS['surface'],
        foreground=COLORS['on_surface'],
        insertcolor=COLORS['on_surface'],
        bordercolor=COLORS['outline'],
        lightcolor=COLORS['outline'],
        darkcolor=COLORS['outline'],
        padding=(SPACING['input_padding_h'], SPACING['input_padding_v']))

    style.map('Outlined.TEntry',
        fieldbackground=[('focus', COLORS['surface']),
                        ('disabled', COLORS['surface'])],
        bordercolor=[('focus', COLORS['primary']),
                    ('disabled', COLORS['outline_variant'])],
        lightcolor=[('focus', COLORS['primary']),
                   ('disabled', COLORS['outline_variant'])],
        darkcolor=[('focus', COLORS['primary']),
                  ('disabled', COLORS['outline_variant'])],
        foreground=[('disabled', COLORS['text_disabled'])])

    # === 错误状态输入框 ===
    style.configure('Error.TEntry',
        fieldbackground=COLORS['surface_container_high'],
        foreground=COLORS['on_surface'],
        insertcolor=COLORS['on_surface'],
        bordercolor=COLORS['danger'],
        lightcolor=COLORS['danger'],
        darkcolor=COLORS['danger'],
        padding=(SPACING['input_padding_h'], SPACING['input_padding_v']))

    style.map('Error.TEntry',
        fieldbackground=[('focus', COLORS['surface_container_highest'])],
        bordercolor=[('focus', COLORS['danger_light'])],
        lightcolor=[('focus', COLORS['danger_light'])],
        darkcolor=[('focus', COLORS['danger_light'])])

    # ----------------------------------------------------------------
    # Combobox 样式 - Material Design 3 下拉选择
    # ----------------------------------------------------------------

    # === 填充下拉框 (Filled Combobox) ===
    style.configure('TCombobox',
        fieldbackground=COLORS['surface_container_high'],
        background=COLORS['surface_container_highest'],
        foreground=COLORS['on_surface'],
        arrowcolor=COLORS['on_surface_variant'],
        bordercolor=COLORS['outline_variant'],
        lightcolor=COLORS['outline_variant'],
        darkcolor=COLORS['outline_variant'],
        padding=(SPACING['input_padding_h'], SPACING['input_padding_v']))

    style.map('TCombobox',
        fieldbackground=[('readonly', COLORS['surface_container_high']),
                        ('disabled', COLORS['surface_container'])],
        selectbackground=[('readonly', COLORS['primary'])],
        selectforeground=[('readonly', COLORS['on_primary'])],
        background=[('disabled', COLORS['surface_container'])],
        foreground=[('disabled', COLORS['text_disabled'])],
        arrowcolor=[('disabled', COLORS['text_disabled'])])

    # === 轮廓下拉框 (Outlined Combobox) ===
    style.configure('Outlined.TCombobox',
        fieldbackground=COLORS['surface'],
        background=COLORS['surface_container_highest'],
        foreground=COLORS['on_surface'],
        arrowcolor=COLORS['on_surface_variant'],
        bordercolor=COLORS['outline'],
        lightcolor=COLORS['outline'],
        darkcolor=COLORS['outline'],
        padding=(SPACING['input_padding_h'], SPACING['input_padding_v']))

    style.map('Outlined.TCombobox',
        fieldbackground=[('readonly', COLORS['surface']),
                        ('disabled', COLORS['surface'])],
        selectbackground=[('readonly', COLORS['primary'])],
        selectforeground=[('readonly', COLORS['on_primary'])],
        foreground=[('disabled', COLORS['text_disabled'])],
        arrowcolor=[('disabled', COLORS['text_disabled'])],
        bordercolor=[('focus', COLORS['primary']),
                    ('disabled', COLORS['outline_variant'])])

    # ----------------------------------------------------------------
    # Spinbox 样式 - Material Design 3 数字输入
    # ----------------------------------------------------------------
    style.configure('TSpinbox',
        fieldbackground=COLORS['surface_container_high'],
        foreground=COLORS['on_surface'],
        arrowcolor=COLORS['on_surface_variant'],
        bordercolor=COLORS['outline_variant'],
        lightcolor=COLORS['outline_variant'],
        darkcolor=COLORS['outline_variant'],
        padding=(SPACING['input_padding_h'], SPACING['input_padding_v']))

    style.map('TSpinbox',
        fieldbackground=[('disabled', COLORS['surface_container'])],
        foreground=[('disabled', COLORS['text_disabled'])],
        arrowcolor=[('disabled', COLORS['text_disabled'])],
        bordercolor=[('focus', COLORS['primary'])],
        lightcolor=[('focus', COLORS['primary'])],
        darkcolor=[('focus', COLORS['primary'])])

    # ----------------------------------------------------------------
    # Checkbutton 样式 - Material Design 3 复选框
    # ----------------------------------------------------------------
    style.configure('TCheckbutton',
        background=COLORS['surface'],
        foreground=COLORS['on_surface'],
        font=default_font)

    style.map('TCheckbutton',
        background=[('active', COLORS['surface'])],
        foreground=[('active', COLORS['on_surface']),
                   ('disabled', COLORS['text_disabled'])])

    # ----------------------------------------------------------------
    # Radiobutton 样式 - Material Design 3 单选框
    # ----------------------------------------------------------------
    style.configure('TRadiobutton',
        background=COLORS['surface'],
        foreground=COLORS['on_surface'],
        font=default_font)

    style.map('TRadiobutton',
        background=[('active', COLORS['surface'])],
        foreground=[('active', COLORS['on_surface']),
                   ('disabled', COLORS['text_disabled'])])

    # ----------------------------------------------------------------
    # Notebook 样式 - Material Design 3 标签页系统
    # ----------------------------------------------------------------

    # === 主标签页容器 ===
    style.configure('TNotebook',
        background=COLORS['surface'],
        borderwidth=0,
        tabmargins=[0, 0, 0, 0])

    # === 默认标签页 (Primary Tabs) ===
    style.configure('TNotebook.Tab',
        background=COLORS['surface_container'],
        foreground=COLORS['on_surface_variant'],
        font=get_font_tuple('label_large', bold=True),
        padding=[SPACING['lg'], SPACING['md']],
        borderwidth=0)

    style.map('TNotebook.Tab',
        background=[('selected', COLORS['surface']),
                   ('active', COLORS['surface_container_high'])],
        foreground=[('selected', COLORS['primary']),
                   ('active', COLORS['on_surface'])])

    # === 次级标签页 (Secondary Tabs) ===
    style.configure('Secondary.TNotebook',
        background=COLORS['surface_container'],
        borderwidth=0)

    style.configure('Secondary.TNotebook.Tab',
        background=COLORS['surface_container_low'],
        foreground=COLORS['on_surface_variant'],
        font=get_font_tuple('label_medium', bold=True),
        padding=[SPACING['md'], SPACING['sm']],
        borderwidth=0)

    style.map('Secondary.TNotebook.Tab',
        background=[('selected', COLORS['surface_container']),
                   ('active', COLORS['surface_container_high'])],
        foreground=[('selected', COLORS['primary']),
                   ('active', COLORS['on_surface'])])

    # === 紧凑标签页 ===
    style.configure('Compact.TNotebook.Tab',
        background=COLORS['surface_container'],
        foreground=COLORS['on_surface_variant'],
        font=get_font_tuple('label_medium', bold=True),
        padding=[SPACING['md'], SPACING['xs']],
        borderwidth=0)

    style.map('Compact.TNotebook.Tab',
        background=[('selected', COLORS['surface']),
                   ('active', COLORS['surface_container_high'])],
        foreground=[('selected', COLORS['primary']),
                   ('active', COLORS['on_surface'])])

    # ----------------------------------------------------------------
    # Treeview 样式 - Material Design 3 列表/表格系统
    # ----------------------------------------------------------------

    # === 基础 Treeview ===
    style.configure('Treeview',
        background=COLORS['surface_container'],
        foreground=COLORS['on_surface'],
        fieldbackground=COLORS['surface_container'],
        bordercolor=COLORS['outline_variant'],
        lightcolor=COLORS['outline_variant'],
        darkcolor=COLORS['outline_variant'],
        rowheight=24)

    style.configure('Treeview.Heading',
        background=COLORS['surface_container_high'],
        foreground=COLORS['on_surface'],
        font=get_font_tuple('label_large', bold=True),
        borderwidth=0,
        padding=[SPACING['md'], SPACING['sm']])

    style.map('Treeview',
        background=[('selected', COLORS['primary']),
                   ('active', COLORS['surface_container_high'])],
        foreground=[('selected', COLORS['on_primary'])])

    style.map('Treeview.Heading',
        background=[('active', COLORS['surface_container_highest'])])

    # === 紧凑 Treeview ===
    style.configure('Compact.Treeview',
        background=COLORS['surface_container'],
        foreground=COLORS['on_surface'],
        fieldbackground=COLORS['surface_container'],
        rowheight=20)

    # === 轮廓 Treeview ===
    style.configure('Outlined.Treeview',
        background=COLORS['surface'],
        foreground=COLORS['on_surface'],
        fieldbackground=COLORS['surface'],
        bordercolor=COLORS['outline'],
        lightcolor=COLORS['outline'],
        darkcolor=COLORS['outline'],
        rowheight=24)

    # ----------------------------------------------------------------
    # Scrollbar 样式 - Material Design 3 滚动条
    # ----------------------------------------------------------------

    # === 基础滚动条 ===
    style.configure('TScrollbar',
        background=COLORS['surface_container_high'],
        troughcolor=COLORS['surface_container'],
        arrowcolor=COLORS['on_surface_variant'],
        borderwidth=0,
        arrowsize=12)

    style.map('TScrollbar',
        background=[('active', COLORS['surface_container_highest']),
                   ('pressed', COLORS['primary'])],
        arrowcolor=[('active', COLORS['on_surface'])])

    # === 细滚动条 ===
    style.configure('Thin.TScrollbar',
        background=COLORS['surface_container_high'],
        troughcolor=COLORS['surface_container'],
        arrowcolor=COLORS['on_surface_variant'],
        borderwidth=0,
        arrowsize=10,
        width=8)

    style.map('Thin.TScrollbar',
        background=[('active', COLORS['surface_container_highest']),
                   ('pressed', COLORS['primary'])])

    # ----------------------------------------------------------------
    # Progressbar 样式 - Material Design 3 进度条
    # ----------------------------------------------------------------

    # === 线性进度条 ===
    style.configure('TProgressbar',
        background=COLORS['primary'],
        troughcolor=COLORS['surface_container_high'],
        borderwidth=0,
        lightcolor=COLORS['primary'],
        darkcolor=COLORS['primary'],
        thickness=4)

    # === 粗进度条 ===
    style.configure('Thick.TProgressbar',
        background=COLORS['primary'],
        troughcolor=COLORS['surface_container_high'],
        borderwidth=0,
        lightcolor=COLORS['primary'],
        darkcolor=COLORS['primary'],
        thickness=8)

    # === 成功进度条 ===
    style.configure('Success.TProgressbar',
        background=COLORS['success'],
        troughcolor=COLORS['surface_container_high'],
        borderwidth=0,
        lightcolor=COLORS['success'],
        darkcolor=COLORS['success'])

    # === 警告进度条 ===
    style.configure('Warning.TProgressbar',
        background=COLORS['warning'],
        troughcolor=COLORS['surface_container_high'],
        borderwidth=0,
        lightcolor=COLORS['warning'],
        darkcolor=COLORS['warning'])

    # === 危险进度条 ===
    style.configure('Danger.TProgressbar',
        background=COLORS['danger'],
        troughcolor=COLORS['surface_container_high'],
        borderwidth=0,
        lightcolor=COLORS['danger'],
        darkcolor=COLORS['danger'])

    # ----------------------------------------------------------------
    # Separator 样式 - Material Design 3 分割线
    # ----------------------------------------------------------------
    style.configure('TSeparator',
        background=COLORS['outline_variant'])

    # === 强调分割线 ===
    style.configure('Strong.TSeparator',
        background=COLORS['outline'])

    # ----------------------------------------------------------------
    # PanedWindow 样式 - Material Design 3 分割窗口
    # ----------------------------------------------------------------
    style.configure('TPanedwindow',
        background=COLORS['surface'])

    # ----------------------------------------------------------------
    # Sizegrip 样式 - Material Design 3 尺寸调整手柄
    # ----------------------------------------------------------------
    style.configure('TSizegrip',
        background=COLORS['surface_container_high'])

    return style


# ============================================================================
# tk (非 ttk) 控件配置函数
# ============================================================================

def configure_tk_root(root):
    """
    配置 tk 根窗口

    Args:
        root: tk.Tk 实例
    """
    root.configure(bg=COLORS['surface'])


def configure_listbox(listbox):
    """
    配置 Listbox 控件

    Args:
        listbox: tk.Listbox 实例
    """
    listbox.configure(
        bg=COLORS['surface_container'],
        fg=COLORS['on_surface'],
        selectbackground=COLORS['primary'],
        selectforeground=COLORS['on_primary'],
        font=get_font('body_medium'),
        borderwidth=1,
        relief='flat',
        highlightthickness=0,
        activestyle='none',
        highlightcolor=COLORS['outline_variant']
    )


def configure_scrolledtext(st):
    """
    配置 ScrolledText 控件

    Args:
        st: scrolledtext.ScrolledText 实例
    """
    st.configure(
        bg=COLORS['surface_dim'],
        fg=COLORS['on_surface'],
        insertbackground=COLORS['on_surface'],
        selectbackground=COLORS['primary'],
        selectforeground=COLORS['on_primary'],
        font=(FONTS['family_mono'], FONTS['body_small']),
        borderwidth=1,
        relief='flat',
        padx=SPACING['padding_md'],
        pady=SPACING['padding_md'],
        highlightthickness=1,
        highlightcolor=COLORS['outline_variant'],
        highlightbackground=COLORS['outline_variant']
    )


def configure_canvas(canvas, bg_color=None):
    """
    配置 Canvas 控件

    Args:
        canvas: tk.Canvas 实例
        bg_color: 背景颜色，默认为画布背景色
    """
    if bg_color is None:
        bg_color = COLORS['canvas_bg']
    canvas.configure(
        bg=bg_color,
        highlightthickness=0
    )


def configure_menu(menu):
    """
    配置 Menu 控件

    Args:
        menu: tk.Menu 实例
    """
    menu.configure(
        bg=COLORS['surface_container'],
        fg=COLORS['on_surface'],
        activebackground=COLORS['primary'],
        activeforeground=COLORS['on_primary'],
        font=get_font('body_medium'),
        borderwidth=0,
        relief='flat'
    )


# ============================================================================
# 对话框样式配置 - Material Design 3 对话框系统
# ============================================================================

def create_dialog_style():
    """
    创建对话框样式配置字典

    Returns:
        dict: 对话框样式配置
    """
    return {
        # 背景
        'bg': COLORS['surface_container_high'],
        'fg': COLORS['on_surface'],

        # 标题
        'title_font': get_font_tuple('headline_small', bold=True),
        'title_fg': COLORS['on_surface'],
        'title_bg': COLORS['surface_container_high'],

        # 内容
        'content_font': get_font_tuple('body_medium'),
        'content_fg': COLORS['on_surface_variant'],
        'content_bg': COLORS['surface_container_high'],

        # 按钮
        'button_confirm_style': 'Primary.TButton',
        'button_cancel_style': 'Text.TButton',
        'button_danger_style': 'Danger.TButton',

        # 边框和圆角 (Tkinter 不支持圆角，使用边框模拟)
        'border_color': COLORS['outline_variant'],
        'border_width': 1,

        # 间距
        'padding': SPACING['dialog_padding'],
        'button_spacing': SPACING['sm'],
        'content_spacing': SPACING['lg'],

        # 尺寸
        'min_width': 280,
        'max_width': 560,
        'min_height': 150,
    }


def create_snackbar_style():
    """
    创建 Snackbar 样式配置字典

    Returns:
        dict: Snackbar 样式配置
    """
    return {
        # 背景
        'bg': COLORS['surface_container_highest'],
        'fg': COLORS['on_surface'],

        # 文字
        'font': get_font_tuple('body_medium'),
        'message_fg': COLORS['on_surface'],

        # 按钮
        'action_font': get_font_tuple('label_large', bold=True),
        'action_fg': COLORS['primary'],

        # 间距
        'padding': SPACING['md'],
        'margin': SPACING['lg'],

        # 尺寸
        'min_width': 250,
        'height': 48,

        # 动画
        'duration': DURATION['snackbar'],
        'show_duration_ms': 4000,  # 显示时长 (ms)
    }


def create_tooltip_style():
    """
    创建 Tooltip 样式配置字典

    Returns:
        dict: Tooltip 样式配置
    """
    return {
        # 背景
        'bg': COLORS['inverse_surface'],
        'fg': COLORS['inverse_on_surface'],

        # 文字
        'font': get_font_tuple('body_small'),

        # 间距
        'padding': SPACING['xs'],

        # 延迟
        'show_delay_ms': 500,
        'hide_delay_ms': 100,
    }


# ============================================================================
# 辅助函数
# ============================================================================

def get_tier_color(tier):
    """获取用户层级对应的颜色"""
    return TIER_COLORS.get(tier, COLORS['text_muted'])


def get_status_color(status):
    """
    根据状态获取颜色

    Args:
        status: 状态字符串 ('success', 'warning', 'danger', 'info', 'default')
    """
    status_map = {
        'success': COLORS['success'],
        'warning': COLORS['warning'],
        'danger': COLORS['danger'],
        'error': COLORS['danger'],
        'info': COLORS['info'],
        'default': COLORS['text_secondary'],
        'connected': COLORS['success'],
        'disconnected': COLORS['text_muted'],
        'running': COLORS['success'],
        'stopped': COLORS['text_muted'],
    }
    return status_map.get(status.lower(), COLORS['text_secondary'])


def create_separator(parent, orient='horizontal'):
    """
    创建分割线

    Args:
        parent: 父控件
        orient: 方向 ('horizontal' 或 'vertical')
    """
    import tkinter.ttk as ttk
    return ttk.Separator(parent, orient=orient)