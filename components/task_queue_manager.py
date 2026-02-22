"""任务队列管理业务逻辑组件"""
import os
import json

class TaskQueueManager:
    """任务队列管理业务逻辑类"""
    
    def __init__(self, task_manager):
        self.task_manager = task_manager
        self.task_queue = []
        self.current_task_index = 0
        self.execution_count = 1
        
    def load_default_tasks(self):
        """加载默认任务到队列"""
        if not self.task_manager:
            return []
            
        tasks = self.task_manager.get_default_task_chain()
        if tasks:
            self.task_queue.extend(tasks)
        return tasks
        
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
        if count > 0:
            self.execution_count = count
            
    def get_execution_count(self):
        """获取执行次数"""
        return self.execution_count
        
    def is_queue_empty(self):
        """检查队列是否为空"""
        return len(self.task_queue) == 0
        
    def get_task_variables(self, task_id):
        """获取任务变量"""
        if self.task_manager:
            return self.task_manager.get_task_variables(task_id)
        return {}
        
    def save_task_queue(self):
        """保存任务队列到本地"""
        import os
        import json
        
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        task_queue_file = os.path.join(cache_dir, "task_queue.json")
        try:
            with open(task_queue_file, 'w', encoding='utf-8') as f:
                json.dump(self.task_queue, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存任务队列失败: {e}")