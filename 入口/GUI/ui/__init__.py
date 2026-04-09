"""用户界面层"""

from .theme import setup_ttk_styles, configure_tk_root, COLORS
from .managers import (
    MainGUIManager,
    AuthManagerGUI,
    DeviceManagerGUI,
    TaskManagerGUI,
    CloudServiceManagerGUI,
    SettingsManagerGUI
)

__all__ = [
    'setup_ttk_styles', 'configure_tk_root', 'COLORS',
    'MainGUIManager', 'AuthManagerGUI', 'DeviceManagerGUI',
    'TaskManagerGUI', 'CloudServiceManagerGUI', 'SettingsManagerGUI'
]
