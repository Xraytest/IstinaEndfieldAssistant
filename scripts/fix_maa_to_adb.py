#!/usr/bin/env python3
"""修复 maa_to_adb 坐标转换函数"""

file_path = r'C:\Users\xray\Documents\ArkStudio\IstinaAI\IstinaEndfieldAssistant\src\core\adb_utils.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 maa_to_adb 函数
old_func = '''def maa_to_adb(x: int, y: int) -> Tuple[int, int]:
    """将 MaaMCP 坐标（1280x720）映射到 ADB 竖屏坐标（1080x1920）

    注意：游戏横屏渲染在竖屏显示器内，MaaMCP 窗口可能包含额外工具栏。
    此转换仅适用于纯游戏内容区域。
    """
    # 默认直接使用（适用于 ADB 直接调用）
    return (x, y)'''

new_func = '''def maa_to_adb(x: int, y: int) -> Tuple[int, int]:
    """将 MaaFw 坐标（1280x720 横屏）映射到 ADB input tap 坐标

    ADB input tap 使用的是逻辑坐标空间，与截图分辨率可能不同。
    根据扫描结果：MaaFw 坐标 * 1.5 = ADB 物理坐标
    
    但 ADB input tap 实际使用的是归一化后的逻辑坐标，需要确认实际空间。
    当前实现：直接返回，由调用方决定是否需要转换。
    """
    # 根据配置注释：ADB 原生 1080x1920 物理坐标 = MaaFw 1280x720 * 1.5
    # 但 ADB input tap 可能使用逻辑坐标，需要实测确认
    return (int(x * 1.5), int(y * 1.5))'''

if old_func in content:
    content = content.replace(old_func, new_func)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: maa_to_adb function updated")
else:
    print("ERROR: pattern not found")
