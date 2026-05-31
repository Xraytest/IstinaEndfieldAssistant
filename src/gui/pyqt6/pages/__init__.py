"""
Page component module
"""

from .auth_page import AuthPage
from .settings_page import SettingsPage
from .device_settings_page import DeviceSettingsPage
from .cloud_page import CloudPage
from .agent_page import AgentPage
from .model_manager_page import ModelManagerPage
from .standard_reasoning_page import StandardReasoningPage
from .prts_full_intelligence_page import PrtsFullIntelligencePage


__all__ = [
    'AuthPage',
    'SettingsPage',
    'DeviceSettingsPage',
    'CloudPage',
    'AgentPage',
    'ModelManagerPage',
    'StandardReasoningPage',
    'PrtsFullIntelligencePage',
]