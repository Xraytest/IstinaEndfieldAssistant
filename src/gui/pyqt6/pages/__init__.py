"""
Page component module
"""

from .auth_page import AuthPage
from .settings_page import SettingsPage
from .cloud_page import CloudPage
from .agent_page import AgentPage
from .model_manager_page import ModelManagerPage


__all__ = [
    'AuthPage',
    'SettingsPage',
    'CloudPage',
    'AgentPage',
    'ModelManagerPage',
]