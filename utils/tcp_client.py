import socket
import json
import struct
import time
import requests
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CloudClient:
    def __init__(self, host='0.0.0.0', port=9999):
        self.host = host
        self.port = port
        self.base_url = f"https://{host}:{port}"
        self.user_id = None

    def connect(self):
        """HTTPS连接（总是返回True，因为这里使用HTTP requests）"""
        try:
            # 测试连接
            response = requests.get(f"{self.base_url}/api/health", verify=False, timeout=5)
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
            response = requests.post(
                f"{self.base_url}{endpoint}",
                data=data,
                verify=False,
                timeout=30
            )
            return response.content
        except Exception as e:
            print(f"请求失败: {e}")
            return None

    def _recv_plain(self, response_data):
        """解包未加密的响应"""
        try:
            if not response_data or len(response_data) < 4:
                print("接收响应失败：数据不足")
                return None

            length = int.from_bytes(response_data[:4], 'big')

            # 提取数据体
            buffer = response_data[4:4+length]
            if len(buffer) < length:
                print(f"接收数据不完整: 需要{length}字节，实际{len(buffer)}字节")
                return None

            print(f"接收到 {len(buffer)} 字节")
            return json.loads(buffer.decode('utf-8'))

        except Exception as e:
            print(f"解包过程中发生异常: {e}")
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
            packet = self._send_plain({'cmd': 'REGISTER', 'user_id': user_id})
            response_data = self._send_request('/api/register', packet)

            if not response_data:
                print("注册响应接收失败：无响应")
                return None

            if len(response_data) < 4:
                print("注册响应接收失败：数据不足")
                return None

            length = int.from_bytes(response_data[:4], 'big')
            if len(response_data) - 4 < length:
                print("注册响应接收失败：数据不完整")
                return None

            response = json.loads(response_data[4:4+length].decode('utf-8'))
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

            # 2. 发送登录请求
            packet = self._send_plain({'cmd': 'LOGIN', 'user_id': uid, 'key': key})
            response_data = self._send_request('/api/login', packet)

            if not response_data:
                return False, "登录失败: 无响应"

            # 3. 接收明文响应
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
        发送聊天请求（明文）
        :param payload: 包含 model, messages 等的完整字典
        """
        if not self.user_id:
            return {'status': 'error', 'msg': '未登录'}

        packet = self._send_plain({'cmd': 'CHAT', 'user_id': self.user_id, 'payload': payload})
        response_data = self._send_request('/api/command', packet)

        # 接收明文响应
        resp = self._recv_plain(response_data)
        return resp

    def get_stats(self):
        """获取用户统计信息"""
        if not self.user_id:
            return {'status': 'error', 'msg': '未登录'}

        packet = self._send_plain({'cmd': 'STATS', 'user_id': self.user_id})
        response_data = self._send_request('/api/command', packet)

        # 接收明文响应
        resp = self._recv_plain(response_data)
        return resp

    def close(self):
        """关闭连接（HTTPS无需显式关闭）"""
        pass

    def disconnect(self):
        """关闭连接（close的别名）"""
        self.close()