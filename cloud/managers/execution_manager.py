"""执行管理业务逻辑组件"""
import threading
import time
import base64

class ExecutionManager:
    """执行管理业务逻辑类"""
    
    def __init__(self, device_manager, screen_capture, touch_executor, task_queue_manager, communicator, auth_manager):
        self.device_manager = device_manager
        self.screen_capture = screen_capture
        self.touch_executor = touch_executor
        self.task_queue_manager = task_queue_manager
        self.communicator = communicator
        self.auth_manager = auth_manager
        
        # 运行中操作跟踪
        self.running_operations = {}  # {operation_id: operation_info}
        self.next_operation_id = 1
        self.running_operations_lock = threading.Lock()
        
        self.client_running = False
        self.client_thread = None
        
        # 跟踪已执行一次的任务
        self.executed_once_tasks = set()
        
    def start_execution(self, log_callback, update_ui_callback, preview_update_callback=None):
        """开始执行"""
        if not self.auth_manager.get_login_status():
            return False, "请先登录后再执行任务"
            
        if not self.device_manager.get_current_device():
            return False, "请先连接设备"
            
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
        """开始一个操作并返回操作ID"""
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
                        log_callback(f"当前任务为空（索引: {current_task_index}），停止执行", "execution", "ERROR")
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
                    
                    update_ui_callback('current_task', f"当前任务: {current_task['name']}")
                    update_ui_callback('progress', f"进度: {current_task_index+1}/{total_tasks}")
                    
                    log_callback(f"执行任务: {current_task['name']}", "execution", "INFO")
                    
                    # 获取任务变量（包括自定义变量）
                    task_variables = {}
                    if 'custom_variables' in current_task:
                        task_variables.update(current_task['custom_variables'])
                    else:
                        task_variables.update(self.task_queue_manager.get_task_variables(task_id))
                    
                    # 捕获屏幕
                    current_device = self.device_manager.get_current_device()
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
                    if self.screen_capture and current_device:
                        device_info = self.screen_capture.get_device_info(current_device)
                        # 确保 image_size 在 device_info 中
                        if 'image_size' not in device_info or device_info['image_size'] is None:
                            device_info['image_size'] = image_size
                    else:
                        device_info = {'resolution': [1080, 1920], 'model': 'Unknown', 'image_size': image_size}
                    
                    # 构建请求数据
                    request_data = {
                        "user_id": self.auth_manager.get_user_id(),
                        "session_id": self.auth_manager.get_session_id(),
                        "device_image": screen_data.decode('utf-8') if screen_data else "",
                        "current_task": task_id,
                        "task_variables": task_variables,
                        "device_info": device_info
                    }
                    
                    # 发送请求到服务端
                    if self.communicator:
                        response = self.communicator.send_request("process_image", request_data)
                    else:
                        log_callback("通信模块未初始化", "execution", "ERROR")
                        break
                    
                    if not response:
                        log_callback("网络连接失败：无法连接到服务端（已尝试重连3次）", "execution", "ERROR")
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
                                # 更新会话ID并重试当前请求
                                request_data["session_id"] = self.auth_manager.get_session_id()
                                continue  # 重试当前任务
                            else:
                                log_callback(f"重新认证失败: {reauth_message}", "execution", "ERROR")
                                break
                        else:
                            log_callback(f"服务端处理失败: {error_message}", "execution", "ERROR")
                            break
                        
                    # 执行触控动作
                    touch_actions = response.get('data', {}).get('touch_actions', [])
                    if touch_actions and self.touch_executor and current_device:
                        # 使用新的 execute_tool_call 方法
                        for action in touch_actions:
                            action_type = action.get('action', '')
                            params = action.get('parameters', {})
                            
                            # 转换坐标格式（兼容旧格式）
                            if 'coordinates' in action:
                                params['coordinates'] = action['coordinates']
                            if 'end_coordinates' in action.get('parameters', {}):
                                params['end_coordinates'] = action['parameters']['end_coordinates']
                            
                            # 生成操作ID并记录运行中操作
                            operation_id = self._start_operation(action_type, params)
                            
                            # 执行工具调用
                            success = self.touch_executor.execute_tool_call(
                                current_device, action_type, params
                            )
                            
                            # 标记操作完成
                            self._complete_operation(operation_id)
                            
                            if not success:
                                # 根据动作类型显示更准确的错误消息
                                if action_type in ('click', 'swipe', 'long_press', 'drag'):
                                    log_callback(f"MaaTouch 执行失败: {action_type}", "execution", "ERROR")
                                else:
                                    log_callback(f"操作执行失败: {action_type}", "execution", "ERROR")
                                break
                            
                    # 检查任务是否完成
                    task_completed = response.get('data', {}).get('task_completed', False)
                    if task_completed:
                        log_callback(f"任务 '{current_task['name']}' 完成", "execution", "INFO")
                        # 如果是"仅执行一次"任务，记录已执行
                        if current_task.get('execute_once', False):
                            self.executed_once_tasks.add(task_id)
                        if self.task_queue_manager.advance_to_next_task():
                            current_task_index += 1
                        else:
                            break
                    else:
                        # 任务未完成，继续当前任务
                        time.sleep(1)
                        
                if not self.client_running:
                    break
                    
                execution += 1
                    
            log_callback("自动化执行结束", "execution", "INFO")
            # 通知UI停止执行
            if hasattr(update_ui_callback, '__call__'):
                update_ui_callback('stop_execution', None)
            else:
                # 如果update_ui_callback是对象，调用其方法
                if hasattr(update_ui_callback, 'stop_execution_ui'):
                    update_ui_callback.stop_execution_ui()
                    
        except Exception as e:
            log_callback(f"自动化执行异常: {str(e)}", "execution", "ERROR")
            import traceback
            log_callback(f"异常详情: {traceback.format_exc()}", "execution", "ERROR")
        finally:
            # 确保在任何情况下都正确重置执行状态
            self.client_running = False
        
    def _handle_authentication_failure(self, log_callback):
        """
        处理认证失败情况，尝试自动重新认证
        
        Args:
            log_callback: 日志回调函数
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # 调用auth_manager的ensure_valid_session方法尝试重新认证
            success, message = self.auth_manager.ensure_valid_session()
            
            if success:
                # 更新会话信息（注意：session_id存储在auth_manager中）
                # self.session_id = self.auth_manager.get_session_id()
                return True, "重新认证成功"
            else:
                # 检查具体的错误类型并提供更详细的错误信息
                user_info = self.auth_manager.get_user_info()
                if not user_info:
                    # 可能是用户不存在或API密钥错误
                    return False, "用户不存在或API密钥无效"
                
                # 检查账户是否被封禁
                if user_info.get('is_banned', False):
                    ban_reason = user_info.get('ban_reason', '未知原因')
                    ban_until = user_info.get('ban_until', 0)
                    if ban_until > 0:
                        return False, f"账户被封禁至 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ban_until))}，原因: {ban_reason}"
                    else:
                        return False, f"账户被永久封禁，原因: {ban_reason}"
                
                return False, message
                
        except Exception as e:
            error_msg = f"重新认证过程中发生异常: {str(e)}"
            log_callback(error_msg, "execution", "ERROR")
            return False, error_msg

    def get_client_running_status(self):
        """获取客户端运行状态"""
        return self.client_running