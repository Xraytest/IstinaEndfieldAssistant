#!/usr/bin/env python3
"""修复 FlowRecorder 截图保存问题"""

path = r"C:\Users\cheng\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\scripts\standard_flow_engine.py"

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修复 FlowRecorder.__init__ - 添加 device_addr 参数
old_recorder_init = '''class FlowRecorder:
    """增强流程记录器 - 自动截图序列"""

    def __init__(self, session_name: str = "standard_flow", record_video: bool = True):
        self.session_name = session_name
        self.record_video = record_video
        self.steps: List[StepRecord] = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_dir = str(PROJECT_ROOT / "cache" / f"flow_{session_name}_{timestamp}")
        self.screenshots_dir = os.path.join(self.session_dir, "screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)
        print(f"[recorder] 会话目录：{self.session_dir}")
        print(f"[recorder] 截图目录：{self.screenshots_dir}")

    def capture_screenshot(self, step_id: int, action: str) -> str:
        """捕获并保存截图"""
        if not self.record_video:
            return ""

        img = adb_screencap()'''

new_recorder_init = '''class FlowRecorder:
    """增强流程记录器 - 自动截图序列"""

    def __init__(self, session_name: str = "standard_flow", record_video: bool = True, device_addr: str = None):
        self.session_name = session_name
        self.record_video = record_video
        self.device_addr = device_addr
        self.steps: List[StepRecord] = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_dir = str(PROJECT_ROOT / "cache" / f"flow_{session_name}_{timestamp}")
        self.screenshots_dir = os.path.join(self.session_dir, "screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)
        print(f"[recorder] 会话目录：{self.session_dir}")
        print(f"[recorder] 截图目录：{self.screenshots_dir}")
        print(f"[recorder] 设备地址：{device_addr or 'default'}")

    def capture_screenshot(self, step_id: int, action: str) -> str:
        """捕获并保存截图"""
        if not self.record_video:
            return ""

        img = adb_screencap(serial=self.device_addr) if self.device_addr else adb_screencap()'''

if old_recorder_init in content:
    content = content.replace(old_recorder_init, new_recorder_init)
    print("✓ 修复了 FlowRecorder")
else:
    print("✗ 未找到 FlowRecorder")

# 2. 修复 recorder 创建处 - 传递 device_addr
old_recorder_create = '''    # 初始化记录器
    recorder = FlowRecorder(
        session_name=args.flow,
        record_video=not args.no_record
    ) if not args.analyze_only else None'''

new_recorder_create = '''    # 初始化记录器
    recorder = FlowRecorder(
        session_name=args.flow,
        record_video=not args.no_record,
        device_addr=device_addr
    ) if not args.analyze_only else None'''

if old_recorder_create in content:
    content = content.replace(old_recorder_create, new_recorder_create)
    print("✓ 修复了 recorder 创建")
else:
    print("✗ 未找到 recorder 创建处")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ 修复完成")
