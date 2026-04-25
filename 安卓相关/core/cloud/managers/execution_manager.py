"""执行管理业务逻辑组件"""
import threading
import time
import base64
import math
import logging
import hashlib
from typing import Dict, Any, Optional

# 导入InferenceManager
try:
    from ...local_inference.inference_manager import InferenceManager, InferenceMode
    HAS_INFERENCE_MANAGER = True
except ImportError:
    HAS_INFERENCE_MANAGER = False
    InferenceMode = None

# VLM 服务器处理图像的基准分辨率
VLM_BASE_WIDTH = 1920
VLM_BASE_HEIGHT = 1080

def normalize_coordinate(coord: float, base_dim: int, target_dim: int) -> int:
    """
    将坐标从 VLM 基准分辨率转换为设备实际分辨率
    
    Args:
        coord: VLM 返回的坐标值（绝对坐标）
        base_dim: VLM 基准分辨率维度（1920 或 1080）
        target_dim: 设备实际分辨率维度
    
    Returns:
        转换后的设备坐标（整数）
    """
    # 如果坐标已经是归一化值（0-1 范围），直接乘以目标分辨率
    if coord <= 1.0:
        return int(coord * target_dim)
    
    # 否则是绝对坐标，需要从基准分辨率转换
    return int(coord * target_dim / base_dim)

def convert_coordinates_for_device(params: dict, device_width: int, device_height: int) -> dict:
    """
    将 VLM 返回的坐标参数转换为设备实际分辨率坐标
    
    Args:
        params: 包含坐标的参数字典
        device_width: 设备实际宽度
        device_height: 设备实际高度
    
    Returns:
        转换后的参数字典
    """
    converted = params.copy()
    
    # 处理单点坐标 (x, y)
    if 'x' in converted:
        converted['x'] = normalize_coordinate(converted['x'], VLM_BASE_WIDTH, device_width)
    if 'y' in converted:
        converted['y'] = normalize_coordinate(converted['y'], VLM_BASE_HEIGHT, device_height)
    
    # 处理 coordinates 列表 [x, y]
    if 'coordinates' in converted and isinstance(converted['coordinates'], list):
        coords = converted['coordinates']
        if len(coords) >= 2:
            converted['coordinates'] = [
                normalize_coordinate(coords[0], VLM_BASE_WIDTH, device_width),
                normalize_coordinate(coords[1], VLM_BASE_HEIGHT, device_height)
            ]
    
    # 处理 swipe 坐标 (x1, y1, x2, y2)
    if 'x1' in converted:
        converted['x1'] = normalize_coordinate(converted['x1'], VLM_BASE_WIDTH, device_width)
    if 'y1' in converted:
        converted['y1'] = normalize_coordinate(converted['y1'], VLM_BASE_HEIGHT, device_height)
    if 'x2' in converted:
        converted['x2'] = normalize_coordinate(converted['x2'], VLM_BASE_WIDTH, device_width)
    if 'y2' in converted:
        converted['y2'] = normalize_coordinate(converted['y2'], VLM_BASE_HEIGHT, device_height)
    
    # 处理 end_coordinates 列表 [x, y]
    if 'end_coordinates' in converted and isinstance(converted['end_coordinates'], list):
        coords = converted['end_coordinates']
        if len(coords) >= 2:
            converted['end_coordinates'] = [
                normalize_coordinate(coords[0], VLM_BASE_WIDTH, device_width),
                normalize_coordinate(coords[1], VLM_BASE_HEIGHT, device_height)
            ]
    
    return converted

class ExecutionManager:
    """执行管理业务逻辑类"""
    
    def __init__(self, device_manager, screen_capture, touch_executor, task_queue_manager, communicator, auth_manager, config=None):
        self.device_manager = device_manager
        self.screen_capture = screen_capture
        self.touch_executor = touch_executor
        self.task_queue_manager = task_queue_manager
        self.communicator = communicator
        self.auth_manager = auth_manager
        self.config = config or {}
        
        # 获取触控方式配置
        touch_config = self.config.get('touch', {})
        self.touch_method = touch_config.get('touch_method', 'maatouch')
        self.is_pc_mode = self.touch_method == 'pc_foreground'
        
        # 运行中操作跟踪
        self.running_operations = {}  # {operation_id: operation_info}
        self.next_operation_id = 1
        self.running_operations_lock = threading.Lock()
        
        self.client_running = False
        self.client_thread = None
        
        # 跟踪已执行一次的任务
        self.executed_once_tasks = set()
        
        # 心跳机制相关
        self.last_heartbeat_time = time.time()
        self.heartbeat_interval = 120  # 2 分钟心跳间隔（游戏 9 分钟超时，确保多次触发心跳）
        self.heartbeat_enabled = True
        
        # ========== 新增：任务验证和决策组件 ==========
        self.logger = logging.getLogger("ExecutionManager")
        
        # 初始化增强监控器（替代原有的 TaskExecutionMonitor）
        from .enhanced_monitor import EnhancedExecutionMonitor, ScreenshotHashCalculator
        self.enhanced_monitor = EnhancedExecutionMonitor(
            max_iterations_per_task=20,
            min_change_rate=0.1,
            timeout_seconds=300,
            validation_interval=3,
            logger=self.logger
        )
        self.screenshot_hash_calculator = ScreenshotHashCalculator()
        
        # 初始化任务验证引擎
        from .task_validator import TaskValidationEngine, TaskContext
        self.validation_engine = TaskValidationEngine(logger=self.logger)
        
        # 初始化决策协调器
        from .decision_coordinator import DecisionCoordinator
        self.decision_coordinator = DecisionCoordinator(logger=self.logger)
        
        # 任务上下文缓存
        self.task_context_cache = {}  # task_id -> TaskContext
        # 验证结果缓存
        self.validation_result_cache = {}  # task_id -> ValidationResult
        
        # ========== 新增：本地推理管理器 ==========
        self.inference_manager = None
        self._inference_mode = "cloud"  # 默认使用云端推理
        self._pending_inference_tasks = {}  # task_id -> task_info
        self._inference_lock = threading.Lock()
        
        # 初始化InferenceManager（如果可用）
        self._initialize_inference_manager()
        
    def _initialize_inference_manager(self):
        """初始化InferenceManager"""
        if not HAS_INFERENCE_MANAGER:
            self.logger.info("InferenceManager不可用，跳过初始化")
            return
        
        try:
            # 从配置中获取推理设置
            inference_config = self.config.get("inference", {})
            self._inference_mode = inference_config.get("mode", "cloud")
            
            # 创建InferenceManager实例
            self.inference_manager = InferenceManager(
                config=self.config,
                communicator=self.communicator
            )
            
            # 初始化InferenceManager
            if self.inference_manager.initialize():
                # 连接信号
                self.inference_manager.inference_complete.connect(self._on_inference_complete)
                self.inference_manager.inference_error.connect(self._on_inference_error)
                self.inference_manager.inference_progress.connect(self._on_inference_progress)
                
                self.logger.info(
                    "InferenceManager初始化成功",
                    mode=self._inference_mode,
                    local_available=self.inference_manager.is_local_available()
                )
            else:
                self.logger.warning("InferenceManager初始化失败，将使用云端推理")
                self.inference_manager = None
                
        except Exception as e:
            self.logger.exception("初始化InferenceManager时发生异常", error=str(e))
            self.inference_manager = None
    
    def _on_inference_complete(self, task_id: str, result: Dict[str, Any]):
        """异步推理完成回调"""
        self.logger.info(f"异步推理完成: {task_id}")
        
        with self._inference_lock:
            if task_id in self._pending_inference_tasks:
                self._pending_inference_tasks[task_id]["status"] = "completed"
                self._pending_inference_tasks[task_id]["result"] = result
                self._pending_inference_tasks[task_id]["completed_at"] = time.time()
    
    def _on_inference_error(self, task_id: str, error: str):
        """异步推理错误回调"""
        self.logger.error(f"异步推理出错: {task_id}, error={error}")
        
        with self._inference_lock:
            if task_id in self._pending_inference_tasks:
                self._pending_inference_tasks[task_id]["status"] = "error"
                self._pending_inference_tasks[task_id]["error"] = error
                self._pending_inference_tasks[task_id]["completed_at"] = time.time()
    
    def _on_inference_progress(self, task_id: str, progress: int):
        """异步推理进度回调"""
        with self._inference_lock:
            if task_id in self._pending_inference_tasks:
                self._pending_inference_tasks[task_id]["progress"] = progress
    
    def set_inference_mode(self, mode: str) -> bool:
        """
        设置推理模式
        
        Args:
            mode: 推理模式 ("local", "cloud", "auto")
            
        Returns:
            是否设置成功
        """
        if mode not in ["local", "cloud", "auto"]:
            self.logger.error(f"无效的推理模式: {mode}")
            return False
        
        # 检查本地推理是否可用
        if mode == "local" and (not self.inference_manager or not self.inference_manager.is_local_available()):
            self.logger.warning("本地推理不可用，无法切换到本地模式")
            return False
        
        self._inference_mode = mode
        
        # 更新InferenceManager的模式
        if self.inference_manager:
            self.inference_manager.switch_mode(mode)
        
        self.logger.info(f"推理模式已切换为: {mode}")
        return True
    
    def get_inference_mode(self) -> str:
        """获取当前推理模式"""
        return self._inference_mode
    
    def is_local_inference_available(self) -> bool:
        """检查本地推理是否可用"""
        return self.inference_manager is not None and self.inference_manager.is_local_available()
        
    def start_execution(self, log_callback, update_ui_callback, preview_update_callback=None):
        """开始执行"""
        if not self.auth_manager.get_login_status():
            return False, "请先登录后再执行任务"
        
        # PC 模式不需要检查 Android 设备连接
        if not self.is_pc_mode:
            if not self.device_manager.get_current_device():
                return False, "请先连接设备"
        else:
            # PC 模式需要检查触控管理器是否已连接 PC 窗口
            if not self.touch_executor.is_connected:
                return False, "请先连接 PC 窗口（触控未初始化）"
        
        if self.task_queue_manager.is_queue_empty():
            return False, "任务队列为空"
            
        if self.client_running:
            return False, "执行已在进行中"
            
        self.client_running = True
        
        self.client_thread = threading.Thread(
            target=self.run_automation,
            args=(log_callback, update_ui_callback, preview_update_callback),
            daemon=True
        )
        self.client_thread.start()
        
        return True, "执行已开始"
        
    def stop_execution(self):
        """停止执行"""
        self.client_running = False
        
    def _start_operation(self, action_type: str, params: dict) -> int:
        """开始一个操作并返回操作 ID"""
        with self.running_operations_lock:
            operation_id = self.next_operation_id
            self.next_operation_id += 1
            
            operation_info = {
                'id': operation_id,
                'action_type': action_type,
                'params': params.copy(),
                'start_time': time.time(),
                'status': 'running'
            }
            self.running_operations[operation_id] = operation_info
            return operation_id
    
    def _complete_operation(self, operation_id: int):
        """标记操作完成"""
        with self.running_operations_lock:
            if operation_id in self.running_operations:
                self.running_operations[operation_id]['status'] = 'completed'
                self.running_operations[operation_id]['end_time'] = time.time()
    
    def get_running_operations(self) -> list:
        """获取当前运行中的操作列表"""
        with self.running_operations_lock:
            return list(self.running_operations.values())
    
    def cancel_operation(self, operation_id: int) -> bool:
        """取消指定的操作"""
        with self.running_operations_lock:
            if operation_id in self.running_operations:
                self.running_operations[operation_id]['status'] = 'cancelled'
                self.running_operations[operation_id]['end_time'] = time.time()
                return True
            return False
    
    def update_operation_params(self, operation_id: int, new_params: dict) -> bool:
        """更新操作参数"""
        with self.running_operations_lock:
            if (operation_id in self.running_operations and
                self.running_operations[operation_id]['status'] == 'running'):
                self.running_operations[operation_id]['params'].update(new_params)
                return True
            return False
    
    def query_running_operations(self) -> list:
        """向服务器查询当前运行中的操作"""
        if not self.communicator:
            return []
        
        request_data = {
            "user_id": self.auth_manager.get_user_id(),
            "session_id": self.auth_manager.get_session_id()
        }
        
        response = self.communicator.send_request("get_running_operations", request_data)
        if response and response.get('status') == 'success':
            return response.get('data', {}).get('running_operations', [])
        return []
    
    def cancel_remote_operation(self, operation_id: int) -> bool:
        """取消远程服务器上的操作"""
        if not self.communicator:
            return False
        
        request_data = {
            "user_id": self.auth_manager.get_user_id(),
            "session_id": self.auth_manager.get_session_id(),
            "operation_id": operation_id
        }
        
        response = self.communicator.send_request("cancel_operation", request_data)
        return response and response.get('status') == 'success'
    
    def update_remote_operation_params(self, operation_id: int, new_params: dict) -> bool:
        """更新远程服务器上操作的参数"""
        if not self.communicator:
            return False
        
        request_data = {
            "user_id": self.auth_manager.get_user_id(),
            "session_id": self.auth_manager.get_session_id(),
            "operation_id": operation_id,
            "new_params": new_params
        }
        
        response = self.communicator.send_request("update_operation_params", request_data)
        return response and response.get('status') == 'success'
        
    def is_running(self):
        """检查是否正在运行"""
        return self.client_running
        
    def run_automation(self, log_callback, update_ui_callback, preview_update_callback=None):
        """运行自动化流程"""
        try:
            log_callback("开始自动化执行...", "execution", "INFO")
            
            total_executions = self.task_queue_manager.get_execution_count()
            is_infinite_loop = self.task_queue_manager.is_infinite_loop()
            
            execution = 0
            self.executed_once_tasks.clear()  # 清空已执行一次的任务记录
            
            # 初始化心跳计时器
            self.reset_heartbeat_timer()
            
            # 初始化异常检测器（保留用于异常检测）
            from .exception_detector import ArknightsEndfieldExceptionDetector
            exception_detector = ArknightsEndfieldExceptionDetector()
            
            # 重置增强监控器（每个执行周期重置）
            self.enhanced_monitor.task_iterations.clear()
            self.enhanced_monitor.task_screenshots.clear()
            self.enhanced_monitor.task_start_time.clear()
            self.enhanced_monitor.task_validation_results.clear()
            
            # 清空任务上下文缓存
            self.task_context_cache.clear()
            self.validation_result_cache.clear()
            
            while self.client_running and (is_infinite_loop or execution < total_executions):
                if not self.client_running:
                    break

                if is_infinite_loop:
                    log_callback(f"执行第 {execution + 1} 次（持续循环模式）", "execution", "INFO")
                else:
                    log_callback(f"执行第 {execution + 1}/{total_executions} 次", "execution", "INFO")

                self.task_queue_manager.reset_current_task_index()
                current_task_index = 0
                total_tasks = len(self.task_queue_manager.get_queue_info()['tasks'])

                # 检查任务队列是否为空
                if total_tasks == 0:
                    log_callback("任务队列为空，停止执行", "execution", "WARNING")
                    break

                while current_task_index < total_tasks and self.client_running:
                    current_task = self.task_queue_manager.get_current_task()
                    if not current_task:
                        log_callback(f"当前任务为空（索引：{current_task_index}），停止执行", "execution", "ERROR")
                        break
                        
                    task_id = current_task['id']
                    
                    # 检查是否为"仅执行一次"任务且已执行过
                    if current_task.get('execute_once', False) and task_id in self.executed_once_tasks:
                        log_callback(f"跳过任务 '{current_task['name']}'（已执行一次）", "execution", "INFO")
                        if self.task_queue_manager.advance_to_next_task():
                            current_task_index += 1
                        else:
                            break
                        continue
                    
                    update_ui_callback('current_task', f"当前任务：{current_task['name']}")
                    update_ui_callback('progress', f"进度：{current_task_index+1}/{total_tasks}")
                    
                    log_callback(f"执行任务：{current_task['name']}", "execution", "INFO")
                    
                    # 获取任务变量（包括自定义变量）
                    task_variables = {}
                    if 'custom_variables' in current_task:
                        task_variables.update(current_task['custom_variables'])
                    else:
                        task_variables.update(self.task_queue_manager.get_task_variables(task_id))
                    
                    # 捕获屏幕
                    current_device = self.device_manager.get_current_device()
                    
                    if self.is_pc_mode:
                        # PC 模式：使用 TouchManager 的截图功能
                        screen_data = self.touch_executor.screencap()
                        if not screen_data:
                            log_callback("PC 窗口截图失败", "execution", "ERROR")
                            break
                        # 获取 PC 窗口分辨率
                        resolution = self.touch_executor.get_resolution()
                        if resolution:
                            image_size = resolution  # (width, height)
                        else:
                            image_size = (1920, 1080)
                        # 捕获成功后，调用预览更新回调
                        if preview_update_callback:
                            preview_update_callback(screen_data)
                    else:
                        # Android 模式：使用 ScreenCapture 模块
                        if self.screen_capture and current_device:
                            screen_data = self.screen_capture.capture_screen(current_device)
                            if not screen_data:
                                log_callback("屏幕捕获失败", "execution", "ERROR")
                                break
                            # 获取实际发送的图像尺寸
                            image_size = self.screen_capture.last_image_size
                            # 捕获成功后，调用预览更新回调
                            if preview_update_callback:
                                preview_update_callback(screen_data)
                        else:
                            log_callback("屏幕捕获模块未初始化或设备未连接", "execution", "ERROR")
                            break
                    
                    # 获取设备信息
                    if self.is_pc_mode:
                        # PC 模式设备信息
                        device_info = {
                            'resolution': list(image_size) if image_size else [1920, 1080],
                            'model': 'PC',
                            'image_size': image_size
                        }
                    elif self.screen_capture and current_device:
                        device_info = self.screen_capture.get_device_info(current_device)
                        # 确保 image_size 在 device_info 中
                        if 'image_size' not in device_info or device_info['image_size'] is None:
                            device_info['image_size'] = image_size
                    else:
                        device_info = {'resolution': [1080, 1920], 'model': 'Unknown', 'image_size': image_size}
                    
                    # 构建任务上下文
                    task_context = {
                        "task_id": task_id,
                        "task_variables": task_variables,
                        "device_info": device_info,
                        "prompt": current_task.get("prompt", "")  # 如果任务有自定义prompt
                    }
                    
                    # 使用InferenceManager处理图像（优先本地推理）
                    response = self._process_image_with_inference_manager(
                        screen_data=screen_data,
                        task_context=task_context,
                        log_callback=log_callback
                    )
                    
                    if not response:
                        log_callback("图像处理失败：无法获取推理结果", "execution", "ERROR")
                        break
                    
                    if not response:
                        log_callback("网络连接失败：无法连接到服务端（已尝试重连 3 次）", "execution", "ERROR")
                        break

                    if response.get('status') != 'success':
                        error_message = response.get('message', '未知错误')
                        error_type = response.get('error_type')

                        # 检查是否是排队状态（供应商限流时会自动排队）
                        if response.get('status') == 'queued':
                            queue_id = response.get('queue_id')
                            log_callback(f"供应商限流，请求已自动加入队列 (ID: {queue_id})，等待后重试...", "execution", "WARNING")
                            # 等待一段时间后重试当前任务（不推进到下一个任务）
                            time.sleep(3)
                            continue

                        # 检查是否是会话过期错误
                        if error_type == 'session_expired':
                            log_callback("检测到会话过期，尝试自动重新认证...", "execution", "WARNING")
                            reauth_success, reauth_message = self._handle_authentication_failure(log_callback)
                            if reauth_success:
                                log_callback("重新认证成功，继续执行任务", "execution", "INFO")
                                # 更新会话 ID 并重试当前请求
                                request_data["session_id"] = self.auth_manager.get_session_id()
                                continue  # 重试当前任务
                            else:
                                log_callback(f"重新认证失败：{reauth_message}", "execution", "ERROR")
                                break
                        else:
                            log_callback(f"服务端处理失败：{error_message}", "execution", "ERROR")
                            break
                    
                    # 执行触控动作
                    # 调试日志：记录完整响应内容的关键字段
                    log_callback(f"服务端响应状态：{response.get('status')}", "execution", "INFO")
                    log_callback(f"服务端响应 keys: {list(response.keys())}", "execution", "INFO")
                    
                    # 服务端返回格式：{"status": "success", "result": {...}}
                    # touch_actions 在 result 子对象中
                    result_data = response.get('result', {})
                    touch_actions = result_data.get('touch_actions', [])
                    
                    # 兼容旧格式：如果 result 中没有，尝试从顶级获取
                    if not touch_actions:
                        touch_actions = response.get('touch_actions', [])
                    # 再兼容 data 子对象格式
                    if not touch_actions:
                        touch_actions = response.get('data', {}).get('touch_actions', [])
                    
                    # 调试日志：记录 touch_actions 内容
                    log_callback(f"服务端响应 touch_actions: {touch_actions}", "execution", "INFO")
                    
                    if touch_actions and self.touch_executor:
                        # 获取设备分辨率用于坐标转换
                        device_resolution = device_info.get('resolution', [1280, 720])
                        device_width = device_resolution[0] if len(device_resolution) >= 2 else 1280
                        device_height = device_resolution[1] if len(device_resolution) >= 2 else 720
                        
                        # 使用新的 execute_tool_call 方法
                        for action in touch_actions:
                            action_type = action.get('action', '')
                            
                            # 构建参数对象：将顶级字段作为参数（服务端返回的格式）
                            params = {}
                            # 从 action 顶级字段获取参数
                            for key in ['coordinates', 'end_coordinates', 'app_name', 'key_code',
                                         'text', 'duration', 'x', 'y', 'x1', 'y1', 'x2', 'y2']:
                                if key in action:
                                    params[key] = action[key]
                            
                            # 如果有 parameters 子对象，合并进来
                            if 'parameters' in action and isinstance(action['parameters'], dict):
                                params.update(action['parameters'])
                            
                            # 对涉及坐标的动作进行坐标转换（VLM 基准分辨率 1920x1080 -> 设备实际分辨率）
                            if action_type in ('click', 'swipe', 'long_press', 'drag'):
                                params = convert_coordinates_for_device(params, device_width, device_height)
                                log_callback(f"坐标转换：VLM(1920x1080) -> 设备 ({device_width}x{device_height})", "execution", "DEBUG")
                            
                            # 生成操作 ID 并记录运行中操作
                            operation_id = self._start_operation(action_type, params)
                            
                            # 执行工具调用（TouchManager 已连接设备，无需传递 device_serial）
                            success = self.touch_executor.execute_tool_call(
                                action_type, params
                            )
                            
                            # 标记操作完成
                            self._complete_operation(operation_id)
                            
                            if not success:
                                # 根据动作类型显示更准确的错误消息
                                if action_type in ('click', 'swipe', 'long_press', 'drag'):
                                    log_callback(f"MaaTouch 执行失败：{action_type}", "execution", "ERROR")
                                else:
                                    log_callback(f"操作执行失败：{action_type}", "execution", "ERROR")
                                break
                    
                    # 检查任务是否完成
                    # 服务端返回格式：顶层 task_completed 字段
                    task_completed = response.get('task_completed', False)
                    # 兼容旧格式：如果顶层没有，尝试从 data 子对象获取
                    if not task_completed:
                        task_completed = response.get('data', {}).get('task_completed', False)
                    # 再兼容 result 子对象格式
                    if not task_completed:
                        task_completed = response.get('result', {}).get('task_completed', False)
                    
                    # 调试日志：记录任务完成状态
                    log_callback(f"任务完成状态：{task_completed}", "execution", "DEBUG")
                    
                    # ========== 增强监控和验证机制 ==========
                    # 计算截图哈希用于变化率检测
                    screenshot_hash = None
                    if screen_data:
                        screenshot_hash = self.screenshot_hash_calculator.calculate_hash(screen_data)
                    
                    # 构建执行上下文
                    execution_context = {
                        'task_id': task_id,
                        'screenshot_hash': screenshot_hash,
                        'execution_time': time.time() - self.enhanced_monitor.task_start_time.get(task_id, time.time()),
                        'iteration_count': self.enhanced_monitor.task_iterations.get(task_id, 0),
                        'device_info': device_info,
                        'task_variables': task_variables,
                        'current_phase': current_task.get('current_phase', 'unknown')
                    }
                    
                    # 跟踪任务执行状态
                    monitor_result = self.enhanced_monitor.track_task_execution(task_id, execution_context)
                    
                    # 处理监控结果 - 停止条件
                    if monitor_result.should_stop:
                        log_callback(f"[增强监控] 任务 '{current_task['name']}' 触发停止：{monitor_result.reason}", "execution", "WARNING")
                        log_callback(f"[增强监控] 建议操作：{monitor_result.action}", "execution", "INFO")
                        
                        # 重置监控器并跳过当前任务
                        self.enhanced_monitor.reset_task(task_id)
                        exception_detector.reset()
                        
                        # 强制推进到下一个任务
                        if self.task_queue_manager.advance_to_next_task():
                            current_task_index += 1
                            log_callback(f"[异常处理] 跳过任务 '{current_task['name']}'，继续下一个任务", "execution", "INFO")
                        else:
                            log_callback("[异常处理] 任务队列已结束", "execution", "INFO")
                            break
                        continue
                    
                    # 处理监控结果 - 验证条件
                    if monitor_result.should_validate:
                        log_callback(f"[验证机制] 开始验证任务 '{current_task['name']}'", "execution", "DEBUG")
                        
                        # 构建任务上下文
                        from .task_validator import TaskContext
                        if task_id not in self.task_context_cache:
                            self.task_context_cache[task_id] = TaskContext(
                                task_id=task_id,
                                current_phase=current_task.get('current_phase', 'unknown'),
                                screenshots=[],
                                ocr_results=[],
                                task_variables=task_variables,
                                device_info=device_info,
                                iteration_count=monitor_result.metrics.get('iteration_count', 0),
                                execution_time=monitor_result.metrics.get('elapsed_time', 0),
                                validation_weights=current_task.get('validation_weights', {}),
                                completion_threshold=current_task.get('completion_threshold', 0.8),
                                business_rules=current_task.get('business_rules', [])
                            )
                        
                        task_context = self.task_context_cache[task_id]
                        task_context.iteration_count = monitor_result.metrics.get('iteration_count', 0)
                        task_context.execution_time = monitor_result.metrics.get('elapsed_time', 0)
                        
                        # 执行验证
                        validation_result = self.validation_engine.validate_task(task_context)
                        
                        # 记录验证结果
                        self.enhanced_monitor.record_validation_result(task_id, {
                            'completed': validation_result.completed,
                            'confidence': validation_result.confidence,
                            'details': validation_result.validation_details,
                            'reason': validation_result.completion_reason
                        })
                        
                        log_callback(
                            f"[验证结果] 任务 '{current_task['name']}' 验证：completed={validation_result.completed}, "
                            f"confidence={validation_result.confidence:.2f}, reason={validation_result.completion_reason}",
                            "execution", "INFO"
                        )
                        
                        # 存储验证结果用于决策
                        self.validation_result_cache[task_id] = validation_result
                        
                        # ========== 决策协调：检查是否需要决策转回 ==========
                        if not validation_result.can_decide_autonomously():
                            # 构建决策上下文
                            decision_context = {
                                'task_id': task_id,
                                'current_phase': current_task.get('current_phase', 'unknown'),
                                'iteration_count': monitor_result.metrics.get('iteration_count', 0),
                                'execution_time': monitor_result.metrics.get('elapsed_time', 0),
                                'change_rate': monitor_result.metrics.get('change_rate', 0),
                                'validation_results': {
                                    'fused': {
                                        'completed': validation_result.completed,
                                        'confidence': validation_result.confidence
                                    }
                                },
                                'device_info': device_info,
                                'task_variables': task_variables,
                                'max_iterations': self.enhanced_monitor.max_iterations_per_task,
                                'timeout_seconds': self.enhanced_monitor.timeout_seconds
                            }
                            
                            # 检查是否需要决策转回
                            should_delegate, trigger_reasons = self.decision_coordinator.should_delegate_decision(decision_context)
                            
                            if should_delegate:
                                log_callback(
                                    f"[决策协调] 任务 '{current_task['name']}' 需要决策转回，原因：{trigger_reasons}",
                                    "execution", "WARNING"
                                )
                                
                                # 创建决策请求
                                decision_request = self.decision_coordinator.create_decision_request(
                                    decision_context, trigger_reasons
                                )
                                
                                log_callback(
                                    f"[决策请求] 紧急程度：{decision_request.urgency_level}, "
                                    f"推荐选项：{len(decision_request.recommended_options)}",
                                    "execution", "INFO"
                                )
                                
                                # 使用自主决策作为降级方案
                                log_callback(
                                    f"[自主决策] 使用自主决策（无主任务响应）",
                                    "execution", "INFO"
                                )
                                
                                # 执行自主决策
                                directive = self.decision_coordinator.make_autonomous_decision(decision_context)
                                
                                log_callback(
                                    f"[决策指令] action={directive.action}, priority={directive.priority}",
                                    "execution", "INFO"
                                )
                                
                                # 根据决策指令执行相应操作
                                if directive.action == "skip":
                                    log_callback(
                                        f"[决策执行] 跳过任务 '{current_task['name']}'，原因：{directive.parameters.get('skip_reason')}",
                                        "execution", "WARNING"
                                    )
                                    self.enhanced_monitor.reset_task(task_id)
                                    if self.task_queue_manager.advance_to_next_task():
                                        current_task_index += 1
                                        continue
                                    else:
                                        break
                                elif directive.action == "continue":
                                    log_callback(
                                        f"[决策执行] 继续执行任务，策略：{directive.parameters.get('validation_strategy')}",
                                        "execution", "INFO"
                                    )
                    
                    # ========== 任务完成判定 ==========
                    # 结合 VLM 声明和验证结果进行任务完成判定
                    validation_result = self.validation_result_cache.get(task_id)
                    if validation_result and validation_result.completed and validation_result.confidence >= 0.7:
                        # 验证器确认任务完成
                        task_completed = True
                        log_callback(f"[任务完成] 基于验证结果确认任务 '{current_task['name']}' 完成", "execution", "INFO")
                    
                    if task_completed:
                        log_callback(f"任务 '{current_task['name']}' 完成", "execution", "INFO")
                        # 重置监控器
                        self.enhanced_monitor.reset_task(task_id)
                        exception_detector.reset()
                        # 如果是"仅执行一次"任务，记录已执行
                        if current_task.get('execute_once', False):
                            self.executed_once_tasks.add(task_id)
                        
                        # ========== 心跳机制：任务完成后检查是否需要执行心跳 ==========
                        if self.check_heartbeat_needed():
                            self.perform_heartbeat(log_callback)
                        # =========================================================
                        
                        if self.task_queue_manager.advance_to_next_task():
                            current_task_index += 1
                        else:
                            break
                    else:
                        # 任务未完成，继续当前任务
                        # 记录迭代信息用于调试
                        iteration_info = self.enhanced_monitor.get_iteration_info(task_id)
                        iteration_count = iteration_info.get('iteration_count', 0)
                        
                        if iteration_count % 5 == 0:
                            log_callback(f"[任务监控] 任务 '{current_task['name']}' 已执行 {iteration_count} 次迭代", "execution", "DEBUG")
                        
                        # ========== 心跳机制：在任务迭代等待时更频繁地检查心跳 ==========
                        # 每 3 次迭代检查一次心跳，确保在长时间等待时及时触发
                        if iteration_count % 3 == 0 and self.check_heartbeat_needed():
                            self.perform_heartbeat(log_callback)
                        # =========================================================
                        
                        time.sleep(1)
                
                if not self.client_running:
                    break
                    
                execution += 1
                
            log_callback("自动化执行结束", "execution", "INFO")
            # 通知 UI 停止执行
            if hasattr(update_ui_callback, '__call__'):
                update_ui_callback('stop_execution', None)
            else:
                # 如果 update_ui_callback 是对象，调用其方法
                if hasattr(update_ui_callback, 'stop_execution_ui'):
                    update_ui_callback.stop_execution_ui()
                    
        except Exception as e:
            log_callback(f"自动化执行异常：{str(e)}", "execution", "ERROR")
            import traceback
            log_callback(f"异常详情：{traceback.format_exc()}", "execution", "ERROR")
        finally:
            # 确保在任何情况下都正确重置执行状态
            self.client_running = False
    
    def _process_image_with_inference_manager(
        self,
        screen_data: bytes,
        task_context: Dict[str, Any],
        log_callback
    ) -> Optional[Dict[str, Any]]:
        """
        使用InferenceManager处理图像，优先本地推理，支持回退到云端
        
        Args:
            screen_data: 屏幕截图数据
            task_context: 任务上下文
            log_callback: 日志回调函数
            
        Returns:
            推理结果字典，失败返回None
        """
        try:
            # 检查是否使用本地推理
            use_local = (
                self.inference_manager and
                self._inference_mode in ["local", "auto"] and
                self.inference_manager.is_local_available()
            )
            
            if use_local:
                log_callback("使用本地推理处理图像...", "execution", "INFO")
                
                try:
                    # 使用同步推理（简化实现）
                    result = self.inference_manager.process_image(
                        image_data=screen_data,
                        task_context=task_context
                    )
                    
                    if result and result.get("status") == "success":
                        log_callback("本地推理成功", "execution", "INFO")
                        # 转换本地推理结果为统一格式
                        return self._convert_inference_result(result)
                    
                    # 本地推理失败，检查是否自动降级
                    if self._inference_mode == "auto":
                        log_callback("本地推理失败，自动降级到云端推理", "execution", "WARNING")
                    else:
                        log_callback(f"本地推理失败: {result.get('error', '未知错误')}", "execution", "ERROR")
                        return None
                        
                except Exception as e:
                    self.logger.exception("本地推理异常", error=str(e))
                    if self._inference_mode == "auto":
                        log_callback(f"本地推理异常，降级到云端: {str(e)}", "execution", "WARNING")
                    else:
                        return None
            
            # 使用云端推理
            if not self.communicator:
                log_callback("通信模块未初始化", "execution", "ERROR")
                return None
            
            log_callback("使用云端推理处理图像...", "execution", "INFO")
            
            # 构建云端请求数据
            request_data = {
                "user_id": self.auth_manager.get_user_id(),
                "session_id": self.auth_manager.get_session_id(),
                "device_image": screen_data.decode('utf-8') if screen_data else "",
                "current_task": task_context.get("task_id", ""),
                "task_variables": task_context.get("task_variables", {}),
                "device_info": task_context.get("device_info", {})
            }
            
            response = self.communicator.send_request("process_image", request_data)
            
            if not response:
                log_callback("网络连接失败：无法连接到服务端", "execution", "ERROR")
                return None
            
            # 处理云端响应
            if response.get('status') == 'success':
                return response
            elif response.get('status') == 'queued':
                # 排队状态，返回特殊标记
                return response
            else:
                error_message = response.get('message', '未知错误')
                log_callback(f"云端推理失败: {error_message}", "execution", "ERROR")
                return response
                
        except Exception as e:
            self.logger.exception("图像处理异常", error=str(e))
            log_callback(f"图像处理异常: {str(e)}", "execution", "ERROR")
            return None
    
    def _convert_inference_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        将InferenceManager的结果转换为统一的响应格式
        
        Args:
            result: InferenceManager返回的结果
            
        Returns:
            统一格式的响应字典
        """
        # 本地推理结果已经是标准格式
        # 确保包含必要的字段
        if result.get("status") != "success":
            return result
        
        # 确保result字段存在
        if "result" not in result:
            result["result"] = {}
        
        # 确保touch_actions在正确的位置
        if "touch_actions" in result and "touch_actions" not in result["result"]:
            result["result"]["touch_actions"] = result["touch_actions"]
        
        # 确保task_completed字段
        if "task_completed" not in result:
            result["task_completed"] = result.get("result", {}).get("task_completed", False)
        
        return result
        
    def _handle_authentication_failure(self, log_callback):
        """
        处理认证失败情况，尝试自动重新认证
        
        Args:
            log_callback: 日志回调函数
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # 调用 auth_manager 的 ensure_valid_session 方法尝试重新认证
            success, message = self.auth_manager.ensure_valid_session()
            
            if success:
                # 更新会话信息（注意：session_id 存储在 auth_manager 中）
                # self.session_id = self.auth_manager.get_session_id()
                return True, "重新认证成功"
            else:
                # 检查具体的错误类型并提供更详细的错误信息
                user_info = self.auth_manager.get_user_info()
                if not user_info:
                    # 可能是用户不存在或 API 密钥错误
                    return False, "用户不存在或 API 密钥无效"
                
                # 检查账户是否被封禁
                if user_info.get('is_banned', False):
                    ban_reason = user_info.get('ban_reason', '未知原因')
                    ban_until = user_info.get('ban_until', 0)
                    if ban_until > 0:
                        return False, f"账户被封禁至 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ban_until))}，原因：{ban_reason}"
                    else:
                        return False, f"账户被永久封禁，原因：{ban_reason}"
                
                return False, message
                
        except Exception as e:
            error_msg = f"重新认证过程中发生异常：{str(e)}"
            log_callback(error_msg, "execution", "ERROR")
            return False, error_msg
    
    # ========== CLI 模式支持方法 ==========
    
    def set_cli_mode(self, enabled: bool = True, screenshot_callback=None, output_dir: str = None):
        """配置 CLI 模式"""
        self._cli_mode = enabled
        self._cli_screenshot_callback = screenshot_callback
        self._cli_output_dir = output_dir
        self._cli_screenshot_data = []
    
    def run_cli_automation(self, log_callback, execution_count: int = 1, control_scheme: str = "ADB", window_title: str = None) -> bool:
        """CLI 模式运行自动化"""
        if not self.auth_manager.get_login_status():
            log_callback("请先登录后再执行任务", "execution", "ERROR")
            return False
        
        if not self.device_manager.current_device:
            log_callback("请先连接设备", "execution", "ERROR")
            return False
        
        if self.client_running:
            log_callback("执行已在进行中", "execution", "ERROR")
            return False
        
        self.client_running = True
        self._cli_screenshot_data = []
        
        try:
            # 设置执行次数
            self.task_queue_manager.execution_count = execution_count
            
            # 运行自动化
            self.run_automation(
                log_callback=log_callback,
                update_ui_callback=lambda k, v: None,  # CLI 模式不需要 UI 更新
                preview_update_callback=self._cli_screenshot_callback
            )
            return True
        except Exception as e:
            log_callback(f"执行异常：{e}", "execution", "ERROR")
            return False
        finally:
            self.client_running = False
    
    def get_cli_screenshot_data(self) -> list:
        """获取 CLI 模式的截图数据"""
        return getattr(self, '_cli_screenshot_data', [])

    def get_client_running_status(self):
        """获取客户端运行状态"""
        return self.client_running
    
    # ========== 心跳机制相关方法 ==========
    
    def check_heartbeat_needed(self) -> bool:
        """
        检查是否需要执行心跳操作
        
        Returns:
            bool: 是否需要执行心跳
        """
        if not self.heartbeat_enabled:
            return False
        
        current_time = time.time()
        elapsed = current_time - self.last_heartbeat_time
        return elapsed >= self.heartbeat_interval
    
    def perform_heartbeat(self, log_callback) -> bool:
        """
        执行心跳操作（点击主界面空白区域）
        
        Args:
            log_callback: 日志回调函数
            
        Returns:
            bool: 心跳执行是否成功
        """
        try:
            log_callback("[心跳机制] 执行心跳操作，保持登录状态...", "execution", "INFO")
            
            # 获取设备分辨率
            if self.is_pc_mode:
                resolution = self.touch_executor.get_resolution()
                if resolution:
                    width, height = resolution
                else:
                    width, height = 1920, 1080
            else:
                current_device = self.device_manager.get_current_device()
                if self.screen_capture and current_device:
                    device_info = self.screen_capture.get_device_info(current_device)
                    resolution = device_info.get('resolution', [1280, 720])
                    width, height = resolution[0], resolution[1]
                else:
                    width, height = 1280, 720
            
            # 点击屏幕中心偏下的空白区域（避免误触 UI 元素）
            # 选择屏幕中心偏下位置，通常是安全区域
            click_x = int(width * 0.5)
            click_y = int(height * 0.6)
            
            log_callback(f"[心跳机制] 点击坐标：({click_x}, {click_y})", "execution", "DEBUG")
            
            # 执行点击操作
            success = self.touch_executor.execute_tool_call(
                'click',
                {'x': click_x, 'y': click_y}
            )
            
            if success:
                self.last_heartbeat_time = time.time()
                log_callback("[心跳机制] 心跳操作执行成功", "execution", "INFO")
            else:
                log_callback("[心跳机制] 心跳操作执行失败", "execution", "WARNING")
            
            return success
            
        except Exception as e:
            log_callback(f"[心跳机制] 心跳操作异常：{str(e)}", "execution", "ERROR")
            return False
    
    def reset_heartbeat_timer(self):
        """重置心跳计时器"""
        self.last_heartbeat_time = time.time()
    
    def set_heartbeat_interval(self, interval_seconds: int):
        """
        设置心跳间隔
        
        Args:
            interval_seconds: 心跳间隔（秒）
        """
        self.heartbeat_interval = interval_seconds
        self.last_heartbeat_time = time.time()
    
    def enable_heartbeat(self, enabled: bool = True):
        """
        启用/禁用心跳机制
        
        Args:
            enabled: 是否启用心跳
        """
        self.heartbeat_enabled = enabled
    
    # ========== 登录超时检测相关方法 ==========
    
    def detect_login_timeout(self, screenshot_data: bytes, log_callback) -> bool:
        """
        检测是否出现登录超时弹窗
        
        Args:
            screenshot_data: 截图数据
            log_callback: 日志回调函数
            
        Returns:
            bool: 是否检测到登录超时
        """
        try:
            # 登录超时弹窗通常包含"长时间无操作"、"自动登出"等关键词
            # 这里应该调用 OCR 识别截图文本，然后检测关键词
            # 由于 OCR 需要额外模块，这里先返回 False
            # 实际实现中应该集成 OCR 检测
            return False
            
        except Exception as e:
            log_callback(f"[登录超时检测] 检测异常：{str(e)}", "execution", "ERROR")
            return False
    
    def handle_login_timeout(self, log_callback) -> bool:
        """
        处理登录超时情况，尝试重新登录
        
        Args:
            log_callback: 日志回调函数
            
        Returns:
            bool: 是否成功恢复
        """
        try:
            log_callback("[登录超时处理] 检测到登录超时，尝试重新登录...", "execution", "WARNING")
            
            # 1. 点击确认/关闭按钮关闭超时弹窗
            if self.is_pc_mode:
                resolution = self.touch_executor.get_resolution()
                width, height = resolution if resolution else (1920, 1080)
            else:
                current_device = self.device_manager.get_current_device()
                if self.screen_capture and current_device:
                    device_info = self.screen_capture.get_device_info(current_device)
                    resolution = device_info.get('resolution', [1280, 720])
                    width, height = resolution[0], resolution[1]
                else:
                    width, height = 1280, 720
            
            # 点击弹窗确认按钮（通常在屏幕底部中心）
            confirm_x = int(width * 0.5)
            confirm_y = int(height * 0.8)
            
            success = self.touch_executor.execute_tool_call(
                'click',
                {'x': confirm_x, 'y': confirm_y}
            )
            
            if not success:
                log_callback("[登录超时处理] 关闭弹窗失败", "execution", "ERROR")
                return False
            
            log_callback("[登录超时处理] 已关闭超时弹窗", "execution", "INFO")
            
            # 2. 等待界面刷新
            time.sleep(2)
            
            # 3. 执行心跳操作，重新激活会话
            self.perform_heartbeat(log_callback)
            
            # 4. 重置心跳计时器
            self.reset_heartbeat_timer()
            
            log_callback("[登录超时处理] 登录超时处理完成，继续执行任务", "execution", "INFO")
            return True
            
        except Exception as e:
            log_callback(f"[登录超时处理] 处理异常：{str(e)}", "execution", "ERROR")
            return False
    
    # ========== InferenceManager资源清理 ==========
    
    def shutdown_inference_manager(self):
        """
        关闭InferenceManager，释放资源
        
        在应用退出或切换配置时调用
        """
        if self.inference_manager:
            try:
                self.logger.info("正在关闭InferenceManager...")
                self.inference_manager.shutdown()
                self.inference_manager = None
                self.logger.info("InferenceManager已关闭")
            except Exception as e:
                self.logger.exception("关闭InferenceManager时发生异常", error=str(e))
    
    def __del__(self):
        """析构函数，确保资源被清理"""
        self.shutdown_inference_manager()
