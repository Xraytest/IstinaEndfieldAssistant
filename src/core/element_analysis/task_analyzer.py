"""每日/每周/活动任务分析器

专门识别和分析明日方舟终末地的每日/每周任务及活动页面。
"""

import time
import re
from typing import Dict, Any, List, Optional, Tuple

from .models import (
    TaskDefinition, TaskStatus, TaskCycle, TaskInstance,
    EventActivity, AnalysisResult, ElementKnowledge,
)
from .element_repo import ElementRepository, AnalysisSession
from .element_analyzer import ElementAnalyzer


# 导航到任务页面的点击坐标（根据前期探索确定的入口位置）
# 世界地图 -> 任务日志按钮 (163, 51)
# 模拟空间/活动入口按钮 (616, 24)
NAVIGATION_POINTS = {
    "task_log": (163, 51),
    "event_entry": (616, 24),
    "mail": (252, 47),
    "close_x": (950, 90),
    "claim_first": (500, 600),  # 估算的"一键领取"位置
}


TASK_NAVIGATE_PROMPT = """你是《明日方舟：终末地》导航分析器。识别当前游戏画面，判断如何进入任务/活动页面。

输出JSON：
{
  "page_name": "当前页面中文名",
  "current_location": "main_menu/world_map/task_ui/event_ui/dialog/loading/other",
  "task_access_points": [
    {"label": "可见按钮文本", "bbox": [x1,y1,x2,y2], "confidence": 0.95, "navigates_to": "任务页面/活动页面/签到"}
  ],
  "ready_for_task_analysis": false,
  "description": "导航建议"
}
"""


class TaskAnalyzer:
    """任务分析器
    
    专门分析每日任务、每周任务和活动任务。
    复用ElementAnalyzer进行VLM分析，增加任务特定的逻辑。
    """

    def __init__(
        self,
        element_analyzer: ElementAnalyzer,
        adb_shell_func=None,  # adb shell tap函数
    ):
        self.analyzer = element_analyzer
        self.adb_shell = adb_shell_func or self._default_adb_tap
        self.repo = ElementRepository()
        self._session: Optional[AnalysisSession] = None

    def _default_adb_tap(self, x: int, y: int) -> bool:
        """默认的ADB点击函数（通过shell调用）"""
        import subprocess
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        adb_path = os.path.join(project_root, "3rd-party", "adb", "adb.exe")
        device = self.analyzer.device_serial
        try:
            subprocess.run(
                [adb_path, "-s", device, "shell", "input", "tap", str(x), str(y)],
                capture_output=True, timeout=10
            )
            return True
        except Exception:
            return False

    def start_session(self) -> AnalysisSession:
        """开始一次新的分析会话"""
        self._session = AnalysisSession(
            device_serial=self.analyzer.device_serial
        )
        return self._session

    def end_session(self) -> Dict[str, Any]:
        """结束当前分析会话"""
        if self._session:
            summary = self._session.finalize()
            self._session = None
            return summary
        return {}

    def analyze_current_page(self) -> Optional[AnalysisResult]:
        """分析当前页面（通用全元素分析）"""
        result = self.analyzer.analyze_full_page()
        if result and self._session:
            self._session.add_result(result)
        return result

    def analyze_current_tasks(self) -> List[TaskDefinition]:
        """分析当前页面的任务
        
        使用任务聚焦分析，从VLM回复中提取任务信息。
        """
        result = self.analyzer.analyze_tasks_focused()
        if not result:
            return []

        if self._session:
            self._session.add_result(result)

        # 从VLM原始回复中提取任务信息
        return self._extract_tasks_from_reply(
            result.raw_reply, result.page_name, result.screenshot_hash
        )

    def _extract_tasks_from_reply(
        self, raw_reply: str, page_name: str, page_hash: str
    ) -> List[TaskDefinition]:
        """从VLM回复中提取结构化任务信息"""
        import json
        import re

        tasks: List[TaskDefinition] = []

        # 尝试提取并解析JSON
        try:
            # 直接解析整个回复
            data = json.loads(raw_reply)
        except json.JSONDecodeError:
            # 尝试从markdown代码块中提取
            code_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw_reply)
            if code_match:
                try:
                    data = json.loads(code_match.group(1))
                except json.JSONDecodeError:
                    return tasks
            else:
                brace_match = re.search(r'\{[\s\S]*\}', raw_reply)
                if brace_match:
                    try:
                        data = json.loads(brace_match.group())
                    except json.JSONDecodeError:
                        return tasks
                else:
                    return tasks

        if not isinstance(data, dict):
            return tasks

        raw_tasks = data.get("tasks", [])
        if not isinstance(raw_tasks, list):
            return tasks

        for idx, raw in enumerate(raw_tasks):
            if not isinstance(raw, dict):
                continue

            task_name = raw.get("task_name", f"任务{idx+1}")
            task_type_str = raw.get("type", "daily")
            status_str = raw.get("status", "unknown")
            progress_text = raw.get("progress", "")
            current = raw.get("current", 0)
            total = raw.get("total", 0)
            claim_bbox = raw.get("claim_button", None)
            rewards = raw.get("rewards", [])

            # 解析周期
            try:
                cycle = TaskCycle(task_type_str)
            except ValueError:
                if "每日" in task_name or "日常" in task_name:
                    cycle = TaskCycle.DAILY
                elif "每周" in task_name or "周常" in task_name:
                    cycle = TaskCycle.WEEKLY
                else:
                    cycle = TaskCycle.UNKNOWN

            # 解析状态
            try:
                status = TaskStatus(status_str)
            except ValueError:
                if "领取" in progress_text or status_str == "claimable":
                    status = TaskStatus.CLAIMABLE
                elif "完成" in status_str:
                    status = TaskStatus.COMPLETED
                elif "进行" in status_str:
                    status = TaskStatus.IN_PROGRESS
                else:
                    status = TaskStatus.UNKNOWN

            task_id = f"task_{cycle.value}_{idx}"

            claim_bbox_tuple = (0.0, 0.0, 0.0, 0.0)
            if isinstance(claim_bbox, (list, tuple)) and len(claim_bbox) == 4:
                claim_bbox_tuple = tuple(map(float, claim_bbox))

            # 从progress文本解析current/total
            if not current and not total and progress_text:
                progress_match = re.match(r"(\d+)\s*/\s*(\d+)", progress_text)
                if progress_match:
                    current = int(progress_match.group(1))
                    total = int(progress_match.group(2))

            task = TaskDefinition(
                task_id=task_id,
                task_name=task_name,
                task_cycle=cycle,
                task_category=data.get("page_name", ""),
                current_progress=current,
                total_progress=total,
                progress_text=progress_text,
                rewards=rewards,
                status=status,
                claim_button_bbox=claim_bbox_tuple,
                page_name=page_name,
                page_hash=page_hash,
                last_seen=time.time(),
            )

            tasks.append(task)

            # 保存到会话和持久化
            if self._session:
                self._session.add_task(task)

            # 保存实例快照
            instance = TaskInstance(
                task_id=task.task_id,
                session_id=self._session.session_id if self._session else "",
                timestamp=time.time(),
                status=task.status,
                current_progress=task.current_progress,
                total_progress=task.total_progress,
                progress_text=task.progress_text,
                screenshot_hash=page_hash,
            )
            self.repo.save_task_instance(instance)

        return tasks

    def find_claim_buttons(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从元素列表中找出领取/领取奖励按钮"""
        claim_keywords = ["领取", "收取", "一键领取", "完成", "提交", "领奖", "得", "签"]
        claim_buttons = []
        for e in elements:
            label = e.get("label", "")
            action = e.get("action", "")
            func = e.get("extra", {}).get("function", "")
            if any(k in label for k in claim_keywords) or any(k in func for k in claim_keywords):
                if action == "tap" or e.get("type") in ("button", "icon"):
                    claim_buttons.append(e)
        return claim_buttons

    def get_daily_tasks(self) -> List[TaskDefinition]:
        """获取每日任务
        
        先分析当前页面，然后过滤出日任务。
        """
        tasks = self.analyze_current_tasks()
        return [t for t in tasks if t.task_cycle == TaskCycle.DAILY]

    def get_weekly_tasks(self) -> List[TaskDefinition]:
        """获取每周任务"""
        tasks = self.analyze_current_tasks()
        return [t for t in tasks if t.task_cycle == TaskCycle.WEEKLY]

    def get_event_tasks(self) -> List[TaskDefinition]:
        """获取活动任务"""
        tasks = self.analyze_current_tasks()
        return [t for t in tasks if t.task_cycle == TaskCycle.EVENT]

    def tap_claim_button(self, task: TaskDefinition) -> bool:
        """点击任务的领取按钮"""
        bbox = task.claim_button_bbox
        if bbox and bbox[2] > bbox[0]:
            cx = int((bbox[0] + bbox[2]) / 2)
            cy = int((bbox[1] + bbox[3]) / 2)
            return self.adb_shell(cx, cy)
        return False

    def tap_position(self, x: int, y: int) -> bool:
        """点击指定坐标"""
        return self.adb_shell(x, y)

    def navigate_to_tasks(self) -> bool:
        """导航到任务页面
        
        尝试点击"任务日志"按钮进入任务UI。
        """
        # 先分析当前页面，找任务入口
        result = self.analyze_current_page()
        if not result:
            # 盲点任务日志位置
            return self.tap_position(*NAVIGATION_POINTS["task_log"])

        # 从元素中找任务相关按钮
        for e in result.elements:
            label = e.get("label", "")
            func = e.get("extra", {}).get("function", "")
            if any(k in label or k in func for k in ["任务", "日志", "mission", "quest"]):
                bbox = e.get("bbox", [])
                if len(bbox) >= 4 and bbox[2] > 0:
                    cx = int((bbox[0] + bbox[2]) / 2)
                    cy = int((bbox[1] + bbox[3]) / 2)
                    return self.tap_position(cx, cy)

        # fallback
        return self.tap_position(*NAVIGATION_POINTS["task_log"])

    def navigate_to_event_page(self) -> bool:
        """导航到活动/活动页面"""
        result = self.analyze_current_page()
        if not result:
            return self.tap_position(*NAVIGATION_POINTS["event_entry"])

        for e in result.elements:
            label = e.get("label", "")
            func = e.get("extra", {}).get("function", "")
            if any(k in label or k in func for k in ["活动", "event", "模拟空间", "活动"]):
                bbox = e.get("bbox", [])
                if len(bbox) >= 4 and bbox[2] > 0:
                    cx = int((bbox[0] + bbox[2]) / 2)
                    cy = int((bbox[1] + bbox[3]) / 2)
                    return self.tap_position(cx, cy)

        return self.tap_position(*NAVIGATION_POINTS["event_entry"])

    def claim_all_available(self) -> List[str]:
        """导航领奖：遍历所有任务页面并领取可领取奖励
        
        流程：
        1. 先分析当前页面，领取可领取任务
        2. 导航到任务日志页面，分析并领取
        3. 导航到活动页面，分析并领取
        4. 关闭任务页面（点击X）
        """
        claimed = []

        # 1. 分析当前页面
        print("  [领奖] 分析当前页面...")
        tasks = self.analyze_current_tasks()
        for task in tasks:
            if task.status == TaskStatus.CLAIMABLE:
                print(f"  [领奖] 领取: {task.task_name}")
                if self.tap_claim_button(task):
                    claimed.append(task.task_name)
                    time.sleep(2)

        # 2. 导航到任务页面
        print("  [领奖] 导航到任务页面...")
        if self.navigate_to_tasks():
            time.sleep(4)
            print("  [领奖] 分析任务页面...")
            tasks = self.analyze_current_tasks()
            for task in tasks:
                if task.status == TaskStatus.CLAIMABLE:
                    print(f"  [领奖] 领取: {task.task_name}")
                    if self.tap_claim_button(task):
                        claimed.append(task.task_name)
                        time.sleep(2)

            # 返回（点击X关闭任务页面）
            self.tap_position(*NAVIGATION_POINTS["close_x"])
            time.sleep(2)

        # 3. 导航到活动页面
        print("  [领奖] 导航到活动页面...")
        if self.navigate_to_event_page():
            time.sleep(4)
            print("  [领奖] 分析活动页面...")
            event_tasks = self.analyze_current_tasks()
            for task in event_tasks:
                if task.status == TaskStatus.CLAIMABLE:
                    print(f"  [领奖] 领取: {task.task_name}")
                    if self.tap_claim_button(task):
                        claimed.append(task.task_name)
                        time.sleep(2)

        print(f"  [领奖] 完成，共领取 {len(claimed)} 个奖励")
        return claimed

    def scan_all_task_pages(self, max_steps: int = 10) -> Dict[str, List[TaskDefinition]]:
        """全面扫描所有任务页面
        
        导航到各个任务相关页面并分析。
        """
        result = {
            "daily": [],
            "weekly": [],
            "event": [],
        }

        # 1. 先分析当前页面
        tasks = self.analyze_current_tasks()
        for t in tasks:
            if t.task_cycle == TaskCycle.DAILY:
                result["daily"].append(t)
            elif t.task_cycle == TaskCycle.WEEKLY:
                result["weekly"].append(t)
            elif t.task_cycle == TaskCycle.EVENT:
                result["event"].append(t)

        # 2. 导航到任务页面
        if self.navigate_to_tasks():
            time.sleep(5)
            tasks = self.analyze_current_tasks()
            for t in tasks:
                if t.task_cycle == TaskCycle.DAILY:
                    result["daily"].append(t)
                elif t.task_cycle == TaskCycle.WEEKLY:
                    result["weekly"].append(t)

        # 3. 导航到活动页面
        if self.navigate_to_event_page():
            time.sleep(5)
            event_tasks = self.analyze_current_tasks()
            result["event"] = event_tasks

        return result
