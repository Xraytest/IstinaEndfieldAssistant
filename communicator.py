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
from logger import get_logger, LogCategory

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
        # 初始化日志（必须在创建加密器之前）
        self.logger = get_logger()
        
        self.host = host
        self.port = port
        self.timeout = timeout
        
        # 协议版本和魔数（用于识别协议）
        self.protocol_magic = b"ARKS"
        self.protocol_version = 1
        
        # 初始化加密器
        self.password = password
        self.cipher = self._create_cipher(password)
        
        self.logger.info(LogCategory.COMMUNICATION, "通信器初始化完成",
                        server=f"{host}:{port}", timeout_seconds=timeout)
        
    def _create_cipher(self, password: str) -> Fernet:
        """创建加密器"""
        self.logger.debug(LogCategory.COMMUNICATION, "创建加密器")
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
        self.logger.debug(LogCategory.COMMUNICATION, "打包消息",
                        data_size=len(data), protocol_version=self.protocol_version)
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
            self.logger.warning(LogCategory.COMMUNICATION, "消息数据长度不足",
                              received_len=len(data), required_len=9)
            return None
            
        magic = data[:4]
        if magic != self.protocol_magic:
            self.logger.warning(LogCategory.COMMUNICATION, "消息魔数不匹配",
                              received_magic=magic.hex(), expected_magic=self.protocol_magic.hex())
            return None
            
        version = struct.unpack('B', data[4:5])[0]
        if version != self.protocol_version:
            self.logger.warning(LogCategory.COMMUNICATION, "协议版本不匹配",
                              received_version=version, expected_version=self.protocol_version)
            return None
            
        data_length = struct.unpack('!I', data[5:9])[0]
        if len(data) < 9 + data_length:
            self.logger.warning(LogCategory.COMMUNICATION, "消息数据不完整",
                              received_len=len(data), expected_len=9+data_length)
            return None
            
        original_data = data[9:9 + data_length]
        self.logger.debug(LogCategory.COMMUNICATION, "消息解包完成",
                        data_size=data_length)
        return original_data
    
    def _send_and_receive(self, message_data: bytes) -> Optional[bytes]:
        """发送消息并接收响应"""
        start_time = time.time()
        self.logger.debug(LogCategory.COMMUNICATION, "开始发送消息",
                        server=f"{self.host}:{self.port}", message_size=len(message_data))
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                
                # 连接服务器
                self.logger.debug(LogCategory.COMMUNICATION, "连接服务器",
                                server=f"{self.host}:{self.port}")
                sock.connect((self.host, self.port))
                
                # 发送消息
                self.logger.debug(LogCategory.COMMUNICATION, "发送消息数据")
                sock.sendall(message_data)
                
                # 接收响应头
                header_data = b""
                while len(header_data) < 9:
                    chunk = sock.recv(9 - len(header_data))
                    if not chunk:
                        self.logger.exception(LogCategory.COMMUNICATION, "接收响应头异常",
                                           received_len=len(header_data))
                        return None
                    header_data += chunk
                
                # 解析数据长度
                data_length = struct.unpack('!I', header_data[5:9])[0]
                self.logger.debug(LogCategory.COMMUNICATION, "接收响应头完成",
                                data_size=data_length)
                
                # 接收数据体
                data_buffer = b""
                while len(data_buffer) < data_length:
                    remaining = data_length - len(data_buffer)
                    chunk = sock.recv(min(4096, remaining))
                    if not chunk:
                        self.logger.exception(LogCategory.COMMUNICATION, "接收响应数据异常",
                                           received_len=len(data_buffer), expected_len=data_length)
                        break
                    data_buffer += chunk
                
                if len(data_buffer) != data_length:
                    self.logger.exception(LogCategory.COMMUNICATION, "响应数据不完整",
                                       received_len=len(data_buffer), expected_len=data_length)
                    return None
                    
                full_response = header_data + data_buffer
                duration_ms = (time.time() - start_time) * 1000
                
                self.logger.info(LogCategory.COMMUNICATION, "通信完成",
                               message_size=len(message_data),
                               response_size=len(full_response),
                               duration_ms=round(duration_ms, 3))
                
                self.logger.log_performance("communication", duration_ms,
                                          server=f"{self.host}:{self.port}")
                
                return self._unpack_message(full_response)
                
        except socket.timeout as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.exception(LogCategory.COMMUNICATION, "通信超时",
                               server=f"{self.host}:{self.port}",
                               timeout_seconds=self.timeout,
                               duration_ms=round(duration_ms, 3),
                               exc_info=True)
            return None
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.exception(LogCategory.COMMUNICATION, "通信异常",
                               server=f"{self.host}:{self.port}",
                               exception_type=type(e).__name__,
                               duration_ms=round(duration_ms, 3),
                               exc_info=True)
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
        start_time = time.time()
        self.logger.debug(LogCategory.COMMUNICATION, "准备发送请求", endpoint=endpoint)
        
        try:
            # 准备请求数据
            request_data = {
                'endpoint': endpoint,
                'data': data,
                'timestamp': int(time.time() * 1000)
            }
            
            # 序列化并加密
            json_data = json.dumps(request_data).encode('utf-8')
            json_size = len(json_data)
            self.logger.debug(LogCategory.COMMUNICATION, "序列化请求数据",
                            endpoint=endpoint, json_size=json_size)
            
            encrypted_data = self.cipher.encrypt(json_data)
            encrypted_size = len(encrypted_data)
            self.logger.debug(LogCategory.COMMUNICATION, "加密请求数据",
                            endpoint=endpoint, encrypted_size=encrypted_size)
            
            # 打包并发送
            message = self._pack_message(encrypted_data)
            response_data = self._send_and_receive(message)
            
            if response_data:
                # 解密响应
                decrypted_response = self.cipher.decrypt(response_data)
                response_json = json.loads(decrypted_response.decode('utf-8'))
                
                duration_ms = (time.time() - start_time) * 1000
                self.logger.info(LogCategory.COMMUNICATION, "请求处理完成",
                               endpoint=endpoint,
                               duration_ms=round(duration_ms, 3))
                
                return response_json
            else:
                duration_ms = (time.time() - start_time) * 1000
                self.logger.exception(LogCategory.COMMUNICATION, "请求处理异常",
                                   endpoint=endpoint,
                                   duration_ms=round(duration_ms, 3))
                return None
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.exception(LogCategory.COMMUNICATION, "请求处理异常",
                               endpoint=endpoint,
                               exception_type=type(e).__name__,
                               duration_ms=round(duration_ms, 3),
                               exc_info=True)
            return None