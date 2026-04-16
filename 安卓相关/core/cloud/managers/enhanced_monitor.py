"""
增强执行监控器 - 提供更精细的执行状态监控和验证集成

功能:
1. 基础监控（迭代次数、变化率、超时）
2. 验证集成（定期触发任务验证）
3. 决策协调（与决策转回机制集成）
"""
import time
import hashlib
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging


class MonitorAction(Enum):
    """监控动作枚举"""
    CONTINUE = "continue"
    VALIDATE = "validate"
    STOP = "stop"
    DELEGATE = "delegate"


@dataclass
class MonitorResult:
    """监控结果"""
    should_stop: bool = False
    should_validate: bool = False
    should_delegate: bool = False
    reason: str = ""
    action: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    validation_result: Optional[Dict[str, Any]] = None


class EnhancedExecutionMonitor:
    """增强执行监控器"""
    
    def __init__(self, 
                 max_iterations_per_task: int = 20,
                 min_change_rate: float = 0.1,
                 timeout_seconds: int = 300,
                 validation_interval: int = 3,
                 logger: Optional[logging.Logger] = None):
        """
        Args:
            max_iterations_per_task: 每个任务最大迭代次数
            min_change_rate: 最小变化率阈值
            timeout_seconds: 超时时间（秒）
            validation_interval: 验证间隔（每 N 次迭代进行一次完整验证）
            logger: 日志记录器
        """
        self.max_iterations_per_task = max_iterations_per_task
        self.min_change_rate = min_change_rate
        self.timeout_seconds = timeout_seconds
        self.validation_interval = validation_interval
        self.logger = logger or logging.getLogger("EnhancedExecutionMonitor")
        
        # 任务跟踪数据
        self.task_iterations = {}  # task_id -> iteration_count
        self.task_screenshots = {}  # task_id -> screenshot_hashes
        self.task_start_time = {}  # task_id -> start_time
        self.task_validation_results = {}  # task_id -> validation_results
    
    def track_task_execution(self, task_id: str, execution_context: Dict[str, Any]) -> MonitorResult:
        """
        跟踪任务执行状态
        
        Args:
            task_id: 任务 ID
            execution_context: 执行上下文，包含截图哈希、执行时间等信息
            
        Returns:
            MonitorResult: 监控结果
        """
        current_time = time.time()
        
        # 初始化任务跟踪
        if task_id not in self.task_iterations:
            self.task_iterations[task_id] = 0
            self.task_screenshots[task_id] = []
            self.task_start_time[task_id] = current_time
            
        # 增加迭代计数
        self.task_iterations[task_id] += 1
        iteration_count = self.task_iterations[task_id]
        
        # 记录截图哈希
        screenshot_hash = execution_context.get('screenshot_hash')
        if screenshot_hash:
            self.task_screenshots[task_id].append(screenshot_hash)
            # 保留最近 10 个哈希
            if len(self.task_screenshots[task_id]) > 10:
                self.task_screenshots[task_id].pop(0)
        
        # 计算执行时间
        elapsed_time = current_time - self.task_start_time[task_id]
        
        # 收集指标
        metrics = {
            'iteration_count': iteration_count,
            'elapsed_time': elapsed_time,
            'change_rate': 0.0
        }
        
        # 检查是否超过最大迭代次数
        if iteration_count >= self.max_iterations_per_task:
            self.logger.warning(f"Task {task_id} reached max iterations: {iteration_count}")
            return MonitorResult(
                should_stop=True,
                reason=f"达到最大迭代次数 ({self.max_iterations_per_task})",
                action="skip_task",
                metrics=metrics
            )
        
        # 检查执行时间
        if elapsed_time > self.timeout_seconds:
            self.logger.warning(f"Task {task_id} exceeded timeout: {elapsed_time:.1f}s")
            return MonitorResult(
                should_stop=True,
                reason=f"任务执行时间过长 ({elapsed_time:.1f}秒)",
                action="skip_task",
                metrics=metrics
            )
        
        # 计算变化率
        if len(self.task_screenshots.get(task_id, [])) >= 5:
            hashes = self.task_screenshots[task_id]
            unique_hashes = len(set(hashes))
            change_rate = unique_hashes / len(hashes)
            metrics['change_rate'] = change_rate
            
            # 检查变化率
            if change_rate < self.min_change_rate:
                self.logger.warning(f"Task {task_id} has low change rate: {change_rate:.2f}")
                return MonitorResult(
                    should_stop=True,
                    reason=f"界面变化率过低 ({change_rate:.2f} < {self.min_change_rate})",
                    action="skip_task",
                    metrics=metrics
                )
        
        # 检查是否需要验证
        should_validate = (iteration_count % self.validation_interval == 0)
        if should_validate:
            self.logger.debug(f"Task {task_id} needs validation at iteration {iteration_count}")
            return MonitorResult(
                should_validate=True,
                reason=f"达到验证间隔 ({iteration_count} iterations)",
                action="validate",
                metrics=metrics
            )
        
        # 正常继续
        return MonitorResult(
            should_stop=False,
            reason="normal_execution",
            action="continue",
            metrics=metrics
        )
    
    def record_validation_result(self, task_id: str, validation_result: Dict[str, Any]):
        """
        记录验证结果
        
        Args:
            task_id: 任务 ID
            validation_result: 验证结果
        """
        self.task_validation_results[task_id] = {
            'timestamp': time.time(),
            'result': validation_result
        }
        self.logger.info(f"Validation result recorded for task {task_id}")
    
    def get_iteration_info(self, task_id: str) -> Dict[str, Any]:
        """获取任务迭代信息"""
        if task_id not in self.task_iterations:
            return {}
            
        iteration_count = self.task_iterations[task_id]
        elapsed_time = time.time() - self.task_start_time[task_id]
        hashes = self.task_screenshots.get(task_id, [])
        unique_hashes = len(set(hashes)) if hashes else 0
        change_rate = unique_hashes / len(hashes) if hashes else 0.0
        
        return {
            'iteration_count': iteration_count,
            'elapsed_time': elapsed_time,
            'screenshot_count': len(hashes),
            'unique_screenshots': unique_hashes,
            'change_rate': change_rate
        }
    
    def reset_task(self, task_id: str):
        """重置任务跟踪"""
        if task_id in self.task_iterations:
            del self.task_iterations[task_id]
        if task_id in self.task_screenshots:
            del self.task_screenshots[task_id]
        if task_id in self.task_start_time:
            del self.task_start_time[task_id]
        if task_id in self.task_validation_results:
            del self.task_validation_results[task_id]
        
        self.logger.info(f"Task {task_id} tracking reset")
    
    def get_task_statistics(self, task_id: str) -> Dict[str, Any]:
        """获取任务统计信息"""
        if task_id not in self.task_iterations:
            return {}
            
        hashes = self.task_screenshots.get(task_id, [])
        unique_hashes = len(set(hashes)) if hashes else 0
        change_rate = unique_hashes / len(hashes) if hashes else 0.0
        
        return {
            'iteration_count': self.task_iterations[task_id],
            'elapsed_time': time.time() - self.task_start_time[task_id],
            'screenshot_count': len(hashes),
            'unique_screenshots': unique_hashes,
            'change_rate': change_rate,
            'validation_results': self.task_validation_results.get(task_id, {})
        }


class ScreenshotHashCalculator:
    """截图哈希计算器"""
    
    @staticmethod
    def calculate_hash(screenshot: np.ndarray) -> str:
        """
        计算截图哈希值
        
        Args:
            screenshot: 截图图像 (numpy 数组)
            
        Returns:
            str: 哈希值
        """
        if screenshot.size > 10000:
            # 取中心区域计算哈希
            h, w = screenshot.shape[:2]
            center = screenshot[h//4:3*h//4, w//4:3*w//4]
            # 转换为灰度并计算哈希
            if len(center.shape) == 3:
                center_gray = np.mean(center, axis=2).astype(np.uint8)
            else:
                center_gray = center
                
            # 计算简单哈希
            return hashlib.md5(center_gray.tobytes()).hexdigest()
        else:
            return hashlib.md5(screenshot.tobytes()).hexdigest()
    
    @staticmethod
    def calculate_change_rate(hash_history: List[str]) -> float:
        """
        计算截图变化率
        
        Args:
            hash_history: 哈希历史列表
            
        Returns:
            float: 变化率 (0.0 - 1.0)
        """
        if len(hash_history) < 2:
            return 1.0
            
        unique_hashes = len(set(hash_history))
        total_frames = len(hash_history)
        
        return unique_hashes / total_frames
