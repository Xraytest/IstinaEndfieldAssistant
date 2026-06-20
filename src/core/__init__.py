"""兼容层 - 从 module 重新导出（完整覆盖）

所有旧路径 from core.xxx import YYY 均重定向到 module/ 版本。
待旧代码全部迁移后，此文件可删除。
"""
from module.logger import *  # noqa
from module.device_state import *  # noqa
from module.adb_utils import *  # noqa
from module.game_data import *  # noqa
from module.vlm import *  # noqa
from module.cloud import *  # noqa
from module.communication import *  # noqa
from module.element_analysis import *  # noqa
from module.local_inference import *  # noqa
from module.ocr import *  # noqa
from module.recognition import *  # noqa
from module.models import *  # noqa
from module.state_machine import *  # noqa
from module.utils import *  # noqa
