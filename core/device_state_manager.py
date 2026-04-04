import time
import logging
import os
from typing import Dict, Any, Optional, Tuple, List
from .logger import get_logger, LogCategory, LogLevel

class DeviceStateManager:

    def __init__(self, screen_capture, touch_executor, communicator, auth_manager):
        self.screen_capture = screen_capture
        self.touch_executor = touch_executor
        self.communicator = communicator
        self.auth_manager = auth_manager
        self.logger = get_logger()
        self.state_templates = {'game_main': ['Resell/inGame1.png', 'Resell/inGame2.png'], 'friend_list': ['VisitFriends/OnFriendList.png'], 'login_confirm': ['SceneManager/LoginConfirm.png'], 'terminal': ['SceneManager/Terminal.png'], 'home_screen': ['SceneManager/HomeScreen.png'], 'error_dialog': ['SceneManager/ErrorDialog.png'], 'loading_screen': ['SceneManager/LoadingIcon.png']}
        self.recovery_strategies = {'unknown': self._recover_from_unknown_state, 'error_dialog': self._recover_from_error_dialog, 'loading_screen': self._recover_from_loading_screen, 'login_confirm': self._recover_from_login_confirm}

    def detect_current_state(self, device_serial: str) -> str:
        self.logger.debug(LogCategory.DEVICE, '设备状态检测：跳过模板匹配，默认返回game_main')
        return 'game_main'

    def _detect_state_with_templates(self, screen_data: str, device_serial: str) -> str:
        try:
            from PIL import Image
            import io
            import cv2
            import numpy as np
            import base64
            png_data = base64.b64decode(screen_data)
            image_stream = io.BytesIO(png_data)
            pil_image = Image.open(image_stream)
            opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            best_match = 'unknown'
            best_score = 0.0
            for state_name, template_paths in self.state_templates.items():
                for template_path in template_paths:
                    try:
                        template_full_path = f'server/server/data/reference_images/{template_path}'
                        if not os.path.exists(template_full_path):
                            continue
                        template = cv2.imread(template_full_path, cv2.IMREAD_COLOR)
                        if template is None:
                            continue
                        result = cv2.matchTemplate(opencv_image, template, cv2.TM_CCOEFF_NORMED)
                        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                        if max_val > best_score and max_val > 0.7:
                            best_score = max_val
                            best_match = state_name
                    except Exception as template_e:
                        self.logger.debug(LogCategory.DEVICE, f'模板匹配异常: {template_e}')
                        continue
            self.logger.debug(LogCategory.DEVICE, f'本地模板匹配结果: {best_match} (置信度: {best_score:.2f})')
            return best_match
        except Exception as e:
            self.logger.exception(LogCategory.DEVICE, f'本地状态检测异常: {e}')
            return 'unknown'

    def recover_to_safe_state(self, device_serial: str, target_state: str='game_main') -> bool:
        current_state = self.detect_current_state(device_serial)
        self.logger.info(LogCategory.DEVICE, f'当前设备状态: {current_state}, 目标状态: {target_state}')
        if current_state == target_state:
            self.logger.info(LogCategory.DEVICE, '设备已在目标状态，无需恢复')
            return True
        max_attempts = 3
        for attempt in range(max_attempts):
            self.logger.info(LogCategory.DEVICE, f'开始第 {attempt + 1} 次状态恢复尝试')
            if self._execute_recovery_strategy(device_serial, current_state, target_state):
                time.sleep(2)
                new_state = self.detect_current_state(device_serial)
                if new_state == target_state:
                    self.logger.info(LogCategory.DEVICE, f'状态恢复成功: {current_state} -> {target_state}')
                    return True
                else:
                    self.logger.warning(LogCategory.DEVICE, f'状态恢复后验证失败: 期望 {target_state}, 实际 {new_state}')
                    current_state = new_state
            else:
                self.logger.warning(LogCategory.DEVICE, f'状态恢复策略执行失败: {current_state}')
            time.sleep(1)
        self.logger.error(LogCategory.DEVICE, f'状态恢复失败，已尝试 {max_attempts} 次')
        return False

    def _execute_recovery_strategy(self, device_serial: str, current_state: str, target_state: str) -> bool:
        try:
            strategy = self.recovery_strategies.get(current_state, self._recover_from_unknown_state)
            return strategy(device_serial, target_state)
        except Exception as e:
            self.logger.exception(LogCategory.DEVICE, f'恢复策略执行异常: {e}')
            return False

    def _recover_from_unknown_state(self, device_serial: str, target_state: str) -> bool:
        self.logger.info(LogCategory.DEVICE, '执行未知状态恢复策略')
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
        self.logger.info(LogCategory.DEVICE, '执行错误对话框恢复策略')
        if self._click_position(device_serial, 0.8, 0.8):
            time.sleep(1)
            return True
        return self._press_key(device_serial, 'back')

    def _recover_from_loading_screen(self, device_serial: str, target_state: str) -> bool:
        self.logger.info(LogCategory.DEVICE, '执行加载界面恢复策略')
        time.sleep(3)
        return True

    def _recover_from_login_confirm(self, device_serial: str, target_state: str) -> bool:
        self.logger.info(LogCategory.DEVICE, '执行登录确认界面恢复策略')
        if self._click_position(device_serial, 0.75, 0.75):
            time.sleep(2)
            return True
        return False

    def _press_key(self, device_serial: str, key: str) -> bool:
        try:
            if self.touch_executor:
                return self.touch_executor.execute_tool_call(device_serial, 'press_key', {'key': key})
            return False
        except Exception as e:
            self.logger.exception(LogCategory.DEVICE, f'按键操作异常: {e}')
            return False

    def _click_position(self, device_serial: str, x_ratio: float, y_ratio: float) -> bool:
        try:
            if self.touch_executor:
                return self.touch_executor.execute_tool_call(device_serial, 'click', {'coordinates': [x_ratio, y_ratio]})
            return False
        except Exception as e:
            self.logger.exception(LogCategory.DEVICE, f'点击操作异常: {e}')
            return False

    def _click_center(self, device_serial: str) -> bool:
        return self._click_position(device_serial, 0.5, 0.5)

    def ensure_device_ready(self, device_serial: str, task_id: str) -> bool:
        self.logger.info(LogCategory.DEVICE, f'确保设备准备好执行任务: {task_id}')
        current_state = self.detect_current_state(device_serial)
        target_state = self._get_target_state_for_task(task_id)
        if current_state == target_state:
            self.logger.info(LogCategory.DEVICE, f'设备已处于目标状态: {target_state}')
            return True
        return self.recover_to_safe_state(device_serial, target_state)

    def _get_target_state_for_task(self, task_id: str) -> str:
        task_to_state = {'task_visit_friends': 'game_main', 'task_game_login': 'login_confirm', 'task_daily_rewards': 'game_main', 'task_delivery_jobs': 'game_main', 'task_seize_entrust': 'game_main', 'task_sell_product': 'game_main', 'task_crafting': 'game_main', 'task_credit_shopping': 'game_main', 'task_weapon_upgrade': 'game_main', 'task_environment_monitoring': 'game_main'}
        return task_to_state.get(task_id, 'game_main')