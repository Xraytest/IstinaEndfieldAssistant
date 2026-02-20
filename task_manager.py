"""
任务管理模块 - 负责任务链管理和用户偏好缓存
"""
import json
import os
import sys
from typing import List, Dict, Any, Optional

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

class TaskManager:
    """任务管理器"""
    
    def __init__(self, config_dir: str = "config", data_dir: str = "data"):
        """
        初始化任务管理器
        
        Args:
            config_dir: 配置目录路径
            data_dir: 数据目录路径
        """
        self.config_dir = config_dir
        self.data_dir = data_dir
        self.tasks_dir = os.path.join(data_dir, "tasks")
        self.user_preferences_file = os.path.join(config_dir, "user_preferences.json")
        
        # 确保目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.tasks_dir, exist_ok=True)
        
        # 加载用户偏好
        self.user_preferences = self._load_user_preferences()
        
    def get_default_task_chain(self) -> List[Dict]:
        """
        获取默认任务链
        
        Returns:
            任务模板列表
        """
        default_tasks_file = os.path.join(self.tasks_dir, "default_tasks.json")
        if os.path.exists(default_tasks_file):
            with open(default_tasks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 返回空任务链
            return []
            
    def add_task_to_chain(self, task_chain: List[Dict], task_template: Dict) -> List[Dict]:
        """
        向任务链添加任务
        
        Args:
            task_chain: 当前任务链
            task_template: 要添加的任务模板
            
        Returns:
            更新后的任务链
        """
        task_chain.append(task_template)
        return task_chain
        
    def remove_task_from_chain(self, task_chain: List[Dict], task_id: str) -> List[Dict]:
        """
        从任务链移除任务
        
        Args:
            task_chain: 当前任务链
            task_id: 要移除的任务ID
            
        Returns:
            更新后的任务链
        """
        return [task for task in task_chain if task.get('id') != task_id]
        
    def get_task_variables(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务变量（包括用户偏好）
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务变量字典
        """
        return self.user_preferences.get(task_id, {})
        
    def set_task_variables(self, task_id: str, variables: Dict[str, Any]):
        """
        设置任务变量（保存用户偏好）
        
        Args:
            task_id: 任务ID
            variables: 任务变量字典
        """
        self.user_preferences[task_id] = variables
        self._save_user_preferences()
        
    def _load_user_preferences(self) -> Dict[str, Dict[str, Any]]:
        """加载用户偏好"""
        if os.path.exists(self.user_preferences_file):
            try:
                with open(self.user_preferences_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
        
    def _save_user_preferences(self):
        """保存用户偏好"""
        try:
            with open(self.user_preferences_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_preferences, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"保存用户偏好失败: {e}")
            
    def create_task_template(self, name: str, description: str, 
                           variables: Optional[List[Dict]] = None) -> Dict:
        """
        创建任务模板
        
        Args:
            name: 任务名称
            description: 任务描述
            variables: 任务变量列表
            
        Returns:
            任务模板字典
        """
        import time
        
        return {
            "id": f"task_{int(time.time())}",
            "name": name,
            "description": description,
            "variables": variables or [],
            "created_at": time.time(),
            "updated_at": time.time()
        }
        
    def save_task_template(self, task_template: Dict):
        """
        保存任务模板到文件
        
        Args:
            task_template: 任务模板字典
        """
        task_id = task_template['id']
        task_file = os.path.join(self.tasks_dir, f"{task_id}.json")
        try:
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task_template, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"保存任务模板失败: {e}")
            
    def load_task_template(self, task_id: str) -> Optional[Dict]:
        """
        从文件加载任务模板
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务模板字典或None
        """
        task_file = os.path.join(self.tasks_dir, f"{task_id}.json")
        if os.path.exists(task_file):
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None