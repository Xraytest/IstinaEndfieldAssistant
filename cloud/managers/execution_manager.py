import threading
import time
import base64
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
import sys
import os

# 使用MaaFramework库的Win32控制器
try:
    from client.core.touch import MaaFwWin32Executor, MaaFwWin32Config
    from maa.define import MaaWin32ScreencapMethodEnum, MaaWin32InputMethodEnum
    PC_CONTROLLER_AVAILABLE = True
except ImportError:
    PC_CONTROLLER_AVAILABLE = False
    print('[警告] MaaFwWin32Executor导入失败，PC设备支持不可用')

try:
    from client.core.device_state_manager import DeviceStateManager
    DEVICE_STATE_MANAGER_AVAILABLE = True
except ImportError:
    DEVICE_STATE_MANAGER_AVAILABLE = False
    print('[警告] DeviceStateManager导入失败，设备状态管理不可用')

# 客户端预识别模块
try:
    from client.core.pre_recognition import (
        ClientPreRecognizer,
        PreRecognitionConfig,
        RecognitionResult,
        create_pre_recognition_config_from_task,
        get_pre_recognizer
    )
    PRE_RECOGNITION_AVAILABLE = True
except ImportError:
    PRE_RECOGNITION_AVAILABLE = False
    print('[警告] 客户端预识别模块导入失败，预识别功能不可用')

class ExecutionManager:

    def __init__(self, device_manager, screen_capture, touch_executor, task_queue_manager, communicator, auth_manager, get_device_type_callback=None):
        self.device_manager = device_manager
        self.screen_capture = screen_capture
        self.touch_executor = touch_executor
        self.task_queue_manager = task_queue_manager
        self.communicator = communicator
        self.auth_manager = auth_manager
        self.get_device_type_callback = get_device_type_callback
        self.pc_controller: Optional[MaaFwWin32Executor] = None
        self.pc_window_title: str = 'Endfield'
        self.device_state_manager: Optional[DeviceStateManager] = None
        self.running_operations = {}
        self.next_operation_id = 1
        self.running_operations_lock = threading.Lock()
        self.client_running = False
        self.client_thread = None
        self.executed_once_tasks = set()
        self.cli_mode = False
        self.cli_screenshot_callback: Optional[Callable[[], Optional[bytes]]] = None
        self.cli_current_task_name: str = ''
        self.cli_current_task_variables: Dict[str, Any] = {}
        self.cli_screenshot_data_list: List[Dict[str, Any]] = []
        self.cli_output_dir: Optional[str] = None
        # 客户端预识别器
        self.pre_recognizer: Optional[ClientPreRecognizer] = None
        self.pre_recognition_enabled: bool = False
        if PRE_RECOGNITION_AVAILABLE:
            self.pre_recognizer = get_pre_recognizer()
            self.pre_recognition_enabled = self.pre_recognizer.is_available()

    def _is_pc_device(self) -> bool:
        if self.get_device_type_callback:
            device_type = self.get_device_type_callback()
            return device_type == 'PC'
        return False

    def _get_pc_window_title(self) -> str:
        if self.device_manager and hasattr(self.device_manager, 'get_pc_window_title'):
            return self.device_manager.get_pc_window_title()
        return self.pc_window_title

    def _get_pc_control_scheme(self) -> str:
        if self.device_manager and hasattr(self.device_manager, 'get_pc_control_scheme'):
            return self.device_manager.get_pc_control_scheme()
        return 'Win32-Front'

    def _init_pc_controller(self, log_callback=None) -> bool:
        if not PC_CONTROLLER_AVAILABLE:
            if log_callback:
                log_callback('PC控制器不可用，请检查MaaFwWin32Executor模块', 'execution', 'ERROR')
            return False
        try:
            window_title = self._get_pc_window_title()
            control_scheme = self._get_pc_control_scheme()
            
            # 根据控制方案创建配置
            if control_scheme == 'Win32-Window':
                # 后台SendMessage模式
                config = MaaFwWin32Config(
                    screencap_method=MaaWin32ScreencapMethodEnum.GDI,
                    mouse_method=MaaWin32InputMethodEnum.SendMessage,
                    keyboard_method=MaaWin32InputMethodEnum.SendMessage
                )
            elif control_scheme == 'Win32-Express':
                # 后台PostMessage模式
                config = MaaFwWin32Config(
                    screencap_method=MaaWin32ScreencapMethodEnum.GDI,
                    mouse_method=MaaWin32InputMethodEnum.PostMessage,
                    keyboard_method=MaaWin32InputMethodEnum.PostMessage
                )
            elif control_scheme == 'Win32-Front':
                # 前台独占模式（默认）
                config = MaaFwWin32Config(
                    screencap_method=MaaWin32ScreencapMethodEnum.DXGI_DesktopDup,
                    mouse_method=MaaWin32InputMethodEnum.Seize,
                    keyboard_method=MaaWin32InputMethodEnum.Seize
                )
            else:
                # 默认使用前台独占模式
                config = MaaFwWin32Config(
                    screencap_method=MaaWin32ScreencapMethodEnum.DXGI_DesktopDup,
                    mouse_method=MaaWin32InputMethodEnum.Seize,
                    keyboard_method=MaaWin32InputMethodEnum.Seize
                )
            
            self.pc_controller = MaaFwWin32Executor(config)
            if log_callback:
                log_callback(f'PC控制器创建（MaaFramework）: {control_scheme}', 'execution', 'INFO')
            
            if self.pc_controller.connect(window_title=window_title):
                if log_callback:
                    log_callback(f'PC控制器连接成功（MaaFramework）: {window_title} ({control_scheme})', 'execution', 'INFO')
                return True
            else:
                if log_callback:
                    log_callback(f"PC控制器连接失败: 未找到窗口 '{window_title}'", 'execution', 'ERROR')
                return False
        except Exception as e:
            if log_callback:
                log_callback(f'PC控制器初始化异常: {e}', 'execution', 'ERROR')
            return False

    def _execute_pc_touch_action(self, action_type: str, params: dict, log_callback=None) -> bool:
        if not self.pc_controller:
            if log_callback:
                log_callback('PC控制器未初始化', 'execution', 'ERROR')
            return False
        try:
            width = getattr(self.pc_controller, '_width', 1920)
            height = getattr(self.pc_controller, '_height', 1080)
            if action_type == 'click':
                coords = params.get('coordinates', [0.5, 0.5])
                if isinstance(coords, list) and len(coords) >= 2:
                    rel_x, rel_y = (coords[0], coords[1])
                else:
                    rel_x, rel_y = (0.5, 0.5)
                abs_x = int(rel_x * width)
                abs_y = int(rel_y * height)
                if log_callback:
                    log_callback(f'[PC点击] 相对坐标: ({rel_x:.4f}, {rel_y:.4f}), 绝对坐标: ({abs_x}, {abs_y})', 'execution', 'INFO')
                success = self.pc_controller.click(abs_x, abs_y)
                if log_callback:
                    log_callback(f"[PC点击] 执行结果: {('成功' if success else '失败')}", 'execution', 'INFO')
                return success
            elif action_type == 'swipe':
                coords = params.get('coordinates', {})
                if isinstance(coords, dict):
                    start = coords.get('start', [0.3, 0.5])
                    end = coords.get('end', [0.7, 0.5])
                else:
                    start = params.get('coordinates', [0.3, 0.5])
                    end = params.get('end_coordinates', [0.7, 0.5])
                x1 = int(start[0] * width)
                y1 = int(start[1] * height)
                x2 = int(end[0] * width)
                y2 = int(end[1] * height)
                duration = params.get('duration', 300)
                if log_callback:
                    log_callback(f'[PC滑动] ({x1},{y1}) -> ({x2},{y2}), duration={duration}ms', 'execution', 'INFO')
                return self.pc_controller.swipe(x1, y1, x2, y2, duration)
            elif action_type == 'long_press':
                coords = params.get('coordinates', [0.5, 0.5])
                if isinstance(coords, list) and len(coords) >= 2:
                    rel_x, rel_y = (coords[0], coords[1])
                else:
                    rel_x, rel_y = (0.5, 0.5)
                abs_x = int(rel_x * width)
                abs_y = int(rel_y * height)
                duration = params.get('duration', 1000)
                if log_callback:
                    log_callback(f'[PC长按] ({abs_x},{abs_y}), duration={duration}ms', 'execution', 'INFO')
                return self.pc_controller.long_press(abs_x, abs_y, duration)
            elif action_type == 'key' or action_type == 'press_key':
                key_code = params.get('key_code', params.get('key', ''))
                if log_callback:
                    log_callback(f'[PC按键] {key_code}', 'execution', 'INFO')
                return self.pc_controller.press_key(str(key_code))
            elif action_type == 'system_button':
                button = params.get('button', 'back')
                key_map = {'back': 'ESC', 'home': 'HOME', 'menu': 'MENU'}
                key_code = key_map.get(button, button.upper())
                if log_callback:
                    log_callback(f'[PC系统按钮] {button} -> {key_code}', 'execution', 'INFO')
                return self.pc_controller.press_key(key_code)
            elif action_type == 'wait':
                duration = params.get('duration', 1.0)
                if log_callback:
                    log_callback(f'[PC等待] 等待 {duration} 秒', 'execution', 'INFO')
                time.sleep(duration)
                return True
            elif action_type == 'input_text':
                text = params.get('text', '')
                if log_callback:
                    log_callback(f'[PC文本输入] {text[:20]}...', 'execution', 'INFO')
                return self.pc_controller.input_text(text)
            elif action_type == 'terminate':
                if log_callback:
                    log_callback('[PC终止] 收到终止指令', 'execution', 'INFO')
                return True
            else:
                if log_callback:
                    log_callback(f'[PC] 未知动作类型: {action_type}', 'execution', 'WARNING')
                return True
        except Exception as e:
            if log_callback:
                log_callback(f'[PC触控执行异常] {e}', 'execution', 'ERROR')
            return False

    def start_execution(self, log_callback, update_ui_callback, preview_update_callback=None):
        if not self.auth_manager.get_login_status():
            return (False, '请先登录后再执行任务')
        if not self.device_manager.get_current_device():
            return (False, '请先连接设备')
        if self.task_queue_manager.is_queue_empty():
            return (False, '任务队列为空')
        if self.client_running:
            return (False, '执行已在进行中')
        self.client_running = True
        self.client_thread = threading.Thread(target=self.run_automation, args=(log_callback, update_ui_callback, preview_update_callback), daemon=True)
        self.client_thread.start()
        return (True, '执行已开始')

    def stop_execution(self):
        self.client_running = False

    def _start_operation(self, action_type: str, params: dict) -> int:
        with self.running_operations_lock:
            operation_id = self.next_operation_id
            self.next_operation_id += 1
            operation_info = {'id': operation_id, 'action_type': action_type, 'params': params.copy(), 'start_time': time.time(), 'status': 'running'}
            self.running_operations[operation_id] = operation_info
            return operation_id

    def _complete_operation(self, operation_id: int):
        with self.running_operations_lock:
            if operation_id in self.running_operations:
                self.running_operations[operation_id]['status'] = 'completed'
                self.running_operations[operation_id]['end_time'] = time.time()

    def get_running_operations(self) -> list:
        with self.running_operations_lock:
            return list(self.running_operations.values())

    def cancel_operation(self, operation_id: int) -> bool:
        with self.running_operations_lock:
            if operation_id in self.running_operations:
                self.running_operations[operation_id]['status'] = 'cancelled'
                self.running_operations[operation_id]['end_time'] = time.time()
                return True
            return False

    def update_operation_params(self, operation_id: int, new_params: dict) -> bool:
        with self.running_operations_lock:
            if operation_id in self.running_operations and self.running_operations[operation_id]['status'] == 'running':
                self.running_operations[operation_id]['params'].update(new_params)
                return True
            return False

    def query_running_operations(self) -> list:
        if not self.communicator:
            return []
        request_data = {'user_id': self.auth_manager.get_user_id(), 'session_id': self.auth_manager.get_session_id()}
        response = self.communicator.send_request('get_running_operations', request_data)
        if response and response.get('status') == 'success':
            return response.get('data', {}).get('running_operations', [])
        return []

    def cancel_remote_operation(self, operation_id: int) -> bool:
        if not self.communicator:
            return False
        request_data = {'user_id': self.auth_manager.get_user_id(), 'session_id': self.auth_manager.get_session_id(), 'operation_id': operation_id}
        response = self.communicator.send_request('cancel_operation', request_data)
        return response and response.get('status') == 'success'

    def update_remote_operation_params(self, operation_id: int, new_params: dict) -> bool:
        if not self.communicator:
            return False
        request_data = {'user_id': self.auth_manager.get_user_id(), 'session_id': self.auth_manager.get_session_id(), 'operation_id': operation_id, 'new_params': new_params}
        response = self.communicator.send_request('update_operation_params', request_data)
        return response and response.get('status') == 'success'

    def is_running(self):
        return self.client_running

    def run_automation(self, log_callback, update_ui_callback, preview_update_callback=None):
        try:
            log_callback('开始自动化执行...', 'execution', 'INFO')
            total_executions = self.task_queue_manager.get_execution_count()
            is_infinite_loop = self.task_queue_manager.is_infinite_loop()
            execution = 0
            self.executed_once_tasks.clear()
            while self.client_running and (is_infinite_loop or execution < total_executions):
                if not self.client_running:
                    break
                if is_infinite_loop:
                    log_callback(f'执行第 {execution + 1} 次（持续循环模式）', 'execution', 'INFO')
                else:
                    log_callback(f'执行第 {execution + 1}/{total_executions} 次', 'execution', 'INFO')
                self.task_queue_manager.reset_current_task_index()
                current_task_index = 0
                total_tasks = len(self.task_queue_manager.get_queue_info()['tasks'])
                if total_tasks == 0:
                    log_callback('任务队列为空，停止执行', 'execution', 'WARNING')
                    break
                while current_task_index < total_tasks and self.client_running:
                    current_task = self.task_queue_manager.get_current_task()
                    if not current_task:
                        log_callback(f'当前任务为空（索引: {current_task_index}），停止执行', 'execution', 'ERROR')
                        break
                    task_id = current_task['id']
                    if current_task.get('execute_once', False) and task_id in self.executed_once_tasks:
                        log_callback(f"跳过任务 '{current_task['name']}'（已执行一次）", 'execution', 'INFO')
                        if self.task_queue_manager.advance_to_next_task():
                            current_task_index += 1
                        else:
                            break
                        continue
                    update_ui_callback('current_task', f"当前任务: {current_task['name']}")
                    update_ui_callback('progress', f'进度: {current_task_index + 1}/{total_tasks}')
                    log_callback(f"执行任务: {current_task['name']}", 'execution', 'INFO')
                    if not self._ensure_device_ready_for_task(current_task, log_callback):
                        log_callback(f"设备状态准备失败，跳过任务: {current_task['name']}", 'execution', 'ERROR')
                        if self.task_queue_manager.advance_to_next_task():
                            current_task_index += 1
                        else:
                            break
                        continue
                    task_variables = {}
                    if 'custom_variables' in current_task:
                        task_variables.update(current_task['custom_variables'])
                    else:
                        task_variables.update(self.task_queue_manager.get_task_variables(task_id))
                    current_device = self.device_manager.get_current_device()
                    if self.screen_capture and current_device:
                        screen_data = self.screen_capture.capture_screen(current_device)
                        if not screen_data:
                            log_callback('屏幕捕获失败', 'execution', 'ERROR')
                            break
                        image_size = self.screen_capture.last_image_size
                        if preview_update_callback:
                            preview_update_callback(screen_data)
                    else:
                        log_callback('屏幕捕获模块未初始化或设备未连接', 'execution', 'ERROR')
                        break
                    
                    # 客户端预识别处理
                    pre_recognition_results = []
                    pre_recognition_context = None
                    if self.pre_recognition_enabled and self.pre_recognizer:
                        try:
                            # 从任务配置创建预识别配置
                            pre_rec_config = create_pre_recognition_config_from_task(current_task)
                            
                            # 执行预识别
                            _, pre_recognition_results = self.pre_recognizer.process_screenshot_base64(
                                screen_data, pre_rec_config
                            )
                            
                            # 生成VLM上下文
                            if pre_recognition_results:
                                pre_recognition_context = self.pre_recognizer.generate_vlm_context(pre_recognition_results)
                                found_count = sum(1 for r in pre_recognition_results if r.found)
                                log_callback(f'预识别完成: 发现 {found_count} 个元素', 'execution', 'INFO')
                        except Exception as e:
                            log_callback(f'预识别处理失败: {str(e)}', 'execution', 'WARNING')
                    
                    if self.screen_capture and current_device:
                        device_info = self.screen_capture.get_device_info(current_device)
                        if 'image_size' not in device_info or device_info['image_size'] is None:
                            device_info['image_size'] = image_size
                    else:
                        device_info = {'resolution': [1080, 1920], 'model': 'Unknown', 'image_size': image_size}
                    
                    # 构建请求数据，包含预识别结果
                    request_data = {
                        'user_id': self.auth_manager.get_user_id(),
                        'session_id': self.auth_manager.get_session_id(),
                        'device_image': screen_data if screen_data else '',
                        'current_task': task_id,
                        'task_variables': task_variables,
                        'device_info': device_info,
                        'pre_recognition': {
                            'enabled': self.pre_recognition_enabled,
                            'results': self.pre_recognizer.results_to_dict(pre_recognition_results) if self.pre_recognizer and pre_recognition_results else [],
                            'context': pre_recognition_context
                        }
                    }
                    if self.communicator:
                        response = self.communicator.send_request('process_image', request_data)
                    else:
                        log_callback('通信模块未初始化', 'execution', 'ERROR')
                        break
                    if not response:
                        log_callback('网络连接失败：无法连接到服务端（已尝试重连3次）', 'execution', 'ERROR')
                        break
                    if response.get('status') != 'success':
                        error_message = response.get('message', '未知错误')
                        error_type = response.get('error_type')
                        if response.get('status') == 'queued':
                            queue_id = response.get('queue_id')
                            log_callback(f'供应商限流，请求已自动加入队列 (ID: {queue_id})，等待后重试...', 'execution', 'WARNING')
                            time.sleep(3)
                            continue
                        if error_type == 'session_expired':
                            log_callback('检测到会话过期，尝试自动重新认证...', 'execution', 'WARNING')
                            reauth_success, reauth_message = self._handle_authentication_failure(log_callback)
                            if reauth_success:
                                log_callback('重新认证成功，继续执行任务', 'execution', 'INFO')
                                request_data['session_id'] = self.auth_manager.get_session_id()
                                continue
                            else:
                                log_callback(f'重新认证失败: {reauth_message}', 'execution', 'ERROR')
                                break
                        else:
                            log_callback(f'服务端处理失败: {error_message}', 'execution', 'ERROR')
                            break
                    touch_actions = response.get('data', {}).get('touch_actions', [])
                    if touch_actions:
                        is_pc = self._is_pc_device()
                        if is_pc and (not self.pc_controller):
                            if not self._init_pc_controller(log_callback):
                                log_callback('PC控制器初始化失败，无法执行触控动作', 'execution', 'ERROR')
                                break
                        for action in touch_actions:
                            action_type = action.get('action', '')
                            params = action.get('parameters', {})
                            if 'coordinates' in action:
                                params['coordinates'] = action['coordinates']
                            if 'end_coordinates' in action.get('parameters', {}):
                                params['end_coordinates'] = action['parameters']['end_coordinates']
                            operation_id = self._start_operation(action_type, params)
                            if is_pc:
                                success = self._execute_pc_touch_action(action_type, params, log_callback)
                            elif self.touch_executor and current_device:
                                success = self.touch_executor.execute_tool_call(current_device, action_type, params, image_size=tuple(image_size))
                            else:
                                log_callback('无可用触控执行器', 'execution', 'ERROR')
                                success = False
                            self._complete_operation(operation_id)
                            if not success:
                                if action_type in ('click', 'swipe', 'long_press', 'drag'):
                                    log_callback(f'触控执行失败: {action_type}', 'execution', 'ERROR')
                                else:
                                    log_callback(f'操作执行失败: {action_type}', 'execution', 'ERROR')
                                break
                    task_completed = response.get('data', {}).get('task_completed', False)
                    if task_completed:
                        log_callback(f"任务 '{current_task['name']}' 完成", 'execution', 'INFO')
                        if current_task.get('execute_once', False):
                            self.executed_once_tasks.add(task_id)
                        if self.task_queue_manager.advance_to_next_task():
                            current_task_index += 1
                        else:
                            break
                    elif not self._check_and_handle_execution_anomaly(response, current_task, log_callback):
                        log_callback(f"任务执行异常无法恢复，跳过任务: {current_task['name']}", 'execution', 'ERROR')
                        if self.task_queue_manager.advance_to_next_task():
                            current_task_index += 1
                        else:
                            break
                    else:
                        time.sleep(1)
                if not self.client_running:
                    break
                execution += 1
            log_callback('自动化执行结束', 'execution', 'INFO')
            if hasattr(update_ui_callback, '__call__'):
                update_ui_callback('stop_execution', None)
            elif hasattr(update_ui_callback, 'stop_execution_ui'):
                update_ui_callback.stop_execution_ui()
        except Exception as e:
            log_callback(f'自动化执行异常: {str(e)}', 'execution', 'ERROR')
            import traceback
            log_callback(f'异常详情: {traceback.format_exc()}', 'execution', 'ERROR')
        finally:
            self.client_running = False

    def _handle_authentication_failure(self, log_callback):
        try:
            success, message = self.auth_manager.ensure_valid_session()
            if success:
                return (True, '重新认证成功')
            else:
                user_info = self.auth_manager.get_user_info()
                if not user_info:
                    return (False, '用户不存在或API密钥无效')
                if user_info.get('is_banned', False):
                    ban_reason = user_info.get('ban_reason', '未知原因')
                    ban_until = user_info.get('ban_until', 0)
                    if ban_until > 0:
                        return (False, f"账户被封禁至 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ban_until))}，原因: {ban_reason}")
                    else:
                        return (False, f'账户被永久封禁，原因: {ban_reason}')
                return (False, message)
        except Exception as e:
            error_msg = f'重新认证过程中发生异常: {str(e)}'
            log_callback(error_msg, 'execution', 'ERROR')
            return (False, error_msg)

    def _init_device_state_manager(self, log_callback=None) -> bool:
        if not DEVICE_STATE_MANAGER_AVAILABLE:
            if log_callback:
                log_callback('设备状态管理器不可用', 'execution', 'WARNING')
            return False
        try:
            self.device_state_manager = DeviceStateManager(self.screen_capture, self.touch_executor, self.communicator, self.auth_manager)
            if log_callback:
                log_callback('设备状态管理器初始化成功', 'execution', 'INFO')
            return True
        except Exception as e:
            if log_callback:
                log_callback(f'设备状态管理器初始化异常: {e}', 'execution', 'ERROR')
            return False

    def get_client_running_status(self):
        return self.client_running

    def set_cli_mode(self, enabled: bool, screenshot_callback: Callable[[], Optional[bytes]]=None, output_dir: str=None):
        self.cli_mode = enabled
        self.cli_screenshot_callback = screenshot_callback
        self.cli_output_dir = output_dir
        self.cli_screenshot_data_list = []

    def _ensure_device_ready_for_task(self, current_task: Dict[str, Any], log_callback) -> bool:
        task_id = current_task['id']
        current_device = self.device_manager.get_current_device()
        if not current_device:
            log_callback('设备未连接，无法准备任务状态', 'execution', 'ERROR')
            return False
        is_pc = self._is_pc_device()
        if is_pc:
            log_callback('PC设备模式，跳过设备状态验证', 'execution', 'INFO')
            return True
        if self.device_state_manager is None:
            if not self._init_device_state_manager(log_callback):
                log_callback('设备状态管理器初始化失败，跳过状态验证', 'execution', 'WARNING')
                return True
        try:
            log_callback(f'开始设备状态验证，任务: {task_id}', 'execution', 'INFO')
            ready = self.device_state_manager.ensure_device_ready(current_device, task_id)
            if ready:
                log_callback('设备状态验证成功', 'execution', 'INFO')
            else:
                log_callback('设备状态验证失败', 'execution', 'ERROR')
            return ready
        except Exception as e:
            log_callback(f'设备状态验证异常: {e}', 'execution', 'ERROR')
            return False

    def _cli_log(self, message: str, log_callback: Callable=None):
        if log_callback:
            log_callback(message, 'execution', 'INFO')
        print(f'[CLI] {message}')

    def _capture_cli_screenshot(self) -> Optional[bytes]:
        if self.cli_screenshot_callback:
            return self.cli_screenshot_callback()
        return None

    def _record_cli_screenshot(self, screenshot_data: bytes, task_name: str, task_variables: Dict):
        if not self.cli_output_dir or not screenshot_data:
            return
        import json
        import re
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        safe_name = re.sub('[<>:"/\\\\|?*]', '_', task_name)[:50]
        filename = f'{timestamp}_{safe_name}.png'
        filepath = os.path.join(self.cli_output_dir, filename)
        if isinstance(screenshot_data, str):
            import base64
            screenshot_bytes = base64.b64decode(screenshot_data)
        else:
            screenshot_bytes = screenshot_data
        with open(filepath, 'wb') as f:
            f.write(screenshot_bytes)
        self.cli_screenshot_data_list.append({'timestamp': timestamp, 'datetime': datetime.now().isoformat(), 'task_name': task_name, 'task_variables': task_variables.copy() if task_variables else {}, 'screenshot_file': filename})
        self._update_cli_description_json()

    def _update_cli_description_json(self):
        if not self.cli_output_dir:
            return
        import json
        description = {'run_start_time': getattr(self, 'cli_run_start_time', ''), 'control_scheme': getattr(self, 'cli_control_scheme', 'Win32-Window'), 'window_title': getattr(self, 'cli_window_title', 'Endfield'), 'screenshot_interval': getattr(self, 'cli_screenshot_interval', 1.0), 'screenshots': self.cli_screenshot_data_list}
        filepath = os.path.join(self.cli_output_dir, 'task_description.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(description, f, ensure_ascii=False, indent=2)

    def run_cli_automation(self, log_callback: Callable=None, execution_count: int=1, control_scheme: str='Win32-Window', window_title: str='Endfield') -> bool:
        self.cli_control_scheme = control_scheme
        self.cli_window_title = window_title
        self.cli_run_start_time = datetime.now().isoformat()
        try:
            self._cli_log('开始CLI自动化执行...', log_callback)
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
                    self._cli_log(f'执行第 {execution + 1} 次（持续循环模式）', log_callback)
                else:
                    self._cli_log(f'执行第 {execution + 1}/{total_executions} 次', log_callback)
                self.task_queue_manager.reset_current_task_index()
                current_task_index = 0
                total_tasks = len(self.task_queue_manager.get_queue_info()['tasks'])
                if total_tasks == 0:
                    self._cli_log('任务队列为空，停止执行', log_callback)
                    break
                while current_task_index < total_tasks and self.client_running:
                    current_task = self.task_queue_manager.get_current_task()
                    if not current_task:
                        self._cli_log(f'当前任务为空（索引: {current_task_index}），停止执行', log_callback)
                        break
                    task_id = current_task['id']
                    if current_task.get('execute_once', False) and task_id in self.executed_once_tasks:
                        self._cli_log(f"跳过任务 '{current_task['name']}'（已执行一次）", log_callback)
                        if self.task_queue_manager.advance_to_next_task():
                            current_task_index += 1
                        else:
                            break
                        continue
                    self._cli_log(f"执行任务: {current_task['name']}", log_callback)
                    self.cli_current_task_name = current_task['name']
                    self.cli_current_task_variables = current_task.get('custom_variables', {})
                    task_variables = {}
                    if 'custom_variables' in current_task:
                        task_variables.update(current_task['custom_variables'])
                    else:
                        task_variables.update(self.task_queue_manager.get_task_variables(task_id))
                    task_completed = self._execute_cli_task_steps(current_task, task_variables, log_callback)
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
            self._cli_log('CLI自动化执行结束', log_callback)
            return True
        except Exception as e:
            error_msg = f'CLI自动化执行异常: {str(e)}'
            self._cli_log(error_msg, log_callback)
            import traceback
            self._cli_log(f'异常详情: {traceback.format_exc()}', log_callback)
            return False
        finally:
            self.client_running = False

    def _execute_cli_task_steps(self, task: Dict, task_variables: Dict, log_callback: Callable) -> bool:
        task_id = task['id']
        max_steps = 100
        step_count = 0
        while step_count < max_steps and self.client_running:
            screenshot_data = self._capture_cli_screenshot()
            if not screenshot_data:
                self._cli_log('屏幕捕获失败', log_callback)
                return False
            self._record_cli_screenshot(screenshot_data, task['name'], task_variables)
            is_pc = self._is_pc_device()
            if is_pc and self.pc_controller:
                try:
                    width = getattr(self.pc_controller, '_width', 1920)
                    height = getattr(self.pc_controller, '_height', 1080)
                    image_size = [width, height]
                except:
                    image_size = [1920, 1080]
            else:
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
            if isinstance(screenshot_data, str):
                screenshot_b64 = screenshot_data
            else:
                screenshot_b64 = base64.b64encode(screenshot_data).decode('utf-8')
            request_data = {'user_id': self.auth_manager.get_user_id(), 'session_id': self.auth_manager.get_session_id(), 'device_image': screenshot_b64, 'current_task': task_id, 'task_variables': task_variables, 'device_info': {'resolution': image_size, 'model': 'PC', 'image_size': image_size}}
            response = self.communicator.send_request('process_image', request_data)
            if not response:
                self._cli_log('网络连接失败', log_callback)
                time.sleep(1)
                continue
            if response.get('status') == 'queued':
                self._cli_log('供应商限流，等待重试...', log_callback)
                time.sleep(3)
                continue
            if response.get('status') != 'success':
                error_msg = response.get('message', '未知错误')
                self._cli_log(f'服务端处理失败: {error_msg}', log_callback)
                return False
            touch_actions = response.get('data', {}).get('touch_actions', [])
            if touch_actions:
                if is_pc:
                    if not self.pc_controller:
                        if not self._init_pc_controller(log_callback):
                            self._cli_log('PC控制器初始化失败', log_callback)
                            return False
                elif not self.touch_executor:
                    self._cli_log('触控执行器未初始化', log_callback)
                    return False
                for action in touch_actions:
                    if not self.client_running:
                        return False
                    action_type = action.get('action', '')
                    params = action.get('parameters', {})
                    if 'coordinates' in action:
                        params['coordinates'] = action['coordinates']
                    if is_pc:
                        success = self._execute_pc_touch_action(action_type, params, log_callback)
                    else:
                        current_device = self.device_manager.get_current_device()
                        success = self.touch_executor.execute_tool_call(current_device, action_type, params, image_size=tuple(image_size))
                        if success:
                            self._cli_log(f'触控执行成功: {action_type}', log_callback)
                    if not success:
                        self._cli_log(f'触控执行失败: {action_type}', log_callback)
                        return False
            task_completed = response.get('data', {}).get('task_completed', False)
            if task_completed:
                return True
            step_count += 1
            time.sleep(1)
        return False

    def get_cli_screenshot_data(self) -> List[Dict[str, Any]]:
        return self.cli_screenshot_data_list

    def _check_and_handle_execution_anomaly(self, response: Dict[str, Any], current_task: Dict[str, Any], log_callback) -> bool:
        task_id = current_task['id']
        current_device = self.device_manager.get_current_device()
        if not current_device:
            return False
        if response.get('status') == 'error':
            error_type = response.get('error_type', 'unknown')
            error_message = response.get('message', '未知错误')
            log_callback(f'检测到任务执行错误: {error_type} - {error_message}', 'execution', 'ERROR')
            if self._attempt_device_recovery(current_task, log_callback):
                log_callback('设备状态恢复成功，继续任务执行', 'execution', 'INFO')
                return True
            else:
                log_callback('设备状态恢复失败', 'execution', 'ERROR')
                return False
        vlm_data = response.get('data', {})
        if vlm_data.get('anomaly_detected', False):
            anomaly_type = vlm_data.get('anomaly_type', 'unknown')
            log_callback(f'VLM检测到异常: {anomaly_type}', 'execution', 'WARNING')
            if anomaly_type in ['界面错误', '逻辑错误', '资源不足']:
                if self._attempt_device_recovery(current_task, log_callback):
                    log_callback('异常恢复成功，继续任务执行', 'execution', 'INFO')
                    return True
                else:
                    log_callback('异常恢复失败', 'execution', 'ERROR')
                    return False
            elif anomaly_type == 'unexpected_action':
                log_callback('检测到意外动作，等待界面稳定', 'execution', 'INFO')
                time.sleep(3)
                return True
            elif self._attempt_device_recovery(current_task, log_callback):
                return True
            else:
                return False
        touch_actions = vlm_data.get('touch_actions', [])
        if not touch_actions:
            log_callback('VLM未返回有效触控动作，可能遇到异常', 'execution', 'WARNING')
            if self._attempt_device_recovery(current_task, log_callback):
                return True
            else:
                return False
        thinking = vlm_data.get('thinking', '')
        error_keywords = ['错误', '异常', '失败', '无法', '找不到', 'error', 'fail', 'cannot', '不能']
        for keyword in error_keywords:
            if keyword in thinking.lower():
                log_callback(f'VLM思考内容包含错误关键词: {keyword}', 'execution', 'WARNING')
                if self._attempt_device_recovery(current_task, log_callback):
                    return True
                else:
                    return False
        return True

    def _attempt_device_recovery(self, current_task: Dict[str, Any], log_callback) -> bool:
        task_id = current_task['id']
        current_device = self.device_manager.get_current_device()
        if not current_device:
            return False
        is_pc = self._is_pc_device()
        if is_pc:
            log_callback('PC设备模式，执行简单恢复', 'execution', 'INFO')
            time.sleep(2)
            return True
        if self.device_state_manager is None:
            if not self._init_device_state_manager(log_callback):
                log_callback('设备状态管理器初始化失败，无法执行恢复', 'execution', 'ERROR')
                return False
        try:
            log_callback('开始设备状态恢复', 'execution', 'INFO')
            ready = self.device_state_manager.ensure_device_ready(current_device, task_id)
            if ready:
                log_callback('设备状态恢复成功', 'execution', 'INFO')
                return True
            else:
                log_callback('设备状态恢复失败', 'execution', 'ERROR')
                return False
        except Exception as e:
            log_callback(f'设备状态恢复异常: {e}', 'execution', 'ERROR')
            return False