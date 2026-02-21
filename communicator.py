"""
客户端通信模块 - 负责与服务端的TCP通信
"""
import socket
import json
import struct
import time
import hashlib
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

class ClientCommunicator:
    """客户端通信器 - 使用TCP与服务端通信"""
    
    def __init__(self, host: str, port: int, password: str = "default_password", timeout: int = 300):
        """
        初始化客户端通信器
        
        Args:
            host: 服务端主机
            port: 服务端端口
            password: 加密密码
            timeout: 连接和读取超时（秒），默认300秒（5分钟）以支持长时间的LLM处理
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        
        # 协议版本和魔数（用于识别协议）
        self.protocol_magic = b"ARKS"
        self.protocol_version = 1
        
        # 初始化加密器
        self.password = password
        self.cipher = self._create_cipher(password)
        
    def _create_cipher(self, password: str) -> Fernet:
        """创建加密器"""
        salt = hashlib.sha256(password.encode()).digest()[:16]
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    def _pack_message(self, data: bytes) -> bytes:
        """
        打包消息格式：
        [4字节魔数][1字节协议版本][4字节数据长度][数据]
        """
        magic = self.protocol_magic
        version = struct.pack('B', self.protocol_version)
        data_length = struct.pack('!I', len(data))
        
        message = magic + version + data_length + data
        return message
    
    def _unpack_message(self, data: bytes) -> Optional[bytes]:
        """
        解包消息
        返回原始数据或None（如果格式无效）
        """
        if len(data) < 9:
            return None
            
        magic = data[:4]
        if magic != self.protocol_magic:
            return None
            
        version = struct.unpack('B', data[4:5])[0]
        if version != self.protocol_version:
            return None
            
        data_length = struct.unpack('!I', data[5:9])[0]
        if len(data) < 9 + data_length:
            return None
            
        original_data = data[9:9 + data_length]
        return original_data
    
    def _send_and_receive(self, message_data: bytes) -> Optional[bytes]:
        """发送消息并接收响应"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))
                
                # 发送消息
                sock.sendall(message_data)
                
                # 接收响应
                header_data = b""
                while len(header_data) < 9:
                    chunk = sock.recv(9 - len(header_data))
                    if not chunk:
                        return None
                    header_data += chunk
                
                data_length = struct.unpack('!I', header_data[5:9])[0]
                data_buffer = b""
                while len(data_buffer) < data_length:
                    remaining = data_length - len(data_buffer)
                    chunk = sock.recv(min(4096, remaining))
                    if not chunk:
                        break
                    data_buffer += chunk
                
                if len(data_buffer) != data_length:
                    return None
                    
                full_response = header_data + data_buffer
                return self._unpack_message(full_response)
                
        except Exception as e:
            print(f"通信失败: {e}")
            return None
    
    def send_request(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict]:
        """
        发送请求到服务端
        
        Args:
            endpoint: API端点标识
            data: 请求数据
            
        Returns:
            响应数据字典或None
        """
        try:
            # 准备请求数据
            request_data = {
                'endpoint': endpoint,
                'data': data,
                'timestamp': int(time.time() * 1000)
            }
            
            # 序列化并加密
            json_data = json.dumps(request_data).encode('utf-8')
            encrypted_data = self.cipher.encrypt(json_data)
            
            # 打包并发送
            message = self._pack_message(encrypted_data)
            response_data = self._send_and_receive(message)
            
            if response_data:
                # 解密响应
                decrypted_response = self.cipher.decrypt(response_data)
                response_json = json.loads(decrypted_response.decode('utf-8'))
                return response_json
            else:
                return None
                
        except Exception as e:
            print(f"请求处理失败: {e}")
            return None