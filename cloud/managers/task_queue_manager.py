"""任务队列管理业务逻辑组件"""
import os
import json

class TaskQueueManager:
    """任务队列管理业务逻辑类"""
    
    def __init__(self, task_manager, cache_dir=None):
        self.task_manager = task_manager
        self.task_queue = []
        self.current_task_index = 0
        self.execution_count = 1
        # 使用传入的缓存目录，如果没有则使用默认路径
        if cache_dir is not None:
            self.cache_dir = cache_dir
        else:
            # 获取client目录路径（相对于当前文件的上两级目录）
            client_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.cache_dir = os.path.join(client_dir, "cache")
        
    def add_task(self, task):
        """添加任务到队列"""
        self.task_queue.append(task)
        
    def remove_task(self, index):
        """从队列中移除任务"""
        if 0 <= index < len(self.task_queue):
            removed_task = self.task_queue.pop(index)
            # 调整当前任务索引
            if index < self.current_task_index:
                self.current_task_index -= 1
            elif index == self.current_task_index:
                self.current_task_index = max(0, self.current_task_index - 1)
            return removed_task
        return None
        
    def clear_queue(self):
        """清空任务队列"""
        self.task_queue = []
        self.current_task_index = 0
        
    def get_queue_info(self):
        """获取队列信息"""
        return {
            'tasks': self.task_queue,
            'count': len(self.task_queue),
            'current_index': self.current_task_index
        }
        
    def get_current_task(self):
        """获取当前任务"""
        if 0 <= self.current_task_index < len(self.task_queue):
            return self.task_queue[self.current_task_index]
        return None
        
    def advance_to_next_task(self):
        """前进到下一个任务"""
        if self.current_task_index < len(self.task_queue) - 1:
            self.current_task_index += 1
            return True
        return False
        
    def reset_current_task_index(self):
        """重置当前任务索引"""
        self.current_task_index = 0
        
    def set_execution_count(self, count):
        """设置执行次数"""
        if count > 0 or count == -1:
            self.execution_count = count
            
    def get_execution_count(self):
        """获取执行次数"""
        return self.execution_count
        
    def is_infinite_loop(self):
        """检查是否为无限循环模式"""
        return self.execution_count == -1
        
    def is_queue_empty(self):
        """检查队列是否为空"""
        return len(self.task_queue) == 0
        
    def get_task_variables(self, task_id):
        """获取任务变量"""
        if self.task_manager:
            return self.task_manager.get_task_variables(task_id)
        return {}
        
    def save_task_queue(self):
        """保存任务队列到本地 - 仅保存id、name和用户自定义设置"""
        import os
        import json
        
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
        task_queue_file = os.path.join(self.cache_dir, "task_queue.json")
        try:
            # 仅保留必要字段：id、name、custom_name、execute_once、custom_variables
            queue_to_save = []
            for task in self.task_queue:
                minimal_task = {
                    'id': task.get('id'),
                    'name': task.get('name'),
                    'custom_name': task.get('custom_name'),
                    'execute_once': task.get('execute_once', False),
                    'custom_variables': task.get('custom_variables', {})
                }
                queue_to_save.append(minimal_task)
            
            with open(task_queue_file, 'w', encoding='utf-8') as f:
                json.dump(queue_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存任务队列失败: {e}")
            
    def reorder_task(self, from_index, to_index):
        """重新排序任务 - 将任务从from_index移动到to_index"""
        if 0 <= from_index < len(self.task_queue) and 0 <= to_index < len(self.task_queue):
            task = self.task_queue.pop(from_index)
            self.task_queue.insert(to_index, task)
            
            # 调整当前任务索引
            if self.current_task_index == from_index:
                self.current_task_index = to_index
            elif from_index < self.current_task_index <= to_index:
                self.current_task_index -= 1
            elif to_index <= self.current_task_index < from_index:
                self.current_task_index += 1
            
            return True
        return False
        
    def move_task(self, from_index, to_index):
        """移动任务到指定位置（别名方法，供GUI调用）"""
        return self.reorder_task(from_index, to_index)