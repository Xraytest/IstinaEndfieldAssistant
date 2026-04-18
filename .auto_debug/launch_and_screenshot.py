#!/usr/bin/env python3
"""
启动 IstinaEndfieldAssistant GUI 并截取屏幕截图
"""

import pyautogui
import time
import subprocess
import os
import sys
import json
from pathlib import Path

# 启用 FAILSAFE - 将鼠标移动到屏幕角落可中止脚本
pyautogui.FAILSAFE = True

# 配置
PROJECT_PATH = Path("c:/Users/xray/Documents/ArkStudio/IstinaAI/IstinaEndfieldAssistant")
LAUNCH_COMMAND = ["python", "入口/GUI/client_main.py"]
SCREENSHOT_DIR = PROJECT_PATH / ".auto_debug" / "screenshots"
SCREENSHOT_PATH = SCREENSHOT_DIR / "initial_screenshot.png"

def ensure_directory(path: Path):
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)

def take_screenshot(path: Path) -> bool:
    """截取屏幕截图并保存"""
    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(str(path))
        return True
    except Exception as e:
        print(f"截图失败: {e}")
        return False

def main():
    result = {
        "success": False,
        "error_message": "",
        "screenshot_after": ""
    }
    
    try:
        # 确保截图目录存在
        ensure_directory(SCREENSHOT_DIR)
        
        # 记录操作前截图（可选）
        screenshot_before_path = SCREENSHOT_DIR / "screenshot_before_launch.png"
        take_screenshot(screenshot_before_path)
        print(f"操作前截图已保存: {screenshot_before_path}")
        
        # 启动应用程序
        print(f"正在启动应用程序...")
        print(f"工作目录: {PROJECT_PATH}")
        print(f"启动命令: {' '.join(LAUNCH_COMMAND)}")
        
        # 使用 Popen 启动进程（非阻塞）
        process = subprocess.Popen(
            LAUNCH_COMMAND,
            cwd=str(PROJECT_PATH),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
        )
        
        print(f"应用程序已启动，PID: {process.pid}")
        
        # 等待应用程序窗口加载（3-5秒）
        wait_time = 5
        print(f"等待 {wait_time} 秒让应用程序加载...")
        time.sleep(wait_time)
        
        # 截取屏幕截图
        print(f"正在截取屏幕截图...")
        if take_screenshot(SCREENSHOT_PATH):
            result["success"] = True
            result["screenshot_after"] = str(SCREENSHOT_PATH)
            print(f"截图已保存: {SCREENSHOT_PATH}")
        else:
            result["error_message"] = "截图失败"
            
    except KeyboardInterrupt:
        result["error_message"] = "用户通过 ESC/键盘中断"
        print("操作被用户中断")
    except Exception as e:
        result["error_message"] = f"执行错误: {str(e)}"
        print(f"错误: {e}")
    
    # 输出 JSON 结果
    print("\n" + "="*50)
    print("执行结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("="*50)
    
    return result

if __name__ == "__main__":
    result = main()
    sys.exit(0 if result["success"] else 1)
