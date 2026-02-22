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
        
        self.client_running = False
        self.client_thread = None
        
    def start_execution(self, log_callback, update_ui_callback):
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
            args=(log_callback, update_ui_callback),
            daemon=True
        )
        self.client_thread.start()
        
        return True, "执行已开始"
        
    def stop_execution(self):
        """停止执行"""
        self.client_running = False
        
    def is_running(self):
        """检查是否正在运行"""
        return self.client_running
        
    def run_automation(self, log_callback, update_ui_callback):
        """运行自动化流程"""
        log_callback("开始自动化执行...", "execution", "INFO")
        
        total_executions = self.task_queue_manager.get_execution_count()
        for execution in range(total_executions):
            if not self.client_running:
                break
                
            log_callback(f"执行第 {execution + 1}/{total_executions} 次", "execution", "INFO")
            
            self.task_queue_manager.reset_current_task_index()
            current_task_index = 0
            total_tasks = len(self.task_queue_manager.get_queue_info()['tasks'])
            
            while current_task_index < total_tasks and self.client_running:
                current_task = self.task_queue_manager.get_current_task()
                if not current_task:
                    break
                    
                task_id = current_task['id']
                
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
                else:
                    log_callback("屏幕捕获模块未初始化或设备未连接", "execution", "ERROR")
                    break
                    
                # 获取设备信息
                if self.screen_capture and current_device:
                    device_info = self.screen_capture.get_device_info(current_device)
                else:
                    device_info = {'resolution': [1080, 1920], 'model': 'Unknown'}
                
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
                    log_callback("服务端处理失败: 无响应", "execution", "ERROR")
                    break
                    
                if response.get('status') != 'success':
                    error_message = response.get('message', '未知错误')
                    log_callback(f"服务端处理失败: {error_message}", "execution", "ERROR")
                    break
                    
                # 执行触控动作
                touch_actions = response.get('data', {}).get('touch_actions', [])
                if touch_actions and self.touch_executor and current_device:
                    success = self.touch_executor.execute_touch_actions(current_device, touch_actions)
                    if not success:
                        log_callback("触控执行失败", "execution", "ERROR")
                        break
                        
                # 检查任务是否完成
                task_completed = response.get('data', {}).get('task_completed', False)
                if task_completed:
                    log_callback(f"任务 '{current_task['name']}' 完成", "execution", "INFO")
                    if self.task_queue_manager.advance_to_next_task():
                        current_task_index += 1
                    else:
                        break
                else:
                    # 任务未完成，继续当前任务
                    time.sleep(1)
                    
            if not self.client_running:
                break
                
        log_callback("自动化执行结束", "execution", "INFO")
        # 通知UI停止执行
        if hasattr(update_ui_callback, '__call__'):
            update_ui_callback('stop_execution', None)
        else:
            # 如果update_ui_callback是对象，调用其方法
            if hasattr(update_ui_callback, 'stop_execution_ui'):
                update_ui_callback.stop_execution_ui()
        
    def get_client_running_status(self):
        """获取客户端运行状态"""
        return self.client_running