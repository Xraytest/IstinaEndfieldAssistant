#!/usr/bin/env python3
"""修复 standard_flow_engine.py 中的 device_addr 作用域和 MaaFw 配置问题"""

path = r"C:\Users\cheng\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\scripts\standard_flow_engine.py"

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修复 StandardFlowExecutor.__init__ - 添加 device_addr 和 adb_path 参数
old_init = '''    def __init__(self, config: FlowConfig, model_engine: Local2BEngine = None, recorder: FlowRecorder = None):
        self.config = config
        self.model = model_engine or Local2BEngine()
        self.recorder = recorder
        self.adb = ADB()
        self._stop_requested = False

        # 初始化 MaaFramework 触控（所有触控必须通过 MaaFw 而非直接 ADB）
        self._maafw = None
        if MAAFW_AVAILABLE:
            try:
                project_root = str(PROJECT_ROOT)
                adb_path = str(PROJECT_ROOT / "3rd-party" / "adb" / "adb.exe")
                maafw_config = MaaFwTouchConfig(
                    adb_path=adb_path,
                    address=f'{device_addr}',
                    screencap_methods=MaaFwTouchConfig.SCREENCAP_ADB_SHELL,
                    input_methods=MaaFwTouchConfig.INPUT_ADB_SHELL,
                )'''

new_init = '''    def __init__(self, config: FlowConfig, model_engine: Local2BEngine = None, recorder: FlowRecorder = None, 
                 device_addr: str = "localhost:16512", adb_path: str = None):
        self.config = config
        self.model = model_engine or Local2BEngine()
        self.recorder = recorder
        self.device_addr = device_addr
        self.adb_path = adb_path or str(PROJECT_ROOT / "3rd-party" / "adb" / "adb.exe")
        self.adb = ADB(device_addr)
        self._stop_requested = False

        # 初始化 MaaFramework 触控（所有触控必须通过 MaaFw 而非直接 ADB）
        self._maafw = None
        if MAAFW_AVAILABLE:
            try:
                maafw_config = MaaFwTouchConfig(
                    adb_path=self.adb_path,
                    address=device_addr,
                    screencap_methods=MaaFwTouchConfig.SCREENCAP_ADB_SHELL,
                    input_methods=3,  # MaaTouch 模式
                )'''

if old_init in content:
    content = content.replace(old_init, new_init)
    print("✓ 修复了 StandardFlowExecutor.__init__")
else:
    print("✗ 未找到 StandardFlowExecutor.__init__")

# 2. 修复 executor 创建处 - 传递 device_addr 和 adb_path
old_executor = '''    # 正常执行模式
    executor = StandardFlowExecutor(config, engine, recorder)

    # ADB 路径（用于前置导航）
    adb_path = str(PROJECT_ROOT / "3rd-party" / "adb" / "adb.exe")'''

new_executor = '''    # 正常执行模式
    adb_path = str(PROJECT_ROOT / "3rd-party" / "adb" / "adb.exe")
    executor = StandardFlowExecutor(config, engine, recorder, device_addr, adb_path)'''

if old_executor in content:
    content = content.replace(old_executor, new_executor)
    print("✓ 修复了 executor 创建")
else:
    print("✗ 未找到 executor 创建处")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ 修复完成")
