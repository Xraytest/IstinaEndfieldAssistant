#!/usr/bin/env python3
"""
配置供应商API密钥
"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def configure_provider():
    """配置供应商API密钥"""
    if len(sys.argv) != 3:
        print("用法: python configure_provider.py <供应商名称> <API密钥>")
        print("示例: python configure_provider.py BigModel your_api_key_here")
        return

    provider_name = sys.argv[1]
    api_key = sys.argv[2]

    try:
        from cloud.admin_gui import DBManager
        db = DBManager("cloud/system_data.db")

        # 更新API密钥
        if db.update_provider(provider_name, api_key=api_key):
            print(f"[SUCCESS] {provider_name} 的API密钥已更新")

            # 验证配置
            cur = db.conn.cursor()
            cur.execute("""
                SELECT name, endpoint, api_key, model_name, api_format
                FROM providers
                WHERE name=?
            """, (provider_name,))
            result = cur.fetchone()

            if result:
                name, endpoint, key, model, fmt = result
                print(f"\n配置信息:")
                print(f"  名称: {name}")
                print(f"  端点: {endpoint}")
                print(f"  模型: {model}")
                print(f"  格式: {fmt}")
                print(f"  API密钥: {key[:10]}..." if len(key) > 10 else "  API密钥: 已配置")

                print(f"\n下一步:")
                print(f"1. 运行测试: python check_provider.py")
                print(f"2. 或运行完整测试: python test_cloud_api.py")
        else:
            print(f"[ERROR] 更新失败，请检查供应商名称是否正确")

        db.conn.close()

    except Exception as e:
        print(f"[ERROR] 配置失败: {e}")

if __name__ == "__main__":
    configure_provider()