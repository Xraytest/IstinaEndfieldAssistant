"""用户认证管理业务逻辑组件"""
import os
import json

from core.foundation.utils.paths import get_cache_dir, get_project_root


class AuthManager:
    """用户认证管理业务逻辑类"""

    def __init__(self, communicator, config):
        self.communicator = communicator
        self.config = config
        self.is_logged_in = False
        self.user_id = ""
        self.session_id = ""

    def register_user(self, username):
        """注册用户"""
        try:
            if self.communicator is None:
                return False, "通信器未初始化"

            response = self.communicator.send_request("register", {"user_id": username})
            if response and response.get('status') == 'success':
                api_key = response.get('key')
                if api_key:
                    arkpass_data = {
                        "user_id": username,
                        "api_key": api_key,
                        "server_host": self.config['server']['host'],
                        "server_port": self.config['server']['port']
                    }

                    cache_dir = get_cache_dir()
                    if not os.path.exists(cache_dir):
                        os.makedirs(cache_dir)

                    arkpass_path = os.path.join(cache_dir, f"{username}.arkpass")
                    with open(arkpass_path, 'w', encoding='utf-8') as f:
                        json.dump(arkpass_data, f, indent=2)

                    self.is_logged_in = True
                    self.user_id = username

                    if self.communicator:
                        self.communicator.set_logged_in(True)

                    return True, None
                else:
                    return False, "服务器响应中缺少API密钥"
            else:
                error_msg = response.get('message', '未知错误')
                return False, error_msg

        except Exception as e:
            return False, str(e)

    def login_with_arkpass(self, file_path):
        """使用arkpass文件登录"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if content.startswith('{') and content.endswith('}'):
                arkpass_data = json.loads(content)
                user_id = arkpass_data.get('user_id')
                api_key = arkpass_data.get('api_key')
            else:
                parts = content.split(':', 1)
                if len(parts) == 2:
                    user_id = parts[0].strip()
                    api_key = parts[1].strip()
                    arkpass_data = {
                        'user_id': user_id,
                        'api_key': api_key
                    }
                else:
                    return False, "ArkPass文件格式无效"

            if not user_id or not api_key:
                return False, "ArkPass文件缺少必要信息"

            response = self.communicator.send_request("login", {
                "user_id": user_id,
                "key": api_key
            })

            if response is None:
                return False, "网络连接异常，请检查网络连接"

            if response.get('status') == 'success':
                session_id = response.get('session_id')
                if session_id:
                    cache_dir = get_cache_dir()
                    if not os.path.exists(cache_dir):
                        os.makedirs(cache_dir)

                    filename = os.path.basename(file_path)
                    cache_path = os.path.join(cache_dir, filename)
                    with open(cache_path, 'w', encoding='utf-8') as f:
                        json.dump(arkpass_data, f, indent=2)

                    self.is_logged_in = True
                    self.user_id = user_id
                    self.session_id = session_id

                    if self.communicator:
                        self.communicator.set_logged_in(True)

                    return True, None
            else:
                error_type = response.get('error_type', 'unknown')
                error_message = response.get('message', '未知错误')
                return False, error_message

        except Exception as e:
            return False, f"登录过程发生异常: {str(e)}"

        return False, "未知错误"

    def auto_login_with_arkpass(self, arkpass_path):
        """自动使用arkpass文件登录"""
        result = self.login_with_arkpass(arkpass_path)
        if isinstance(result, tuple) and len(result) >= 2:
            success, error_msg = result[:2]
            if not success:
                try:
                    os.remove(arkpass_path)
                    print(f"已删除无效的ArkPass文件: {arkpass_path}")
                except Exception as e:
                    print(f"删除ArkPass文件失败: {e}")
            return (success, error_msg)
        return (result, None) if result else (False, "自动登录失败")

    def check_login_status(self):
        """检查登录状态"""
        possible_paths = []

        cache_dir = get_cache_dir()
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        else:
            cache_files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith('.arkpass')]
            possible_paths.extend(cache_files)

        project_root = get_project_root()
        if os.path.exists(project_root):
            root_files = [os.path.join(project_root, f) for f in os.listdir(project_root) if f.endswith('.arkpass')]
            possible_paths.extend(root_files)

        current_files = [f for f in os.listdir('.') if f.endswith('.arkpass')]
        possible_paths.extend(current_files)

        unique_paths = []
        seen = set()
        for path in possible_paths:
            if path not in seen and os.path.exists(path):
                unique_paths.append(path)
                seen.add(path)

        network_error = None
        for arkpass_path in unique_paths:
            result = self.auto_login_with_arkpass(arkpass_path)
            if isinstance(result, tuple) and len(result) >= 2:
                success, error_msg = result[:2]
                if success:
                    return True, None
                if error_msg and ("网络连接异常" in error_msg or "网络错误" in error_msg):
                    network_error = error_msg
            elif result:
                return True, None

        if network_error:
            return False, network_error

        if not unique_paths:
            return False, None

        return self.is_logged_in, None

    def get_login_status(self):
        """获取登录状态"""
        return self.is_logged_in

    def get_user_id(self):
        """获取用户ID"""
        return self.user_id

    def get_session_id(self):
        """获取会话ID"""
        return self.session_id

    def get_user_info(self):
        """获取用户信息"""
        if not self.is_logged_in:
            return None

        try:
            response = self.communicator.send_request("get_user_info", {
                "user_id": self.user_id,
                "session_id": self.session_id
            })

            if response and response.get('status') == 'success':
                return response.get('user_info')
            else:
                return None
        except Exception as e:
            print(f"获取用户信息失败: {e}")
            return None

    def is_session_valid(self):
        """检查会话是否有效"""
        if not self.is_logged_in or not self.session_id:
            return False

        try:
            response = self.communicator.send_request("get_user_info", {
                "user_id": self.user_id,
                "session_id": self.session_id
            })

            if response and response.get('status') == 'success':
                return True
            else:
                return False

        except Exception as e:
            print(f"检查会话有效性失败: {e}")
            return False

    def ensure_valid_session(self):
        """确保会话有效"""
        if not self.is_logged_in:
            return False, "未登录"

        if self.is_session_valid():
            return True, "会话有效"

        print("会话已过期，尝试重新登录...")

        possible_paths = []

        cache_dir = get_cache_dir()
        if os.path.exists(cache_dir):
            cache_files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith('.arkpass')]
            possible_paths.extend(cache_files)

        project_root = get_project_root()
        if os.path.exists(project_root):
            root_files = [os.path.join(project_root, f) for f in os.listdir(project_root) if f.endswith('.arkpass')]
            possible_paths.extend(root_files)

        current_files = [f for f in os.listdir('.') if f.endswith('.arkpass')]
        possible_paths.extend(current_files)

        unique_paths = []
        seen = set()
        for path in possible_paths:
            if path not in seen and os.path.exists(path):
                unique_paths.append(path)
                seen.add(path)

        for arkpass_path in unique_paths:
            result = self.login_with_arkpass(arkpass_path)
            if isinstance(result, tuple) and len(result) >= 2:
                success, error_msg = result[:2]
                if success:
                    if self.communicator:
                        self.communicator.set_logged_in(True)
                    return True, "重新登录成功"
                else:
                    try:
                        os.remove(arkpass_path)
                        print(f"已删除无效的ArkPass文件: {arkpass_path}")
                    except Exception as e:
                        print(f"删除ArkPass文件失败: {e}")
            elif result:
                if self.communicator:
                    self.communicator.set_logged_in(True)
                return True, "重新登录成功"

        return False, "重新登录失败"