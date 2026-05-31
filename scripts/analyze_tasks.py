"""
任务分析脚本 - 复用IEA代码分析明日方舟终末地每日/每周任务

使用方法：
  python scripts/analyze_tasks.py                   # 完整分析
  python scripts/analyze_tasks.py --quick            # 快速分析当前页面
  python scripts/analyze_tasks.py --claim            # 分析并领取
  python scripts/analyze_tasks.py --session          # 完整会话+扫所有任务页
  python scripts/analyze_tasks.py --device 127.0.0.1:16512

依赖：
  - IstinaPlatform 服务端运行在 127.0.0.1:9999
  - ADB 连接设备 localhost:16512
"""

import sys
import os
import time
import json
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 路径设置
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from core.element_analysis import (
    ElementAnalyzer, TaskAnalyzer, AnalysisSession,
    ElementRepository, TaskDefinition, TaskStatus, TaskCycle,
)
from core.communication import ClientCommunicator
from screenshot import ScreenCapture
from device.adb_manager import ADBDeviceManager


def setup_components(
    device_serial: str = "localhost:16512",
    server_host: str = "127.0.0.1",
    server_port: int = 9999,
    password: str = "default_password",
    api_key: str = "aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763",
    model_tag: str = "exploration_deep",
):
    """初始化所有组件"""
    print("=" * 60)
    print(f"  设备: {device_serial}")
    print(f"  服务端: {server_host}:{server_port}")
    print(f"  模型标签: {model_tag}")
    print("=" * 60)

    # ADB
    adb_path = os.path.join(project_root, "3rd-party", "adb", "adb.exe")
    print(f"\n[1/4] 初始化ADB...")
    adb_mgr = ADBDeviceManager(adb_path=adb_path)
    if adb_mgr.connect_device(device_serial):
        print(f"  设备连接成功")
    else:
        print(f"  设备连接失败，尝试中...")
        time.sleep(2)

    # 截图
    print(f"\n[2/4] 初始化截图模块...")
    screen_capture = ScreenCapture(adb_mgr)

    # 通信
    print(f"\n[3/4] 连接IstinaPlatform服务端...")
    communicator = ClientCommunicator(
        host=server_host, port=server_port, password=password, timeout=120
    )

    # 登录
    print(f"  登录...")
    login_result = communicator.send_request("login", {
        "user_id": "explorer",
        "key": api_key,
    })
    if not login_result or login_result.get("status") != "success":
        print(f"  登录失败: {login_result}")
        sys.exit(1)
    session_id = login_result.get("session_id", "")
    print(f"  会话ID: {session_id[:16]}...")
    communicator.set_logged_in(True)

    # 创建分析器
    print(f"\n[4/4] 创建元素分析器...")
    element_analyzer = ElementAnalyzer(
        communicator=communicator,
        screen_capture=screen_capture,
        device_serial=device_serial,
        model_tag=model_tag,
        session_id=session_id,
        user_id="explorer",
    )

    task_analyzer = TaskAnalyzer(
        element_analyzer=element_analyzer,
    )

    repo = ElementRepository()

    return communicator, element_analyzer, task_analyzer, repo, session_id


def do_quick_analysis(task_analyzer: TaskAnalyzer):
    """快速分析当前页面"""
    print("\n快速分析当前页面...")
    result = task_analyzer.analyze_current_page()
    if not result:
        print("分析失败 - 无法获取VLM响应")
        return

    print(f"\n页面: {result.page_name} ({result.page_type})")
    print(f"描述: {result.description[:100] if result.description else '无'}")
    print(f"元素数: {len(result.elements)}")
    print(f"特征: 每日={'是' if result.has_daily_tasks else '否'} | 每周={'是' if result.has_weekly_tasks else '否'} | 活动={'是' if result.has_event else '否'}")

    # 打印前10个元素
    print("\n--- 关键元素 ---")
    for i, e in enumerate(result.elements[:15]):
        bbox = e.get("bbox", [])
        extra = e.get("extra", {})
        func = extra.get("function", "") if isinstance(extra, dict) else ""
        bbox_str = f"({int(bbox[0])},{int(bbox[1])})-({int(bbox[2])},{int(bbox[3])})" if len(bbox) >= 4 else "无坐标"
        print(f"  [{i+1}] {e.get('type','?')} \"{e.get('label','')}\" {bbox_str} | {func[:30]}")

    return result


def do_task_analysis(task_analyzer: TaskAnalyzer):
    """分析当前页面中的任务"""
    print("\n分析当前页面的每日/每周/活动任务...")
    tasks = task_analyzer.analyze_current_tasks()

    if not tasks:
        print("未发现任务信息")
        return []

    print(f"\n发现 {len(tasks)} 个任务:")
    for i, t in enumerate(tasks):
        status_icon = {
            TaskStatus.NOT_STARTED: "",
            TaskStatus.IN_PROGRESS: "\u23f3",
            TaskStatus.COMPLETED: "\u2705",
            TaskStatus.CLAIMABLE: "\U0001f381",
            TaskStatus.CLAIMED: "\u2705",
        }.get(t.status, "\u2753")

        cycle_name = {
            TaskCycle.DAILY: "每日",
            TaskCycle.WEEKLY: "每周",
            TaskCycle.EVENT: "活动",
        }.get(t.task_cycle, "未知")

        progress_str = t.progress_text or f"{t.current_progress}/{t.total_progress}" if t.total_progress > 0 else ""
        print(f"  {status_icon} [{cycle_name}] {t.task_name}")
        if progress_str:
            print(f"    进度: {progress_str}")
        print(f"    状态: {t.status.value}")
        if t.claim_button_bbox and t.claim_button_bbox[2] > 0:
            print(f"    领取按钮: ({int(t.claim_button_bbox[0])},{int(t.claim_button_bbox[1])})-({int(t.claim_button_bbox[2])},{int(t.claim_button_bbox[3])})")

    return tasks


def do_full_scan(task_analyzer: TaskAnalyzer):
    """全面扫描所有任务页面"""
    print("\n全面扫描所有任务页面...")
    print("  此操作会导航到任务页面和活动页面\n")

    session = task_analyzer.start_session()

    # 1. 当前页面分析
    print("[1/3] 分析当前页面...")
    do_task_analysis(task_analyzer)

    # 2. 导航到任务页面
    print(f"\n[2/3] 导航到任务页面...")
    if task_analyzer.navigate_to_tasks():
        print("  点击任务入口，等待画面加载...")
        time.sleep(5)
        do_task_analysis(task_analyzer)

        # 尝试返回
        print("  返回上一页...")
        task_analyzer.tap_position(950, 90)  # X按钮
        time.sleep(3)

    # 3. 导航到活动页面
    print(f"\n[3/3] 导航到活动页面...")
    if task_analyzer.navigate_to_event_page():
        print("  点击活动入口，等待画面加载...")
        time.sleep(5)
        do_task_analysis(task_analyzer)

    # 结束会话
    summary = task_analyzer.end_session()
    print(f"\n{'=' * 50}")
    print("分析会话摘要:")
    print(f"  会话ID: {summary.get('session_id', '')}")
    print(f"  时长: {summary.get('duration_seconds', 0)}秒")
    print(f"  访问页面: {summary.get('pages_visited')}")
    print(f"  分析次数: {summary.get('analysis_count', 0)}")
    print(f"  发现任务: {summary.get('tasks_found', 0)}")
    print(f"{'=' * 50}")

    return summary


def do_claim(task_analyzer: TaskAnalyzer):
    """分析并领取可领取任务奖励"""
    print("\n分析并领取可领取任务奖励...")
    claimed = task_analyzer.claim_all_available()
    if claimed:
        print(f"\n已领取 {len(claimed)} 个奖励:")
        for c in claimed:
            print(f"  - {c}")
    else:
        print("\n未发现可领取的任务奖励")
    return claimed


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="IstinaEndfieldAssistant - 每日/每周任务分析"
    )
    parser.add_argument("--device", default="localhost:16512", help="ADB设备地址")
    parser.add_argument("--model", default="exploration_deep", help="VLM模型标签")
    parser.add_argument("--quick", action="store_true", help="仅快速分析当前页面")
    parser.add_argument("--claim", action="store_true", help="分析并领取奖励")
    parser.add_argument("--session", action="store_true", help="完整会话扫描")
    parser.add_argument("--full", action="store_true", help="完整分析（默认行为）")
    args = parser.parse_args()

    # 初始化
    communicator, element_analyzer, task_analyzer, repo, session_id = setup_components(
        device_serial=args.device,
        model_tag=args.model,
    )

    # 根据参数执行不同模式
    if args.quick:
        # 仅快速分析
        do_quick_analysis(task_analyzer)
    elif args.claim:
        # 分析并领取（含导航到任务/活动页面）
        do_claim(task_analyzer)
    elif args.session:
        # 完整扫描并领取
        do_full_scan(task_analyzer)
        do_claim(task_analyzer)
    else:
        # 默认：导航 → 扫描任务 → 领取
        print("\n" + "=" * 50)
        print("模式: 默认（导航 → 扫描 → 领取）")
        print("=" * 50)

        session = task_analyzer.start_session()

        quick_result = do_quick_analysis(task_analyzer)

        if quick_result and (quick_result.has_daily_tasks or quick_result.has_weekly_tasks):
            time.sleep(2)
            do_task_analysis(task_analyzer)

        # 导航到任务页面并分析领奖
        claimed = task_analyzer.claim_all_available()
        if claimed:
            print(f"\n本次领取 {len(claimed)} 个奖励:")
            for c in claimed:
                print(f"  - {c}")

        summary = task_analyzer.end_session()
        print(f"\n{'=' * 50}")
        print("分析会话摘要:")
        print(f"  会话ID: {summary.get('session_id', '')}")
        print(f"  时长: {summary.get('duration_seconds', 0)}秒")
        print(f"  分析次数: {summary.get('analysis_count', 0)}")
        print(f"  发现任务: {summary.get('tasks_found', 0)}")
        print(f"{'=' * 50}")

    print("\n数据已持久化到:")
    print(f"  data/elements/   - 页面元素知识")
    print(f"  data/tasks/      - 任务定义与实例")
    print(f"  data/events/     - 活动信息")
    print(f"  data/analysis/   - 分析历史记录")
    print("\n完成")


if __name__ == "__main__":
    main()
