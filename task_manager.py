# task_manager.py
import json
import os
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime
from dataclasses import dataclass, asdict, field

@dataclass
class TaskVariable:
    """任务变量定义"""
    name: str
    type: Literal['int', 'bool', 'float', 'str']
    default: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""
    
    def validate(self, value: Any) -> bool:
        """验证变量值是否合法"""
        try:
            if self.type == 'int':
                v = int(value)
                if self.min_value is not None and v < self.min_value:
                    return False
                if self.max_value is not None and v > self.max_value:
                    return False
                return True
            elif self.type == 'bool':
                return isinstance(value, bool) or str(value).lower() in ['true', 'false', '1', '0']
            elif self.type == 'float':
                v = float(value)
                if self.min_value is not None and v < self.min_value:
                    return False
                if self.max_value is not None and v > self.max_value:
                    return False
                return True
            elif self.type == 'str':
                return isinstance(value, str) and len(value) <= 100
            return False
        except:
            return False

@dataclass
class TaskOperation:
    """基础操作定义"""
    type: Literal['click', 'swipe', 'wait', 'key', 'text', 'vlm_step']
    params: Dict[str, Any]
    condition: Optional[str] = None  # 条件表达式（Python语法）
    description: str = ""

@dataclass
class TaskDefinition:
    """任务定义（模板）"""
    id: str
    name: str
    description: str  # 自然语言目标描述
    game: str = "arknights_et"  # 游戏标识
    variables: List[TaskVariable] = field(default_factory=list)
    operations: List[TaskOperation] = field(default_factory=list)
    estimated_duration: int = 30  # 预估执行时间(秒)
    success_indicators: List[str] = field(default_factory=list)  # 成功标志（用于VLM验证）
    
    def instantiate(self, variable_values: Dict[str, Any], repeat_count: int = 1) -> 'TaskInstance':
        """创建任务实例"""
        # 验证变量
        for var in self.variables:
            if var.name not in variable_values:
                variable_values[var.name] = var.default
            elif not var.validate(variable_values[var.name]):
                raise ValueError(f"变量 {var.name} 值 {variable_values[var.name]} 不合法")
        
        return TaskInstance(
            task_id=self.id,
            task_name=self.name,
            variable_values=variable_values,
            repeat_count=repeat_count,
            operations=self.operations
        )

@dataclass
class TaskInstance:
    """任务实例（带具体参数）"""
    task_id: str
    task_name: str
    variable_values: Dict[str, Any]
    repeat_count: int = 1
    operations: List[TaskOperation] = field(default_factory=list)
    enabled: bool = True

@dataclass
class TaskGroup:
    """任务组（可持久化）"""
    name: str = "日常长草"
    tasks: List[TaskInstance] = field(default_factory=list)
    global_settings: Dict[str, Any] = field(default_factory=lambda: {
        "operation_delay": 0.8,      # 基础操作间隔(秒)
        "vlm_think_timeout": 30,     # VLM思考超时(秒)
        "max_retries": 3,            # 单任务最大重试次数
        "screenshot_interval": 2.0   # 截图间隔(秒)
    })
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_executed: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskGroup':
        # 兼容旧版本
        tasks = []
        for task_data in data.get('tasks', []):
            # 处理旧格式
            if 'variable_values' not in task_data:
                task_data['variable_values'] = {}
            if 'repeat_count' not in task_data:
                task_data['repeat_count'] = 1
            if 'enabled' not in task_data:
                task_data['enabled'] = True
            tasks.append(TaskInstance(**task_data))
        
        return cls(
            name=data.get('name', '日常长草'),
            tasks=tasks,
            global_settings=data.get('global_settings', {
                "operation_delay": 0.8,
                "vlm_think_timeout": 30,
                "max_retries": 3,
                "screenshot_interval": 2.0
            }),
            created_at=data.get('created_at', datetime.now().isoformat()),
            last_executed=data.get('last_executed')
        )

class TaskManager:
    """任务管理核心"""
    TASKS_DIR = "tasks"
    CURRENT_FILE = "current_task_group.json"
    
    def __init__(self):
        os.makedirs(self.TASKS_DIR, exist_ok=True)
        self.current_group: Optional[TaskGroup] = None
        self.load_current_group()
        self.register_default_tasks()
    
    def register_default_tasks(self):
        """注册明日方舟终末地默认任务模板"""
        if self.current_group and self.current_group.tasks:
            return  # 已有任务组，不覆盖
        
        # 创建默认任务组
        group = TaskGroup(name="终末地日常")
        
        # 任务1: 基建收菜
        task1 = TaskDefinition(
            id="collect_drone",
            name="无人机收菜",
            description="收集所有无人机的产出物",
            variables=[
                TaskVariable("drone_count", "int", 4, 1, 8, "无人机数量"),
                TaskVariable("use_accelerator", "bool", False, description="是否使用加速器")
            ],
            operations=[
                TaskOperation("click", {"x": 180, "y": 1800}, description="点击基建入口"),
                TaskOperation("wait", {"duration": 1500}),
                TaskOperation("vlm_step", {"prompt": "识别所有可收取的无人机，返回点击坐标列表"}, description="VLM识别可收取无人机"),
                TaskOperation("click", {"x": 540, "y": 1800}, description="点击返回"),
            ],
            success_indicators=["显示'收取成功'", "无人机状态变为'空闲'"]
        )
        group.tasks.append(task1.instantiate({"drone_count": 4, "use_accelerator": False}, repeat_count=1))
        
        # 任务2: 刷体力
        task2 = TaskDefinition(
            id="spend_stamina",
            name="消耗体力",
            description="刷指定关卡直到体力不足",
            variables=[
                TaskVariable("stage_id", "str", "LS-5", description="关卡ID"),
                TaskVariable("max_runs", "int", 10, 1, 50, "最大刷图次数"),
                TaskVariable("use_originium", "bool", False, description="是否使用源石恢复体力")
            ],
            operations=[
                TaskOperation("click", {"x": 950, "y": 1800}, description="点击战术终端"),
                TaskOperation("wait", {"duration": 1000}),
                TaskOperation("vlm_step", {"prompt": f"找到关卡{task2.variables[0].default}并点击进入"}, description="VLM导航到关卡"),
                TaskOperation("click", {"x": 950, "y": 1700}, description="点击开始行动"),
            ],
            success_indicators=["显示'行动结束'", "获得战利品"]
        )
        group.tasks.append(task2.instantiate({"stage_id": "LS-5", "max_runs": 10, "use_originium": False}, repeat_count=1))
        
        # 任务3: 信用商店
        task3 = TaskDefinition(
            id="credit_shop",
            name="信用商店采购",
            description="购买信用商店中所有可购买物品",
            variables=[
                TaskVariable("max_items", "int", 5, 1, 20, "最大购买数量"),
                TaskVariable("skip_sold_out", "bool", True, description="跳过已售罄商品")
            ],
            operations=[
                TaskOperation("click", {"x": 300, "y": 1800}, description="点击商店"),
                TaskOperation("wait", {"duration": 1200}),
                TaskOperation("swipe", {"start_x": 540, "start_y": 1500, "end_x": 540, "end_y": 800, "duration": 400}, description="滑动到信用商店"),
                TaskOperation("vlm_step", {"prompt": "识别所有'购买'按钮并返回坐标"}, description="VLM识别购买按钮"),
            ],
            success_indicators=["显示'购买成功'", "信用点数减少"]
        )
        group.tasks.append(task3.instantiate({"max_items": 5, "skip_sold_out": True}, repeat_count=1))
        
        self.current_group = group
        self.save_current_group()
    
    def load_current_group(self) -> bool:
        """加载当前任务组"""
        path = os.path.join(self.TASKS_DIR, self.CURRENT_FILE)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_group = TaskGroup.from_dict(data)
                    return True
            except Exception as e:
                print(f"加载任务组失败: {e}")
        return False
    
    def save_current_group(self) -> bool:
        """保存当前任务组"""
        if not self.current_group:
            return False
        
        try:
            path = os.path.join(self.TASKS_DIR, self.CURRENT_FILE)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.current_group.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存任务组失败: {e}")
            return False
    
    def get_task_templates(self) -> List[TaskDefinition]:
        """获取所有任务模板（用于设计器）"""
        # 实际应用中可从数据库/文件加载更多模板
        templates = []
        
        # 添加当前组中使用过的任务定义
        if self.current_group:
            # 此处简化：实际应维护全局任务模板库
            pass
        
        # 返回默认模板（简化版）
        return [
            TaskDefinition(
                id="custom_task",
                name="自定义任务",
                description="创建新任务",
                variables=[
                    TaskVariable("param1", "int", 1, 1, 100, "参数1"),
                    TaskVariable("enable_feature", "bool", True, description="启用特性")
                ],
                operations=[]
            )
        ]
    
    def add_task_to_group(self, task_instance: TaskInstance):
        """添加任务到当前组"""
        if not self.current_group:
            self.current_group = TaskGroup()
        self.current_group.tasks.append(task_instance)
        self.save_current_group()
    
    def remove_task_from_group(self, index: int):
        """从当前组移除任务"""
        if self.current_group and 0 <= index < len(self.current_group.tasks):
            self.current_group.tasks.pop(index)
            self.save_current_group()
    
    def update_task_in_group(self, index: int, task_instance: TaskInstance):
        """更新组内任务"""
        if self.current_group and 0 <= index < len(self.current_group.tasks):
            self.current_group.tasks[index] = task_instance
            self.save_current_group()
    
    def reorder_tasks(self, from_idx: int, to_idx: int):
        """重新排序任务"""
        if self.current_group and 0 <= from_idx < len(self.current_group.tasks) and 0 <= to_idx < len(self.current_group.tasks):
            task = self.current_group.tasks.pop(from_idx)
            self.current_group.tasks.insert(to_idx, task)
            self.save_current_group()