"""服务层 — 依赖 capability + foundation 的高层服务模块

包含：device_state（设备状态管理）、cloud（云端/Agent 模块）、
communication（TCP 通信）、element_analysis（元素分析）、
page_analyzer（页面分析）
"""

from .device_state import DeviceStateManager

from .cloud import (
    AgentExecutor,
    ExplorationEngine,
    OptimizedExplorationEngine,
    PageTree,
    PageNode,
    PageEdge,
    UIElement,
    PageState,
    hash_screenshot,
    hash_element,
    CombatController,
    CombatLoop,
    VLMController,
    AuthManager,
    DeviceManager,
    ArknightsEndfieldExceptionDetector,
    TaskExecutionMonitor,
    LogManager,
)

from .communication import ClientCommunicator

from .element_analysis import (
    ElementAnalyzer,
    ElementRepository,
    AnalysisSession,
    TaskAnalyzer,
)

from .page_analyzer import (
    HighPrecisionPageAnalyzer,
    RecognitionEngine,
)

__all__ = [
    # device_state
    "DeviceStateManager",
    # cloud
    "AgentExecutor",
    "ExplorationEngine",
    "OptimizedExplorationEngine",
    "PageTree",
    "PageNode",
    "PageEdge",
    "UIElement",
    "PageState",
    "hash_screenshot",
    "hash_element",
    "CombatController",
    "CombatLoop",
    "VLMController",
    "AuthManager",
    "DeviceManager",
    "ArknightsEndfieldExceptionDetector",
    "TaskExecutionMonitor",
    "LogManager",
    # communication
    "ClientCommunicator",
    # element_analysis
    "ElementAnalyzer",
    "ElementRepository",
    "AnalysisSession",
    "TaskAnalyzer",
    # page_analyzer
    "HighPrecisionPageAnalyzer",
    "RecognitionEngine",
]
