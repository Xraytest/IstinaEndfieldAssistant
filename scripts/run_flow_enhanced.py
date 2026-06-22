#!/usr/bin/env python3
"""
标准流执行器 v3 - 完整集成 OCR + 状态机 + 增强 check 动作

在真实设备上执行标准流，支持：
1. PaddleOCR 本地识别
2. 状态机扩展（loop/check/find_and_click）
3. 增强的 check 动作（OCR + 页面分析器双模式）
4. 视觉分析
"""

import sys
import os
import argparse
import json
from pathlib import Path
from typing import Dict, Any

from _path_setup import PROJECT_ROOT, SRC_DIR, MODULE_DIR, ensure_path
ensure_path()

PROJECT_ROOT = PROJECT_ROOT
SRC_DIR = SRC_DIR

from standard_flow_engine import FlowConfig, FlowRecorder, Local2BEngine
from core.adb_utils import ADB, adb_screencap, list_devices

# MaaFw 触控
try:
    from device.touch.maafw_touch_adapter import MaaFwTouchExecutor, MaaFwTouchConfig
    MAAFW_AVAILABLE = True
except ImportError:
    MaaFwTouchExecutor = None
    MAAFW_AVAILABLE = False

# OCR 和状态机
try:
    from core.ocr.ocr_manager import OCRManager
    OCR_MANAGER_AVAILABLE = True
except ImportError:
    OCRManager = None
    OCR_MANAGER_AVAILABLE = False

try:
    from flow_state_machine import FlowStateMachine
    STATE_MACHINE_AVAILABLE = True
except ImportError:
    FlowStateMachine = None
    STATE_MACHINE_AVAILABLE = False


class EnhancedFlowExecutor:
    """增强的标准流执行器 - 集成 OCR + 状态机"""
    
    def __init__(self, config: FlowConfig, device_serial: str, use_ocr: bool = False, use_state_machine: bool = False):
        self.config = config
        self.device_serial = device_serial
        self.adb = ADB(serial=device_serial)
        self.use_ocr = use_ocr
        self.use_state_machine = use_state_machine
        
        # 初始化 MaaFw 触控
        self._maafw = None
        if MAAFW_AVAILABLE:
            try:
                maafw_config = MaaFwTouchConfig(
                    adb_path=str(PROJECT_ROOT / "3rd-party" / "adb" / "adb.exe"),
                    address=device_serial,
                    screencap_methods=MaaFwTouchConfig.SCREENCAP_ADB_SHELL,
                    input_methods=2,  # MiniTouch
                )
                self._maafw = MaaFwTouchExecutor(maafw_config)
                if self._maafw.connect():
                    print(f"[MaaFw] 触控初始化成功，分辨率：{self._maafw.get_resolution()}")
                else:
                    print("[MaaFw] 连接失败")
            except Exception as e:
                print(f"[MaaFw] 初始化异常：{e}")

        # 初始化 OCR 管理器
        self.ocr_manager = None
        if use_ocr and OCR_MANAGER_AVAILABLE:
            try:
                self.ocr_manager = OCRManager()
                print(f"[OCR] OCR 管理器初始化成功（MaaFw 内置 OCR）")
            except Exception as e:
                print(f"[OCR] 初始化失败：{e}")
                self.use_ocr = False
        
        # 初始化状态机
        self.state_machine = None
        if use_state_machine and STATE_MACHINE_AVAILABLE:
            try:
                self.state_machine = FlowStateMachine(ocr_manager=self.ocr_manager, device_manager=self)
                print(f"[StateMachine] 状态机扩展已启用")
            except Exception as e:
                print(f"[StateMachine] 初始化失败：{e}")
                self.use_state_machine = False
    
    def _tap(self, x: int, y: int):
        """点击 - 使用 MaaFw"""
        if self._maafw and self._maafw.connected:
            self._maafw.safe_press(x, y)
        else:
            # ADB 回退
            import subprocess
            subprocess.run(["adb", "-s", self.device_serial, "shell", "input", "tap", str(x), str(y)])
    
    def _swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300):
        """滑动 - 使用 MaaFw"""
        if self._maafw and self._maafw.connected:
            self._maafw.safe_swipe(x1, y1, x2, y2, duration)
        else:
            # ADB 回退
            import subprocess
            subprocess.run(["adb", "-s", self.device_serial, "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)])
    
    def _back(self):
        """返回 - 使用 MaaFw"""
        if self._maafw and self._maafw.connected:
            job = self._maafw.post_keyevent(4)  # KEYCODE_BACK
            if job:
                job.wait()
        else:
            # ADB 回退
            import subprocess
            subprocess.run(["adb", "-s", self.device_serial, "shell", "input", "keyevent", "4"])
    
    def _check_page_type(self, step_cfg: Dict[str, Any]) -> bool:
        """
        增强的 check 动作 - 使用 OCR + 页面分析器
        
        Returns:
            bool: 检查是否成功
        """
        success = False
        page_type = "unknown"
        
        # 优先使用 OCR 管理器
        if self.ocr_manager:
            try:
                print(f"  [CHECK] 使用 OCR 管理器检测页面...")
                state = self.ocr_manager.capture_and_recognize(self.device_serial)
                page_type = state.page_type
                description = state.description
                print(f"  [CHECK] 页面={page_type} 描述={description}")
                
                expected = step_cfg.get("expect")
                if expected:
                    world_types = ("world", "world_transition", "world_map", "explore")
                    if page_type == expected or (expected == "world" and page_type in world_types):
                        print(f"  [OK] 页面匹配预期：{expected}")
                        success = True
                    else:
                        print(f"  [WARN] 页面不匹配：期望={expected} 实际={page_type}")
                else:
                    if page_type not in ("error", "unknown"):
                        success = True
                        print(f"  [OK] 页面类型：{page_type}")
                
            except Exception as e:
                print(f"  [WARN] OCR 检测失败：{e}")
        
        return success
    
    def execute_flow(self, flow_name: str) -> bool:
        """执行标准流"""
        flow_config = self.config.get_flow(flow_name)
        if not flow_config:
            print(f"[ERROR] 未找到流程：{flow_name}")
            return False
        
        steps = flow_config.get("steps", [])
        nav_coords = self.config.get_variable("nav_coords", {})
        
        print(f"\n{'='*60}")
        print(f"执行：{flow_name}")
        print(f"步骤：{len(steps)}")
        print(f"{'='*60}\n")
        
        all_success = True
        
        for i, step_cfg in enumerate(steps):
            step_id = i + 1
            step_action = step_cfg.get("action", "none")
            step_desc = step_cfg.get("desc", str(step_cfg))
            
            print(f"\n[步骤 {step_id}/{len(steps)}] {step_desc}")
            print("-" * 50)
            
            success = False
            
            if step_action == "check":
                # 使用增强的 check
                success = self._check_page_type(step_cfg)
            
            elif step_action == "tap":
                coords = step_cfg.get("coords", [540, 360])
                if isinstance(coords, str) and "{{" in coords:
                    var_key = coords.strip("{}")
                    coords = nav_coords.get(var_key, [540, 360])
                
                print(f"  [TAP] {coords}")
                self._tap(coords[0], coords[1])
                self.adb.wait(1)
                success = True
            
            elif step_action == "swipe":
                start = step_cfg.get("start", [200, 1700])
                end = step_cfg.get("end", [200, 1400])
                duration = step_cfg.get("duration", 1000)
                print(f"  [SWIPE] {start} -> {end}")
                self._swipe(start[0], start[1], end[0], end[1], duration)
                self.adb.wait(1)
                success = True
            
            elif step_action == "claim":
                coords = nav_coords.get("claim_all", [810, 900])
                print(f"  [CLAIM] {coords}")
                self._tap(coords[0], coords[1])
                self.adb.wait(2)
                success = True
            
            elif step_action == "back":
                print(f"  [BACK]")
                self._back()
                self.adb.wait(1)
                success = True
            
            elif step_action == "wait":
                duration = step_cfg.get("duration", 2)
                print(f"  [WAIT] {duration}s")
                self.adb.wait(duration)
                success = True
            
            else:
                print(f"  [WARN] 未知动作：{step_action}")
                success = True
            
            status = "OK" if success else "FAIL"
            print(f"  [{status}]\n")
            
            if not success:
                all_success = False
        
        return all_success


def main():
    parser = argparse.ArgumentParser(description="标准流执行器 v3 - 增强版")
    parser.add_argument("--flow", type=str, default="daily_quest", help="流程名称")
    parser.add_argument("--device", type=str, default=None, help="设备序列号")
    parser.add_argument("--use-ocr", action="store_true", help="启用 OCR")
    parser.add_argument("--use-state-machine", action="store_true", help="启用状态机")
    parser.add_argument("--list-devices", action="store_true", help="列出设备")
    
    args = parser.parse_args()
    
    if args.list_devices:
        devices = list_devices()
        print("可用设备:")
        for d in devices:
            print(f"  - {d}")
        return 0
    
    device_serial = args.device or list_devices()[0]
    print(f"[设备] {device_serial}")
    
    # 检查连接
    adb = ADB(serial=device_serial)
    if not adb.check_connection():
        print(f"[ERROR] 设备未连接")
        return 1
    
    # 加载配置
    config = FlowConfig()
    
    # 创建执行器
    executor = EnhancedFlowExecutor(
        config=config,
        device_serial=device_serial,
        use_ocr=args.use_ocr,
        use_state_machine=args.use_state_machine
    )
    
    # 执行流程
    print(f"\n开始执行 {args.flow}...")
    success = executor.execute_flow(args.flow)
    
    print(f"\n流程完成：{'成功' if success else '有失败步骤'}")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
