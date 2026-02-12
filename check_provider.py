#!/usr/bin/env python3
"""
检查供应商配置并指导修复
"""

import sys
import os
import json

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_provider_config():
    """检查供应商配置"""
    print("=== 检查BigModel供应商配置 ===")

    try:
        from cloud.admin_gui import DBManager
        db = DBManager("cloud/system_data.db")

        cur = db.conn.cursor()
        cur.execute("""
            SELECT name, endpoint, api_key, model_name, api_format, tier_requirement, is_active
            FROM providers
            WHERE name='BigModel'
        """)
        result = cur.fetchone()

        if not result:
            print("\n[问题] 未找到BigModel供应商")
            print("正在添加BigModel供应商...")

            # 添加BigModel供应商
            if db.add_provider(
                name="BigModel",
                endpoint="https://open.bigmodel.cn/api/paas/v4/chat/completions",
                tier_req="Free",
                priority=5,
                api_key=None,  # 需要用户填入
                model_name="glm-4.6v-flash",
                api_format="z-ai"
            ):
                print("[OK] BigModel供应商已添加")

                # 重新查询
                cur.execute("""
                    SELECT name, endpoint, api_key, model_name, api_format, tier_requirement, is_active
                    FROM providers
                    WHERE name='BigModel'
                """)
                result = cur.fetchone()
            else:
                print("[ERROR] 添加BigModel供应商失败")
                return False

        name, endpoint, api_key, model_name, api_format, tier, is_active = result

        print(f"\n配置信息:")
        print(f"  名称: {name}")
        print(f"  端点: {endpoint}")
        print(f"  模型: {model_name}")
        print(f"  格式: {api_format}")
        print(f"  等级要求: {tier}")
        print(f"  活跃状态: {'是' if is_active else '否'}")
        print(f"  API密钥: {'已配置' if api_key and api_key.strip() else '未配置'}")

        if not api_key or not api_key.strip():
            print("\n[主要问题] API密钥未配置")
            print("\n解决步骤:")
            print("1. 访问 https://open.bigmodel.cn/")
            print("2. 注册/登录智谱AI平台")
            print("3. 在控制台获取API Key")
            print("4. 运行以下命令配置API密钥:")
            print(f"\n   python configure_provider.py BigModel YOUR_API_KEY")
            return False
        else:
            print("\n[OK] API密钥已配置")
            return True

    except Exception as e:
        print(f"[ERROR] 检查配置失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_request():
    """测试简单请求（不使用特殊字符）"""
    print("\n\n=== 测试简单请求 ===")

    try:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        from cloud.admin_gui import DBManager
        db = DBManager("cloud/system_data.db")

        # 获取配置
        cur = db.conn.cursor()
        cur.execute("""
            SELECT endpoint, api_key, model_name, api_format
            FROM providers
            WHERE name='BigModel' AND is_active=1
        """)
        result = cur.fetchone()
        db.conn.close()

        if not result:
            print("[ERROR] BigModel供应商未配置或未激活")
            return False

        endpoint, api_key, model_name, api_format = result

        # 简单测试请求
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "max_tokens": 10
        }

        print(f"发送测试请求到: {endpoint}")

        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=10,
            verify=False
        )

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                if content:
                    print(f"[SUCCESS] 回复: {content}")
                    return True
                else:
                    print("[WARNING] 回复内容为空")
            else:
                print("[WARNING] 响应格式异常")
        else:
            print(f"[ERROR] 请求失败: {response.status_code}")
            print(f"错误信息: {response.text[:200]}")

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")

    return False

def main():
    """主函数"""
    print("BigModel供应商配置检查工具")
    print("="*50)

    # 1. 检查配置
    config_ok = check_provider_config()

    if config_ok:
        # 2. 测试请求
        test_ok = test_simple_request()

        if test_ok:
            print("\n[SUCCESS] BigModel供应商配置正确且可用")
            print("\n下一步:")
            print("1. 启动管理GUI: python cloud/admin_gui.py")
            print("2. 启动云服务器")
            print("3. 运行完整测试: python test_cloud_api.py")
        else:
            print("\n[WARNING] API测试未通过")
            print("可能原因:")
            print("1. API密钥无效")
            print("2. 账户余额不足")
            print("3. 网络连接问题")
    else:
        print("\n[INFO] 请先配置API密钥")

        # 提供快速配置脚本
        print("\n快速配置方法:")
        print("1. 获取智谱AI API密钥")
        print("2. 运行: python configure_provider.py BigModel YOUR_API_KEY")

if __name__ == "__main__":
    main()