import socket
import json
import struct
import time
from crypto_tool import SecureTransport

class CloudClient:
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.sock = None
        self.crypto = None
        self.user_id = None

    def connect(self):
        """建立 TCP 连接"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False

    def _send_raw(self, data):
        """发送未加密的原始包 (仅限登录/注册)"""
        payload = json.dumps(data).encode('utf-8')
        self.sock.sendall(struct.pack('>I', len(payload)) + payload)

    def _recv_secure(self, crypto):
        """使用传入的加密器接收包"""
        try:
            header_data = self.sock.recv(4)
            if not header_data:
                print("接收包头失败：连接已关闭")
                return None

            length = struct.unpack('>I', header_data)[0]
            print(f"准备接收 {length} 字节的加密数据")

            data = b''
            while len(data) < length:
                chunk = self.sock.recv(min(4096, length - len(data)))
                if not chunk:
                    print("接收包体失败：连接中断")
                    return None
                data += chunk

            print(f"接收到 {len(data)} 字节，开始解密")
            return crypto.decrypt(data)
        except Exception as e:
            print(f"接收解密失败: {e}")
            return None

    def _send_secure(self, data, crypto):
        """使用加密器发送数据包"""
        payload = crypto.encrypt(data)
        self.sock.sendall(struct.pack('>I', len(payload)) + payload)

    def register(self, user_id):
        """用户注册，返回密钥"""
        if not self.connect():
            return None

        try:
            self._send_raw({'cmd': 'REGISTER', 'user_id': user_id})

            # 接收注册结果（明文）
            header_data = self.sock.recv(4)
            if not header_data:
                print("注册响应接收失败：无数据")
                return None

            length = struct.unpack('>I', header_data)[0]
            data = b''
            while len(data) < length:
                chunk = self.sock.recv(min(4096, length - len(data)))
                if not chunk:
                    print("注册响应接收失败：连接中断")
                    return None
                data += chunk

            response = json.loads(data.decode('utf-8'))
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
        finally:
            self.close()

    def login_with_file(self, filepath):
        """使用 .arkpass 文件登录"""
        if not self.connect():
            return False, "连接失败"

        try:
            # 1. 读取文件内容获取 key
            with open(filepath, 'r') as f:
                uid, key = f.read().strip().split(':')

            # 2. 发送明文登录请求
            self._send_raw({'cmd': 'LOGIN', 'user_id': uid, 'key': key})

            # 3. 登录包发出后，立即预设加密器准备接收加密的回包
            temp_crypto = SecureTransport(key)
            resp = self._recv_secure(temp_crypto)

            if resp and resp['status'] == 'success':
                self.crypto = temp_crypto  # 正式启用加密
                self.user_id = uid
                return True, resp['layer']
            else:
                error_msg = resp.get('msg', '认证失败') if resp else '无响应'
                print(f"登录失败: {error_msg}")
                return False, error_msg
        except Exception as e:
            print(f"登录异常: {e}")
            return False, f"登录异常: {str(e)}"
        finally:
            if not (self.crypto and self.user_id):
                self.close()

    def chat_completion(self, payload):
        """
        发送聊天请求（加密）
        :param payload: 包含 model, messages 等的完整字典
        """
        if not self.crypto or not self.user_id:
            return {'status': 'error', 'msg': '未登录'}

        # 直接发送 payload，不再在此处重新封装，因为 gui.py 已经组装好了
        self._send_secure({'cmd': 'CHAT', 'payload': payload}, self.crypto)

        # 接收响应（加密）
        resp = self._recv_secure(self.crypto)
        return resp

    def get_stats(self):
        """获取用户统计信息"""
        if not self.crypto or not self.user_id:
            return {'status': 'error', 'msg': '未登录'}

        self._send_secure({'cmd': 'STATS'}, self.crypto)

        # 接收响应（加密）
        resp = self._recv_secure(self.crypto)
        return resp

    def close(self):
        """关闭连接"""
        if self.sock:
            self.sock.close()

    def disconnect(self):
        """关闭连接（close的别名）"""
        self.close()