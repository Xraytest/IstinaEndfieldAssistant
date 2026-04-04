COLORS = {'primary': '#4285F4', 'primary_hover': '#3367D6', 'primary_light': '#BBDEFB', 'primary_lighter': '#E3F2FD', 'primary_lightest': '#F5FBFF', 'primary_dark': '#1976D2', 'primary_darker': '#0D47A1', 'on_primary': '#FFFFFF', 'on_primary_container': '#1976D2', 'secondary': '#757575', 'secondary_light': '#BDBDBD', 'secondary_dark': '#616161', 'secondary_container': '#F5F5F5', 'on_secondary': '#FFFFFF', 'on_secondary_container': '#424242', 'tertiary': '#03DAC6', 'tertiary_light': '#80DEEA', 'tertiary_dark': '#00ACC1', 'tertiary_container': '#E0F7FA', 'on_tertiary': '#FFFFFF', 'on_tertiary_container': '#00838F', 'success': '#34A853', 'success_light': '#81C784', 'success_dark': '#2E7D32', 'success_container': '#E8F5E9', 'on_success': '#FFFFFF', 'warning': '#FBBC05', 'warning_light': '#FFD54F', 'warning_dark': '#F57C00', 'warning_container': '#FFF3E0', 'on_warning': '#FFFFFF', 'danger': '#EA4335', 'danger_light': '#EF9A9A', 'danger_dark': '#C53929', 'danger_container': '#FFEBEE', 'on_danger': '#FFFFFF', 'info': '#4285F4', 'info_light': '#64B5F6', 'info_dark': '#1976D2', 'info_container': '#E3F2FD', 'on_info': '#FFFFFF', 'bg_primary': '#FFFFFF', 'bg_secondary': '#F5F5F5', 'bg_tertiary': '#EEEEEE', 'bg_card': '#FFFFFF', 'bg_elevated': '#FAFAFA', 'surface': '#FFFFFF', 'surface_dim': '#F5F5F5', 'surface_bright': '#FFFFFF', 'surface_container_lowest': '#FFFFFF', 'surface_container_low': '#F5F5F5', 'surface_container': '#EEEEEE', 'surface_container_high': '#E0E0E0', 'surface_container_highest': '#BDBDBD', 'on_surface': '#212121', 'on_surface_variant': '#757575', 'text_primary': '#333333', 'text_secondary': '#666666', 'text_tertiary': '#999999', 'text_muted': '#BBBBBB', 'text_disabled': '#CCCCCC', 'border_color': '#E8E8E8', 'border_light': '#F0F0F0', 'divider_color': '#E8E8E8', 'outline': '#CCCCCC', 'outline_variant': '#E8E8E8', 'state_hover': 'rgba(0, 0, 0, 0.04)', 'state_focus': 'rgba(0, 0, 0, 0.08)', 'state_press': 'rgba(0, 0, 0, 0.12)', 'state_drag': 'rgba(0, 0, 0, 0.16)', 'primary_state_hover': 'rgba(66, 133, 244, 0.08)', 'primary_state_focus': 'rgba(66, 133, 244, 0.12)', 'primary_state_press': 'rgba(66, 133, 244, 0.16)', 'canvas_bg': '#FAFAFA', 'log_bg': '#FFFFFF', 'selection_bg': '#E8F0FE', 'hover_bg': '#F8F9FA', 'inverse_surface': '#333333', 'inverse_on_surface': '#FFFFFF', 'inverse_primary': '#A0C4FF', 'shadow': 'rgba(0, 0, 0, 0.08)', 'shadow_light': 'rgba(0, 0, 0, 0.04)'}
TIER_COLORS = {'free': COLORS['text_secondary'], 'prime': COLORS['success'], 'plus': COLORS['warning'], 'pro': COLORS['danger']}
FONTS = {'family': 'Microsoft YaHei UI', 'family_fallback': 'Segoe UI', 'family_mono': 'Consolas', 'family_display': 'Microsoft YaHei UI', 'display_large': 32, 'display_medium': 28, 'display_small': 24, 'headline_large': 22, 'headline_medium': 18, 'headline_small': 16, 'title_large': 16, 'title_medium': 14, 'title_small': 12, 'body_large': 14, 'body_medium': 13, 'body_small': 12, 'label_large': 13, 'label_medium': 12, 'label_small': 11, 'size_small': 11, 'size_base': 12, 'size_medium': 13, 'size_large': 14, 'size_xlarge': 16, 'size_title': 16, 'size_header': 18}
FONT_WEIGHTS = {'thin': 100, 'extra_light': 200, 'light': 300, 'regular': 400, 'medium': 500, 'semi_bold': 600, 'bold': 700, 'extra_bold': 800, 'black': 900}
SPACING_UNIT = 4
SPACING = {'none': 0, 'xxxs': 2, 'xxs': 4, 'xs': 6, 'sm': 8, 'md': 12, 'lg': 16, 'xl': 20, 'xxl': 24, 'xxxl': 32, 'component': 8, 'section': 16, 'container': 20, 'padding_xs': 4, 'padding_sm': 8, 'padding_md': 12, 'padding_lg': 16, 'padding_xl': 20, 'margin_xs': 4, 'margin_sm': 8, 'margin_md': 12, 'margin_lg': 16, 'margin_xl': 20, 'icon_text': 6, 'button_padding_h': 16, 'button_padding_v': 8, 'input_padding_h': 12, 'input_padding_v': 8, 'card_padding': 16, 'list_item_padding': 10, 'dialog_padding': 20}
CORNER_RADIUS = {'none': 0, 'xs': 4, 'sm': 6, 'md': 8, 'lg': 12, 'xl': 16, 'xxl': 24, 'full': 9999, 'button': 6, 'button_sm': 4, 'button_lg': 8, 'card': 8, 'card_lg': 12, 'input': 4, 'input_outlined': 4, 'input_filled': 6, 'dialog': 12, 'chip': 16, 'badge': 9999, 'fab': 16, 'menu': 8, 'tooltip': 4, 'snackbar': 8}
ELEVATION = {'level_0': 0, 'level_1': 1, 'level_2': 2, 'level_3': 3, 'level_4': 4, 'level_5': 5, 'card': 1, 'card_hover': 2, 'button': 0, 'button_floating': 3, 'menu': 2, 'dialog': 3, 'drawer': 4, 'modal': 5}
DURATION = {'instant': 0, 'fast': 100, 'normal': 200, 'slow': 300, 'slower': 400, 'hover': 150, 'press': 100, 'fade': 200, 'slide': 300, 'expand': 250, 'dialog': 280, 'snackbar': 250}

def get_font(size_key='size_base', bold=False):
    size = FONTS.get(size_key, 12)
    weight = 'bold' if bold else 'normal'
    return (FONTS['family'], size, weight)

def get_font_tuple(size_key='size_base', bold=False):
    size = FONTS.get(size_key, 12)
    weight = 'bold' if bold else 'normal'
    return (FONTS['family'], size, weight)

def setup_ttk_styles(style=None):
    import tkinter.ttk as ttk
    if style is None:
        style = ttk.Style()
    style.theme_use('clam')
    default_font = get_font_tuple('body_medium')
    bold_font = get_font_tuple('body_medium', bold=True)
    style.configure('TFrame', background=COLORS['surface'])
    style.configure('Surface.TFrame', background=COLORS['surface'])
    style.configure('SurfaceDim.TFrame', background=COLORS['surface_dim'])
    style.configure('SurfaceBright.TFrame', background=COLORS['surface_bright'])
    style.configure('SurfaceContainer.TFrame', background=COLORS['surface_container'])
    style.configure('SurfaceContainerLow.TFrame', background=COLORS['surface_container_low'])
    style.configure('SurfaceContainerHigh.TFrame', background=COLORS['surface_container_high'])
    style.configure('Card.TFrame', background=COLORS['bg_card'])
    style.configure('CardFilled.TFrame', background=COLORS['surface_container_low'])
    style.configure('CardElevated.TFrame', background=COLORS['surface'])
    style.configure('CardOutlined.TFrame', background=COLORS['surface'], bordercolor=COLORS['outline_variant'])
    style.configure('TLabelframe', background=COLORS['surface'], bordercolor=COLORS['border_color'], relief='solid', borderwidth=1)
    style.configure('TLabelframe.Label', background=COLORS['surface'], foreground=COLORS['text_primary'], font=get_font_tuple('title_medium', bold=True))
    style.configure('Card.TLabelframe', background=COLORS['surface'], bordercolor=COLORS['border_color'], relief='solid', borderwidth=1)
    style.configure('Card.TLabelframe.Label', background=COLORS['surface'], foreground=COLORS['primary'], font=get_font_tuple('title_medium', bold=True))
    style.configure('CardFilled.TLabelframe', background=COLORS['surface_container_low'], bordercolor=COLORS['border_color'], relief='solid', borderwidth=1)
    style.configure('CardFilled.TLabelframe.Label', background=COLORS['surface_container_low'], foreground=COLORS['text_primary'], font=get_font_tuple('title_medium', bold=True))
    style.configure('TLabel', background=COLORS['surface'], foreground=COLORS['text_primary'], font=default_font)
    style.configure('Secondary.TLabel', background=COLORS['surface'], foreground=COLORS['text_secondary'], font=default_font)
    style.configure('Muted.TLabel', background=COLORS['surface'], foreground=COLORS['text_secondary'], font=get_font_tuple('body_small'))
    style.configure('Title.TLabel', background=COLORS['surface'], foreground=COLORS['text_primary'], font=get_font_tuple('title_large', bold=True))
    style.configure('Header.TLabel', background=COLORS['surface'], foreground=COLORS['primary'], font=get_font_tuple('headline_small', bold=True))
    style.configure('Status.TLabel', background=COLORS['surface_container_low'], foreground=COLORS['text_secondary'], font=get_font_tuple('body_small'))
    style.configure('Success.TLabel', background=COLORS['surface'], foreground=COLORS['success'], font=default_font)
    style.configure('Warning.TLabel', background=COLORS['surface'], foreground=COLORS['warning'], font=default_font)
    style.configure('Danger.TLabel', background=COLORS['surface'], foreground=COLORS['danger'], font=default_font)
    style.configure('TButton', background=COLORS['surface_container_low'], foreground=COLORS['text_primary'], font=bold_font, borderwidth=1, focuscolor='none', relief='solid', padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))
    style.map('TButton', background=[('active', COLORS['surface_container']), ('pressed', COLORS['surface_container_high']), ('disabled', COLORS['surface_container_low'])], foreground=[('active', COLORS['text_primary']), ('disabled', COLORS['text_disabled'])])
    style.configure('Primary.TButton', background=COLORS['surface_container_low'], foreground=COLORS['text_primary'], font=bold_font, borderwidth=1, focuscolor='none', relief='solid', padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))
    style.map('Primary.TButton', background=[('active', COLORS['surface_container']), ('pressed', COLORS['surface_container_high']), ('disabled', COLORS['surface_container_low'])], foreground=[('active', COLORS['text_primary']), ('disabled', COLORS['text_disabled'])])
    style.configure('Secondary.TButton', background=COLORS['surface_container_low'], foreground=COLORS['text_primary'], font=bold_font, borderwidth=1, focuscolor='none', relief='solid', padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))
    style.map('Secondary.TButton', background=[('active', COLORS['surface_container']), ('pressed', COLORS['surface_container_high']), ('disabled', COLORS['surface_container_low'])], foreground=[('active', COLORS['text_primary']), ('disabled', COLORS['text_disabled'])])
    style.configure('Success.TButton', background=COLORS['surface_container_low'], foreground=COLORS['text_primary'], font=bold_font, borderwidth=1, focuscolor='none', relief='solid', padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))
    style.map('Success.TButton', background=[('active', COLORS['surface_container']), ('pressed', COLORS['surface_container_high']), ('disabled', COLORS['surface_container_low'])], foreground=[('active', COLORS['text_primary']), ('disabled', COLORS['text_disabled'])])
    style.configure('Warning.TButton', background=COLORS['surface_container_low'], foreground=COLORS['text_primary'], font=bold_font, borderwidth=1, focuscolor='none', relief='solid', padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))
    style.map('Warning.TButton', background=[('active', COLORS['surface_container']), ('pressed', COLORS['surface_container_high']), ('disabled', COLORS['surface_container_low'])], foreground=[('active', COLORS['text_primary']), ('disabled', COLORS['text_disabled'])])
    style.configure('Danger.TButton', background=COLORS['surface_container_low'], foreground=COLORS['text_primary'], font=bold_font, borderwidth=1, focuscolor='none', relief='solid', padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))
    style.map('Danger.TButton', background=[('active', COLORS['surface_container']), ('pressed', COLORS['surface_container_high']), ('disabled', COLORS['surface_container_low'])], foreground=[('active', COLORS['text_primary']), ('disabled', COLORS['text_disabled'])])
    style.configure('Outline.TButton', background=COLORS['surface_container_low'], foreground=COLORS['text_primary'], font=bold_font, borderwidth=1, focuscolor='none', relief='solid', padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))
    style.map('Outline.TButton', background=[('active', COLORS['surface_container']), ('pressed', COLORS['surface_container_high']), ('disabled', COLORS['surface_container_low'])], foreground=[('active', COLORS['text_primary']), ('pressed', COLORS['text_primary']), ('disabled', COLORS['text_disabled'])])
    style.configure('OutlineSecondary.TButton', background=COLORS['surface_container_low'], foreground=COLORS['text_primary'], font=bold_font, borderwidth=1, focuscolor='none', relief='solid', padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))
    style.map('OutlineSecondary.TButton', background=[('active', COLORS['surface_container']), ('pressed', COLORS['surface_container_high']), ('disabled', COLORS['surface_container_low'])], foreground=[('active', COLORS['text_primary']), ('pressed', COLORS['text_primary']), ('disabled', COLORS['text_disabled'])])
    style.configure('OutlineDanger.TButton', background=COLORS['surface_container_low'], foreground=COLORS['text_primary'], font=bold_font, borderwidth=1, focuscolor='none', relief='solid', padding=(SPACING['button_padding_h'], SPACING['button_padding_v']))
    style.map('OutlineDanger.TButton', background=[('active', COLORS['surface_container']), ('pressed', COLORS['surface_container_high']), ('disabled', COLORS['surface_container_low'])], foreground=[('active', COLORS['text_primary']), ('pressed', COLORS['text_primary']), ('disabled', COLORS['text_disabled'])])
    style.configure('Text.TButton', background=COLORS['surface_container_low'], foreground=COLORS['text_primary'], font=bold_font, borderwidth=1, focuscolor='none', relief='solid', padding=(SPACING['padding_sm'], SPACING['padding_xs']))
    style.map('Text.TButton', background=[('active', COLORS['surface_container']), ('pressed', COLORS['surface_container_high']), ('disabled', COLORS['surface_container_low'])], foreground=[('active', COLORS['text_primary']), ('pressed', COLORS['text_primary']), ('disabled', COLORS['text_disabled'])])
    style.configure('Small.TButton', background=COLORS['surface_container_low'], foreground=COLORS['text_primary'], font=get_font_tuple('label_medium', bold=True), borderwidth=1, focuscolor='none', relief='solid', padding=(SPACING['padding_sm'], SPACING['padding_xs']))
    style.map('Small.TButton', background=[('active', COLORS['surface_container']), ('pressed', COLORS['surface_container_high'])], foreground=[('active', COLORS['text_primary']), ('pressed', COLORS['text_primary'])])
    style.configure('TEntry', fieldbackground=COLORS['surface'], foreground=COLORS['text_primary'], insertcolor=COLORS['text_primary'], bordercolor=COLORS['border_color'], lightcolor=COLORS['border_color'], darkcolor=COLORS['border_color'], padding=(SPACING['input_padding_h'], SPACING['input_padding_v']))
    style.map('TEntry', fieldbackground=[('focus', COLORS['surface']), ('disabled', COLORS['surface_container_low'])], bordercolor=[('focus', COLORS['primary']), ('disabled', COLORS['border_color'])], lightcolor=[('focus', COLORS['primary']), ('disabled', COLORS['border_color'])], darkcolor=[('focus', COLORS['primary']), ('disabled', COLORS['border_color'])], foreground=[('disabled', COLORS['text_disabled'])])
    style.configure('Outlined.TEntry', fieldbackground=COLORS['surface'], foreground=COLORS['text_primary'], insertcolor=COLORS['text_primary'], bordercolor=COLORS['outline'], lightcolor=COLORS['outline'], darkcolor=COLORS['outline'], padding=(SPACING['input_padding_h'], SPACING['input_padding_v']))
    style.map('Outlined.TEntry', fieldbackground=[('focus', COLORS['surface']), ('disabled', COLORS['surface'])], bordercolor=[('focus', COLORS['primary']), ('disabled', COLORS['border_color'])], lightcolor=[('focus', COLORS['primary']), ('disabled', COLORS['border_color'])], darkcolor=[('focus', COLORS['primary']), ('disabled', COLORS['border_color'])], foreground=[('disabled', COLORS['text_disabled'])])
    style.configure('Error.TEntry', fieldbackground=COLORS['surface'], foreground=COLORS['text_primary'], insertcolor=COLORS['text_primary'], bordercolor=COLORS['danger'], lightcolor=COLORS['danger'], darkcolor=COLORS['danger'], padding=(SPACING['input_padding_h'], SPACING['input_padding_v']))
    style.configure('TCombobox', fieldbackground=COLORS['surface'], background=COLORS['surface_container_low'], foreground=COLORS['text_primary'], arrowcolor=COLORS['text_secondary'], bordercolor=COLORS['border_color'], lightcolor=COLORS['border_color'], darkcolor=COLORS['border_color'], padding=(SPACING['input_padding_h'], SPACING['input_padding_v']))
    style.map('TCombobox', fieldbackground=[('readonly', COLORS['surface']), ('disabled', COLORS['surface_container_low'])], selectbackground=[('readonly', COLORS['primary'])], selectforeground=[('readonly', COLORS['on_primary'])], background=[('disabled', COLORS['surface_container_low'])], foreground=[('disabled', COLORS['text_disabled'])], arrowcolor=[('disabled', COLORS['text_disabled'])])
    style.configure('TSpinbox', fieldbackground=COLORS['surface'], foreground=COLORS['text_primary'], arrowcolor=COLORS['text_secondary'], bordercolor=COLORS['border_color'], lightcolor=COLORS['border_color'], darkcolor=COLORS['border_color'], padding=(SPACING['input_padding_h'], SPACING['input_padding_v']))
    style.map('TSpinbox', fieldbackground=[('disabled', COLORS['surface_container_low'])], foreground=[('disabled', COLORS['text_disabled'])], arrowcolor=[('disabled', COLORS['text_disabled'])], bordercolor=[('focus', COLORS['primary'])], lightcolor=[('focus', COLORS['primary'])], darkcolor=[('focus', COLORS['primary'])])
    style.configure('TCheckbutton', background=COLORS['surface'], foreground=COLORS['text_primary'], font=default_font)
    style.map('TCheckbutton', background=[('active', COLORS['surface_container']), ('selected', COLORS['surface_container_low'])], foreground=[('active', COLORS['text_primary']), ('disabled', COLORS['text_disabled'])], indicatorbackground=[('selected', COLORS['primary'])])
    style.configure('TRadiobutton', background=COLORS['surface'], foreground=COLORS['text_primary'], font=default_font)
    style.map('TRadiobutton', background=[('active', COLORS['surface'])], foreground=[('active', COLORS['text_primary']), ('disabled', COLORS['text_disabled'])])
    style.configure('TNotebook', background=COLORS['surface'], borderwidth=0, tabmargins=[0, 0, 0, 0])
    style.configure('TNotebook.Tab', background=COLORS['surface'], foreground=COLORS['text_secondary'], font=get_font_tuple('label_large', bold=True), padding=[SPACING['xl'], SPACING['md']], borderwidth=0)
    style.map('TNotebook.Tab', background=[('selected', COLORS['surface']), ('active', COLORS['surface'])], foreground=[('selected', COLORS['primary']), ('active', COLORS['text_primary'])])
    style.configure('Secondary.TNotebook', background=COLORS['surface_container_low'], borderwidth=0)
    style.configure('Secondary.TNotebook.Tab', background=COLORS['surface_container_low'], foreground=COLORS['text_secondary'], font=get_font_tuple('label_medium', bold=True), padding=[SPACING['md'], SPACING['sm']], borderwidth=0)
    style.map('Secondary.TNotebook.Tab', background=[('selected', COLORS['surface']), ('active', COLORS['surface_container'])], foreground=[('selected', COLORS['primary']), ('active', COLORS['text_primary'])])
    style.configure('Compact.TNotebook.Tab', background=COLORS['surface'], foreground=COLORS['text_secondary'], font=get_font_tuple('label_medium', bold=True), padding=[SPACING['md'], SPACING['xs']], borderwidth=0)
    style.map('Compact.TNotebook.Tab', background=[('selected', COLORS['surface']), ('active', COLORS['surface'])], foreground=[('selected', COLORS['primary']), ('active', COLORS['text_primary'])])
    style.configure('Treeview', background=COLORS['surface'], foreground=COLORS['text_primary'], fieldbackground=COLORS['surface'], bordercolor=COLORS['border_color'], lightcolor=COLORS['border_color'], darkcolor=COLORS['border_color'], rowheight=28)
    style.configure('Treeview.Heading', background=COLORS['surface_container_low'], foreground=COLORS['text_primary'], font=get_font_tuple('label_large', bold=True), borderwidth=0, padding=[SPACING['md'], SPACING['sm']])
    style.map('Treeview', background=[('selected', COLORS['selection_bg']), ('active', COLORS['surface_container_low'])], foreground=[('selected', COLORS['primary']), ('active', COLORS['text_primary'])])
    style.map('Treeview.Heading', background=[('active', COLORS['surface_container'])])
    style.configure('Compact.Treeview', background=COLORS['surface'], foreground=COLORS['text_primary'], fieldbackground=COLORS['surface'], rowheight=24)
    style.configure('TScrollbar', background=COLORS['surface_container'], troughcolor=COLORS['surface_container_low'], arrowcolor=COLORS['text_secondary'], borderwidth=0, arrowsize=12)
    style.map('TScrollbar', background=[('active', COLORS['surface_container_high']), ('pressed', COLORS['primary'])], arrowcolor=[('active', COLORS['text_primary'])])
    style.configure('Thin.TScrollbar', background=COLORS['surface_container'], troughcolor=COLORS['surface_container_low'], arrowcolor=COLORS['text_secondary'], borderwidth=0, arrowsize=10, width=8)
    style.configure('TProgressbar', background=COLORS['primary'], troughcolor=COLORS['surface_container_low'], borderwidth=0, lightcolor=COLORS['primary'], darkcolor=COLORS['primary'], thickness=4)
    style.configure('Thick.TProgressbar', background=COLORS['primary'], troughcolor=COLORS['surface_container_low'], borderwidth=0, lightcolor=COLORS['primary'], darkcolor=COLORS['primary'], thickness=8)
    style.configure('Success.TProgressbar', background=COLORS['success'], troughcolor=COLORS['surface_container_low'], borderwidth=0, lightcolor=COLORS['success'], darkcolor=COLORS['success'])
    style.configure('Warning.TProgressbar', background=COLORS['warning'], troughcolor=COLORS['surface_container_low'], borderwidth=0, lightcolor=COLORS['warning'], darkcolor=COLORS['warning'])
    style.configure('Danger.TProgressbar', background=COLORS['danger'], troughcolor=COLORS['surface_container_low'], borderwidth=0, lightcolor=COLORS['danger'], darkcolor=COLORS['danger'])
    style.configure('TSeparator', background=COLORS['divider_color'])
    style.configure('Strong.TSeparator', background=COLORS['outline'])
    style.configure('TPanedwindow', background=COLORS['surface'])
    style.configure('TSizegrip', background=COLORS['surface_container'])
    return style

def configure_tk_root(root):
    root.configure(bg=COLORS['surface'])

def configure_listbox(listbox):
    listbox.configure(bg=COLORS['surface'], fg=COLORS['text_primary'], selectbackground=COLORS['selection_bg'], selectforeground=COLORS['primary'], font=get_font('body_medium'), borderwidth=1, relief='solid', highlightthickness=1, activestyle='none', highlightcolor=COLORS['primary'], highlightbackground=COLORS['border_color'])

def configure_scrolledtext(st):
    st.configure(bg=COLORS['surface'], fg=COLORS['text_primary'], insertbackground=COLORS['text_primary'], selectbackground=COLORS['selection_bg'], selectforeground=COLORS['text_primary'], font=(FONTS['family_mono'], FONTS['body_small']), borderwidth=1, relief='solid', padx=SPACING['padding_md'], pady=SPACING['padding_md'], highlightthickness=1, highlightcolor=COLORS['primary'], highlightbackground=COLORS['border_color'])

def configure_canvas(canvas, bg_color=None):
    if bg_color is None:
        bg_color = COLORS['canvas_bg']
    canvas.configure(bg=bg_color, highlightthickness=0)

def configure_menu(menu):
    menu.configure(bg=COLORS['surface'], fg=COLORS['text_primary'], activebackground=COLORS['primary'], activeforeground=COLORS['on_primary'], font=get_font('body_medium'), borderwidth=0, relief='flat')

def create_dialog_style():
    return {'bg': COLORS['surface'], 'fg': COLORS['text_primary'], 'title_font': get_font_tuple('headline_small', bold=True), 'title_fg': COLORS['text_primary'], 'title_bg': COLORS['surface'], 'content_font': get_font_tuple('body_medium'), 'content_fg': COLORS['text_secondary'], 'content_bg': COLORS['surface'], 'button_confirm_style': 'Primary.TButton', 'button_cancel_style': 'Outline.TButton', 'button_danger_style': 'Danger.TButton', 'border_color': COLORS['border_color'], 'border_width': 1, 'padding': SPACING['dialog_padding'], 'button_spacing': SPACING['sm'], 'content_spacing': SPACING['lg'], 'min_width': 280, 'max_width': 560, 'min_height': 150}

def create_snackbar_style():
    return {'bg': COLORS['surface_container_high'], 'fg': COLORS['text_primary'], 'font': get_font_tuple('body_medium'), 'message_fg': COLORS['text_primary'], 'action_font': get_font_tuple('label_large', bold=True), 'action_fg': COLORS['primary'], 'padding': SPACING['md'], 'margin': SPACING['lg'], 'min_width': 250, 'height': 48, 'duration': DURATION['snackbar'], 'show_duration_ms': 4000}

def create_tooltip_style():
    return {'bg': COLORS['inverse_surface'], 'fg': COLORS['inverse_on_surface'], 'font': get_font_tuple('body_small'), 'padding': SPACING['xs'], 'show_delay_ms': 500, 'hide_delay_ms': 100}

def get_tier_color(tier):
    return TIER_COLORS.get(tier, COLORS['text_secondary'])

def get_status_color(status):
    status_map = {'success': COLORS['success'], 'warning': COLORS['warning'], 'danger': COLORS['danger'], 'error': COLORS['danger'], 'info': COLORS['info'], 'default': COLORS['text_secondary'], 'connected': COLORS['success'], 'disconnected': COLORS['text_muted'], 'running': COLORS['success'], 'stopped': COLORS['text_muted']}
    return status_map.get(status.lower(), COLORS['text_secondary'])

def create_separator(parent, orient='horizontal'):
    import tkinter.ttk as ttk
    return ttk.Separator(parent, orient=orient)