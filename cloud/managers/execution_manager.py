"""执行管理业务逻辑组件"""
import threading
import time
import base64
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime

# PC设备支持 - Win32Controller
import sys
import os
# 添加server目录到路径以便导入Win32Controller
server_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'server')
if server_path not in sys.path:
    sys.path.insert(0, server_path)

try:
    from server.core.controller.win32_controller import Win32Controller
    from server.core.controller.controller_base import InputMethod
    PC_CONTROLLER_AVAILABLE = True
except ImportError:
    PC_CONTROLLER_AVAILABLE = False
    print("[警告] Win32Controller导入失败，PC设备支持不可用")

# 设备状态管理
try:
    from client.core.device_state_manager import DeviceStateManager
    DEVICE_STATE_MANAGER_AVAILABLE = True
except ImportError:
    DEVICE_STATE_MANAGER_AVAILABLE = False
    print("[警告] DeviceStateManager导入失败，设备状态管理不可用")

class ExecutionManager:
    """执行管理业务逻辑类 - GUI和CLI共用"""
    
    def __init__(self, device_manager, screen_capture, touch_executor, task_queue_manager, communicator, auth_manager, get_device_type_callback=None):
        self.device_manager = device_manager
        self.screen_capture = screen_capture
        self.touch_executor = touch_executor
        self.task_queue_manager = task_queue_manager
        self.communicator = communicator
        self.auth_manager = auth_manager
        self.get_device_type_callback = get_device_type_callback  # 获取设备类型的回调
        
        # PC设备控制器
        self.pc_controller: Optional[Win32Controller] = None
        self.pc_window_title: str = "Endfield"  # 默认窗口标题
        
        # 设备状态管理器
        self.device_state_manager: Optional[DeviceStateManager] = None
        
        # 运行中操作跟踪
        self.running_operations = {}  # {operation_id: operation_info}
        self.next_operation_id = 1
        self.running_operations_lock = threading.Lock()
        
        self.client_running = False
        self.client_thread = None
        
        # 跟踪已执行一次的任务
        self.executed_once_tasks = set()
        
        # CLI模式特有属性
        self.cli_mode = False
        self.cli_screenshot_callback: Optional[Callable[[], Optional[bytes]]] = None
        self.cli_current_task_name: str = ""
        self.cli_current_task_variables: Dict[str, Any] = {}
        self.cli_screenshot_data_list: List[Dict[str, Any]] = []
        self.cli_output_dir: Optional[str] = None
    
    def _is_pc_device(self) -> bool:
        """检查当前是否为PC设备"""
        if self.get_device_type_callback:
            device_type = self.get_device_type_callback()
            return device_type == "PC"
        return False
    
    def _get_pc_window_title(self) -> str:
        """获取PC窗口标题"""
        if self.device_manager and hasattr(self.device_manager, 'get_pc_window_title'):
            return self.device_manager.get_pc_window_title()
        return self.pc_window_title
    
    def _get_pc_control_scheme(self) -> str:
        """获取PC触控方案"""
        if self.device_manager and hasattr(self.device_manager, 'get_pc_control_scheme'):
            return self.device_manager.get_pc_control_scheme()
        return "Win32-Front"  # 默认使用前台方案
    
    def _init_pc_controller(self, log_callback=None) -> bool:
        """初始化PC控制器（根据选择的触控方案）"""
        if not PC_CONTROLLER_AVAILABLE:
            if log_callback:
                log_callback("PC控制器不可用，请检查Win32Controller模块", "execution", "ERROR")
            return False
        
        try:
            # 获取窗口标题和触控方案
            window_title = self._get_pc_window_title()
            control_scheme = self._get_pc_control_scheme()
            
            # 根据触控方案创建对应的控制器
            if control_scheme == "Win32-Window":
                self.pc_controller = Win32Controller.create_window_controller()
            elif control_scheme == "Win32-Express":
                self.pc_controller = Win32Controller.create_express_controller()
            elif control_scheme == "Win32-Front":
                self.pc_controller = Win32Controller.create_front_controller()
            else:
                self.pc_controller = Win32Controller.create_front_controller()
            
            if log_callback:
                log_callback(f"PC控制器创建: {control_scheme}", "execution", "INFO")
            
            # 连接到游戏窗口
            if self.pc_controller.connect(window_title=window_title):
                if log_callback:
                    log_callback(f"PC控制器连接成功: {window_title} ({control_scheme})", "execution", "INFO")
                return True
            else:
                if log_callback:
                    log_callback(f"PC控制器连接失败: 未找到窗口 '{window_title}'", "execution", "ERROR")
                return False
        except Exception as e:
            if log_callback:
                log_callback(f"PC控制器初始化异常: {e}", "execution", "ERROR")
            return False
    
    def _execute_pc_touch_action(self, action_type: str, params: dict, log_callback=None) -> bool:
        """执行PC设备的触控动作"""
        if not self.pc_controller:
            if log_callback:
                log_callback("PC控制器未初始化", "execution", "ERROR")
            return False
        
        try:
            # 获取窗口尺寸 (Win32Controller使用_width和_height属性)
            width = getattr(self.pc_controller, '_width', 1920)
            height = getattr(self.pc_controller, '_height', 1080)
            
            if action_type == 'click':
                # 获取坐标
                coords = params.get('coordinates', [0.5, 0.5])
                if isinstance(coords, list) and len(coords) >= 2:
                    rel_x, rel_y = coords[0], coords[1]
                else:
                    rel_x, rel_y = 0.5, 0.5
                
                # 转换为绝对坐标
                abs_x = int(rel_x * width)
                abs_y = int(rel_y * height)
                
                if log_callback:
                    log_callback(f"[PC点击] 相对坐标: ({rel_x:.4f}, {rel_y:.4f}), 绝对坐标: ({abs_x}, {abs_y})", "execution", "INFO")
                
                success = self.pc_controller.click(abs_x, abs_y)
                if log_callback:
                    log_callback(f"[PC点击] 执行结果: {'成功' if success else '失败'}", "execution", "INFO")
                return success
            
            elif action_type == 'swipe':
                # 获取滑动坐标
                coords = params.get('coordinates', {})
                if isinstance(coords, dict):
                    start = coords.get('start', [0.3, 0.5])
                    end = coords.get('end', [0.7, 0.5])
                else:
                    # 旧格式
                    start = params.get('coordinates', [0.3, 0.5])
                    end = params.get('end_coordinates', [0.7, 0.5])
                
                x1 = int(start[0] * width)
                y1 = int(start[1] * height)
                x2 = int(end[0] * width)
                y2 = int(end[1] * height)
                duration = params.get('duration', 300)
                
                if log_callback:
                    log_callback(f"[PC滑动] ({x1},{y1}) -> ({x2},{y2}), duration={duration}ms", "execution", "INFO")
                
                return self.pc_controller.swipe(x1, y1, x2, y2, duration)
            
            elif action_type == 'long_press':
                coords = params.get('coordinates', [0.5, 0.5])
                if isinstance(coords, list) and len(coords) >= 2:
                    rel_x, rel_y = coords[0], coords[1]
                else:
                    rel_x, rel_y = 0.5, 0.5
                
                abs_x = int(rel_x * width)
                abs_y = int(rel_y * height)
                duration = params.get('duration', 1000)
                
                if log_callback:
                    log_callback(f"[PC长按] ({abs_x},{abs_y}), duration={duration}ms", "execution", "INFO")
                
                return self.pc_controller.long_press(abs_x, abs_y, duration)
            
            elif action_type == 'key' or action_type == 'press_key':
                key_code = params.get('key_code', params.get('key', ''))
                if log_callback:
                    log_callback(f"[PC按键] {key_code}", "execution", "INFO")
                return self.pc_controller.press_key(str(key_code))
            
            elif action_type == 'system_button':
                button = params.get('button', 'back')
                # 映射系统按钮到按键
                key_map = {'back': 'ESC', 'home': 'HOME', 'menu': 'MENU'}
                key_code = key_map.get(button, button.upper())
                if log_callback:
                    log_callback(f"[PC系统按钮] {button} -> {key_code}", "execution", "INFO")
                return self.pc_controller.press_key(key_code)
            
            elif action_type == 'wait':
                # 等待动作
                duration = params.get('duration', 1.0)
                if log_callback:
                    log_callback(f"[PC等待] 等待 {duration} 秒", "execution", "INFO")
                time.sleep(duration)
                return True
            
            elif action_type == 'input_text':
                # 文本输入
                text = params.get('text', '')
                if log_callback:
                    log_callback(f"[PC文本输入] {text[:20]}...", "execution", "INFO")
                return self.pc_controller.input_text(text)
            
            elif action_type == 'terminate':
                # 终止任务
                if log_callback:
                    log_callback("[PC终止] 收到终止指令", "execution", "INFO")
                return True
            
            else:
                if log_callback:
                    log_callback(f"[PC] 未知动作类型: {action_type}", "execution", "WARNING")
                return True  # 未知动作返回True以避免中断任务链
                
        except Exception as e:
            if log_callback:
                log_callback(f"[PC触控执行异常] {e}", "execution", "ERROR")
            return False
        
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
                    
                    # 设备状态验证和恢复
                    if not self._ensure_device_ready_for_task(current_task, log_callback):
                        log_callback(f"设备状态准备失败，跳过任务: {current_task['name']}", "execution", "ERROR")
                        if self.task_queue_manager.advance_to_next_task():
                            current_task_index += 1
                        else:
                            break
                        continue
                    
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
                    if touch_actions:
                        # 检查是否为PC设备
                        is_pc = self._is_pc_device()
                        
                        # PC设备：初始化PC控制器（如果尚未初始化）
                        if is_pc and not self.pc_controller:
                            if not self._init_pc_controller(log_callback):
                                log_callback("PC控制器初始化失败，无法执行触控动作", "execution", "ERROR")
                                break
                        
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
                            
                            # 根据设备类型选择执行器
                            if is_pc:
                                # PC设备使用Win32Controller
                                success = self._execute_pc_touch_action(action_type, params, log_callback)
                            elif self.touch_executor and current_device:
                                # 安卓设备使用TouchExecutor
                                success = self.touch_executor.execute_tool_call(
                                    current_device, action_type, params
                                )
                            else:
                                log_callback("无可用触控执行器", "execution", "ERROR")
                                success = False
                            
                            # 标记操作完成
                            self._complete_operation(operation_id)
                            
                            if not success:
                                # 根据动作类型显示更准确的错误消息
                                if action_type in ('click', 'swipe', 'long_press', 'drag'):
                                    log_callback(f"触控执行失败: {action_type}", "execution", "ERROR")
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
                        # 任务未完成，检查是否需要异常恢复
                        if not self._check_and_handle_execution_anomaly(response, current_task, log_callback):
                            log_callback(f"任务执行异常无法恢复，跳过任务: {current_task['name']}", "execution", "ERROR")
                            if self.task_queue_manager.advance_to_next_task():
                                current_task_index += 1
                            else:
                                break
                        else:
                            # 任务正常进行，继续当前任务
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
    
    def _init_device_state_manager(self, log_callback=None) -> bool:
        """初始化设备状态管理器"""
        if not DEVICE_STATE_MANAGER_AVAILABLE:
            if log_callback:
                log_callback("设备状态管理器不可用", "execution", "WARNING")
            return False
        
        try:
            self.device_state_manager = DeviceStateManager(
                self.screen_capture,
                self.touch_executor,
                self.communicator,
                self.auth_manager
            )
            if log_callback:
                log_callback("设备状态管理器初始化成功", "execution", "INFO")
            return True
        except Exception as e:
            if log_callback:
                log_callback(f"设备状态管理器初始化异常: {e}", "execution", "ERROR")
            return False

    def get_client_running_status(self):
        """获取客户端运行状态"""
        return self.client_running
    
    # ==================== CLI模式支持方法 ====================
    
    def set_cli_mode(self, enabled: bool, screenshot_callback: Callable[[], Optional[bytes]] = None,
                     output_dir: str = None):
        """
        设置CLI模式
        
        Args:
            enabled: 是否启用CLI模式
            screenshot_callback: 截图回调函数（CLI模式下使用）
            output_dir: 输出目录
        """
        self.cli_mode = enabled
        self.cli_screenshot_callback = screenshot_callback
        self.cli_output_dir = output_dir
        self.cli_screenshot_data_list = []
    
    def _ensure_device_ready_for_task(self, current_task: Dict[str, Any], log_callback) -> bool:
        """
        确保设备准备好执行当前任务
        
        Args:
            current_task: 当前任务信息
            log_callback: 日志回调函数
            
        Returns:
            设备是否准备好
        """
        task_id = current_task['id']
        current_device = self.device_manager.get_current_device()
        
        if not current_device:
            log_callback("设备未连接，无法准备任务状态", "execution", "ERROR")
            return False
        
        # 检查是否为PC设备
        is_pc = self._is_pc_device()
        if is_pc:
            # PC设备不需要复杂的设备状态管理
            log_callback("PC设备模式，跳过设备状态验证", "execution", "INFO")
            return True
        
        # 初始化设备状态管理器（如果尚未初始化）
        if self.device_state_manager is None:
            if not self._init_device_state_manager(log_callback):
                log_callback("设备状态管理器初始化失败，跳过状态验证", "execution", "WARNING")
                return True  # 继续执行，但不进行状态验证
        
        # 确保设备准备好执行任务
        try:
            log_callback(f"开始设备状态验证，任务: {task_id}", "execution", "INFO")
            ready = self.device_state_manager.ensure_device_ready(current_device, task_id)
            if ready:
                log_callback("设备状态验证成功", "execution", "INFO")
            else:
                log_callback("设备状态验证失败", "execution", "ERROR")
            return ready
        except Exception as e:
            log_callback(f"设备状态验证异常: {e}", "execution", "ERROR")
            return False
    
    def _cli_log(self, message: str, log_callback: Callable = None):
        """CLI模式日志输出"""
        if log_callback:
            log_callback(message, "execution", "INFO")
        print(f"[CLI] {message}")
    
    def _capture_cli_screenshot(self) -> Optional[bytes]:
        """CLI模式截图"""
        if self.cli_screenshot_callback:
            return self.cli_screenshot_callback()
        return None
    
    def _record_cli_screenshot(self, screenshot_data: bytes, task_name: str, task_variables: Dict):
        """记录CLI模式截图信息"""
        if not self.cli_output_dir or not screenshot_data:
            return
        
        import json
        import re
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', task_name)[:50]
        filename = f"{timestamp}_{safe_name}.png"
        filepath = os.path.join(self.cli_output_dir, filename)
        
        # 保存截图
        if isinstance(screenshot_data, str):
            # Base64 encoded string, decode to bytes
            import base64
            screenshot_bytes = base64.b64decode(screenshot_data)
        else:
            # Already bytes
            screenshot_bytes = screenshot_data
            
        with open(filepath, 'wb') as f:
            f.write(screenshot_bytes)
        
        # 记录信息
        self.cli_screenshot_data_list.append({
            "timestamp": timestamp,
            "datetime": datetime.now().isoformat(),
            "task_name": task_name,
            "task_variables": task_variables.copy() if task_variables else {},
            "screenshot_file": filename
        })
        
        # 更新描述文件
        self._update_cli_description_json()
    
    def _update_cli_description_json(self):
        """更新CLI模式描述JSON文件"""
        if not self.cli_output_dir:
            return
        
        import json
        
        description = {
            "run_start_time": getattr(self, 'cli_run_start_time', ''),
            "control_scheme": getattr(self, 'cli_control_scheme', 'Win32-Window'),
            "window_title": getattr(self, 'cli_window_title', 'Endfield'),
            "screenshot_interval": getattr(self, 'cli_screenshot_interval', 1.0),
            "screenshots": self.cli_screenshot_data_list
        }
        
        filepath = os.path.join(self.cli_output_dir, "task_description.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(description, f, ensure_ascii=False, indent=2)
    
    def run_cli_automation(self, log_callback: Callable = None,
                           execution_count: int = 1,
                           control_scheme: str = "Win32-Window",
                           window_title: str = "Endfield") -> bool:
        """
        CLI模式运行自动化流程 - 与GUI共用核心逻辑
        
        Args:
            log_callback: 日志回调函数
            execution_count: 执行次数，-1表示无限循环
            control_scheme: 触控方案
            window_title: 窗口标题
            
        Returns:
            是否成功完成
        """
        # 保存CLI配置
        self.cli_control_scheme = control_scheme
        self.cli_window_title = window_title
        self.cli_run_start_time = datetime.now().isoformat()
        
        try:
            self._cli_log("开始CLI自动化执行...", log_callback)
            
            # 设置执行次数
            self.task_queue_manager.set_execution_count(execution_count)
            total_executions = self.task_queue_manager.get_execution_count()
            is_infinite_loop = self.task_queue_manager.is_infinite_loop()
            
            execution = 0
            self.executed_once_tasks.clear()
            self.client_running = True
            
            while self.client_running and (is_infinite_loop or execution < total_executions):
                if not self.client_running:
                    break

                if is_infinite_loop:
                    self._cli_log(f"执行第 {execution + 1} 次（持续循环模式）", log_callback)
                else:
                    self._cli_log(f"执行第 {execution + 1}/{total_executions} 次", log_callback)

                self.task_queue_manager.reset_current_task_index()
                current_task_index = 0
                total_tasks = len(self.task_queue_manager.get_queue_info()['tasks'])

                if total_tasks == 0:
                    self._cli_log("任务队列为空，停止执行", log_callback)
                    break

                while current_task_index < total_tasks and self.client_running:
                    current_task = self.task_queue_manager.get_current_task()
                    if not current_task:
                        self._cli_log(f"当前任务为空（索引: {current_task_index}），停止执行", log_callback)
                        break
                        
                    task_id = current_task['id']
                    
                    # 检查是否为"仅执行一次"任务且已执行过
                    if current_task.get('execute_once', False) and task_id in self.executed_once_tasks:
                        self._cli_log(f"跳过任务 '{current_task['name']}'（已执行一次）", log_callback)
                        if self.task_queue_manager.advance_to_next_task():
                            current_task_index += 1
                        else:
                            break
                        continue
                    
                    self._cli_log(f"执行任务: {current_task['name']}", log_callback)
                    
                    # 更新CLI任务信息
                    self.cli_current_task_name = current_task['name']
                    self.cli_current_task_variables = current_task.get('custom_variables', {})
                    
                    # 获取任务变量
                    task_variables = {}
                    if 'custom_variables' in current_task:
                        task_variables.update(current_task['custom_variables'])
                    else:
                        task_variables.update(self.task_queue_manager.get_task_variables(task_id))
                    
                    # 执行任务步骤循环
                    task_completed = self._execute_cli_task_steps(
                        current_task, task_variables, log_callback
                    )
                    
                    if task_completed:
                        self._cli_log(f"任务 '{current_task['name']}' 完成", log_callback)
                        if current_task.get('execute_once', False):
                            self.executed_once_tasks.add(task_id)
                        if self.task_queue_manager.advance_to_next_task():
                            current_task_index += 1
                        else:
                            break
                    else:
                        self._cli_log(f"任务 '{current_task['name']}' 失败", log_callback)
                        break
                    
                    time.sleep(1)
                
                if not self.client_running:
                    break
                
                execution += 1
            
            self._cli_log("CLI自动化执行结束", log_callback)
            return True
            
        except Exception as e:
            error_msg = f"CLI自动化执行异常: {str(e)}"
            self._cli_log(error_msg, log_callback)
            import traceback
            self._cli_log(f"异常详情: {traceback.format_exc()}", log_callback)
            return False
        finally:
            self.client_running = False
    
    def _execute_cli_task_steps(self, task: Dict, task_variables: Dict,
                                 log_callback: Callable) -> bool:
        """
        CLI模式执行单个任务的步骤循环
        
        Args:
            task: 任务信息
            task_variables: 任务变量
            log_callback: 日志回调
            
        Returns:
            任务是否完成
        """
        task_id = task['id']
        max_steps = 100
        step_count = 0
        
        while step_count < max_steps and self.client_running:
            # 截图
            screenshot_data = self._capture_cli_screenshot()
            if not screenshot_data:
                self._cli_log("屏幕捕获失败", log_callback)
                return False
            
            # 记录截图
            self._record_cli_screenshot(screenshot_data, task['name'], task_variables)
            
            # 获取图像尺寸 - 根据设备类型选择不同方式
            is_pc = self._is_pc_device()
            if is_pc and self.pc_controller:
                # PC设备使用控制器尺寸
                try:
                    width = getattr(self.pc_controller, '_width', 1920)
                    height = getattr(self.pc_controller, '_height', 1080)
                    image_size = [width, height]
                except:
                    image_size = [1920, 1080]
            else:
                # 安卓设备使用截图尺寸
                try:
                    from PIL import Image
                    import io
                    import base64
                    if isinstance(screenshot_data, str):
                        img_bytes = base64.b64decode(screenshot_data)
                    else:
                        img_bytes = screenshot_data
                    img = Image.open(io.BytesIO(img_bytes))
                    image_size = list(img.size)
                except:
                    image_size = [1920, 1080]
            
            # 构建请求
            if isinstance(screenshot_data, str):
                # Already base64 encoded string
                screenshot_b64 = screenshot_data
            else:
                # Raw bytes, need to encode
                screenshot_b64 = base64.b64encode(screenshot_data).decode('utf-8')
            request_data = {
                "user_id": self.auth_manager.get_user_id(),
                "session_id": self.auth_manager.get_session_id(),
                "device_image": screenshot_b64,
                "current_task": task_id,
                "task_variables": task_variables,
                "device_info": {
                    'resolution': image_size,
                    'model': 'PC',
                    'image_size': image_size
                }
            }
            
            # 发送请求
            response = self.communicator.send_request("process_image", request_data)
            
            if not response:
                self._cli_log("网络连接失败", log_callback)
                time.sleep(1)
                continue
            
            if response.get('status') == 'queued':
                self._cli_log("供应商限流，等待重试...", log_callback)
                time.sleep(3)
                continue
            
            if response.get('status') != 'success':
                error_msg = response.get('message', '未知错误')
                self._cli_log(f"服务端处理失败: {error_msg}", log_callback)
                return False
            
            # 执行触控动作
            touch_actions = response.get('data', {}).get('touch_actions', [])
            if touch_actions:
                # 根据设备类型选择执行器
                if is_pc:
                    # PC设备：确保PC控制器已初始化
                    if not self.pc_controller:
                        if not self._init_pc_controller(log_callback):
                            self._cli_log("PC控制器初始化失败", log_callback)
                            return False
                else:
                    # 安卓设备：确保touch_executor可用
                    if not self.touch_executor:
                        self._cli_log("触控执行器未初始化", log_callback)
                        return False
                
                for action in touch_actions:
                    if not self.client_running:
                        return False
                    
                    action_type = action.get('action', '')
                    params = action.get('parameters', {})
                    
                    if 'coordinates' in action:
                        params['coordinates'] = action['coordinates']
                    
                    # 根据设备类型执行触控
                    if is_pc:
                        success = self._execute_pc_touch_action(action_type, params, log_callback)
                    else:
                        # 安卓设备使用TouchExecutor，传递截图尺寸用于正确的坐标转换
                        current_device = self.device_manager.get_current_device()
                        success = self.touch_executor.execute_tool_call(
                            current_device, action_type, params,
                            image_size=tuple(image_size)  # 传递截图实际尺寸
                        )
                        if success:
                            self._cli_log(f"触控执行成功: {action_type}", log_callback)
                    
                    if not success:
                        self._cli_log(f"触控执行失败: {action_type}", log_callback)
                        return False
            
            # 检查任务是否完成
            task_completed = response.get('data', {}).get('task_completed', False)
            if task_completed:
                return True
            
            step_count += 1
            time.sleep(1)
        
        return False
    
    def get_cli_screenshot_data(self) -> List[Dict[str, Any]]:
        """获取CLI模式截图数据列表"""
        return self.cli_screenshot_data_list
    
    def _check_and_handle_execution_anomaly(self, response: Dict[str, Any], current_task: Dict[str, Any], log_callback) -> bool:
        """
        检查并处理任务执行中的异常
        
        Args:
            response: 服务器响应
            current_task: 当前任务信息
            log_callback: 日志回调函数
            
        Returns:
            是否成功处理异常（True表示可以继续，False表示需要跳过任务）
        """
        task_id = current_task['id']
        current_device = self.device_manager.get_current_device()
        
        if not current_device:
            return False
        
        # 检查是否有明确的异常指示
        if response.get('status') == 'error':
            error_type = response.get('error_type', 'unknown')
            error_message = response.get('message', '未知错误')
            log_callback(f"检测到任务执行错误: {error_type} - {error_message}", "execution", "ERROR")
            
            # 尝试设备状态恢复
            if self._attempt_device_recovery(current_task, log_callback):
                log_callback("设备状态恢复成功，继续任务执行", "execution", "INFO")
                return True
            else:
                log_callback("设备状态恢复失败", "execution", "ERROR")
                return False
        
        # 检查VLM响应中的异常标记
        vlm_data = response.get('data', {})
        if vlm_data.get('anomaly_detected', False):
            anomaly_type = vlm_data.get('anomaly_type', 'unknown')
            log_callback(f"VLM检测到异常: {anomaly_type}", "execution", "WARNING")
            
            # 根据异常类型决定处理策略
            if anomaly_type in ['界面错误', '逻辑错误', '资源不足']:
                if self._attempt_device_recovery(current_task, log_callback):
                    log_callback("异常恢复成功，继续任务执行", "execution", "INFO")
                    return True
                else:
                    log_callback("异常恢复失败", "execution", "ERROR")
                    return False
            elif anomaly_type == 'unexpected_action':
                # 动作异常，可能需要重新规划
                log_callback("检测到意外动作，等待界面稳定", "execution", "INFO")
                time.sleep(3)
                return True
            else:
                # 其他异常类型，尝试通用恢复
                if self._attempt_device_recovery(current_task, log_callback):
                    return True
                else:
                    return False
        
        # 检查触控动作是否为空或无效
        touch_actions = vlm_data.get('touch_actions', [])
        if not touch_actions:
            log_callback("VLM未返回有效触控动作，可能遇到异常", "execution", "WARNING")
            # 尝试设备状态恢复
            if self._attempt_device_recovery(current_task, log_callback):
                return True
            else:
                return False
        
        # 检查思考内容中是否包含错误关键词
        thinking = vlm_data.get('thinking', '')
        error_keywords = ['错误', '异常', '失败', '无法', '找不到', 'error', 'fail', 'cannot', '不能']
        for keyword in error_keywords:
            if keyword in thinking.lower():
                log_callback(f"VLM思考内容包含错误关键词: {keyword}", "execution", "WARNING")
                if self._attempt_device_recovery(current_task, log_callback):
                    return True
                else:
                    return False
        
        # 没有检测到异常，正常继续
        return True
    
    def _attempt_device_recovery(self, current_task: Dict[str, Any], log_callback) -> bool:
        """
        尝试设备状态恢复
        
        Args:
            current_task: 当前任务信息
            log_callback: 日志回调函数
            
        Returns:
            恢复是否成功
        """
        task_id = current_task['id']
        current_device = self.device_manager.get_current_device()
        
        if not current_device:
            return False
        
        # 检查是否为PC设备
        is_pc = self._is_pc_device()
        if is_pc:
            # PC设备使用简单的恢复策略
            log_callback("PC设备模式，执行简单恢复", "execution", "INFO")
            time.sleep(2)
            return True
        
        # 安卓设备使用设备状态管理器进行恢复
        if self.device_state_manager is None:
            if not self._init_device_state_manager(log_callback):
                log_callback("设备状态管理器初始化失败，无法执行恢复", "execution", "ERROR")
                return False
        
        try:
            log_callback("开始设备状态恢复", "execution", "INFO")
            ready = self.device_state_manager.ensure_device_ready(current_device, task_id)
            if ready:
                log_callback("设备状态恢复成功", "execution", "INFO")
                return True
            else:
                log_callback("设备状态恢复失败", "execution", "ERROR")
                return False
        except Exception as e:
            log_callback(f"设备状态恢复异常: {e}", "execution", "ERROR")
            return False