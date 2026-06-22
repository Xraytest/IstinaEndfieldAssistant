import time
import os
from typing import Dict, Any, Optional, Tuple, List
from core.foundation.logger import get_logger, LogCategory, LogLevel

class DeviceStateManager:

    def __init__(self, screen_capture, touch_executor, communicator, auth_manager):
        self.screen_capture = screen_capture
        self.touch_executor = touch_executor
        self.communicator = communicator
        self.auth_manager = auth_manager
        self.logger = get_logger()
        # 状态模板缓存，将从服务端获取
        self._state_templates_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._cache_timestamp: float = 0
        self._cache_ttl: float = 300  # 缓存有效期5分钟
        self.recovery_strategies = {'unknown': self._recover_from_unknown_state, 'error_dialog': self._recover_from_error_dialog, 'loading_screen': self._recover_from_loading_screen, 'login_confirm': self._recover_from_login_confirm}

    def detect_current_state(self, device_serial: str) -> str:
        """检测当前设备状态，使用模板匹配
        
        Args:
            device_serial: 设备序列号
            
        Returns:
            检测到的状态名称
        """
        try:
            # 获取屏幕截图
            screenshot_data = self.screen_capture.capture_screen(device_serial)
            if not screenshot_data:
                self.logger.warning(LogCategory.ADB, '无法获取屏幕截图，返回unknown状态')
                return 'unknown'
            
            # 使用模板匹配检测状态
            detected_state = self._detect_state_with_templates(screenshot_data, device_serial)
            self.logger.info(LogCategory.ADB, f'设备状态检测结果: {detected_state}')
            return detected_state
            
        except Exception as e:
            self.logger.exception(LogCategory.ADB, f'状态检测异常: {e}')
            return 'unknown'

    def _get_state_templates_from_server(self) -> Dict[str, List[Dict[str, Any]]]:
        """从服务端获取状态模板配置
        
        Returns:
            状态模板配置字典
        """
        try:
            if not self.communicator:
                self.logger.warning(LogCategory.ADB, '通信器未初始化，无法获取状态模板')
                return {}
            
            # 检查缓存是否有效
            current_time = time.time()
            if self._state_templates_cache and (current_time - self._cache_timestamp) < self._cache_ttl:
                self.logger.debug(LogCategory.ADB, '使用缓存的状态模板')
                return self._state_templates_cache
            
            # 从服务端获取状态模板
            response = self.communicator.send_request(
                "get_state_templates",
                {}
            )
            
            if response and response.get('status') == 'success':
                templates = response.get('templates', {})
                self._state_templates_cache = templates
                self._cache_timestamp = current_time
                self.logger.info(LogCategory.ADB, f'从服务端获取状态模板成功: {len(templates)}个状态')
                return templates
            else:
                error_msg = response.get('message', '未知错误') if response else '无响应'
                self.logger.warning(LogCategory.ADB, f'从服务端获取状态模板失败: {error_msg}')
                return self._state_templates_cache  # 返回缓存（即使可能过期）
                
        except Exception as e:
            self.logger.exception(LogCategory.ADB, f'获取状态模板异常: {e}')
            return self._state_templates_cache  # 返回缓存（即使可能过期）

    def _detect_state_with_templates(self, screen_data: str, device_serial: str) -> str:
        """使用模板匹配检测状态
        
        Args:
            screen_data: base64编码的屏幕截图
            device_serial: 设备序列号
            
        Returns:
            匹配到的状态名称
        """
        try:
            from PIL import Image
            import io
            import cv2
            import numpy as np
            import base64
            
            # 解码屏幕截图
            png_data = base64.b64decode(screen_data)
            image_stream = io.BytesIO(png_data)
            pil_image = Image.open(image_stream)
            opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # 从服务端获取状态模板
            state_templates = self._get_state_templates_from_server()
            
            # 如果没有获取到模板，尝试使用本地默认模板
            if not state_templates:
                self.logger.warning(LogCategory.ADB, '未获取到状态模板，使用默认配置')
                state_templates = self._get_default_state_templates()
            
            best_match = 'unknown'
            best_score = 0.0
            
            # 遍历所有状态模板进行匹配
            for state_name, template_configs in state_templates.items():
                for template_config in template_configs:
                    try:
                        # 支持两种格式：字符串路径或字典配置
                        if isinstance(template_config, str):
                            template_path = template_config
                            threshold = 0.7
                        elif isinstance(template_config, dict):
                            template_path = template_config.get('path', '')
                            threshold = template_config.get('threshold', 0.7)
                        else:
                            continue
                        
                        if not template_path:
                            continue
                        
                        # 从服务端获取模板图像数据
                        template_image = self._get_template_image_from_server(template_path)
                        if template_image is None:
                            continue
                        
                        # 执行模板匹配
                        result = cv2.matchTemplate(opencv_image, template_image, cv2.TM_CCOEFF_NORMED)
                        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                        
                        if max_val > best_score and max_val > threshold:
                            best_score = max_val
                            best_match = state_name
                            
                    except Exception as template_e:
                        self.logger.debug(LogCategory.ADB, f'模板匹配异常: {template_e}')
                        continue
            
            self.logger.debug(LogCategory.ADB, f'模板匹配结果: {best_match} (置信度: {best_score:.2f})')
            return best_match
            
        except Exception as e:
            self.logger.exception(LogCategory.ADB, f'状态检测异常: {e}')
            return 'unknown'

    def _get_template_image_from_server(self, template_path: str) -> Optional[Any]:
        """从服务端获取模板图像
        
        Args:
            template_path: 模板路径
            
        Returns:
            OpenCV图像对象或None
        """
        try:
            import cv2
            import numpy as np
            
            if not self.communicator:
                return None
            
            # 请求模板图像数据
            response = self.communicator.send_request(
                "get_template_image",
                {"template_path": template_path}
            )
            
            if response and response.get('status') == 'success':
                image_data = response.get('image_data')
                if image_data:
                    # 解码base64图像数据
                    import base64
                    img_bytes = base64.b64decode(image_data)
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    return img
            
            return None
            
        except Exception as e:
            self.logger.debug(LogCategory.ADB, f'获取模板图像失败: {template_path}, 错误: {e}')
            return None

    def _get_default_state_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取默认状态模板配置（本地回退）
        
        Returns:
            默认状态模板配置
        """
        return {
            'game_main': [
                {'path': 'Resell/inGame1.png', 'threshold': 0.7},
                {'path': 'Resell/inGame2.png', 'threshold': 0.7}
            ],
            'friend_list': [
                {'path': 'VisitFriends/OnFriendList.png', 'threshold': 0.7}
            ],
            'login_confirm': [
                {'path': 'SceneManager/LoginConfirm.png', 'threshold': 0.7}
            ],
            'terminal': [
                {'path': 'SceneManager/Terminal.png', 'threshold': 0.7}
            ],
            'home_screen': [
                {'path': 'SceneManager/HomeScreen.png', 'threshold': 0.7}
            ],
            'error_dialog': [
                {'path': 'SceneManager/ErrorDialog.png', 'threshold': 0.7}
            ],
            'loading_screen': [
                {'path': 'SceneManager/LoadingIcon.png', 'threshold': 0.7}
            ]
        }

    def clear_template_cache(self):
        """清除状态模板缓存"""
        self._state_templates_cache = {}
        self._cache_timestamp = 0
        self.logger.info(LogCategory.ADB, '状态模板缓存已清除')

    def recover_to_safe_state(self, device_serial: str, target_state: str='game_main') -> bool:
        current_state = self.detect_current_state(device_serial)
        self.logger.info(LogCategory.ADB, f'当前设备状态: {current_state}, 目标状态: {target_state}')
        if current_state == target_state:
            self.logger.info(LogCategory.ADB, '设备已在目标状态，无需恢复')
            return True
        max_attempts = 3
        for attempt in range(max_attempts):
            self.logger.info(LogCategory.ADB, f'开始第 {attempt + 1} 次状态恢复尝试')
            if self._execute_recovery_strategy(device_serial, current_state, target_state):
                time.sleep(2)
                new_state = self.detect_current_state(device_serial)
                if new_state == target_state:
                    self.logger.info(LogCategory.ADB, f'状态恢复成功: {current_state} -> {target_state}')
                    return True
                else:
                    self.logger.warning(LogCategory.ADB, f'状态恢复后验证失败: 期望 {target_state}, 实际 {new_state}')
                    current_state = new_state
            else:
                self.logger.warning(LogCategory.ADB, f'状态恢复策略执行失败: {current_state}')
            time.sleep(1)
        self.logger.error(LogCategory.ADB, f'状态恢复失败，已尝试 {max_attempts} 次')
        return False

    def _execute_recovery_strategy(self, device_serial: str, current_state: str, target_state: str) -> bool:
        try:
            strategy = self.recovery_strategies.get(current_state, self._recover_from_unknown_state)
            return strategy(device_serial, target_state)
        except Exception as e:
            self.logger.exception(LogCategory.ADB, f'恢复策略执行异常: {e}')
            return False

    def _recover_from_unknown_state(self, device_serial: str, target_state: str) -> bool:
        self.logger.info(LogCategory.ADB, '执行未知状态恢复策略')
        if self._press_key(device_serial, 'back'):
            time.sleep(1)
            return True
        if self._click_center(device_serial):
            time.sleep(1)
            return True
        for i in range(3):
            if self._press_key(device_serial, 'back'):
                time.sleep(0.5)
            else:
                break
        time.sleep(1)
        return True

    def _recover_from_error_dialog(self, device_serial: str, target_state: str) -> bool:
        self.logger.info(LogCategory.ADB, '执行错误对话框恢复策略')
        if self._click_position(device_serial, 0.8, 0.8):
            time.sleep(1)
            return True
        return self._press_key(device_serial, 'back')

    def _recover_from_loading_screen(self, device_serial: str, target_state: str) -> bool:
        self.logger.info(LogCategory.ADB, '执行加载界面恢复策略')
        time.sleep(3)
        return True

    def _recover_from_login_confirm(self, device_serial: str, target_state: str) -> bool:
        self.logger.info(LogCategory.ADB, '执行登录确认界面恢复策略')
        if self._click_position(device_serial, 0.75, 0.75):
            time.sleep(2)
            return True
        return False

    def _press_key(self, device_serial: str, key: str) -> bool:
        try:
            if self.touch_executor:
                return self.touch_executor.execute_tool_call('press_key', {'key': key})
            return False
        except Exception as e:
            self.logger.exception(LogCategory.ADB, f'按键操作异常: {e}')
            return False

    def _click_position(self, device_serial: str, x_ratio: float, y_ratio: float) -> bool:
        try:
            if self.touch_executor:
                # 将比例坐标转换为像素坐标
                res = self.touch_executor.get_resolution()
                if res != (0, 0):
                    x_px = int(x_ratio * res[0])
                    y_px = int(y_ratio * res[1])
                else:
                    x_px = int(x_ratio * 1920)
                    y_px = int(y_ratio * 1080)
                return self.touch_executor.execute_tool_call('click', {'x': x_px, 'y': y_px})
            return False
        except Exception as e:
            self.logger.exception(LogCategory.ADB, f'点击操作异常: {e}')
            return False

    def _click_center(self, device_serial: str) -> bool:
        return self._click_position(device_serial, 0.5, 0.5)

    def ensure_device_ready(self, device_serial: str, task_id: str) -> bool:
        self.logger.info(LogCategory.ADB, f'确保设备准备好执行任务: {task_id}')
        current_state = self.detect_current_state(device_serial)
        target_state = self._get_target_state_for_task(task_id)
        if current_state == target_state:
            self.logger.info(LogCategory.ADB, f'设备已处于目标状态: {target_state}')
            return True
        return self.recover_to_safe_state(device_serial, target_state)

    def _get_target_state_for_task(self, task_id: str) -> str:
        task_to_state = {'task_visit_friends': 'game_main', 'task_game_login': 'login_confirm', 'task_daily_rewards': 'game_main', 'task_delivery_jobs': 'game_main', 'task_seize_entrust': 'game_main', 'task_sell_product': 'game_main', 'task_crafting': 'game_main', 'task_credit_shopping': 'game_main', 'task_weapon_upgrade': 'game_main', 'task_environment_monitoring': 'game_main'}
        return task_to_state.get(task_id, 'game_main')