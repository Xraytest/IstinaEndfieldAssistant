#!/usr/bin/env python3
"""
批量更新导入路径脚本
用于将旧的导入语句更新为新的模块化导入
"""

import os
import re

# 导入路径映射表
IMPORT_MAPPINGS = {
    # Core模块
    r'^from logger import': 'from client.core.logger import',
    r'^import logger$': 'from client.core import logger',
    r'^from adb_manager import': 'from client.core.adb_manager import',
    r'^import adb_manager$': 'from client.core import adb_manager',
    r'^from screen_capture import': 'from client.core.screen_capture import',
    r'^import screen_capture$': 'from client.core import screen_capture',
    r'^from touch_adapter import': 'from client.core.touch.touch_adapter import',
    r'^from maafw_touch_adapter import': 'from client.core.touch.maafw_touch_adapter import',
    r'^from touch_executor import': 'from client.core.touch.touch_executor import',
    r'^from communicator import': 'from client.core.communication.communicator import',
    r'^import communicator$': 'from client.core.communication import communicator',

    # Business模块
    r'^from task_manager import': 'from client.business.task_manager import',
    r'^import task_manager$': 'from client.business import task_manager',
    r'^from components\.auth_manager import': 'from client.business.managers.auth_manager import',
    r'^from components\.device_manager import': 'from client.business.managers.device_manager import',
    r'^from components\.execution_manager import': 'from client.business.managers.execution_manager import',
    r'^from components\.task_queue_manager import': 'from client.business.managers.task_queue_manager import',
    r'^from components\.log_manager import': 'from client.business.managers.log_manager import',

    # UI模块
    r'^from theme import': 'from client.ui.theme import',
    r'^import theme$': 'from client.ui import theme',
    r'^from managers\.main_gui_manager import': 'from client.ui.managers.main_gui_manager import',
    r'^from managers\.auth_manager_gui import': 'from client.ui.managers.auth_manager_gui import',
    r'^from managers\.device_manager_gui import': 'from client.ui.managers.device_manager_gui import',
    r'^from managers\.task_manager_gui import': 'from client.ui.managers.task_manager_gui import',
    r'^from managers\.cloud_service_manager_gui import': 'from client.ui.managers.cloud_service_manager_gui import',
    r'^from managers\.settings_manager_gui import': 'from client.ui.managers.settings_manager_gui import',

    # 其他
    r'^from client_main import': 'from client.ui.main_window import',
}

def update_file_imports(file_path):
    """更新文件中的导入语句"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        modified = False

        # 应用所有映射
        for old_pattern, new_import in IMPORT_MAPPINGS.items():
            # 只匹配行首的导入语句（避免匹配到注释或字符串）
            pattern = re.compile(old_pattern, re.MULTILINE)
            content, count = pattern.subn(new_import, content)
            if count > 0:
                modified = True
                print(f"  ✓ 更新 {count} 处: {old_pattern}")

        # 如果有修改，写回文件
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  已保存: {file_path}")
            return True
        else:
            print(f"  无需修改: {file_path}")
            return False

    except Exception as e:
        print(f"  ✗ 处理文件失败: {file_path} - {e}")
        return False

def process_directory(directory, file_extensions={'.py'}):
    """递归处理目录中的所有Python文件"""
    print(f"\n处理目录: {directory}\n")

    modified_files = []
    total_files = 0

    for root, dirs, files in os.walk(directory):
        # 跳过某些目录
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.pytest_cache'}]

        for file in files:
            if any(file.endswith(ext) for ext in file_extensions):
                total_files += 1
                file_path = os.path.join(root, file)
                print(f"检查: {file_path}")
                if update_file_imports(file_path):
                    modified_files.append(file_path)

    return total_files, modified_files

def main():
    """主函数"""
    print("=" * 60)
    print("批量更新导入路径脚本")
    print("=" * 60)

    # 获取脚本所在目录的client目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    client_dir = script_dir if 'client' in script_dir else os.path.join(script_dir, 'client')

    if not os.path.exists(client_dir):
        print(f"错误: 找不到client目录: {client_dir}")
        return

    print(f"\n工作目录: {client_dir}\n")

    # 处理client目录
    total, modified = process_directory(client_dir)

    # 统计结果
    print("\n" + "=" * 60)
    print("处理完成！")
    print("=" * 60)
    print(f"总共处理文件数: {total}")
    print(f"修改的文件数: {len(modified)}")

    if modified:
        print("\n修改的文件列表:")
        for file in modified:
            print(f"  - {file}")
    else:
        print("\n没有文件需要修改")

    print("\n请运行测试验证修改是否正确！")
    print("=" * 60)

if __name__ == '__main__':
    main()
