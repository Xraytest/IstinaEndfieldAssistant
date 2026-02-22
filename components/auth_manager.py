"""用户认证管理业务逻辑组件"""
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

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
                
            # 调用服务端注册接口
            response = self.communicator.send_request("register", {"user_id": username})
            if response and response.get('status') == 'success':
                api_key = response.get('key')
                if api_key:
                    # 保存arkpass文件
                    arkpass_data = {
                        "user_id": username,
                        "api_key": api_key,
                        "server_host": self.config['server']['host'],
                        "server_port": self.config['server']['port']
                    }
                    
                    cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
                    if not os.path.exists(cache_dir):
                        os.makedirs(cache_dir)
                        
                    arkpass_path = os.path.join(cache_dir, f"{username}.arkpass")
                    with open(arkpass_path, 'w', encoding='utf-8') as f:
                        json.dump(arkpass_data, f, indent=2)
                        
                    # 更新状态
                    self.is_logged_in = True
                    self.user_id = username
                    
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
            
            # 尝试解析JSON格式
            if content.startswith('{') and content.endswith('}'):
                arkpass_data = json.loads(content)
                user_id = arkpass_data.get('user_id')
                api_key = arkpass_data.get('api_key')
                is_json_format = True
            else:
                # 尝试解析旧格式 username:api_key
                parts = content.split(':', 1)
                if len(parts) == 2:
                    user_id = parts[0].strip()
                    api_key = parts[1].strip()
                    # 为legacy格式创建JSON数据用于缓存
                    arkpass_data = {
                        'user_id': user_id,
                        'api_key': api_key
                    }
                else:
                    return False, "ArkPass文件格式无效"
            
            if not user_id or not api_key:
                return False, "ArkPass文件缺少必要信息"
                
            # 调用服务端登录接口
            response = self.communicator.send_request("login", {
                "user_id": user_id,
                "key": api_key
            })
            
            if response is None:
                return False, "网络连接异常，请检查网络连接"
                
            if response.get('status') == 'success':
                session_id = response.get('session_id')
                if session_id:
                    # 缓存arkpass文件到本地
                    cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
                    if not os.path.exists(cache_dir):
                        os.makedirs(cache_dir)
                        
                    filename = os.path.basename(file_path)
                    cache_path = os.path.join(cache_dir, filename)
                    with open(cache_path, 'w', encoding='utf-8') as f:
                        json.dump(arkpass_data, f, indent=2)
                        
                    # 更新状态
                    self.is_logged_in = True
                    self.user_id = user_id
                    self.session_id = session_id
                    
                    return True, None
                    
            else:
                # 处理不同的错误类型
                error_type = response.get('error_type', 'unknown')
                error_message = response.get('message', '未知错误')
                
                if error_type in ['user_not_found', 'invalid_api_key']:
                    # 用户不存在或密钥错误，应该删除缓存的arkpass文件
                    return False, error_message, error_type
                else:
                    # 其他错误类型（如封禁等）
                    return False, error_message, error_type
                    
        except Exception as e:
            return False, f"登录过程发生异常: {str(e)}"
            
        return False, "未知错误"
        
    def auto_login_with_arkpass(self, arkpass_path):
        """自动使用arkpass文件登录"""
        result = self.login_with_arkpass(arkpass_path)
        if isinstance(result, tuple):
            success, error_msg, *error_type = result
            if not success and len(error_type) > 0:
                error_type_val = error_type[0]
                # 如果是用户不存在或密钥错误，删除缓存的arkpass文件
                if error_type_val in ['user_not_found', 'invalid_api_key']:
                    try:
                        os.remove(arkpass_path)
                        print(f"已删除无效的ArkPass文件: {arkpass_path}")
                    except Exception as e:
                        print(f"删除ArkPass文件失败: {e}")
            return success, error_msg
        return result
        
    def check_login_status(self):
        """检查登录状态 - 只返回布尔值，不处理UI"""
        # 检查多个可能的arkpass文件位置
        possible_paths = []
        
        # 1. 客户端缓存目录
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        else:
            cache_files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith('.arkpass')]
            possible_paths.extend(cache_files)
        
        # 2. 项目根目录（相对于client目录的上一级）
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        root_files = [os.path.join(project_root, f) for f in os.listdir(project_root) if f.endswith('.arkpass')]
        possible_paths.extend(root_files)
        
        # 3. 当前工作目录
        current_files = [f for f in os.listdir('.') if f.endswith('.arkpass')]
        possible_paths.extend(current_files)
        
        # 去重并按优先级排序（缓存目录优先）
        unique_paths = []
        seen = set()
        for path in possible_paths:
            if path not in seen and os.path.exists(path):
                unique_paths.append(path)
                seen.add(path)
        
        # 尝试每个arkpass文件
        for arkpass_path in unique_paths:
            result = self.auto_login_with_arkpass(arkpass_path)
            if isinstance(result, tuple):
                success, error_msg = result
                if success:
                    return True
            elif result:
                return True
                
        return self.is_logged_in
        
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