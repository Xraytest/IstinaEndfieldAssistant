import os
import json

class TaskQueueManager:

    def __init__(self, task_manager, cache_dir=None):
        self.task_manager = task_manager
        self.task_queue = []
        self.current_task_index = 0
        self.execution_count = 1
        if cache_dir is not None:
            self.cache_dir = cache_dir
        else:
            client_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.cache_dir = os.path.join(client_dir, 'cache')

    def add_task(self, task):
        self.task_queue.append(task)

    def remove_task(self, index):
        if 0 <= index < len(self.task_queue):
            removed_task = self.task_queue.pop(index)
            if index < self.current_task_index:
                self.current_task_index -= 1
            elif index == self.current_task_index:
                self.current_task_index = max(0, self.current_task_index - 1)
            return removed_task
        return None

    def clear_queue(self):
        self.task_queue = []
        self.current_task_index = 0

    def get_queue_info(self):
        return {'tasks': self.task_queue, 'count': len(self.task_queue), 'current_index': self.current_task_index}

    def get_current_task(self):
        if 0 <= self.current_task_index < len(self.task_queue):
            return self.task_queue[self.current_task_index]
        return None

    def advance_to_next_task(self):
        if self.current_task_index < len(self.task_queue) - 1:
            self.current_task_index += 1
            return True
        return False

    def reset_current_task_index(self):
        self.current_task_index = 0

    def set_execution_count(self, count):
        if count > 0 or count == -1:
            self.execution_count = count

    def get_execution_count(self):
        return self.execution_count

    def is_infinite_loop(self):
        return self.execution_count == -1

    def is_queue_empty(self):
        return len(self.task_queue) == 0

    def get_task_variables(self, task_id):
        if self.task_manager:
            return self.task_manager.get_task_variables(task_id)
        return {}

    def save_task_queue(self):
        import os
        import json
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        task_queue_file = os.path.join(self.cache_dir, 'task_queue.json')
        try:
            queue_to_save = []
            for task in self.task_queue:
                minimal_task = {'id': task.get('id'), 'name': task.get('name'), 'custom_name': task.get('custom_name'), 'execute_once': task.get('execute_once', False), 'custom_variables': task.get('custom_variables', {})}
                queue_to_save.append(minimal_task)
            with open(task_queue_file, 'w', encoding='utf-8') as f:
                json.dump(queue_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'保存任务队列失败: {e}')

    def reorder_task(self, from_index, to_index):
        if 0 <= from_index < len(self.task_queue) and 0 <= to_index < len(self.task_queue):
            task = self.task_queue.pop(from_index)
            self.task_queue.insert(to_index, task)
            if self.current_task_index == from_index:
                self.current_task_index = to_index
            elif from_index < self.current_task_index <= to_index:
                self.current_task_index -= 1
            elif to_index <= self.current_task_index < from_index:
                self.current_task_index += 1
            return True
        return False

    def move_task(self, from_index, to_index):
        return self.reorder_task(from_index, to_index)