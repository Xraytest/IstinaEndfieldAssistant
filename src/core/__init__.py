"""IstinaAI 核心模块 — 三层嵌套架构

foundation/  基础层：utils, logger, models, game_data（无内部依赖）
capability/  能力层：device, screenshot, adb_utils, ocr, recognition, state_machine, local_inference, vlm
service/     服务层：element_analysis, page_analyzer, device_state, cloud, communication

旧导入路径 from core.xxx import YYY 仍然有效（通过各层 __init__.py 链式导出）。
"""

# foundation 层
from .foundation import *  # noqa

# capability 层
from .capability import *  # noqa

# service 层
from .service import *  # noqa
