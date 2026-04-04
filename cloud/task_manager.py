import json
import os
import sys
from typing import List, Dict, Any, Optional
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

class TaskManager:

    def __init__(self, config_dir: str='config', data_dir: str='data'):
        self.config_dir: str = config_dir
        self.data_dir: str = data_dir
        self.user_preferences_file: str = os.path.join(config_dir, 'user_preferences.json')
        os.makedirs(self.config_dir, exist_ok=True)
        self.user_preferences: Dict[str, Dict[str, Any]] = self._load_user_preferences()

    def add_task_to_chain(self, task_chain: List[Dict], task_template: Dict) -> List[Dict]:
        task_chain.append(task_template)
        return task_chain

    def remove_task_from_chain(self, task_chain: List[Dict], task_id: str) -> List[Dict]:
        return [task for task in task_chain if task.get('id') != task_id]

    def get_task_variables(self, task_id: str) -> Dict[str, Any]:
        return self.user_preferences.get(task_id, {})

    def set_task_variables(self, task_id: str, variables: Dict[str, Any]):
        self.user_preferences[task_id] = variables
        self._save_user_preferences()

    def _load_user_preferences(self) -> Dict[str, Dict[str, Any]]:
        if os.path.exists(self.user_preferences_file):
            try:
                with open(self.user_preferences_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_user_preferences(self):
        try:
            with open(self.user_preferences_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_preferences, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f'保存用户偏好失败: {e}')

    def create_task_template(self, name: str, description: str, variables: Optional[List[Dict]]=None) -> Dict:
        import time
        return {'id': f'task_{int(time.time())}', 'name': name, 'description': description, 'variables': variables or [], 'created_at': time.time(), 'updated_at': time.time()}