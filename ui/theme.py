"""
ReAcrture 客户端主题模块
基于MAA界面风格 - 浅色主题设计
采用清爽简洁的蓝色主色调
"""

# ============================================================================
# 颜色定义 - MAA风格浅色主题
# ============================================================================

COLORS = {
    # === 主色调系统 (Primary) - 蓝色系 ===
    'primary': '#4285F4',              # 主色 - 柔和蓝色
    'primary_hover': '#3367D6',        # 主色悬停
    'primary_light': '#BBDEFB',        # 主色浅色
    'primary_lighter': '#E3F2FD',      # 主色更浅
    'primary_lightest': '#F5FBFF',     # 主色最浅（背景）
    'primary_dark': '#1976D2',         # 主色深色
    'primary_darker': '#0D47A1',       # 主色更深
    # 主色文字
    'on_primary': '#FFFFFF',           # 主色上的文字
    'on_primary_container': '#1976D2', # 主色容器上的文字

    # === 次级色系统 (Secondary) - 蓝灰色 ===
    'secondary': '#757575',            # 次级色 - 中性灰
    'secondary_light': '#BDBDBD',      # 次级色浅色
    'secondary_dark': '#616161',       # 次级色深色
    'secondary_container': '#F5F5F5',  # 次级色容器
    'on_secondary': '#FFFFFF',         # 次级色上的文字
    'on_secondary_container': '#424242',  # 次级色容器上的文字

    # === 第三色系统 (Tertiary) - 青色 ===
    'tertiary': '#03DAC6',             # 第三色 - 柔和青色
    'tertiary_light': '#80DEEA',       # 第三色浅色
    'tertiary_dark': '#00ACC1',        # 第三色深色
    'tertiary_container': '#E0F7FA',   # 第三色容器
    'on_tertiary': '#FFFFFF',          # 第三色上的文字
    'on_tertiary_container': '#00838F',  # 第三色容器上的文字

    # === 语义颜色 ===
    'success': '#34A853',              # 成功 - 柔和绿色
    'success_light': '#81C784',        # 成功浅色
    'success_dark': '#2E7D32',         # 成功深色
    'success_container': '#E8F5E9',    # 成功容器
    'on_success': '#FFFFFF',           # 成功上的文字

    'warning': '#FBBC05',              # 警告 - 柔和橙色
    'warning_light': '#FFD54F',        # 警告浅色
    'warning_dark': '#F57C00',         # 警告深色
    'warning_container': '#FFF3E0',    # 警告容器
    'on_warning': '#FFFFFF',           # 警告上的文字

    'danger': '#EA4335',               # 危险 - 柔和红色
    'danger_light': '#EF9A9A',         # 危险浅色
    'danger_dark': '#C53929',          # 危险深色
    'danger_container': '#FFEBEE',     # 危险容器
    'on_danger': '#FFFFFF',            # 危险上的文字

    'info': '#4285F4',                 # 信息 - 柔和蓝色
    'info_light': '#64B5F6',           # 信息浅色
    'info_dark': '#1976D2',            # 信息深色
    'info_container': '#E3F2FD',       # 信息容器
    'on_info': '#FFFFFF',              # 信息上的文字

    # === 背景色系统 (浅色主题) ===
    'bg_primary': '#FFFFFF',           # 主背景 - 纯白
    'bg_secondary': '#F5F5F5',         # 次级背景 - 浅灰
    'bg_tertiary': '#EEEEEE',          # 第三级背景 - 更浅灰
    'bg_card': '#FFFFFF',              # 卡片背景
    'bg_elevated': '#FAFAFA',          # 提升背景

    # 表面变体
    'surface': '#FFFFFF',              # 表面色 - 纯白
    'surface_dim': '#F5F5F5',          # 暗淡表面
    'surface_bright': '#FFFFFF',       # 明亮表面
    'surface_container_lowest': '#FFFFFF',  # 最低容器
    'surface_container_low': '#F5F5F5',     # 低容器
    'surface_container': '#EEEEEE',         # 容器
    'surface_container_high': '#E0E0E0',    # 高容器
    'surface_container_highest': '#BDBDBD', # 最高容器

    # 表面文字
    'on_surface': '#212121',           # 表面上的文字 - 深灰
    'on_surface_variant': '#757575',   # 表面变体上的文字 - 中灰

    # === 文字颜色 ===
    'text_primary': '#333333',         # 主文字 - 柔和深灰
    'text_secondary': '#666666',       # 次级文字 - 中灰
    'text_tertiary': '#999999',        # 第三级文字 - 浅灰
    'text_muted': '#BBBBBB',           # 淡化文字
    'text_disabled': '#CCCCCC',        # 禁用文字

    # === 边框和分割线 ===
    'border_color': '#E8E8E8',         # 边框色 - 柔和浅灰
    'border_light': '#F0F0F0',         # 浅边框
    'divider_color': '#E8E8E8',        # 分割线
    'outline': '#CCCCCC',              # 轮廓色
    'outline_variant': '#E8E8E8',      # 轮廓变体

    # === 状态层颜色 (State Layers) ===
    'state_hover': 'rgba(0, 0, 0, 0.04)',    # 悬停状态层
    'state_focus': 'rgba(0, 0, 0, 0.08)',    # 聚焦状态层
    'state_press': 'rgba(0, 0, 0, 0.12)',    # 按压状态层
    'state_drag': 'rgba(0, 0, 0, 0.16)',     # 拖拽状态层
    # 主色状态层
    'primary_state_hover': 'rgba(66, 133, 244, 0.08)',
    'primary_state_focus': 'rgba(66, 133, 244, 0.12)',
    'primary_state_press': 'rgba(66, 133, 244, 0.16)',

    # === 特殊用途 ===
    'canvas_bg': '#FAFAFA',            # 画布背景
    'log_bg': '#FFFFFF',               # 日志背景
    'selection_bg': '#E8F0FE',         # 选中背景 - 柔和浅蓝
    'hover_bg': '#F8F9FA',             # 悬停背景
    'inverse_surface': '#333333',      # 反转表面
    'inverse_on_surface': '#FFFFFF',   # 反转表面上的文字
    'inverse_primary': '#A0C4FF',      # 反转主色

    # === 阴影颜色 ===
    'shadow': 'rgba(0, 0, 0, 0.08)',    # 阴影
    'shadow_light': 'rgba(0, 0, 0, 0.04)',  # 浅阴影
}

# 用户层级颜色
TIER_COLORS = {
    'free': COLORS['text_secondary'],
    'prime': COLORS['success'],
    'plus': COLORS['warning'],
    'pro': COLORS['danger'],
}

# ============================================================================
# 字体定义
# ============================================================================

FONTS = {
    # === 字体族 ===
    'family': 'Microsoft YaHei UI',
    'family_fallback': 'Segoe UI',
    'family_mono': 'Consolas',
    'family_display': 'Microsoft YaHei UI',

    # === 字号系统 ===
    'display_large': 32,
    'display_medium': 28,
    'display_small': 24,

    'headline_large': 22,
    'headline_medium': 18,
    'headline_small': 16,

    'title_large': 16,
    'title_medium': 14,
    'title_small': 12,

    'body_large': 14,
    'body_medium': 13,
    'body_small': 12,

    'label_large': 13,
    'label_medium': 12,
    'label_small': 11,

    # === 兼容旧系统 ===
    'size_small': 11,
    'size_base': 12,
    'size_medium': 13,
    'size_large': 14,
    'size_xlarge': 16,
    'size_title': 16,
    'size_header': 18,
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

# ============================================================================
# 间距定义
# ============================================================================

SPACING_UNIT = 4

SPACING = {
    'none': 0,
    'xxxs': 2,
    'xxs': 4,
    'xs': 6,
    'sm': 8,
    'md': 12,
    'lg': 16,
    'xl': 20,
    'xxl': 24,
    'xxxl': 32,

    'component': 8,
    'section': 16,
    'container': 20,

    'padding_xs': 4,
    'padding_sm': 8,
    'padding_md': 12,
    'padding_lg': 16,
    'padding_xl': 20,

    'margin_xs': 4,
    'margin_sm': 8,
    'margin_md': 12,
    'margin_lg': 16,
    'margin_xl': 20,

    'icon_text': 6,
    'button_padding_h': 16,
    'button_padding_v': 8,
    'input_padding_h': 12,
    'input_padding_v': 8,
    'card_padding': 16,
    'list_item_padding': 10,
    'dialog_padding': 20,
}

# ============================================================================
# 圆角定义
# ============================================================================

CORNER_RADIUS = {
    'none': 0,
    'xs': 4,
    'sm': 6,
    'md': 8,
    'lg': 12,
    'xl': 16,
    'xxl': 24,
    'full': 9999,

    'button': 6,
    'button_sm': 4,
    'button_lg': 8,
    'card': 8,
    'card_lg': 12,
    'input': 4,
    'input_outlined': 4,
    'input_filled': 6,
    'dialog': 12,
    'chip': 16,
    'badge': 9999,
    'fab': 16,
    'menu': 8,
    'tooltip': 4,
    'snackbar': 8,
}

# ============================================================================
# 阴影定义
# ============================================================================

ELEVATION = {
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

DURATION = {
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
# 样式配置辅助函数
# ============================================================================

def get_font(size_key='size_base', bold=False):
    """获取字体配置"""
    size = FONTS.get(size_key, 12)
    weight = 'bold' if bold else 'normal'
    return (FONTS['family'], size, weight)


def get_font_tuple(size_key='size_base', bold=False):
    """获取字体元组（用于ttk样式）"""
    size = FONTS.get(size_key, 12)
    weight = 'bold' if bold else 'normal'
    return (FONTS['family'], size, weight)


# ============================================================================
# ttk 样式配置函数
# ============================================================================

def setup_ttk_styles(style=None):
    """
    配置 ttk 样式 - MAA风格浅色主题
    """
    import tkinter.ttk as ttk

    if style is None:
        style = ttk.Style()

    # 设置整体主题
    style.theme_use('clam')

    # 默认字体
    default_font = get_font_tuple('body_medium')
    bold_font = get_font_tuple('body_medium', bold=True)

    # ----------------------------------------------------------------
    # Frame 样式
    # ----------------------------------------------------------------
    style.configure('TFrame',
        background=COLORS['surface'])

    style.configure('Surface.TFrame',
        background=COLORS['surface'])

    style.configure('SurfaceDim.TFrame',
        background=COLORS['surface_dim'])

    style.configure('SurfaceBright.TFrame',
        background=COLORS['surface_bright'])

    style.configure('SurfaceContainer.TFrame',
        background=COLORS['surface_container'])

    style.configure('SurfaceContainerLow.TFrame',
        background=COLORS['surface_container_low'])

    style.configure('SurfaceContainerHigh.TFrame',
        background=COLORS['surface_container_high'])

    # ----------------------------------------------------------------
    # 卡片样式
    # ----------------------------------------------------------------
    style.configure('Card.TFrame',
        background=COLORS['bg_card'])

    style.configure('CardFilled.TFrame',
        background=COLORS['surface_container_low'])

    style.configure('CardElevated.TFrame',
        background=COLORS['surface'])

    style.configure('CardOutlined.TFrame',
        background=COLORS['surface'],
        bordercolor=COLORS['outline_variant'])

    # ----------------------------------------------------------------
    # LabelFrame 样式 - 卡片容器
    # ----------------------------------------------------------------
    style.configure('TLabelframe',
        background=COLORS['surface'],
        bordercolor=COLORS['border_color'],
        relief='solid',
        borderwidth=1)

    style.configure('TLabelframe.Label',
        background=COLORS['surface'],
        foreground=COLORS['text_primary'],
        font=get_font_tuple('title_medium', bold=True))

    style.configure('Card.TLabelframe',
        background=COLORS['surface'],
        bordercolor=COLORS['border_color'],
        relief='solid',
        borderwidth=1)

    style.configure('Card.TLabelframe.Label',
        background=COLORS['surface'],
        foreground=COLORS['primary'],
        font=get_font_tuple('title_medium', bold=True))

    style.configure('CardFilled.TLabelframe',
        background=COLORS['surface_container_low'],
        bordercolor=COLORS['border_color'],
        relief='solid',
        borderwidth=1)

    style.configure('CardFilled.TLabelframe.Label',
        background=COLORS['surface_container_low'],
        foreground=COLORS['text_primary'],
        font=get_font_tuple('title_medium', bold=True))

    # ----------------------------------------------------------------
    # Label 样式
    # ----------------------------------------------------------------
    style.configure('TLabel',
        background=COLORS['surface'],
        foreground=COLORS['text_primary'],
        font=default_font)

    style.configure('Secondary.TLabel',
        background=COLORS['surface'],
        foreground=COLORS['text_secondary'],
        font=default_font)

    style.configure('Muted.TLabel',
        background=COLORS['surface'],
        foreground=COLORS['text_secondary'],
        font=get_font_tuple('body_small'))

    style.configure('Title.TLabel',
        background=COLORS['surface'],
        foreground=COLORS['text_primary'],
        font=get_font_tuple('title_large', bold=True))

    style.configure('Header.TLabel',
        background=COLORS['surface'],
        foreground=COLORS['primary'],
        font=get_font_tuple('headline_small', bold=True))

    style.configure('Status.TLabel',
        background=COLORS['surface_container_low'],
        foreground=COLORS['text_secondary'],
        font=get_font_tuple('body_small'))

    # 状态标签
    style.configure('Success.TLabel',
        background=COLORS['surface'],
        foreground=COLORS['success'],
        font=default_font)

    style.configure('Warning.TLabel',
        background=COLORS['surface'],
        foreground=COLORS['warning'],
        font=default_font)

    style.configure('Danger.TLabel',
        background=COLORS['surface'],
        foreground=COLORS['danger'],
        font=default_font)

    # ----------------------------------------------------------------
    # Button 样式 - MAA风格（圆角按钮）
    # ----------------------------------------------------------------

    # 默认按钮 - 浅色背景带圆角
    style.configure('TButton',
        background=COLORS['surface_container_low'],
        foreground=COLORS['text_primary'],
        font=bold_font,
        borderwidth=1,
        focuscolor='none',
        relief='solid',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('TButton',
        background=[('active', COLORS['surface_container']),
                   ('pressed', COLORS['surface_container_high']),
                   ('disabled', COLORS['surface_container_low'])],
        foreground=[('active', COLORS['text_primary']),
                   ('disabled', COLORS['text_disabled'])])

    # 主要按钮 - 浅灰色背景带圆角（统一为浅灰色）
    style.configure('Primary.TButton',
        background=COLORS['surface_container_low'],
        foreground=COLORS['text_primary'],
        font=bold_font,
        borderwidth=1,
        focuscolor='none',
        relief='solid',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('Primary.TButton',
        background=[('active', COLORS['surface_container']),
                   ('pressed', COLORS['surface_container_high']),
                   ('disabled', COLORS['surface_container_low'])],
        foreground=[('active', COLORS['text_primary']),
                   ('disabled', COLORS['text_disabled'])])

    # 次级按钮 - 浅灰色背景带圆角（统一为浅灰色）
    style.configure('Secondary.TButton',
        background=COLORS['surface_container_low'],
        foreground=COLORS['text_primary'],
        font=bold_font,
        borderwidth=1,
        focuscolor='none',
        relief='solid',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('Secondary.TButton',
        background=[('active', COLORS['surface_container']),
                   ('pressed', COLORS['surface_container_high']),
                   ('disabled', COLORS['surface_container_low'])],
        foreground=[('active', COLORS['text_primary']),
                   ('disabled', COLORS['text_disabled'])])

    # 成功按钮 - 浅灰色背景带圆角（统一为浅灰色）
    style.configure('Success.TButton',
        background=COLORS['surface_container_low'],
        foreground=COLORS['text_primary'],
        font=bold_font,
        borderwidth=1,
        focuscolor='none',
        relief='solid',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('Success.TButton',
        background=[('active', COLORS['surface_container']),
                   ('pressed', COLORS['surface_container_high']),
                   ('disabled', COLORS['surface_container_low'])],
        foreground=[('active', COLORS['text_primary']),
                   ('disabled', COLORS['text_disabled'])])

    # 警告按钮 - 浅灰色背景带圆角（统一为浅灰色）
    style.configure('Warning.TButton',
        background=COLORS['surface_container_low'],
        foreground=COLORS['text_primary'],
        font=bold_font,
        borderwidth=1,
        focuscolor='none',
        relief='solid',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('Warning.TButton',
        background=[('active', COLORS['surface_container']),
                   ('pressed', COLORS['surface_container_high']),
                   ('disabled', COLORS['surface_container_low'])],
        foreground=[('active', COLORS['text_primary']),
                   ('disabled', COLORS['text_disabled'])])

    # 危险按钮 - 浅灰色背景带圆角（统一为浅灰色）
    style.configure('Danger.TButton',
        background=COLORS['surface_container_low'],
        foreground=COLORS['text_primary'],
        font=bold_font,
        borderwidth=1,
        focuscolor='none',
        relief='solid',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('Danger.TButton',
        background=[('active', COLORS['surface_container']),
                   ('pressed', COLORS['surface_container_high']),
                   ('disabled', COLORS['surface_container_low'])],
        foreground=[('active', COLORS['text_primary']),
                   ('disabled', COLORS['text_disabled'])])

    # 轮廓按钮 - 浅灰色背景带圆角（统一为浅灰色）
    style.configure('Outline.TButton',
        background=COLORS['surface_container_low'],
        foreground=COLORS['text_primary'],
        font=bold_font,
        borderwidth=1,
        focuscolor='none',
        relief='solid',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('Outline.TButton',
        background=[('active', COLORS['surface_container']),
                   ('pressed', COLORS['surface_container_high']),
                   ('disabled', COLORS['surface_container_low'])],
        foreground=[('active', COLORS['text_primary']),
                   ('pressed', COLORS['text_primary']),
                   ('disabled', COLORS['text_disabled'])])

    # 轮廓按钮 - 次级 - 浅灰色背景带圆角（统一为浅灰色）
    style.configure('OutlineSecondary.TButton',
        background=COLORS['surface_container_low'],
        foreground=COLORS['text_primary'],
        font=bold_font,
        borderwidth=1,
        focuscolor='none',
        relief='solid',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('OutlineSecondary.TButton',
        background=[('active', COLORS['surface_container']),
                   ('pressed', COLORS['surface_container_high']),
                   ('disabled', COLORS['surface_container_low'])],
        foreground=[('active', COLORS['text_primary']),
                   ('pressed', COLORS['text_primary']),
                   ('disabled', COLORS['text_disabled'])])

    # 轮廓按钮 - 危险 - 浅灰色背景带圆角（统一为浅灰色）
    style.configure('OutlineDanger.TButton',
        background=COLORS['surface_container_low'],
        foreground=COLORS['text_primary'],
        font=bold_font,
        borderwidth=1,
        focuscolor='none',
        relief='solid',
        padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))

    style.map('OutlineDanger.TButton',
        background=[('active', COLORS['surface_container']),
                   ('pressed', COLORS['surface_container_high']),
                   ('disabled', COLORS['surface_container_low'])],
        foreground=[('active', COLORS['text_primary']),
                   ('pressed', COLORS['text_primary']),
                   ('disabled', COLORS['text_disabled'])])

    # 文本按钮 - 浅灰色背景带圆角（统一为浅灰色）
    style.configure('Text.TButton',
        background=COLORS['surface_container_low'],
        foreground=COLORS['text_primary'],
        font=bold_font,
        borderwidth=1,
        focuscolor='none',
        relief='solid',
        padding=(SPACING['padding_sm'], SPACING['padding_xs']))

    style.map('Text.TButton',
        background=[('active', COLORS['surface_container']),
                   ('pressed', COLORS['surface_container_high']),
                   ('disabled', COLORS['surface_container_low'])],
        foreground=[('active', COLORS['text_primary']),
                   ('pressed', COLORS['text_primary']),
                   ('disabled', COLORS['text_disabled'])])

    # 小型按钮
    style.configure('Small.TButton',
        background=COLORS['surface_container_low'],
        foreground=COLORS['text_primary'],
        font=get_font_tuple('label_medium', bold=True),
        borderwidth=1,
        focuscolor='none',
        relief='solid',
        padding=(SPACING['padding_sm'], SPACING['padding_xs']))

    style.map('Small.TButton',
        background=[('active', COLORS['surface_container']),
                   ('pressed', COLORS['surface_container_high'])],
        foreground=[('active', COLORS['text_primary']),
                   ('pressed', COLORS['text_primary'])])

    # ----------------------------------------------------------------
    # Entry 样式
    # ----------------------------------------------------------------
    style.configure('TEntry',
        fieldbackground=COLORS['surface'],
        foreground=COLORS['text_primary'],
        insertcolor=COLORS['text_primary'],
        bordercolor=COLORS['border_color'],
        lightcolor=COLORS['border_color'],
        darkcolor=COLORS['border_color'],
        padding=(SPACING['input_padding_h'], SPACING['input_padding_v']))

    style.map('TEntry',
        fieldbackground=[('focus', COLORS['surface']),
                        ('disabled', COLORS['surface_container_low'])],
        bordercolor=[('focus', COLORS['primary']),
                    ('disabled', COLORS['border_color'])],
        lightcolor=[('focus', COLORS['primary']),
                   ('disabled', COLORS['border_color'])],
        darkcolor=[('focus', COLORS['primary']),
                  ('disabled', COLORS['border_color'])],
        foreground=[('disabled', COLORS['text_disabled'])])

    # 轮廓输入框
    style.configure('Outlined.TEntry',
        fieldbackground=COLORS['surface'],
        foreground=COLORS['text_primary'],
        insertcolor=COLORS['text_primary'],
        bordercolor=COLORS['outline'],
        lightcolor=COLORS['outline'],
        darkcolor=COLORS['outline'],
        padding=(SPACING['input_padding_h'], SPACING['input_padding_v']))

    style.map('Outlined.TEntry',
        fieldbackground=[('focus', COLORS['surface']),
                        ('disabled', COLORS['surface'])],
        bordercolor=[('focus', COLORS['primary']),
                    ('disabled', COLORS['border_color'])],
        lightcolor=[('focus', COLORS['primary']),
                   ('disabled', COLORS['border_color'])],
        darkcolor=[('focus', COLORS['primary']),
                  ('disabled', COLORS['border_color'])],
        foreground=[('disabled', COLORS['text_disabled'])])

    # 错误状态输入框
    style.configure('Error.TEntry',
        fieldbackground=COLORS['surface'],
        foreground=COLORS['text_primary'],
        insertcolor=COLORS['text_primary'],
        bordercolor=COLORS['danger'],
        lightcolor=COLORS['danger'],
        darkcolor=COLORS['danger'],
        padding=(SPACING['input_padding_h'], SPACING['input_padding_v']))

    # ----------------------------------------------------------------
    # Combobox 样式
    # ----------------------------------------------------------------
    style.configure('TCombobox',
        fieldbackground=COLORS['surface'],
        background=COLORS['surface_container_low'],
        foreground=COLORS['text_primary'],
        arrowcolor=COLORS['text_secondary'],
        bordercolor=COLORS['border_color'],
        lightcolor=COLORS['border_color'],
        darkcolor=COLORS['border_color'],
        padding=(SPACING['input_padding_h'], SPACING['input_padding_v']))

    style.map('TCombobox',
        fieldbackground=[('readonly', COLORS['surface']),
                        ('disabled', COLORS['surface_container_low'])],
        selectbackground=[('readonly', COLORS['primary'])],
        selectforeground=[('readonly', COLORS['on_primary'])],
        background=[('disabled', COLORS['surface_container_low'])],
        foreground=[('disabled', COLORS['text_disabled'])],
        arrowcolor=[('disabled', COLORS['text_disabled'])])

    # ----------------------------------------------------------------
    # Spinbox 样式
    # ----------------------------------------------------------------
    style.configure('TSpinbox',
        fieldbackground=COLORS['surface'],
        foreground=COLORS['text_primary'],
        arrowcolor=COLORS['text_secondary'],
        bordercolor=COLORS['border_color'],
        lightcolor=COLORS['border_color'],
        darkcolor=COLORS['border_color'],
        padding=(SPACING['input_padding_h'], SPACING['input_padding_v']))

    style.map('TSpinbox',
        fieldbackground=[('disabled', COLORS['surface_container_low'])],
        foreground=[('disabled', COLORS['text_disabled'])],
        arrowcolor=[('disabled', COLORS['text_disabled'])],
        bordercolor=[('focus', COLORS['primary'])],
        lightcolor=[('focus', COLORS['primary'])],
        darkcolor=[('focus', COLORS['primary'])])

    # ----------------------------------------------------------------
    # Checkbutton 样式
    # ----------------------------------------------------------------
    style.configure('TCheckbutton',
        background=COLORS['surface'],
        foreground=COLORS['text_primary'],
        font=default_font)

    style.map('TCheckbutton',
        background=[('active', COLORS['surface_container']),
                   ('selected', COLORS['surface_container_low'])],
        foreground=[('active', COLORS['text_primary']),
                   ('disabled', COLORS['text_disabled'])],
        indicatorbackground=[('selected', COLORS['primary'])])

    # ----------------------------------------------------------------
    # Radiobutton 样式
    # ----------------------------------------------------------------
    style.configure('TRadiobutton',
        background=COLORS['surface'],
        foreground=COLORS['text_primary'],
        font=default_font)

    style.map('TRadiobutton',
        background=[('active', COLORS['surface'])],
        foreground=[('active', COLORS['text_primary']),
                   ('disabled', COLORS['text_disabled'])])

    # ----------------------------------------------------------------
    # Notebook 样式 - MAA风格标签页
    # ----------------------------------------------------------------

    # 主标签页容器
    style.configure('TNotebook',
        background=COLORS['surface'],
        borderwidth=0,
        tabmargins=[0, 0, 0, 0])

    # 默认标签页 - MAA风格蓝色下划线
    style.configure('TNotebook.Tab',
        background=COLORS['surface'],
        foreground=COLORS['text_secondary'],
        font=get_font_tuple('label_large', bold=True),
        padding=[SPACING['xl'], SPACING['md']],
        borderwidth=0)

    style.map('TNotebook.Tab',
        background=[('selected', COLORS['surface']),
                   ('active', COLORS['surface'])],
        foreground=[('selected', COLORS['primary']),
                   ('active', COLORS['text_primary'])])

    # 次级标签页
    style.configure('Secondary.TNotebook',
        background=COLORS['surface_container_low'],
        borderwidth=0)

    style.configure('Secondary.TNotebook.Tab',
        background=COLORS['surface_container_low'],
        foreground=COLORS['text_secondary'],
        font=get_font_tuple('label_medium', bold=True),
        padding=[SPACING['md'], SPACING['sm']],
        borderwidth=0)

    style.map('Secondary.TNotebook.Tab',
        background=[('selected', COLORS['surface']),
                   ('active', COLORS['surface_container'])],
        foreground=[('selected', COLORS['primary']),
                   ('active', COLORS['text_primary'])])

    # 紧凑标签页
    style.configure('Compact.TNotebook.Tab',
        background=COLORS['surface'],
        foreground=COLORS['text_secondary'],
        font=get_font_tuple('label_medium', bold=True),
        padding=[SPACING['md'], SPACING['xs']],
        borderwidth=0)

    style.map('Compact.TNotebook.Tab',
        background=[('selected', COLORS['surface']),
                   ('active', COLORS['surface'])],
        foreground=[('selected', COLORS['primary']),
                   ('active', COLORS['text_primary'])])

    # ----------------------------------------------------------------
    # Treeview 样式
    # ----------------------------------------------------------------
    style.configure('Treeview',
        background=COLORS['surface'],
        foreground=COLORS['text_primary'],
        fieldbackground=COLORS['surface'],
        bordercolor=COLORS['border_color'],
        lightcolor=COLORS['border_color'],
        darkcolor=COLORS['border_color'],
        rowheight=28)

    style.configure('Treeview.Heading',
        background=COLORS['surface_container_low'],
        foreground=COLORS['text_primary'],
        font=get_font_tuple('label_large', bold=True),
        borderwidth=0,
        padding=[SPACING['md'], SPACING['sm']])

    style.map('Treeview',
        background=[('selected', COLORS['selection_bg']),
                   ('active', COLORS['surface_container_low'])],
        foreground=[('selected', COLORS['primary']),
                   ('active', COLORS['text_primary'])])

    style.map('Treeview.Heading',
        background=[('active', COLORS['surface_container'])])

    # 紧凑 Treeview
    style.configure('Compact.Treeview',
        background=COLORS['surface'],
        foreground=COLORS['text_primary'],
        fieldbackground=COLORS['surface'],
        rowheight=24)

    # ----------------------------------------------------------------
    # Scrollbar 样式
    # ----------------------------------------------------------------
    style.configure('TScrollbar',
        background=COLORS['surface_container'],
        troughcolor=COLORS['surface_container_low'],
        arrowcolor=COLORS['text_secondary'],
        borderwidth=0,
        arrowsize=12)

    style.map('TScrollbar',
        background=[('active', COLORS['surface_container_high']),
                   ('pressed', COLORS['primary'])],
        arrowcolor=[('active', COLORS['text_primary'])])

    # 细滚动条
    style.configure('Thin.TScrollbar',
        background=COLORS['surface_container'],
        troughcolor=COLORS['surface_container_low'],
        arrowcolor=COLORS['text_secondary'],
        borderwidth=0,
        arrowsize=10,
        width=8)

    # ----------------------------------------------------------------
    # Progressbar 样式
    # ----------------------------------------------------------------
    style.configure('TProgressbar',
        background=COLORS['primary'],
        troughcolor=COLORS['surface_container_low'],
        borderwidth=0,
        lightcolor=COLORS['primary'],
        darkcolor=COLORS['primary'],
        thickness=4)

    style.configure('Thick.TProgressbar',
        background=COLORS['primary'],
        troughcolor=COLORS['surface_container_low'],
        borderwidth=0,
        lightcolor=COLORS['primary'],
        darkcolor=COLORS['primary'],
        thickness=8)

    style.configure('Success.TProgressbar',
        background=COLORS['success'],
        troughcolor=COLORS['surface_container_low'],
        borderwidth=0,
        lightcolor=COLORS['success'],
        darkcolor=COLORS['success'])

    style.configure('Warning.TProgressbar',
        background=COLORS['warning'],
        troughcolor=COLORS['surface_container_low'],
        borderwidth=0,
        lightcolor=COLORS['warning'],
        darkcolor=COLORS['warning'])

    style.configure('Danger.TProgressbar',
        background=COLORS['danger'],
        troughcolor=COLORS['surface_container_low'],
        borderwidth=0,
        lightcolor=COLORS['danger'],
        darkcolor=COLORS['danger'])

    # ----------------------------------------------------------------
    # Separator 样式
    # ----------------------------------------------------------------
    style.configure('TSeparator',
        background=COLORS['divider_color'])

    style.configure('Strong.TSeparator',
        background=COLORS['outline'])

    # ----------------------------------------------------------------
    # PanedWindow 样式
    # ----------------------------------------------------------------
    style.configure('TPanedwindow',
        background=COLORS['surface'])

    # ----------------------------------------------------------------
    # Sizegrip 样式
    # ----------------------------------------------------------------
    style.configure('TSizegrip',
        background=COLORS['surface_container'])

    return style


# ============================================================================
# tk (非 ttk) 控件配置函数
# ============================================================================

def configure_tk_root(root):
    """
    配置 tk 根窗口
    """
    root.configure(bg=COLORS['surface'])


def configure_listbox(listbox):
    """
    配置 Listbox 控件 - MAA风格
    """
    listbox.configure(
        bg=COLORS['surface'],
        fg=COLORS['text_primary'],
        selectbackground=COLORS['selection_bg'],
        selectforeground=COLORS['primary'],
        font=get_font('body_medium'),
        borderwidth=1,
        relief='solid',
        highlightthickness=1,
        activestyle='none',
        highlightcolor=COLORS['primary'],
        highlightbackground=COLORS['border_color']
    )


def configure_scrolledtext(st):
    """
    配置 ScrolledText 控件
    """
    st.configure(
        bg=COLORS['surface'],
        fg=COLORS['text_primary'],
        insertbackground=COLORS['text_primary'],
        selectbackground=COLORS['selection_bg'],
        selectforeground=COLORS['text_primary'],
        font=(FONTS['family_mono'], FONTS['body_small']),
        borderwidth=1,
        relief='solid',
        padx=SPACING['padding_md'],
        pady=SPACING['padding_md'],
        highlightthickness=1,
        highlightcolor=COLORS['primary'],
        highlightbackground=COLORS['border_color']
    )


def configure_canvas(canvas, bg_color=None):
    """
    配置 Canvas 控件
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
    """
    menu.configure(
        bg=COLORS['surface'],
        fg=COLORS['text_primary'],
        activebackground=COLORS['primary'],
        activeforeground=COLORS['on_primary'],
        font=get_font('body_medium'),
        borderwidth=0,
        relief='flat'
    )


# ============================================================================
# 对话框样式配置
# ============================================================================

def create_dialog_style():
    """
    创建对话框样式配置字典
    """
    return {
        'bg': COLORS['surface'],
        'fg': COLORS['text_primary'],
        'title_font': get_font_tuple('headline_small', bold=True),
        'title_fg': COLORS['text_primary'],
        'title_bg': COLORS['surface'],
        'content_font': get_font_tuple('body_medium'),
        'content_fg': COLORS['text_secondary'],
        'content_bg': COLORS['surface'],
        'button_confirm_style': 'Primary.TButton',
        'button_cancel_style': 'Outline.TButton',
        'button_danger_style': 'Danger.TButton',
        'border_color': COLORS['border_color'],
        'border_width': 1,
        'padding': SPACING['dialog_padding'],
        'button_spacing': SPACING['sm'],
        'content_spacing': SPACING['lg'],
        'min_width': 280,
        'max_width': 560,
        'min_height': 150,
    }


def create_snackbar_style():
    """
    创建 Snackbar 样式配置字典
    """
    return {
        'bg': COLORS['surface_container_high'],
        'fg': COLORS['text_primary'],
        'font': get_font_tuple('body_medium'),
        'message_fg': COLORS['text_primary'],
        'action_font': get_font_tuple('label_large', bold=True),
        'action_fg': COLORS['primary'],
        'padding': SPACING['md'],
        'margin': SPACING['lg'],
        'min_width': 250,
        'height': 48,
        'duration': DURATION['snackbar'],
        'show_duration_ms': 4000,
    }


def create_tooltip_style():
    """
    创建 Tooltip 样式配置字典
    """
    return {
        'bg': COLORS['inverse_surface'],
        'fg': COLORS['inverse_on_surface'],
        'font': get_font_tuple('body_small'),
        'padding': SPACING['xs'],
        'show_delay_ms': 500,
        'hide_delay_ms': 100,
    }


# ============================================================================
# 辅助函数
# ============================================================================

def get_tier_color(tier):
    """获取用户层级对应的颜色"""
    return TIER_COLORS.get(tier, COLORS['text_secondary'])


def get_status_color(status):
    """
    根据状态获取颜色
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
    """
    import tkinter.ttk as ttk
    return ttk.Separator(parent, orient=orient)
