"""
触控执行调试脚本 - 验证触控在任务链中的真实执行效果

使用方法：
1. PC设备测试：python -m client.test_scripts.test_touch_execution --mode pc --window-title "Endfield"
2. Android设备测试：python -m client.test_scripts.test_touch_execution --mode android --device-serial <serial>

验证方式：
- 执行前后截图对比
- 通过task_cycle_analyse.py分析截图验证触控效果
"""
import os
import sys
import time
import argparse
import base64
from datetime import datetime
from typing import Optional, List, Dict, Any

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
client_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(client_dir)
if client_dir not in sys.path:
    sys.path.insert(0, client_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入客户端组件
from client.core.logger import init_logger, get_logger, LogCategory

# PC设备支持 - 使用MaaFramework库
try:
    from client.core.touch import MaaFwWin32Executor, MaaFwWin32Config
    from maa.define import MaaWin32ScreencapMethodEnum, MaaWin32InputMethodEnum
    PC_CONTROLLER_AVAILABLE = True
except ImportError as e:
    PC_CONTROLLER_AVAILABLE = False
    print(f"[警告] MaaFwWin32Executor导入失败: {e}")

# Android设备支持
try:
    from client.core.adb_manager import ADBDeviceManager
    from client.core.touch import MaaFwTouchExecutor, MaaFwTouchConfig
    from client.core.screen_capture import ScreenCapture
    ANDROID_CONTROLLER_AVAILABLE = True
except ImportError as e:
    ANDROID_CONTROLLER_AVAILABLE = False
    print(f"[警告] Android组件导入失败: {e}")


class TouchExecutionDebugger:
    """触控执行调试器"""
    
    def __init__(self, output_dir: str = None):
        """初始化调试器"""
        self.output_dir = output_dir or os.path.join(client_dir, "debug_output", f"touch_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化日志
        log_config_path = os.path.join(client_dir, "config", "logging_config.json")
        if os.path.exists(log_config_path):
            init_logger(log_config_path)
        self.logger = get_logger()
        
        # 控制器（MaaFramework）
        self.pc_controller: Optional[MaaFwWin32Executor] = None
        self.android_touch_executor = None
        self.android_screen_capture = None
        self.adb_manager = None
        
        # 截图记录
        self.screenshots: List[Dict[str, Any]] = []
    
    def init_pc_controller(self, window_title: str, control_scheme: str = "Win32-Front") -> bool:
        """初始化PC控制器（使用MaaFramework库）"""
        if not PC_CONTROLLER_AVAILABLE:
            self.logger.error(LogCategory.MAIN, "PC控制器不可用（MaaFwWin32Executor未安装）")
            return False
        
        try:
            # 根据触控方案创建配置
            if control_scheme == "Win32-Window":
                config = MaaFwWin32Config(
                    screencap_method=MaaWin32ScreencapMethodEnum.GDI,
                    mouse_method=MaaWin32InputMethodEnum.SendMessage,
                    keyboard_method=MaaWin32InputMethodEnum.SendMessage
                )
            elif control_scheme == "Win32-Express":
                config = MaaFwWin32Config(
                    screencap_method=MaaWin32ScreencapMethodEnum.GDI,
                    mouse_method=MaaWin32InputMethodEnum.PostMessage,
                    keyboard_method=MaaWin32InputMethodEnum.PostMessage
                )
            elif control_scheme == "Win32-Front":
                config = MaaFwWin32Config(
                    screencap_method=MaaWin32ScreencapMethodEnum.DXGI_DesktopDup,
                    mouse_method=MaaWin32InputMethodEnum.Seize,
                    keyboard_method=MaaWin32InputMethodEnum.Seize
                )
            else:
                config = MaaFwWin32Config(
                    screencap_method=MaaWin32ScreencapMethodEnum.DXGI_DesktopDup,
                    mouse_method=MaaWin32InputMethodEnum.Seize,
                    keyboard_method=MaaWin32InputMethodEnum.Seize
                )
            
            self.pc_controller = MaaFwWin32Executor(config)
            self.logger.info(LogCategory.MAIN, f"PC控制器创建（MaaFramework）: {control_scheme}")
            
            # 连接到游戏窗口
            if self.pc_controller.connect(window_title=window_title):
                self.logger.info(LogCategory.MAIN, f"PC控制器连接成功（MaaFramework）: {window_title}")
                return True
            else:
                self.logger.error(LogCategory.MAIN, f"PC控制器连接失败: 未找到窗口 '{window_title}'")
                return False
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, f"PC控制器初始化异常: {e}")
            return False
    
    def init_android_controller(self, device_serial: str) -> bool:
        """初始化Android控制器"""
        if not ANDROID_CONTROLLER_AVAILABLE:
            self.logger.error(LogCategory.MAIN, "Android控制器不可用")
            return False
        
        try:
            # 初始化ADB管理器
            self.adb_manager = ADBDeviceManager()
            
            # 初始化触控执行器
            config = MaaFwTouchConfig(
                press_duration_ms=50,
                press_jitter_px=2,
                swipe_delay_min_ms=100,
                swipe_delay_max_ms=300
            )
            self.android_touch_executor = MaaFwTouchExecutor(self.adb_manager, config)
            
            # 初始化屏幕捕获
            self.android_screen_capture = ScreenCapture(self.adb_manager)
            
            self.logger.info(LogCategory.MAIN, f"Android控制器初始化成功: {device_serial}")
            return True
        except Exception as e:
            self.logger.exception(LogCategory.MAIN, f"Android控制器初始化异常: {e}")
            return False
    
    def capture_screenshot(self, label: str = "") -> Optional[bytes]:
        """捕获截图"""
        screenshot_data = None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        if self.pc_controller:
            # PC设备截图
            try:
                image = self.pc_controller.screencap()
                if image is not None:
                    # 转换为PNG格式
                    from PIL import Image
                    import io
                    if isinstance(image, bytes):
                        # 已经是字节数据
                        screenshot_data = image
                    else:
                        # PIL Image对象
                        buffer = io.BytesIO()
                        image.save(buffer, format='PNG')
                        screenshot_data = buffer.getvalue()
                    
                    self.logger.info(LogCategory.MAIN, f"PC截图成功: {label}")
            except Exception as e:
                self.logger.exception(LogCategory.MAIN, f"PC截图失败: {e}")
        
        elif self.android_screen_capture and self.adb_manager:
            # Android设备截图
            try:
                device = self.adb_manager.get_connected_devices()[0] if self.adb_manager.get_connected_devices() else None
                if device:
                    screenshot_data = self.android_screen_capture.capture_screen(device)
                    self.logger.info(LogCategory.MAIN, f"Android截图成功: {label}")
            except Exception as e:
                self.logger.exception(LogCategory.MAIN, f"Android截图失败: {e}")
        
        # 保存截图记录
        if screenshot_data:
            filename = f"{timestamp}_{label}.png" if label else f"{timestamp}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(screenshot_data)
            
            self.screenshots.append({
                "timestamp": timestamp,
                "label": label,
                "filename": filename
            })
            
            self.logger.info(LogCategory.MAIN, f"截图保存: {filepath}")
        
        return screenshot_data
    
    def execute_click(self, x: float, y: float, purpose: str = "点击") -> bool:
        """
        执行点击操作
        
        Args:
            x: X坐标（归一化0-1或像素）
            y: Y坐标（归一化0-1或像素）
            purpose: 操作目的
        """
        self.logger.info(LogCategory.MAIN, f"执行点击: ({x}, {y}) - {purpose}")
        
        if self.pc_controller:
            # PC设备点击
            width = getattr(self.pc_controller, '_width', 1920)
            height = getattr(self.pc_controller, '_height', 1080)
            
            # 转换归一化坐标
            if 0 <= x <= 1 and 0 <= y <= 1:
                abs_x = int(x * width)
                abs_y = int(y * height)
            else:
                abs_x = int(x)
                abs_y = int(y)
            
            self.logger.info(LogCategory.MAIN, f"PC点击: 相对({x}, {y}) -> 绝对({abs_x}, {abs_y})")
            return self.pc_controller.click(abs_x, abs_y)
        
        elif self.android_touch_executor:
            # Android设备点击
            device = self.adb_manager.get_connected_devices()[0] if self.adb_manager.get_connected_devices() else None
            if device:
                return self.android_touch_executor.safe_press(device, int(x), int(y), purpose)
        
        return False
    
    def execute_swipe(self, x1: float, y1: float, x2: float, y2: float, 
                      duration: int = 300, purpose: str = "滑动") -> bool:
        """
        执行滑动操作
        
        Args:
            x1, y1: 起点坐标
            x2, y2: 终点坐标
            duration: 持续时间（毫秒）
            purpose: 操作目的
        """
        self.logger.info(LogCategory.MAIN, f"执行滑动: ({x1}, {y1}) -> ({x2}, {y2}) - {purpose}")
        
        if self.pc_controller:
            # PC设备滑动
            width = getattr(self.pc_controller, '_width', 1920)
            height = getattr(self.pc_controller, '_height', 1080)
            
            # 转换归一化坐标
            if 0 <= x1 <= 1:
                x1 = int(x1 * width)
            if 0 <= y1 <= 1:
                y1 = int(y1 * height)
            if 0 <= x2 <= 1:
                x2 = int(x2 * width)
            if 0 <= y2 <= 1:
                y2 = int(y2 * height)
            
            self.logger.info(LogCategory.MAIN, f"PC滑动: ({x1}, {y1}) -> ({x2}, {y2})")
            return self.pc_controller.swipe(int(x1), int(y1), int(x2), int(y2), duration)
        
        elif self.android_touch_executor:
            # Android设备滑动
            device = self.adb_manager.get_connected_devices()[0] if self.adb_manager.get_connected_devices() else None
            if device:
                return self.android_touch_executor.safe_swipe(device, int(x1), int(y1), int(x2), int(y2), duration, purpose)
        
        return False
    
    def run_test_sequence(self, test_actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        运行测试序列
        
        Args:
            test_actions: 测试动作列表
            [
                {"type": "click", "x": 0.5, "y": 0.5, "purpose": "测试点击"},
                {"type": "swipe", "x1": 0.3, "y1": 0.5, "x2": 0.7, "y2": 0.5, "duration": 300, "purpose": "测试滑动"},
                {"type": "wait", "duration": 1.0},
                ...
            ]
        """
        results = {
            "start_time": datetime.now().isoformat(),
            "actions": [],
            "screenshots": []
        }
        
        # 初始截图
        self.capture_screenshot("before_test")
        
        for i, action in enumerate(test_actions):
            action_type = action.get("type", "unknown")
            action_result = {
                "index": i,
                "type": action_type,
                "params": action,
                "success": False
            }
            
            self.logger.info(LogCategory.MAIN, f"执行测试动作 {i+1}/{len(test_actions)}: {action_type}")
            
            try:
                if action_type == "click":
                    success = self.execute_click(
                        action.get("x", 0.5),
                        action.get("y", 0.5),
                        action.get("purpose", f"测试点击{i+1}")
                    )
                    action_result["success"] = success
                    
                    # 点击后截图
                    time.sleep(0.5)  # 等待界面响应
                    self.capture_screenshot(f"after_click_{i+1}")
                
                elif action_type == "swipe":
                    success = self.execute_swipe(
                        action.get("x1", 0.3),
                        action.get("y1", 0.5),
                        action.get("x2", 0.7),
                        action.get("y2", 0.5),
                        action.get("duration", 300),
                        action.get("purpose", f"测试滑动{i+1}")
                    )
                    action_result["success"] = success
                    
                    # 滑动后截图
                    time.sleep(0.5)
                    self.capture_screenshot(f"after_swipe_{i+1}")
                
                elif action_type == "wait":
                    duration = action.get("duration", 1.0)
                    self.logger.info(LogCategory.MAIN, f"等待 {duration} 秒")
                    time.sleep(duration)
                    action_result["success"] = True
                
                elif action_type == "screenshot":
                    self.capture_screenshot(action.get("label", f"screenshot_{i+1}"))
                    action_result["success"] = True
                
                else:
                    self.logger.warning(LogCategory.MAIN, f"未知动作类型: {action_type}")
            
            except Exception as e:
                self.logger.exception(LogCategory.MAIN, f"执行动作异常: {e}")
                action_result["error"] = str(e)
            
            results["actions"].append(action_result)
        
        # 最终截图
        self.capture_screenshot("after_test")
        
        results["end_time"] = datetime.now().isoformat()
        results["screenshots"] = self.screenshots
        
        # 保存结果
        self._save_results(results)
        
        return results
    
    def _save_results(self, results: Dict[str, Any]):
        """保存测试结果"""
        import json
        
        results_file = os.path.join(self.output_dir, "test_results.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        self.logger.info(LogCategory.MAIN, f"测试结果保存: {results_file}")
        
        # 生成task_description.json用于task_cycle_analyse.py分析
        description = {
            "run_start_time": results.get("start_time", ""),
            "control_scheme": "PC" if self.pc_controller else "Android",
            "window_title": getattr(self, 'window_title', 'Unknown'),
            "screenshot_interval": 0.5,
            "screenshots": [
                {
                    "timestamp": s["timestamp"],
                    "task_name": s["label"],
                    "task_variables": {},
                    "screenshot_file": s["filename"]
                }
                for s in self.screenshots
            ]
        }
        
        description_file = os.path.join(self.output_dir, "task_description.json")
        with open(description_file, 'w', encoding='utf-8') as f:
            json.dump(description, f, ensure_ascii=False, indent=2)
        
        self.logger.info(LogCategory.MAIN, f"描述文件保存: {description_file}")


def main():
    parser = argparse.ArgumentParser(description="触控执行调试脚本")
    parser.add_argument("--mode", choices=["pc", "android"], default="pc", help="设备模式")
    parser.add_argument("--window-title", default="Endfield", help="PC窗口标题")
    parser.add_argument("--control-scheme", default="Win32-Front", help="PC触控方案")
    parser.add_argument("--device-serial", default="", help="Android设备序列号")
    parser.add_argument("--output-dir", default="", help="输出目录")
    
    args = parser.parse_args()
    
    # 创建调试器
    debugger = TouchExecutionDebugger(args.output_dir if args.output_dir else None)
    
    # 初始化控制器
    if args.mode == "pc":
        if not debugger.init_pc_controller(args.window_title, args.control_scheme):
            print(f"PC控制器初始化失败，请确保窗口 '{args.window_title}' 存在")
            return 1
    else:
        if not debugger.init_android_controller(args.device_serial):
            print("Android控制器初始化失败")
            return 1
    
    # 定义测试序列（示例：简单的界面点击测试）
    test_actions = [
        {"type": "screenshot", "label": "initial_state"},
        {"type": "click", "x": 0.5, "y": 0.5, "purpose": "中心点击测试"},
        {"type": "wait", "duration": 1.0},
        {"type": "screenshot", "label": "after_center_click"},
        {"type": "swipe", "x1": 0.3, "y1": 0.5, "x2": 0.7, "y2": 0.5, "duration": 300, "purpose": "水平滑动测试"},
        {"type": "wait", "duration": 1.0},
        {"type": "screenshot", "label": "after_swipe"},
    ]
    
    # 运行测试
    print(f"\n开始触控测试 ({args.mode} 模式)...")
    print(f"输出目录: {debugger.output_dir}")
    
    results = debugger.run_test_sequence(test_actions)
    
    print(f"\n测试完成!")
    print(f"成功动作: {sum(1 for a in results['actions'] if a['success'])}/{len(results['actions'])}")
    print(f"截图数量: {len(results['screenshots'])}")
    print(f"\n使用以下命令分析截图:")
    print(f"  python -m client.cli-method.debug_tools.task_cycle_analyse --output-dir {debugger.output_dir}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())