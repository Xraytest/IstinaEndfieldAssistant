"""能力层 — 依赖 foundation 的底层能力模块

包含：device（设备管理）、screenshot（截图）、adb_utils（ADB 工具）、
ocr（OCR 识别）、recognition（多源融合识别）、state_machine（状态机）、
local_inference（本地推理）、vlm（VLM 客户端）
"""

from .device import (
    ADBDeviceManager,
    AdbDeviceInfo,
    TouchManager,
    TouchDeviceType,
    MaaFwTouchExecutor,
    MaaFwTouchConfig,
)

from .screenshot import ScreenCapture

from .adb_utils import (
    ADB,
    adb_screencap,
    list_devices,
    _adb_cmd,
    check_device,
)

from .ocr import (
    OCRManager,
    ScreenDecider,
    ScreenState,
)

from .recognition import (
    RecognitionEngine,
    PREDEFINED_STATES,
    SmartElementDetector,
)

from .state_machine import (
    StateMachineExecutor,
    ExecutionState,
)

from .local_inference import (
    InferenceManager,
    LocalInferenceEngine,
    ModelManager,
    PromptCache,
    GPUInfo,
    GPUChecker,
    check_gpu,
    is_gpu_sufficient,
    AsyncInferenceWorker,
    RealtimeInferenceEngine,
)

from .vlm import (
    VLMClient,
    create_vlm_client,
    vlm_analyze,
    VLMOptions,
)

__all__ = [
    # device
    "ADBDeviceManager",
    "AdbDeviceInfo",
    "TouchManager",
    "TouchDeviceType",
    "MaaFwTouchExecutor",
    "MaaFwTouchConfig",
    # screenshot
    "ScreenCapture",
    # adb_utils
    "ADB",
    "adb_screencap",
    "list_devices",
    "_adb_cmd",
    "check_device",
    # ocr
    "OCRManager",
    "ScreenDecider",
    "ScreenState",
    # recognition
    "RecognitionEngine",
    "PREDEFINED_STATES",
    "SmartElementDetector",
    # state_machine
    "StateMachineExecutor",
    "ExecutionState",
    # local_inference
    "InferenceManager",
    "LocalInferenceEngine",
    "ModelManager",
    "PromptCache",
    "GPUInfo",
    "GPUChecker",
    "check_gpu",
    "is_gpu_sufficient",
    "AsyncInferenceWorker",
    "RealtimeInferenceEngine",
    # vlm
    "VLMClient",
    "create_vlm_client",
    "vlm_analyze",
    "VLMOptions",
]
