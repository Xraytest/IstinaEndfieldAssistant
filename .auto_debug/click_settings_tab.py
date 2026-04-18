#!/usr/bin/env python3
"""
点击设置标签页并截取屏幕截图
"""

import pyautogui
import time
import json
import sys
from pathlib import Path

# 启用 FAILSAFE - 将鼠标移动到屏幕角落可中止脚本
pyautogui.FAILSAFE = True

# 配置
PROJECT_PATH = Path("c:/Users/xray/Documents/ArkStudio/IstinaAI/IstinaEndfieldAssistant")
SCREENSHOT_DIR = PROJECT_PATH / ".auto_debug" / "screenshots"
SCREENSHOT_BEFORE_PATH = SCREENSHOT_DIR / "before_click_settings.png"
SCREENSHOT_AFTER_PATH = SCREENSHOT_DIR / "after_click_settings.png"

# 设置标签页坐标
SETTINGS_TAB_X = 310
SETTINGS_TAB_Y = 165

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
        
        # 记录操作前截图
        print("正在截取操作前截图...")
        if not take_screenshot(SCREENSHOT_BEFORE_PATH):
            result["error_message"] = "操作前截图失败"
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return result
        print(f"操作前截图已保存: {SCREENSHOT_BEFORE_PATH}")
        
        # 点击设置标签页
        print(f"正在点击设置标签页，坐标: ({SETTINGS_TAB_X}, {SETTINGS_TAB_Y})")
        pyautogui.click(SETTINGS_TAB_X, SETTINGS_TAB_Y)
        
        # 等待界面响应（1-2秒）
        wait_time = 2
        print(f"等待 {wait_time} 秒让界面响应...")
        time.sleep(wait_time)
        
        # 截取操作后屏幕截图
        print("正在截取操作后截图...")
        if take_screenshot(SCREENSHOT_AFTER_PATH):
            result["success"] = True
            result["screenshot_after"] = str(SCREENSHOT_AFTER_PATH)
            print(f"操作后截图已保存: {SCREENSHOT_AFTER_PATH}")
        else:
            result["error_message"] = "操作后截图失败"
            
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
