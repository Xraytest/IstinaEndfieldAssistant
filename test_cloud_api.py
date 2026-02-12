#!/usr/bin/env python3
"""
测试云服务与供应商通信
"""

import sys
import os
import json
import time
import sqlite3

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_cloud_service():
    """测试云服务API连接"""
    print("=== 测试云服务API ===")

    try:
        # 1. 测试注册
        print("1. 测试用户注册...")
        import requests

        # 云服务地址
        cloud_url = "https://api.r54134544.nyat.app:57460"

        # 注册测试
        register_data = {
            'cmd': 'REGISTER',
            'user_id': 'test_user_' + str(int(time.time()))
        }

        print(f"  发送注册请求到: {cloud_url}/api/register")
        try:
            response = requests.post(f"{cloud_url}/api/register",
                                    json=register_data,
                                    verify=False,
                                    timeout=10)
            print(f"  响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"  注册结果: {result}")

                if result.get('status') == 'success':
                    api_key = result.get('key')
                    print(f"  获得API密钥: {api_key[:20]}...")

                    # 保存在本地
                    with open('test_user.arkpass', 'w') as f:
                        f.write(f"{register_data['user_id']}:{api_key}")
                    print(f"  已保存在 test_user.arkpass")

                    # 2. 测试登录
                    print("\n2. 测试用户登录...")
                    login_data = {
                        'cmd': 'LOGIN',
                        'user_id': register_data['user_id'],
                        'key': api_key
                    }

                    print(f"  发送登录请求到: {cloud_url}/api/login")
                    response = requests.post(f"{cloud_url}/api/login",
                                        json=login_data,
                                        verify=False,
                                        timeout=10)
                    print(f"  响应状态码: {response.status_code}")

                    if response.status_code == 200:
                        result = response.json()
                        print(f"  登录结果: {result}")

                        if result.get('status') == 'success':
                            print(f"  登录成功，层级: {result.get('layer')}")

                            # 3. 测试命令请求
                            print("\n3. 测试命令请求...")

                            # 先添加一个测试供应商
                            test_provider = add_test_provider(cloud_url)

                            command_data = {
                                'cmd': 'CHAT',
                                'user_id': register_data['user_id'],
                                'payload': {
                                    'prompt': '测试消息',
                                    'temperature': 0.7,
                                    'max_tokens': 50
                                }
                            }

                            print(f"  发送测试命令到: {cloud_url}/api/command")
                            response = requests.post(f"{cloud_url}/api/command",
                                                json=command_data,
                                                verify=False,
                                                timeout=30)
                            print(f"  响应状态码: {response.status_code}")
                            print(f"  响应内容: {response.text[:200]}...")

                            if response.status_code == 200:
                                result = response.json()
                                print(f"  结果: {result}")
                                return True
                else:
                    print(f"  注册失败: {result.get('msg')}")
            else:
                print(f"  注册失败: HTTP {response.status_code}")
                print(f"  错误内容: {response.text[:200]}")
        except requests.exceptions.ConnectionError as e:
            print(f"  连接错误: {e}")
        except Exception as e:
            print(f"  异常: {e}")

        return False

    except Exception as e:
        print(f"测试失败: {e}")
        return False

def add_test_provider(cloud_url):
    """添加测试供应商"""
    print("添加本地测试供应商...")

    try:
        from cloud.admin_gui import DBManager

        # 使用云服务API本身作为供应商
        db = DBManager("cloud/system_data.db")

        # 尝试直接使用云服务API路径（如果支持的话）
        test_endpoints = [
            ("OpenAI格式测试", "https://api.openai.com/v1/chat/completions", "openai"),
            ("智谱AI测试", "https://open.bigmodel.cn/api/paas/v4/chat/completions", "z-ai")
        ]

        for name, endpoint, fmt in test_endpoints:
            print(f"  添加供应商: {name} ({fmt}格式)")

            # 对于真实API，我们添加但标记为不可用，因为需要真实密钥
            if db.add_provider(name, endpoint, "Test", 1, "test_key_placeholder", "gpt-3.5-turbo", fmt):
                print(f"    ✓ 供应商 {name} 添加成功（需要配置真实密钥）")
            else:
                print(f"    ✗ 供应商 {name} 添加失败")

        db.conn.close()
        print("供应商配置完成")

    except Exception as e:
        print(f"添加供应商失败: {e}")

def test_database():
    """检查数据库状态"""
    print("\n=== 检查数据库状态 ===")

    try:
        from cloud.admin_gui import DBManager

        db = DBManager("cloud/system_data.db")

        # 检查用户
        cur = db.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        user_count = cur.fetchone()[0]
        print(f"数据库中的用户数量: {user_count}")

        # 检查供应商
        cur.execute("SELECT name, endpoint, api_format FROM providers WHERE is_active=1")
        providers = cur.fetchall()

        print(f"活跃供应商数量: {len(providers)}")
        for name, endpoint, api_format in providers:
            print(f"  - {name} ({api_format}格式): {endpoint}")

        # 如果没有供应商，添加一个测试供应商
        if not providers:
            print("\n添加测试供应商...")
            if db.add_provider("测试供应商", "https://httpbin.org/post", "Free", 1, "test_key", "gpt-3.5-turbo", "openai"):
                print("✓ 测试供应商添加成功")
            else:
                print("✗ 测试供应商添加失败")

        db.conn.close()

    except Exception as e:
        print(f"数据库检查失败: {e}")

def test_direct_provider():
    """直接测试供应商API"""
    print("\n=== 直接测试供应商API ===")

    try:
        # 测试一个公开的API（如果可用）
        test_endpoints = [
            ("HTTPBin", "https://httpbin.org/post", "openai", {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Hello, world!"}],
                "max_tokens": 20
            }),
            ("JSONplaceholder", "https://jsonplaceholder.typicode.com/posts", "openai", {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Hello, world!"}],
                "max_tokens": 20
            })
        ]

        for name, endpoint, fmt, payload in test_endpoints:
            print(f"\n测试{name}...")
            try:
                # 简化的APIClient模拟
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "TestClient/1.0"
                }

                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=10,
                    verify=False
                )

                print(f"  状态码: {response.status_code}")
                print(f"  响应内容: {response.text[:200]}")

                if response.status_code >= 400:
                    print(f"  跳过（状态码 {response.status_code}）")

            except Exception as e:
                print(f"  测试失败: {e}")

        print("\n注意: 以上是公开测试API，仅用于验证连接性")

    except Exception as e:
        print(f"直接测试失败: {e}")

def main():
    """主测试函数"""
    print("开始测试云服务通信...")
    print("="*50)

    # 检查数据库
    test_database()

    # 测试云服务API
    cloud_success = test_cloud_service()

    if not cloud_success:
        print("\n⚠ 云服务连接失败，尝试直接测试供应商API...")
        test_direct_provider()

    # 提供操作提示
    print("\n" + "="*50)
    print("操作提示:")
    print("1. 如果云服务测试失败，请检查:")
    print("   - 云服务地址是否正确")
    print("   - 网络连接是否正常")
    print("   - 防火墙是否阻止连接")
    print("2. 如果需要添加真实供应商，请在管理GUI中:")
    print("   - 连接云服务: https://api.r54134544.nyat.app:57460")
    print("   - 添加供应商: 填写真实的API端点和密钥")
    print("   - 选择API格式: openai 或 z-ai")
    print("3. 查看日志了解详细错误信息")

    return 0 if cloud_success else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)