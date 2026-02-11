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
        nonce = raw_bytes[:12]
        tag = raw_bytes[12:28]
        ciphertext = raw_bytes[28:]
        cipher = AES.new(self.aes_key, AES.MODE_GCM, nonce=nonce)
        cipher.update(self.aad)
        try:
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            return json.loads(plaintext.decode('utf-8'))
        except Exception as e:
            raise PermissionError(f"解密失败: {str(e)}")