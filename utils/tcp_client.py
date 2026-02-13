import socket
import json
import struct
import time
import requests
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CloudClient:
    def __init__(self, host='api.r54134544.nyat.app', port=57460):
        self.host = host
        self.port = port
        self.base_url = f"https://{host}:{port}"
        self.user_id = None

    def connect(self):
        """HTTPS连接（总是返回True，因为这里使用HTTP requests）"""
        try:
            # 测试连接
            response = requests.get(f"{self.base_url}/api/health", verify=True, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"连接失败: {e}")
            return False

    def _send_raw(self, data):
        """发送未加密的原始包 (仅限登录/注册)"""
        payload = json.dumps(data).encode('utf-8')
        packet = len(payload).to_bytes(4, 'big') + payload
        return packet

    def _send_request(self, endpoint, data):
        """发送HTTP请求"""
        try:
            print(f"发送请求到: {self.base_url}{endpoint}")
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=data,
                verify=True,
                timeout=30
            )
            print(f"响应状态码: {response.status_code}")
            if response.status_code != 200:
                print(f"响应内容: {response.text[:200]}")
            return response.content
        except Exception as e:
            print(f"请求失败: {e}")
            return None

    def _recv_plain(self, response_data):
        """处理HTTP响应"""
        try:
            if not response_data:
                print("接收响应失败：无响应")
                return None

            # 直接解析JSON响应（不处理长度头）
            try:
                response_text = response_data.decode('utf-8')
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}")
                print(f"响应内容: {response_data[:200]}...")
                return None

        except Exception as e:
            print(f"处理响应时发生异常: {e}")
            return None

    def _send_plain(self, data):
        """发送未加密的数据包"""
        payload = json.dumps(data).encode('utf-8')
        packet = len(payload).to_bytes(4, 'big') + payload
        return packet

    def register(self, user_id):
        """用户注册，返回密钥"""
        try:
            # 发送注册请求
            data = {'cmd': 'REGISTER', 'user_id': user_id}
            response_data = self._send_request('/api/register', data)

            if not response_data:
                print("注册响应接收失败：无响应")
                return None

            response = self._recv_plain(response_data)
            if not response:
                print("注册响应解析失败")
                return None

            print(f"注册响应: {response}")

            if response['status'] == 'success':
                key = response['key']
                # 保存为 .arkpass 文件
                with open(f"{user_id}.arkpass", 'w') as f:
                    f.write(f"{user_id}:{key}")
                return key
            else:
                print(f"注册失败: {response.get('msg', '未知错误')}")
                return None
        except Exception as e:
            print(f"注册异常: {e}")
            return None

    def login_with_file(self, filepath):
        """使用 .arkpass 文件登录"""
        try:
            # 1. 读取文件内容获取 key
            with open(filepath, 'r') as f:
                uid, key = f.read().strip().split(':')

            print(f"尝试登录用户: {uid}")

            # 2. 发送登录请求
            data = {'cmd': 'LOGIN', 'user_id': uid, 'key': key}
            response_data = self._send_request('/api/login', data)

            if not response_data:
                return False, "登录失败: 无响应"

            # 3. 处理响应
            resp = self._recv_plain(response_data)

            if resp and resp['status'] == 'success':
                self.user_id = uid
                return True, resp.get('layer', 'cloud')
            else:
                error_msg = resp.get('msg', '认证失败') if resp else '无响应'
                print(f"登录失败: {error_msg}")
                return False, error_msg
        except Exception as e:
            print(f"登录异常: {e}")
            return False, f"登录异常: {str(e)}"

    def chat_completion(self, payload):
        """
        发送聊天请求
        :param payload: 包含 model, messages 等的完整字典
        """
        if not self.user_id:
            return {'status': 'error', 'msg': '未登录'}

        data = {'cmd': 'CHAT', 'user_id': self.user_id, 'payload': payload}

        # 添加自动重试机制
        max_retries = 3
        for attempt in range(max_retries):
            response_data = self._send_request('/api/command', data)

            # 处理响应
            resp = self._recv_plain(response_data)

            if resp and resp.get('status') == 'error':
                error_msg = resp.get('msg', '')
                # 检查是否是请求过多或服务器繁忙的错误
                if any(keyword in error_msg for keyword in ['请求过于频繁', '服务器繁忙', '速率限制中']) and attempt < max_retries - 1:
                    print(f"请求受限，等待0.5秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(0.5)
                    continue

            return resp

        # 所有重试都失败后返回最后一次响应
        return resp

    def get_stats(self):
        """获取用户统计信息"""
        if not self.user_id:
            return {'status': 'error', 'msg': '未登录'}

        data = {'cmd': 'STATS', 'user_id': self.user_id}
        response_data = self._send_request('/api/command', data)

        # 处理响应
        resp = self._recv_plain(response_data)
        return resp

    def close(self):
        """关闭连接（HTTPS无需显式关闭）"""
        pass

    def disconnect(self):
        """关闭连接（close的别名）"""
        self.close()