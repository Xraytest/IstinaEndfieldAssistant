from Crypto.Cipher import AES
import os
import json

class SecureTransport:
    def __init__(self, key_hex_512):
        # 将 512 位 (128字符) 十六进制密钥转为二进制
        full_key = bytes.fromhex(key_hex_512)
        # 前 32 字节 (256位) 作为 AES 密钥
        self.aes_key = full_key[:32]
        # 后 32 字节作为关联数据 (AAD) 用于 GCM 校验
        self.aad = full_key[32:]

    def encrypt(self, data_dict):
        """加密字典并返回字节流"""
        plaintext = json.dumps(data_dict).encode('utf-8')
        nonce = os.urandom(12)  # GCM 推荐 12 字节 Nonce
        cipher = AES.new(self.aes_key, AES.MODE_GCM, nonce=nonce)
        cipher.update(self.aad)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)
        # 传输结构: Nonce(12) + Tag(16) + Ciphertext
        return nonce + tag + ciphertext

    def decrypt(self, raw_bytes):
        """解密字节流并返回字典"""
        # 1. 数据包长度基础验证：最小长度应为 12字节 Nonce + 16字节 Tag = 28字节
        if len(raw_bytes) < 28:
            raise PermissionError(f"数据包长度不足: 实际收到 {len(raw_bytes)} 字节，最小要求 28 字节")

        try:
            # 2. 严格按照协议格式切片数据包: [Nonce(12)] + [Tag(16)] + [Ciphertext(剩余)]
            nonce = raw_bytes[:12]
            tag = raw_bytes[12:28]
            ciphertext = raw_bytes[28:]  # 修复关键点：密文长度不再硬编码16字节，而是动态适应实际数据

            # 3. 调试日志输出：打印切片详情（生产环境可移除或降级为debug级别）
            print(f"[解密调试] 数据包总长度: {len(raw_bytes)}, Nonce长度: {len(nonce)}, Tag长度: {len(tag)}, 密文长度: {len(ciphertext)}")

            # 4. 数据完整性检查：Nonce 和 Tag 必须为固定长度
            if len(nonce) != 12:
                raise PermissionError(f" nonce 长度异常: 期望 12 字节，实际 {len(nonce)} 字节")
            if len(tag) != 16:
                raise PermissionError(f" tag 长度异常: 期望 16 字节，实际 {len(tag)} 字节")

            # 5. 打印AAD信息用于调试
            if hasattr(self, 'aad'):
                print(f"[解密调试] 当前AAD (hex): {self.aad.hex()}")
                print(f"[解密调试] 当前AES密钥 (前16字节): {self.aes_key[:16].hex()}")

            # 6. 初始化 AES-GCM 解密器并使用AAD 进行认证
            cipher = AES.new(self.aes_key, AES.MODE_GCM, nonce=nonce)
            cipher.update(self.aad)

            # 6. 执行解密和认证标签验证
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)

            # 7. 反序列化 JSON 数据
            try:
                message_dict = json.loads(plaintext.decode('utf-8'))
            except json.JSONDecodeError as json_err:
                raise PermissionError(f"JSON 反序列化失败: {json_err}")

            return message_dict

        except PermissionError:
            # 直接抛出我们自定义的权限错误，保留原始错误信息
            raise
        except Exception as e:
            # 捕获并包装所有其他异常，防止底层错误细节泄露
            print(f"[解密调试] 底层异常类型: {type(e).__name__}")
            print(f"[解密调试] 底层异常信息: {str(e)}")
            raise PermissionError(f"解密过程中发生异常: {type(e).__name__}")