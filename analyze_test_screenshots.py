#!/usr/bin/env python3
"""
分析测试截图 - 用于验证设备控制是否正常工作
"""
import os
import sys
import glob
from datetime import datetime

def find_latest_test_dir():
    """查找最新的测试输出目录"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "debug_output")
    
    if not os.path.exists(output_dir):
        return None
    
    # 获取所有 run_android_* 目录
    test_dirs = glob.glob(os.path.join(output_dir, "run_android_*"))
    if not test_dirs:
        return None
    
    # 按时间排序，返回最新的
    test_dirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return test_dirs[0]

def analyze_screenshots(test_dir):
    """分析测试目录中的截图"""
    if not test_dir or not os.path.exists(test_dir):
        print("❌ 测试目录不存在")
        return
    
    # 获取所有截图文件
    screenshots = glob.glob(os.path.join(test_dir, "*.png"))
    
    if not screenshots:
        print(f"[ERROR] 目录 {test_dir} 中没有截图文件")
        return
    
    print(f"\n[DIR] 测试目录: {test_dir}")
    print(f"[IMG] 截图数量: {len(screenshots)}")
    
    # 按时间排序
    screenshots.sort()
    
    # 分析每个截图
    print("\n=== 截图列表 ===")
    for i, screenshot in enumerate(screenshots[:10], 1):  # 只显示前10个
        filename = os.path.basename(screenshot)
        file_size = os.path.getsize(screenshot)
        mtime = datetime.fromtimestamp(os.path.getmtime(screenshot))
        
        # 尝试解码文件名中的中文部分
        try:
            # 文件名格式: 时间戳_决策.png
            parts = filename.split('_')
            if len(parts) >= 4:
                decision = parts[3] if len(parts) > 3 else "未知"
            else:
                decision = "未知"
        except:
            decision = "解码失败"
        
        print(f"{i}. {filename}")
        print(f"   大小: {file_size/1024:.1f}KB, 时间: {mtime.strftime('%H:%M:%S')}")
    
    if len(screenshots) > 10:
        print(f"\n... 还有 {len(screenshots) - 10} 个截图")
    
    # 检查task_description.json
    task_file = os.path.join(test_dir, "task_description.json")
    if os.path.exists(task_file):
        print(f"\n[TASK] 任务描述文件存在: {task_file}")
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"   内容长度: {len(content)} 字符")
        except Exception as e:
            print(f"   [ERROR] 读取失败: {e}")
    
    return screenshots

def main():
    print("=" * 60)
    print("测试截图分析工具")
    print("=" * 60)
    
    # 查找所有测试目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "debug_output")
    
    if os.path.exists(output_dir):
        test_dirs = glob.glob(os.path.join(output_dir, "run_android_*"))
        test_dirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        print(f"\n找到 {len(test_dirs)} 个测试目录")
        
        # 分析前3个最新的目录
        for test_dir in test_dirs[:3]:
            screenshots = glob.glob(os.path.join(test_dir, "*.png"))
            screenshot_count = len(screenshots)
            
            mtime = datetime.fromtimestamp(os.path.getmtime(test_dir))
            print(f"\n- {os.path.basename(test_dir)}")
            print(f"  时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  截图数: {screenshot_count}")
            
            if screenshot_count == 0:
                print(f"  [WARN] 空目录 - 截图未被保存!")
    
    # 详细分析最新的有截图的目录
    latest_with_screenshots = None
    for test_dir in test_dirs:
        screenshots = glob.glob(os.path.join(test_dir, "*.png"))
        if screenshots:
            latest_with_screenshots = test_dir
            break
    
    if latest_with_screenshots:
        print("\n" + "=" * 60)
        print("详细分析最新有截图的测试目录")
        print("=" * 60)
        analyze_screenshots(latest_with_screenshots)
    else:
        print("\n[ERROR] 没有找到包含截图的测试目录")
        print("   这表明截图保存功能可能存在问题")

if __name__ == "__main__":
    main()