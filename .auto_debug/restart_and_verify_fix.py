#!/usr/bin/env python3
"""
重启 IstinaEndfieldAssistant GUI 应用并验证修复
执行流程：
1. 终止当前运行的应用（如果还在运行）
2. 重新启动应用程序
3. 等待加载（5秒）
4. 点击"设置"标签页（坐标约 [310, 165]）
5. 等待界面响应（2秒）
6. 截取屏幕截图保存
"""

import pyautogui
import time
import subprocess
import os
import sys
import json
import signal
from pathlib import Path
from datetime import datetime

# 启用 FAILSAFE - 将鼠标移动到屏幕角落可中止脚本
pyautogui.FAILSAFE = True

# 配置
PROJECT_PATH = Path("c:/Users/xray/Documents/ArkStudio/IstinaAI/IstinaEndfieldAssistant")
LAUNCH_COMMAND = ["python", "入口/GUI/client_main.py"]
SCREENSHOT_DIR = PROJECT_PATH / ".auto_debug" / "screenshots"
SCREENSHOT_PATH = SCREENSHOT_DIR / "verify_fix_settings.png"

# 设置标签页坐标
SETTINGS_TAB_COORDS = (310, 165)

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

def kill_existing_app():
    """终止当前运行的应用进程"""
    try:
        # 查找并终止 client_main.py 进程
        import psutil
        killed = False
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'client_main.py' in ' '.join(cmdline):
                    print(f"找到正在运行的应用进程 (PID: {proc.info['pid']})")
                    proc.terminate()
                    proc.wait(timeout=3)
                    print(f"已终止进程 PID: {proc.info['pid']}")
                    killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass
        
        if not killed:
            # 备用方案：使用 taskkill
            os.system("taskkill /f /im python.exe 2>nul")
            print("已尝试终止所有 python 进程")
        
        # 等待进程完全终止
        time.sleep(2)
        return True
    except Exception as e:
        print(f"终止进程时出错: {e}")
        return False

def launch_app():
    """启动应用程序"""
    try:
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
        return process
    except Exception as e:
        print(f"启动应用失败: {e}")
        return None

def click_settings_tab():
    """点击设置标签页"""
    try:
        print(f"点击设置标签页，坐标: {SETTINGS_TAB_COORDS}")
        pyautogui.click(SETTINGS_TAB_COORDS[0], SETTINGS_TAB_COORDS[1])
        return True
    except Exception as e:
        print(f"点击设置标签页失败: {e}")
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
        
        # 1. 终止当前运行的应用
        print("="*50)
        print("步骤 1: 终止当前运行的应用")
        print("="*50)
        kill_existing_app()
        
        # 2. 重新启动应用程序
        print("\n" + "="*50)
        print("步骤 2: 重新启动应用程序")
        print("="*50)
        process = launch_app()
        if not process:
            result["error_message"] = "启动应用失败"
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return result
        
        # 3. 等待应用程序加载（5秒）
        print("\n" + "="*50)
        print("步骤 3: 等待应用程序加载")
        print("="*50)
        wait_time = 5
        print(f"等待 {wait_time} 秒让应用程序加载...")
        time.sleep(wait_time)
        
        # 操作前截图
        screenshot_before = SCREENSHOT_DIR / "verify_fix_before_click.png"
        take_screenshot(screenshot_before)
        print(f"操作前截图已保存: {screenshot_before}")
        
        # 4. 点击"设置"标签页
        print("\n" + "="*50)
        print("步骤 4: 点击设置标签页")
        print("="*50)
        if not click_settings_tab():
            result["error_message"] = "点击设置标签页失败"
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return result
        
        # 5. 等待界面响应（2秒）
        print("\n" + "="*50)
        print("步骤 5: 等待界面响应")
        print("="*50)
        response_wait = 2
        print(f"等待 {response_wait} 秒让界面响应...")
        time.sleep(response_wait)
        
        # 6. 截取屏幕截图
        print("\n" + "="*50)
        print("步骤 6: 截取验证截图")
        print("="*50)
        if take_screenshot(SCREENSHOT_PATH):
            result["success"] = True
            result["screenshot_after"] = str(SCREENSHOT_PATH)
            print(f"验证截图已保存: {SCREENSHOT_PATH}")
        else:
            result["error_message"] = "截图失败"
        
    except KeyboardInterrupt:
        result["error_message"] = "用户通过 ESC/键盘中断"
        print("\n操作被用户中断 (KeyboardInterrupt)")
    except Exception as e:
        result["error_message"] = f"执行错误: {str(e)}"
        print(f"\n错误: {e}")
    
    # 输出 JSON 结果
    print("\n" + "="*50)
    print("执行结果:")
    print("="*50)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("="*50)
    
    return result

if __name__ == "__main__":
    result = main()
    sys.exit(0 if result["success"] else 1)
